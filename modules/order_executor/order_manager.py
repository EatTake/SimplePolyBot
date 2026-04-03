"""
订单管理器模块

实现订单执行的核心逻辑：
- 价格验证
- FAK 市场订单创建
- 订单簿深度检查
- 滑点保护
- 订单执行结果处理
- 错误处理
"""

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_DOWN
import time

import structlog

from modules.order_executor.clob_client import ClobClientWrapper, ClobClientError
from modules.order_executor.fee_calculator import FeeCalculator
from shared.config import Config
from shared.risk_manager import RiskManager, RiskCheckResult
from shared.position_tracker import PositionTracker
from shared.constants import (
    ORDER_TYPE_FAK,
    ORDER_SIDE_BUY,
    MIN_ORDER_SIZE,
    MAX_ORDER_SIZE,
)

logger = structlog.get_logger()


class OrderManagerError(Exception):
    """订单管理器异常"""
    pass


class OrderValidation:
    """订单验证结果"""
    
    def __init__(
        self,
        is_valid: bool,
        reason: str = "",
        adjusted_price: Optional[float] = None,
        adjusted_size: Optional[float] = None,
    ):
        self.is_valid = is_valid
        self.reason = reason
        self.adjusted_price = adjusted_price
        self.adjusted_size = adjusted_size


