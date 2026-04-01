"""
策略引擎模块

实现完整的策略分析流程，包括：
- Redis 订阅者：订阅市场数据
- 价格队列管理：180 秒滚动队列
- OLS 线性回归：价格趋势分析
- 动态安全垫计算：风险控制
- 买入信号生成器：交易信号生成
- 市场生命周期管理：状态机
- Redis 发布者：发布交易信号
"""

from modules.strategy_engine.redis_subscriber import RedisSubscriber, create_subscriber
from modules.strategy_engine.price_queue import PriceQueue, PricePoint
from modules.strategy_engine.ols_regression import OLSRegression, RegressionResult, perform_regression
from modules.strategy_engine.safety_cushion import (
    SafetyCushionCalculator,
    SafetyCushionResult,
    calculate_safety_cushion,
)
from modules.strategy_engine.signal_generator import (
    SignalGenerator,
    TradingSignal,
    SignalAction,
    SignalDirection,
    generate_trading_signal,
)
from modules.strategy_engine.market_lifecycle import (
    MarketLifecycleManager,
    MarketCycle,
    MarketPhase,
    get_market_cycle,
)
from modules.strategy_engine.redis_publisher import RedisPublisher, create_publisher
from modules.strategy_engine.main import StrategyEngine


__all__ = [
    "RedisSubscriber",
    "create_subscriber",
    "PriceQueue",
    "PricePoint",
    "OLSRegression",
    "RegressionResult",
    "perform_regression",
    "SafetyCushionCalculator",
    "SafetyCushionResult",
    "calculate_safety_cushion",
    "SignalGenerator",
    "TradingSignal",
    "SignalAction",
    "SignalDirection",
    "generate_trading_signal",
    "MarketLifecycleManager",
    "MarketCycle",
    "MarketPhase",
    "get_market_cycle",
    "RedisPublisher",
    "create_publisher",
    "StrategyEngine",
]
