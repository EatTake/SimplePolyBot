"""
买入信号生成器模块

实现差额计算、方向判断、信号触发条件判断
支持时间窗口判断（T-100s 至 T-10s）和最大买入价格查表
"""

import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from shared.logger import get_logger
from shared.config import Config
from modules.strategy_engine.safety_cushion import SafetyCushionCalculator, SafetyCushionResult


logger = get_logger(__name__)


class SignalAction(Enum):
    """信号动作类型"""
    BUY = "BUY"
    WAIT = "WAIT"
    HOLD = "HOLD"


class SignalDirection(Enum):
    """信号方向类型"""
    UP = "UP"
    DOWN = "DOWN"


@dataclass
class TradingSignal:
    """
    交易信号
    
    包含完整的交易决策信息
    """
    action: SignalAction
    direction: Optional[SignalDirection]
    current_price: float
    start_price: float
    price_difference: float
    max_buy_price: float
    safety_cushion: float
    slope_k: float
    r_squared: float
    time_remaining: float
    timestamp: float
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            信号字典
        """
        return {
            "action": self.action.value,
            "direction": self.direction.value if self.direction else None,
            "current_price": self.current_price,
            "start_price": self.start_price,
            "price_difference": self.price_difference,
            "max_buy_price": self.max_buy_price,
            "safety_cushion": self.safety_cushion,
            "slope_k": self.slope_k,
            "r_squared": self.r_squared,
            "time_remaining": self.time_remaining,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }


class SignalGenerator:
    """
    买入信号生成器
    
    根据价格差额、趋势方向、安全垫等条件生成交易信号
    """
    
    def __init__(
        self,
        min_time_remaining: float = 10.0,
        max_time_remaining: float = 100.0,
        min_price_difference: float = 0.01,
        min_r_squared: float = 0.5,
        min_confidence: float = 0.6,
    ):
        """
        初始化信号生成器
        
        Args:
            min_time_remaining: 最小剩余时间（秒），默认 10 秒
            max_time_remaining: 最大剩余时间（秒），默认 100 秒
            min_price_difference: 最小价格差额，默认 0.01
            min_r_squared: 最小 R² 值，默认 0.5
            min_confidence: 最小置信度，默认 0.6
        """
        self.min_time_remaining = min_time_remaining
        self.max_time_remaining = max_time_remaining
        self.min_price_difference = min_price_difference
        self.min_r_squared = min_r_squared
        self.min_confidence = min_confidence
        
        config = Config.get_instance()
        try:
            strategy_config = config.get_strategy_config()
            self.max_buy_prices = strategy_config.max_buy_prices
        except Exception:
            self.max_buy_prices = {
                "default": 0.95,
                "high_confidence": 0.98,
                "low_volatility": 0.92,
                "fast_market": 0.90
            }
        
        self.safety_cushion_calculator = SafetyCushionCalculator()
        
        logger.info(
            "初始化信号生成器",
            min_time_remaining=min_time_remaining,
            max_time_remaining=max_time_remaining,
            min_price_difference=min_price_difference
        )
    
    def generate_signal(
        self,
        current_price: float,
        start_price: float,
        slope_k: float,
        r_squared: float,
        time_remaining: float,
    ) -> TradingSignal:
        """
        生成交易信号
        
        Args:
            current_price: 当前价格
            start_price: 周期起始价格
            slope_k: 回归斜率
            r_squared: 决定系数
            time_remaining: 剩余时间（秒）
        
        Returns:
            交易信号
        """
        timestamp = time.time()
        
        price_difference = self.calculate_price_difference(current_price, start_price)
        
        direction = self.determine_direction(current_price - start_price)
        
        safety_cushion_result = self.safety_cushion_calculator.calculate(
            slope_k, time_remaining
        )
        
        max_buy_price = self.calculate_max_buy_price(
            current_price, safety_cushion_result.total_cushion
        )
        
        confidence = self.calculate_confidence(r_squared, abs(slope_k), price_difference)
        
        action = self.determine_action(
            price_difference=price_difference,
            time_remaining=time_remaining,
            r_squared=r_squared,
            confidence=confidence,
            max_buy_price=max_buy_price,
        )
        
        signal = TradingSignal(
            action=action,
            direction=direction if action == SignalAction.BUY else None,
            current_price=current_price,
            start_price=start_price,
            price_difference=price_difference,
            max_buy_price=max_buy_price,
            safety_cushion=safety_cushion_result.total_cushion,
            slope_k=slope_k,
            r_squared=r_squared,
            time_remaining=time_remaining,
            timestamp=timestamp,
            confidence=confidence,
        )
        
        logger.info(
            "生成交易信号",
            action=action.value,
            direction=direction.value if direction else None,
            price_difference=price_difference,
            time_remaining=time_remaining,
            confidence=confidence
        )
        
        return signal
    
    def calculate_price_difference(
        self,
        current_price: float,
        start_price: float,
    ) -> float:
        """
        计算价格差额
        
        Args:
            current_price: 当前价格
            start_price: 起始价格
        
        Returns:
            价格差额（绝对值）
        """
        difference = abs(current_price - start_price)
        
        logger.debug(
            "计算价格差额",
            current_price=current_price,
            start_price=start_price,
            difference=difference
        )
        
        return difference
    
    def determine_direction(self, price_difference: float) -> Optional[SignalDirection]:
        """
        判断价格方向
        
        Args:
            price_difference: 价格差额（可正可负）
        
        Returns:
            价格方向（UP 或 DOWN），如果差额为0则返回 None
        """
        if price_difference > 0:
            return SignalDirection.UP
        elif price_difference < 0:
            return SignalDirection.DOWN
        else:
            return None
    
    def determine_action(
        self,
        price_difference: float,
        time_remaining: float,
        r_squared: float,
        confidence: float,
        max_buy_price: float,
    ) -> SignalAction:
        """
        判断信号动作
        
        Args:
            price_difference: 价格差额
            time_remaining: 剩余时间
            r_squared: R² 值
            confidence: 置信度
            max_buy_price: 最大买入价格
        
        Returns:
            信号动作
        """
        if not self.is_in_time_window(time_remaining):
            logger.debug(
                "不在时间窗口内",
                time_remaining=time_remaining,
                min_time=self.min_time_remaining,
                max_time=self.max_time_remaining
            )
            return SignalAction.WAIT
        
        if price_difference < self.min_price_difference:
            logger.debug(
                "价格差额不足",
                price_difference=price_difference,
                min_difference=self.min_price_difference
            )
            return SignalAction.WAIT
        
        if r_squared < self.min_r_squared:
            logger.debug(
                "R² 值不足",
                r_squared=r_squared,
                min_r_squared=self.min_r_squared
            )
            return SignalAction.WAIT
        
        if confidence < self.min_confidence:
            logger.debug(
                "置信度不足",
                confidence=confidence,
                min_confidence=self.min_confidence
            )
            return SignalAction.WAIT
        
        if max_buy_price > self.get_max_buy_price_limit(confidence):
            logger.debug(
                "最大买入价格超限",
                max_buy_price=max_buy_price,
                limit=self.get_max_buy_price_limit(confidence)
            )
            return SignalAction.WAIT
        
        return SignalAction.BUY
    
    def is_in_time_window(self, time_remaining: float) -> bool:
        """
        检查是否在有效时间窗口内
        
        Args:
            time_remaining: 剩余时间（秒）
        
        Returns:
            是否在时间窗口内
        """
        return self.min_time_remaining <= time_remaining <= self.max_time_remaining
    
    def calculate_max_buy_price(
        self,
        current_price: float,
        safety_cushion: float,
    ) -> float:
        """
        计算最大买入价格
        
        Args:
            current_price: 当前价格
            safety_cushion: 安全垫
        
        Returns:
            最大买入价格
        """
        max_price = current_price - safety_cushion
        
        max_price = max(0.01, min(0.99, max_price))
        
        return max_price
    
    def get_max_buy_price_limit(self, confidence: float) -> float:
        """
        根据置信度获取最大买入价格限制
        
        Args:
            confidence: 置信度
        
        Returns:
            最大买入价格限制
        """
        if confidence >= 0.8:
            return self.max_buy_prices.get("high_confidence", 0.98)
        elif confidence >= 0.6:
            return self.max_buy_prices.get("default", 0.95)
        else:
            return self.max_buy_prices.get("fast_market", 0.90)
    
    def calculate_confidence(
        self,
        r_squared: float,
        abs_slope: float,
        price_difference: float,
    ) -> float:
        """
        计算信号置信度
        
        综合考虑 R²、斜率和价格差额
        
        Args:
            r_squared: 决定系数
            abs_slope: 斜率绝对值
            price_difference: 价格差额
        
        Returns:
            置信度（0-1）
        """
        r_squared_weight = 0.5
        slope_weight = 0.3
        difference_weight = 0.2
        
        normalized_slope = min(abs_slope * 1000, 1.0)
        
        normalized_difference = min(price_difference * 10, 1.0)
        
        confidence = (
            r_squared * r_squared_weight +
            normalized_slope * slope_weight +
            normalized_difference * difference_weight
        )
        
        return min(1.0, max(0.0, confidence))


def generate_trading_signal(
    current_price: float,
    start_price: float,
    slope_k: float,
    r_squared: float,
    time_remaining: float,
) -> TradingSignal:
    """
    生成交易信号的便捷函数
    
    Args:
        current_price: 当前价格
        start_price: 起始价格
        slope_k: 回归斜率
        r_squared: 决定系数
        time_remaining: 剩余时间
    
    Returns:
        交易信号
    """
    generator = SignalGenerator()
    return generator.generate_signal(
        current_price, start_price, slope_k, r_squared, time_remaining
    )
