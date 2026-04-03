from __future__ import annotations

"""
止损止盈监控模块

自动监控持仓状态，在达到止损或止盈条件时执行卖出订单
- 定期检查所有 open positions
- 止损：当前价格 < 成本价 × (1 - 止损比例)
- 止盈：当前价格 > 成本价 × (1 + 止盈比例)
- 触发时执行 FAK 卖单
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StopLossAlert:
    """止损/止盈触发事件记录"""

    token_id: str
    reason: str
    trigger_price: float
    cost_price: float
    quantity: float
    executed_at: float
    order_result: Optional[Dict[str, Any]] = None


@dataclass
class Position:
    """持仓数据结构（与 PositionTracker 返回格式一致）"""

    token_id: str
    current_price: float
    avg_cost: float
    quantity: float
    market_id: str = ""
    side: str = "LONG"


class StopLossMonitor:
    """
    止损止盈监控器
    
    在独立线程中定期检查持仓，当价格触及止损或止盈阈值时自动执行卖出订单
    """

    def __init__(
        self,
        order_manager: Any,
        position_tracker: Any,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化止损止盈监控器
        
        Args:
            order_manager: OrderManager 实例，用于执行卖单
            position_tracker: PositionTracker 实例，用于获取持仓
            config: 配置字典，包含 stop_loss_take_profit 参数
        """
        self.order_manager = order_manager
        self.position_tracker = position_tracker

        if config is not None:
            sltp_config = config.get("stop_loss_take_profit", {})
            self.enabled: bool = sltp_config.get("enabled", True)
            self.stop_loss_pct: float = sltp_config.get("stop_loss_percentage", 0.1)
            self.take_profit_pct: float = sltp_config.get("take_profit_percentage", 0.2)
        else:
            self.enabled = True
            self.stop_loss_pct = 0.1
            self.take_profit_pct = 0.2

        self.check_interval: float = 5.0

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        self._check_count: int = 0
        self._trigger_count: int = 0
        self._stop_loss_count: int = 0
        self._take_profit_count: int = 0
        self._alert_history: List[StopLossAlert] = []

        logger.info(
            "初始化止损止盈监控器",
            enabled=self.enabled,
            stop_loss_pct=self.stop_loss_pct,
            take_profit_pct=self.take_profit_pct,
            check_interval=self.check_interval,
        )

    def start(self) -> None:
        """启动监控循环（独立 daemon 线程）"""
        if self._running:
            logger.warning("止损监控已在运行中")
            return

        if not self.enabled:
            logger.info("止损止盈监控已禁用，不启动")
            return

        self._running = True
        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        logger.info("止损止盈监控已启动", check_interval=self.check_interval)

    def stop(self) -> None:
        """停止监控"""
        if not self._running:
            return

        logger.info("正在停止止损止盈监控...")
        self._running = False
        self._shutdown_event.set()

        if self._thread is not None:
            self._thread.join(timeout=10.0)
            self._thread = None

        logger.info("止损止盈监控已停止")

    def _monitor_loop(self) -> None:
        """主监控循环"""
        logger.info("进入止损止盈监控主循环")

        while self._running and not self._shutdown_event.is_set():
            try:
                if self._shutdown_event.wait(timeout=self.check_interval):
                    break

                self._check_positions()

            except Exception as e:
                logger.error("监控循环异常", error=str(e))

        logger.info("退出止损止盈监控主循环")

    def _check_positions(self) -> None:
        """获取并检查所有持仓"""
        self._check_count += 1

        try:
            open_positions = self.position_tracker.get_open_positions()

            if not open_positions:
                return

            for position in open_positions:
                try:
                    reason = self._check_position(position)

                    if reason is not None:
                        self._execute_stop_order(position, reason)

                except Exception as e:
                    logger.error(
                        "检查持仓异常",
                        token_id=getattr(position, "token_id", "unknown"),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("获取持仓列表失败", error=str(e))

    def _check_position(self, position: Any) -> Optional[str]:
        """
        检查单个持仓是否触发止损或止盈
        
        Args:
            position: 持仓对象，需包含 current_price、avg_cost 属性
        
        Returns:
            触发原因字符串 ("STOP_LOSS" / "TAKE_PROFIT") 或 None
        """
        current_price = getattr(position, "current_price", None)
        avg_cost = getattr(position, "avg_cost", None)

        if current_price is None or avg_cost is None or avg_cost <= 0:
            return None

        stop_loss_threshold = avg_cost * (1 - self.stop_loss_pct)
        take_profit_threshold = avg_cost * (1 + self.take_profit_pct)

        if current_price < stop_loss_threshold:
            return "STOP_LOSS"

        if current_price > take_profit_threshold:
            return "TAKE_PROFIT"

        return None

    def _execute_stop_order(self, position: Any, reason: str) -> Optional[Any]:
        """
        执行止损/止盈卖出订单
        
        Args:
            position: 触发的持仓对象
            reason: 触发原因
        
        Returns:
            OrderResult 或 None
        """
        token_id = getattr(position, "token_id", "")
        quantity = getattr(position, "quantity", 0)
        current_price = getattr(position, "current_price", 0)
        avg_cost = getattr(position, "avg_cost", 0)

        self._trigger_count += 1

        if reason == "STOP_LOSS":
            self._stop_loss_count += 1
        else:
            self._take_profit_count += 1

        logger.warning(
            "触发止损/止盈",
            token_id=token_id,
            reason=reason,
            trigger_price=current_price,
            cost_price=avg_cost,
            quantity=quantity,
        )

        try:
            result = self.order_manager.execute_sell_order(
                token_id=token_id,
                size=quantity,
                order_type="FAK",
            )

            alert = StopLossAlert(
                token_id=token_id,
                reason=reason,
                trigger_price=current_price,
                cost_price=avg_cost,
                quantity=quantity,
                executed_at=time.time(),
                order_result=result.to_dict() if hasattr(result, "to_dict") else None,
            )

            self._alert_history.append(alert)

            max_alerts = 1000
            if len(self._alert_history) > max_alerts:
                self._alert_history = self._alert_history[-max_alerts:]

            logger.info(
                "止损/止盈订单执行完成",
                token_id=token_id,
                reason=reason,
                success=result.success if hasattr(result, "success") else False,
                order_id=result.order_id if hasattr(result, "order_id") else None,
            )

            return result

        except Exception as e:
            logger.error(
                "执行止损/止盈订单失败",
                token_id=token_id,
                reason=reason,
                error=str(e),
            )

            alert = StopLossAlert(
                token_id=token_id,
                reason=reason,
                trigger_price=current_price,
                cost_price=avg_cost,
                quantity=quantity,
                executed_at=time.time(),
                order_result=None,
            )
            self._alert_history.append(alert)

            return None

    def is_running(self) -> bool:
        """返回当前运行状态"""
        return self._running

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            包含检查次数、触发次数等信息的字典
        """
        return {
            "is_running": self._running,
            "enabled": self.enabled,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "check_interval": self.check_interval,
            "check_count": self._check_count,
            "trigger_count": self._trigger_count,
            "stop_loss_count": self._stop_loss_count,
            "take_profit_count": self._take_profit_count,
            "alert_history_size": len(self._alert_history),
        }

    def get_alert_history(self, limit: int = 50) -> List[StopLossAlert]:
        """
        获取触发历史记录
        
        Args:
            limit: 返回记录数量限制
        
        Returns:
            触发事件列表
        """
        return self._alert_history[-limit:]

    def reset_stats(self) -> None:
        """重置统计数据"""
        self._check_count = 0
        self._trigger_count = 0
        self._stop_loss_count = 0
        self._take_profit_count = 0
        self._alert_history.clear()