class OrderResult:
    """订单执行结果"""
    
    def __init__(
        self,
        success: bool,
        order_id: Optional[str] = None,
        status: Optional[str] = None,
        filled_size: float = 0.0,
        avg_price: float = 0.0,
        fee: float = 0.0,
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.order_id = order_id
        self.status = status
        self.filled_size = filled_size
        self.avg_price = avg_price
        self.fee = fee
        self.error_message = error_message
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "order_id": self.order_id,
            "status": self.status,
            "filled_size": self.filled_size,
            "avg_price": self.avg_price,
            "fee": self.fee,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class OrderManager:
    """
    订单管理器
    
    负责订单执行的核心逻辑，包括：
    - 价格验证
    - 订单创建和提交
    - 滑点保护
    - 错误处理
    """
    
    def __init__(
        self,
        clob_client: ClobClientWrapper,
        fee_calculator: Optional[FeeCalculator] = None,
        config: Optional[Config] = None,
    ):
        """
        初始化订单管理器
        
        Args:
            clob_client: CLOB 客户端实例
            fee_calculator: 手续费计算器实例
            config: 配置实例
        """
        self.clob_client = clob_client
        self.fee_calculator = fee_calculator or FeeCalculator()
        self.config = config or Config.get_instance()
        
        strategy_config = self.config.get_strategy_config()
        self.max_buy_prices = strategy_config.max_buy_prices
        self.order_sizes = strategy_config.order_sizes
        self.risk_management = strategy_config.risk_management

        self.position_tracker = PositionTracker()
        self.risk_manager = RiskManager(config=self.risk_management, position_tracker=self.position_tracker)

        self._order_history: List[Dict[str, Any]] = []
        
        logger.info("初始化订单管理器")
    
    def validate_price(
        self,
        token_id: str,
        price: float,
        side: str,
        max_buy_price: Optional[float] = None,
    ) -> OrderValidation:
        """
        验证价格是否合理
        
        对于买单：当前买入价 < 最高可买入价格
        对于卖单：当前卖出价 > 最低可卖出价格
        
        Args:
            token_id: 代币 ID
            price: 计划价格
            side: 交易方向
            max_buy_price: 最高可买入价格（可选）
        
        Returns:
            OrderValidation 验证结果
        """
        try:
            if side.upper() == ORDER_SIDE_BUY:
                if max_buy_price is None:
                    max_buy_price = self.max_buy_prices.get("default", 0.95)
                
                if price >= max_buy_price:
                    reason = f"买入价格 {price} 超过最高可买入价格 {max_buy_price}"
                    logger.warning(
                        "价格验证失败",
                        token_id=token_id,
                        price=price,
                        max_buy_price=max_buy_price,
                        reason=reason
                    )
                    return OrderValidation(is_valid=False, reason=reason)
                
                if price <= 0 or price >= 1:
                    reason = f"买入价格 {price} 超出有效范围 (0, 1)"
                    logger.warning("价格验证失败", reason=reason)
                    return OrderValidation(is_valid=False, reason=reason)
            
            logger.debug(
                "价格验证通过",
                token_id=token_id,
                price=price,
                side=side
            )
            
            return OrderValidation(is_valid=True)
            
        except Exception as e:
            logger.error("价格验证异常", error=str(e))
            return OrderValidation(is_valid=False, reason=str(e))
    
    def check_order_book_depth(
        self,
        token_id: str,
        required_size: float,
        price: float,
        side: str,
    ) -> Tuple[bool, float]:
        """
        检查订单簿深度是否足够
        
        Args:
            token_id: 代币 ID
            required_size: 需要的数量
            price: 价格
            side: 交易方向
        
        Returns:
            (是否足够, 可用数量)
        """
        try:
            order_book = self.clob_client.get_order_book(token_id)
            
            if side.upper() == ORDER_SIDE_BUY:
                asks = order_book.get("asks", [])
                available_size = 0.0
                
                for ask in asks:
                    ask_price = float(ask.get("price", 0))
                    ask_size = float(ask.get("size", 0))
                    
                    if ask_price <= price:
                        available_size += ask_size
                
                is_sufficient = available_size >= required_size
                
                logger.debug(
                    "检查订单簿深度（买单）",
                    token_id=token_id,
                    required_size=required_size,
                    available_size=available_size,
                    is_sufficient=is_sufficient
                )
                
                return is_sufficient, available_size
            else:
                bids = order_book.get("bids", [])
                available_size = 0.0
                
                for bid in bids:
                    bid_price = float(bid.get("price", 0))
                    bid_size = float(bid.get("size", 0))
                    
                    if bid_price >= price:
                        available_size += bid_size
                
                is_sufficient = available_size >= required_size
                
                logger.debug(
                    "检查订单簿深度（卖单）",
                    token_id=token_id,
                    required_size=required_size,
                    available_size=available_size,
                    is_sufficient=is_sufficient
                )
                
                return is_sufficient, available_size
                
        except Exception as e:
            logger.error("检查订单簿深度失败", error=str(e))
            return False, 0.0
    
    def calculate_slippage_protected_price(
        self,
        token_id: str,
        side: str,
        max_slippage: float = 0.02,
    ) -> Optional[float]:
        """
        计算滑点保护价格
        
        Args:
            token_id: 代币 ID
            side: 交易方向
            max_slippage: 最大滑点比例（默认 2%）
        
        Returns:
            滑点保护价格
        """
        try:
            order_book = self.clob_client.get_order_book(token_id)
            
            if side.upper() == ORDER_SIDE_BUY:
                asks = order_book.get("asks", [])
                if not asks:
                    logger.warning("订单簿中没有卖单")
                    return None
                
                best_ask = float(asks[0].get("price", 0))
                protected_price = best_ask * (1 + max_slippage)
                
                logger.debug(
                    "计算滑点保护价格（买单）",
                    best_ask=best_ask,
                    max_slippage=max_slippage,
                    protected_price=protected_price
                )
                
                return protected_price
            else:
                bids = order_book.get("bids", [])
                if not bids:
                    logger.warning("订单簿中没有买单")
                    return None
                
                best_bid = float(bids[0].get("price", 0))
                protected_price = best_bid * (1 - max_slippage)
                
                logger.debug(
                    "计算滑点保护价格（卖单）",
                    best_bid=best_bid,
                    max_slippage=max_slippage,
                    protected_price=protected_price
                )
                
                return protected_price
                
        except Exception as e:
            logger.error("计算滑点保护价格失败", error=str(e))
            return None
    
    def adjust_price_to_tick_size(
        self,
        price: float,
        tick_size: str,
        round_down: bool = True,
    ) -> float:
        """
        调整价格以符合 Tick Size
        
        Args:
            price: 原始价格
            tick_size: Tick Size 字符串
            round_down: 是否向下取整
        
        Returns:
            调整后的价格
        """
        try:
            tick_decimal = Decimal(tick_size)
            price_decimal = Decimal(str(price))
            
            if round_down:
                adjusted = (price_decimal / tick_decimal).to_integral_value(rounding=ROUND_DOWN) * tick_decimal
            else:
                adjusted = (price_decimal / tick_decimal).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick_decimal
            
            adjusted_float = float(adjusted)
            
            logger.debug(
                "调整价格到 Tick Size",
                original_price=price,
                tick_size=tick_size,
                adjusted_price=adjusted_float
            )
            
            return adjusted_float
            
        except Exception as e:
            logger.error("调整价格失败", error=str(e))
            return price
    
    def validate_order_size(
        self,
        size: float,
        available_balance: float,
    ) -> OrderValidation:
        """
        验证订单大小
        
        Args:
            size: 计划订单大小
            available_balance: 可用余额
        
        Returns:
            OrderValidation 验证结果
        """
        min_size = self.order_sizes.get("min", MIN_ORDER_SIZE)
        max_size = self.order_sizes.get("max", MAX_ORDER_SIZE)
        
        if size < min_size:
            reason = f"订单大小 {size} 小于最小值 {min_size}"
            logger.warning("订单大小验证失败", reason=reason)
            return OrderValidation(is_valid=False, reason=reason)
        
        if size > max_size:
            adjusted_size = max_size
            reason = f"订单大小 {size} 超过最大值 {max_size}，调整为 {adjusted_size}"
            logger.info("订单大小调整", reason=reason)
            return OrderValidation(
                is_valid=True,
                reason=reason,
                adjusted_size=adjusted_size
            )
        
        if size > available_balance:
            adjusted_size = available_balance
            reason = f"订单大小 {size} 超过可用余额 {available_balance}，调整为 {adjusted_size}"
            logger.info("订单大小调整", reason=reason)
            return OrderValidation(
                is_valid=True,
                reason=reason,
                adjusted_size=adjusted_size
            )
        
        return OrderValidation(is_valid=True)
    
    def execute_buy_order(
        self,
        token_id: str,
        size: float,
        max_price: Optional[float] = None,
        max_slippage: float = 0.02,
        order_type: str = ORDER_TYPE_FAK,
        category: Optional[str] = None,
    ) -> OrderResult:
        """
        执行买入订单
        
        Args:
            token_id: 代币 ID
            size: 订单大小（USDC）
            max_price: 最高买入价格（可选）
            max_slippage: 最大滑点比例
            order_type: 订单类型（默认 FAK）
            category: 市场类型（用于手续费计算）
        
        Returns:
            OrderResult 执行结果
        """
        start_time = time.time()
        
        try:
            logger.info(
                "开始执行买入订单",
                token_id=token_id,
                size=size,
                max_price=max_price,
                order_type=order_type
            )
            
            balance = self.clob_client.get_usdc_balance()

            risk_check = self.risk_manager.check_before_order(
                token_id=token_id,
                side=ORDER_SIDE_BUY,
                price=max_price or self.max_buy_prices.get("default", 0.95),
                size=size,
            )
            if not risk_check.passed:
                logger.warning(
                    "订单被风控拒绝",
                    token_id=token_id,
                    reason=risk_check.reason,
                    details=risk_check.check_details,
                )
                return OrderResult(
                    success=False,
                    error_message=f"Risk check failed: {risk_check.reason}",
                    metadata={"risk_check": risk_check.check_details},
                )

            size_validation = self.validate_order_size(size, balance)
            if not size_validation.is_valid:
                return OrderResult(
                    success=False,
                    error_message=size_validation.reason
                )
            
            actual_size = size_validation.adjusted_size or size
            
            if max_price is None:
                max_price = self.max_buy_prices.get("default", 0.95)
            
            price_validation = self.validate_price(token_id, max_price, ORDER_SIDE_BUY)
            if not price_validation.is_valid:
                return OrderResult(
                    success=False,
                    error_message=price_validation.reason
                )
            
            protected_price = self.calculate_slippage_protected_price(
                token_id,
                ORDER_SIDE_BUY,
                max_slippage
            )
            
            if protected_price is None:
                return OrderResult(
                    success=False,
                    error_message="无法计算滑点保护价格"
                )
            
            final_price = min(protected_price, max_price)
            
            tick_size = self.clob_client.get_tick_size(token_id)
            final_price = self.adjust_price_to_tick_size(final_price, tick_size)
            
            is_sufficient, available_size = self.check_order_book_depth(
                token_id,
                actual_size,
                final_price,
                ORDER_SIDE_BUY
            )
            
            if not is_sufficient:
                logger.warning(
                    "订单簿深度不足",
                    required_size=actual_size,
                    available_size=available_size
                )
            
            response = self.clob_client.create_and_submit_order(
                token_id=token_id,
                price=final_price,
                size=actual_size,
                side=ORDER_SIDE_BUY,
                order_type=order_type
            )
            
            success = response.get("success", False)
            order_id = response.get("orderID", "")
            status = response.get("status", "")
            error_msg = response.get("errorMsg", "")
            
            fee = self.fee_calculator.calculate_taker_fee(
                shares=actual_size,
                price=final_price,
                category=category
            )
            
            result = OrderResult(
                success=success,
                order_id=order_id,
                status=status,
                filled_size=actual_size if success else 0.0,
                avg_price=final_price,
                fee=fee,
                error_message=error_msg,
                metadata={
                    "token_id": token_id,
                    "side": ORDER_SIDE_BUY,
                    "order_type": order_type,
                    "execution_time": time.time() - start_time,
                    "risk_check": risk_check.check_details,
                }
            )
            
            self._record_order(result)
            
            logger.info(
                "买入订单执行完成",
                success=success,
                order_id=order_id,
                status=status,
                filled_size=result.filled_size,
                avg_price=result.avg_price,
                fee=fee
            )
            
            return result
            
        except ClobClientError as e:
            logger.error("CLOB 客户端错误", error=str(e))
            return OrderResult(
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            logger.error("执行买入订单异常", error=str(e))
            return OrderResult(
                success=False,
                error_message=str(e)
            )
    
    def execute_sell_order(
        self,
        token_id: str,
        size: float,
        min_price: Optional[float] = None,
        max_slippage: float = 0.02,
        order_type: str = ORDER_TYPE_FAK,
        category: Optional[str] = None,
    ) -> OrderResult:
        """
        执行卖出订单
        
        Args:
            token_id: 代币 ID
            size: 订单大小（份额数量）
            min_price: 最低卖出价格（可选）
            max_slippage: 最大滑点比例
            order_type: 订单类型（默认 FAK）
            category: 市场类型（用于手续费计算）
        
        Returns:
            OrderResult 执行结果
        """
        start_time = time.time()
        
        try:
            logger.info(
                "开始执行卖出订单",
                token_id=token_id,
                size=size,
                min_price=min_price,
                order_type=order_type
            )
            
            token_balance = self.clob_client.get_token_balance(token_id)

            risk_check = self.risk_manager.check_before_order(
                token_id=token_id,
                side="SELL",
                price=min_price or 0.01,
                size=size,
            )
            if not risk_check.passed:
                logger.warning(
                    "卖单被风控拒绝",
                    token_id=token_id,
                    reason=risk_check.reason,
                    details=risk_check.check_details,
                )
                return OrderResult(
                    success=False,
                    error_message=f"Risk check failed: {risk_check.reason}",
                    metadata={"risk_check": risk_check.check_details},
                )

            if token_balance < size:
                error_msg = f"代币余额不足：需要 {size}，可用 {token_balance}"
                logger.warning(error_msg)
                return OrderResult(
                    success=False,
                    error_message=error_msg
                )
            
            if min_price is None:
                min_price = 0.01
            
            protected_price = self.calculate_slippage_protected_price(
                token_id,
                "SELL",
                max_slippage
            )
            
            if protected_price is None:
                return OrderResult(
                    success=False,
                    error_message="无法计算滑点保护价格"
                )
            
            final_price = max(protected_price, min_price)
            
            tick_size = self.clob_client.get_tick_size(token_id)
            final_price = self.adjust_price_to_tick_size(final_price, tick_size, round_down=False)
            
            response = self.clob_client.create_and_submit_order(
                token_id=token_id,
                price=final_price,
                size=size,
                side="SELL",
                order_type=order_type
            )
            
            success = response.get("success", False)
            order_id = response.get("orderID", "")
            status = response.get("status", "")
            error_msg = response.get("errorMsg", "")
            
            fee = self.fee_calculator.calculate_taker_fee(
                shares=size,
                price=final_price,
                category=category
            )
            
            result = OrderResult(
                success=success,
                order_id=order_id,
                status=status,
                filled_size=size if success else 0.0,
                avg_price=final_price,
                fee=fee,
                error_message=error_msg,
                metadata={
                    "token_id": token_id,
                    "side": "SELL",
                    "order_type": order_type,
                    "execution_time": time.time() - start_time,
                    "risk_check": risk_check.check_details,
                }
            )
            
            self._record_order(result)
            
            logger.info(
                "卖出订单执行完成",
                success=success,
                order_id=order_id,
                status=status,
                filled_size=result.filled_size,
                avg_price=result.avg_price,
                fee=fee
            )
            
            return result
            
        except ClobClientError as e:
            logger.error("CLOB 客户端错误", error=str(e))
            return OrderResult(
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            logger.error("执行卖出订单异常", error=str(e))
            return OrderResult(
                success=False,
                error_message=str(e)
            )
    
    def _record_order(self, result: OrderResult) -> None:
        """
        记录订单到历史
        
        Args:
            result: 订单执行结果
        """
        record = {
            "timestamp": time.time(),
            "result": result.to_dict()
        }
        
        self._order_history.append(record)
        
        max_history = 1000
        if len(self._order_history) > max_history:
            self._order_history = self._order_history[-max_history:]
    
    def get_order_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取订单历史
        
        Args:
            limit: 返回数量限制
        
        Returns:
            订单历史列表
        """
        return self._order_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取订单统计信息
        
        Returns:
            统计信息字典
        """
        if not self._order_history:
            return {
                "total_orders": 0,
                "successful_orders": 0,
                "failed_orders": 0,
                "total_volume": 0.0,
                "total_fees": 0.0,
                "risk_status": self.risk_manager.get_risk_status(),
            }
        
        total = len(self._order_history)
        successful = sum(1 for r in self._order_history if r["result"]["success"])
        failed = total - successful
        
        total_volume = sum(
            r["result"]["filled_size"] * r["result"]["avg_price"]
            for r in self._order_history
            if r["result"]["success"]
        )
        
        total_fees = sum(
            r["result"]["fee"]
            for r in self._order_history
            if r["result"]["success"]
        )
        
        return {
            "total_orders": total,
            "successful_orders": successful,
            "failed_orders": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "total_volume": total_volume,
            "total_fees": total_fees,
            "risk_status": self.risk_manager.get_risk_status(),
        }
