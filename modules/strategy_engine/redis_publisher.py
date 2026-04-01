"""
Redis 发布者模块

发布交易信号至 Redis trading_signal 频道
支持买入信号和等待信号的发布
"""

import json
import time
from typing import Dict, Any, Optional

from shared.logger import get_logger
from shared.redis_client import RedisClient
from shared.constants import TRADING_SIGNAL_CHANNEL
from modules.strategy_engine.signal_generator import TradingSignal, SignalAction, SignalDirection


logger = get_logger(__name__)


class RedisPublisherError(Exception):
    """Redis 发布者异常"""
    pass


class RedisPublisher:
    """
    Redis 发布者类
    
    负责发布交易信号到 Redis 频道
    """
    
    def __init__(self, redis_client: RedisClient, channel: str = TRADING_SIGNAL_CHANNEL):
        """
        初始化 Redis 发布者
        
        Args:
            redis_client: Redis 客户端实例
            channel: 发布频道，默认为 TRADING_SIGNAL_CHANNEL
        """
        self.redis_client = redis_client
        self.channel = channel
        
        self._published_count = 0
        self._error_count = 0
        
        logger.info("初始化 Redis 发布者", channel=channel)
    
    def publish_signal(self, signal: TradingSignal) -> bool:
        """
        发布交易信号
        
        Args:
            signal: 交易信号对象
        
        Returns:
            发布是否成功
        """
        try:
            message = self._format_signal_message(signal)
            
            success = self.redis_client.publish_message(self.channel, message)
            
            if success:
                self._published_count += 1
                
                logger.info(
                    "交易信号已发布",
                    action=signal.action.value,
                    direction=signal.direction.value if signal.direction else None,
                    max_buy_price=signal.max_buy_price,
                    channel=self.channel
                )
            else:
                self._error_count += 1
                logger.error("交易信号发布失败", signal=signal.to_dict())
            
            return success
            
        except Exception as e:
            self._error_count += 1
            logger.error("发布交易信号异常", error=str(e), signal=signal.to_dict())
            return False
    
    def publish_buy_signal(
        self,
        direction: SignalDirection,
        max_price: float,
        current_price: float,
        confidence: float,
        timestamp: Optional[float] = None,
    ) -> bool:
        """
        发布买入信号
        
        Args:
            direction: 信号方向（UP 或 DOWN）
            max_price: 最大买入价格
            current_price: 当前价格
            confidence: 置信度
            timestamp: 时间戳，默认为当前时间
        
        Returns:
            发布是否成功
        """
        if timestamp is None:
            timestamp = time.time()
        
        message = {
            "action": SignalAction.BUY.value,
            "direction": direction.value,
            "max_price": max_price,
            "current_price": current_price,
            "confidence": confidence,
            "timestamp": timestamp,
        }
        
        return self._publish_message(message)
    
    def publish_wait_signal(self, timestamp: Optional[float] = None) -> bool:
        """
        发布等待信号
        
        Args:
            timestamp: 时间戳，默认为当前时间
        
        Returns:
            发布是否成功
        """
        if timestamp is None:
            timestamp = time.time()
        
        message = {
            "action": SignalAction.WAIT.value,
            "timestamp": timestamp,
        }
        
        return self._publish_message(message)
    
    def publish_custom_message(self, message: Dict[str, Any]) -> bool:
        """
        发布自定义消息
        
        Args:
            message: 消息字典
        
        Returns:
            发布是否成功
        """
        return self._publish_message(message)
    
    def _format_signal_message(self, signal: TradingSignal) -> Dict[str, Any]:
        """
        格式化信号消息
        
        Args:
            signal: 交易信号对象
        
        Returns:
            格式化后的消息字典
        """
        message = {
            "action": signal.action.value,
            "timestamp": signal.timestamp,
        }
        
        if signal.action == SignalAction.BUY and signal.direction:
            message.update({
                "direction": signal.direction.value,
                "max_price": signal.max_buy_price,
                "current_price": signal.current_price,
                "start_price": signal.start_price,
                "price_difference": signal.price_difference,
                "safety_cushion": signal.safety_cushion,
                "slope_k": signal.slope_k,
                "r_squared": signal.r_squared,
                "time_remaining": signal.time_remaining,
                "confidence": signal.confidence,
            })
        
        return message
    
    def _publish_message(self, message: Dict[str, Any]) -> bool:
        """
        发布消息到 Redis 频道
        
        Args:
            message: 消息字典
        
        Returns:
            发布是否成功
        """
        try:
            success = self.redis_client.publish_message(self.channel, message)
            
            if success:
                self._published_count += 1
                logger.debug("消息已发布", channel=self.channel, message=message)
            else:
                self._error_count += 1
                logger.error("消息发布失败", channel=self.channel, message=message)
            
            return success
            
        except Exception as e:
            self._error_count += 1
            logger.error("发布消息异常", error=str(e), channel=self.channel)
            return False
    
    def get_statistics(self) -> Dict[str, int]:
        """
        获取发布统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "published_count": self._published_count,
            "error_count": self._error_count,
            "total_attempts": self._published_count + self._error_count,
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._published_count = 0
        self._error_count = 0
        
        logger.info("Redis 发布者统计信息已重置")


def create_publisher(redis_client: RedisClient, channel: str = TRADING_SIGNAL_CHANNEL) -> RedisPublisher:
    """
    创建 Redis 发布者的便捷函数
    
    Args:
        redis_client: Redis 客户端实例
        channel: 发布频道
    
    Returns:
        RedisPublisher 实例
    """
    return RedisPublisher(redis_client, channel)
