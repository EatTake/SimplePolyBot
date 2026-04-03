from __future__ import annotations

"""
风控管理器模块

实现交易前的风险检查：
- 单仓位限制检查
- 总敞口限制检查
- 日亏损限额检查
- 余额保留检查
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from shared.logger import get_logger
from shared.config import Config


logger = get_logger(__name__)


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    reason: str
    check_details: Dict[str, Any] = field(default_factory=dict)


class RiskManager:
    """
    风控管理器
    
    负责在订单执行前进行风险检查，确保交易符合预设的风控规则。
    
    检查项包括：
    1. 单仓位限制：单个市场的持仓不超过 max_position_size
    2. 总敞口限制：所有市场总持仓不超过 max_total_exposure
    3. 日亏损限额：当日累计亏损不超过 max_daily_loss
    4. 余额保留：预估剩余余额不低于 min_balance
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        position_tracker: Optional[Any] = None,
    ):
        """
        初始化风控管理器
        
        参数:
            config: 风控配置字典，如果为 None 则从 Config 加载
            position_tracker: 持仓追踪器，用于获取当前持仓和日盈亏信息
        """
        if config is None:
            try:
                strategy_config = Config().get_strategy_config()
                config = strategy_config.risk_management
            except Exception:
                config = {}
        
        self.max_position_size: float = float(config.get("max_position_size", 5000.0))
        self.max_total_exposure: float = float(config.get("max_total_exposure", 20000.0))
        self.max_daily_loss: float = float(config.get("max_daily_loss", 500.0))
        self.max_drawdown: float = float(config.get("max_drawdown", 0.15))
        self.min_balance: float = float(config.get("min_balance", 100.0))
        
        self.position_tracker = position_tracker
        
        self._daily_pnl: float = 0.0
    
    def check_before_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
    ) -> RiskCheckResult:
        """
        下单前风控检查
        
        参数:
            token_id: 代币 ID
            side: 买卖方向（BUY/SELL）
            price: 订单价格
            size: 订单数量
            
        返回:
            RiskCheckResult: 包含检查结果和详细信息
        """
        order_value = price * size
        check_details: Dict[str, Any] = {
            "token_id": token_id,
            "side": side,
            "price": price,
            "size": size,
            "order_value": order_value,
        }
        
        current_position = 0.0
        total_exposure = 0.0
        daily_pnl = 0.0
        current_balance = 0.0
        balance_available = False
        
        if self.position_tracker is not None:
            try:
                if hasattr(self.position_tracker, 'get_position'):
                    current_position = self.position_tracker.get_position(token_id)
                elif hasattr(self.position_tracker, 'get_positions'):
                    positions = self.position_tracker.get_positions()
                    current_position = positions.get(token_id, 0.0)
                
                if hasattr(self.position_tracker, 'get_total_exposure'):
                    total_exposure = self.position_tracker.get_total_exposure()
                elif hasattr(self.position_tracker, 'get_positions'):
                    positions = self.position_tracker.get_positions()
                    total_exposure = sum(positions.values())
                
                if hasattr(self.position_tracker, 'get_daily_pnl'):
                    daily_pnl = self.position_tracker.get_daily_pnl()
                
                if hasattr(self.position_tracker, 'get_balance'):
                    current_balance = self.position_tracker.get_balance()
                    balance_available = True
            except Exception as e:
                logger.warning(
                    "获取持仓信息失败，跳过部分检查",
                    error=str(e),
                    token_id=token_id,
                )
        
        check_details["current_position"] = current_position
        check_details["total_exposure"] = total_exposure
        check_details["daily_pnl"] = daily_pnl
        check_details["current_balance"] = current_balance
        
        is_buy = side.upper() == "BUY"
        
        new_position = current_position + order_value if is_buy else current_position
        new_total_exposure = total_exposure + order_value if is_buy else total_exposure
        estimated_remaining = current_balance - order_value if is_buy else current_balance
        
        check_details["new_position"] = new_position
        check_details["new_total_exposure"] = new_total_exposure
        check_details["estimated_remaining"] = estimated_remaining
        
        if is_buy and new_position > self.max_position_size:
            return RiskCheckResult(
                passed=False,
                reason=f"单仓位超限: 当前 {current_position:.2f} + 订单 {order_value:.2f} = {new_position:.2f} > 限制 {self.max_position_size:.2f}",
                check_details=check_details,
            )
        
        if is_buy and new_total_exposure > self.max_total_exposure:
            return RiskCheckResult(
                passed=False,
                reason=f"总敞口超限: 当前 {total_exposure:.2f} + 订单 {order_value:.2f} = {new_total_exposure:.2f} > 限制 {self.max_total_exposure:.2f}",
                check_details=check_details,
            )
        
        effective_daily_pnl = daily_pnl + self._daily_pnl
        if effective_daily_pnl < -self.max_daily_loss:
            return RiskCheckResult(
                passed=False,
                reason=f"日亏损超限: 当日累计亏损 {abs(effective_daily_pnl):.2f} > 限制 {self.max_daily_loss:.2f}",
                check_details={**check_details, "effective_daily_pnl": effective_daily_pnl},
            )
        
        if is_buy and balance_available and estimated_remaining < self.min_balance:
            return RiskCheckResult(
                passed=False,
                reason=f"余额不足: 预估剩余 {estimated_remaining:.2f} < 最低要求 {self.min_balance:.2f}",
                check_details=check_details,
            )
        
        logger.info(
            "风控检查通过",
            token_id=token_id,
            side=side,
            order_value=order_value,
        )
        
        return RiskCheckResult(
            passed=True,
            reason="所有风控检查通过",
            check_details=check_details,
        )
    
    def update_daily_pnl(self, pnl: float) -> None:
        """
        更新日内盈亏记录
        
        参数:
            pnl: 盈亏金额（正数为盈利，负数为亏损）
        """
        self._daily_pnl += pnl
        logger.debug(
            "更新日盈亏",
            pnl=pnl,
            cumulative=self._daily_pnl,
        )
    
    def reset_daily_stats(self) -> None:
        """重置每日统计（可在每日 UTC 0 点调用）"""
        old_pnl = self._daily_pnl
        self._daily_pnl = 0.0
        logger.info(
            "重置日统计数据",
            previous_daily_pnl=old_pnl,
        )
    
    def get_risk_status(self) -> Dict[str, Any]:
        """
        返回当前风控状态快照
        
        返回:
            包含风控参数和当前状态的字典
        """
        status = {
            "risk_parameters": {
                "max_position_size": self.max_position_size,
                "max_total_exposure": self.max_total_exposure,
                "max_daily_loss": self.max_daily_loss,
                "max_drawdown": self.max_drawdown,
                "min_balance": self.min_balance,
            },
            "current_state": {
                "daily_pnl": self._daily_pnl,
                "position_tracker_available": self.position_tracker is not None,
            },
        }
        
        if self.position_tracker is not None:
            try:
                if hasattr(self.position_tracker, 'get_positions'):
                    positions = self.position_tracker.get_positions()
                    status["current_state"]["positions"] = positions
                    status["current_state"]["total_exposure"] = sum(positions.values())
                
                if hasattr(self.position_tracker, 'get_balance'):
                    status["current_state"]["balance"] = self.position_tracker.get_balance()
                
                if hasattr(self.position_tracker, 'get_daily_pnl'):
                    status["current_state"]["tracker_daily_pnl"] = self.position_tracker.get_daily_pnl()
            except Exception as e:
                logger.warning("获取状态信息失败", error=str(e))
        
        return status
