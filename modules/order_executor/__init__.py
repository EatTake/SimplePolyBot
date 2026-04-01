"""
订单执行器模块

负责接收交易信号并执行订单
"""

from modules.order_executor.redis_subscriber import RedisSubscriber, TradingSignal
from modules.order_executor.clob_client import ClobClientWrapper, ClobClientError
from modules.order_executor.fee_calculator import FeeCalculator
from modules.order_executor.order_manager import OrderManager, OrderResult, OrderManagerError
from modules.order_executor.main import OrderExecutor

__all__ = [
    "RedisSubscriber",
    "TradingSignal",
    "ClobClientWrapper",
    "ClobClientError",
    "FeeCalculator",
    "OrderManager",
    "OrderResult",
    "OrderManagerError",
    "OrderExecutor",
]
