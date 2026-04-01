"""
Redis 订阅者模块

订阅 Redis trading_signal 频道
解析买入信号并传递给订单管理器
"""

import json
import threading
from typing import Any, Callable, Dict, Optional
import time

import structlog

from shared.redis_client import RedisClient, RedisConnectionConfig
from shared.constants import TRADING_SIGNAL_CHANNEL
from shared.config import Config

logger = structlog.get_logger()


class TradingSignal:
    """
    交易信号数据结构
    
    包含交易所需的所有信息
    """
    
    def __init__(
        self,
        signal_id: str,
        token_id: str,
        market_id: str,
        side: str,
        price: Optional[float],
        size: float,
        confidence: float,
        strategy: str,
        timestamp: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化交易信号
        
        Args:
            signal_id: 信号唯一 ID
            token_id: 代币 ID
            market_id: 市场 ID
            side: 交易方向（"BUY" 或 "SELL"）
            price: 价格（可选，市场单可为 None）
            size: 数量
            confidence: 信号置信度（0-1）
            strategy: 策略名称
            timestamp: 时间戳
            metadata: 其他元数据
        """
        self.signal_id = signal_id
        self.token_id = token_id
        self.market_id = market_id
        self.side = side.upper()
        self.price = price
        self.size = size
        self.confidence = confidence
        self.strategy = strategy
        self.timestamp = timestamp
        self.metadata = metadata or {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradingSignal":
        """
        从字典创建交易信号
        
        Args:
            data: 信号数据字典
        
        Returns:
            TradingSignal 实例
        """
        return cls(
            signal_id=data.get("signal_id", ""),
            token_id=data.get("token_id", ""),
            market_id=data.get("market_id", ""),
            side=data.get("side", "BUY"),
            price=data.get("price"),
            size=data.get("size", 0),
            confidence=data.get("confidence", 0.0),
            strategy=data.get("strategy", "unknown"),
            timestamp=data.get("timestamp", int(time.time())),
            metadata=data.get("metadata", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            信号数据字典
        """
        return {
            "signal_id": self.signal_id,
            "token_id": self.token_id,
            "market_id": self.market_id,
            "side": self.side,
            "price": self.price,
            "size": self.size,
            "confidence": self.confidence,
            "strategy": self.strategy,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    def validate(self) -> bool:
        """
        验证信号数据完整性
        
        Returns:
            是否有效
        """
        if not self.signal_id:
            logger.warning("信号缺少 signal_id")
            return False
        
        if not self.token_id:
            logger.warning("信号缺少 token_id", signal_id=self.signal_id)
            return False
        
        if self.side not in ["BUY", "SELL"]:
            logger.warning(
                "信号方向无效",
                signal_id=self.signal_id,
                side=self.side
            )
            return False
        
        if self.size <= 0:
            logger.warning(
                "信号数量无效",
                signal_id=self.signal_id,
                size=self.size
            )
            return False
        
        if not (0 <= self.confidence <= 1):
            logger.warning(
                "信号置信度无效",
                signal_id=self.signal_id,
                confidence=self.confidence
            )
            return False
        
        return True
    
    def __repr__(self) -> str:
        return (
            f"TradingSignal(signal_id={self.signal_id}, "
            f"token_id={self.token_id}, "
            f"side={self.side}, "
            f"price={self.price}, "
            f"size={self.size}, "
            f"confidence={self.confidence})"
        )


class RedisSubscriber:
    """
    Redis 订阅者
    
    订阅 trading_signal 频道，接收并解析交易信号
    """
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        signal_handler: Optional[Callable[[TradingSignal], None]] = None,
        config: Optional[Config] = None,
    ):
        """
        初始化 Redis 订阅者
        
        Args:
            redis_client: Redis 客户端实例
            signal_handler: 信号处理函数
            config: 配置实例
        """
        self.config = config or Config.get_instance()
        
        if redis_client:
            self.redis_client = redis_client
        else:
            redis_config = self._get_redis_config()
            self.redis_client = RedisClient(redis_config)
            self.redis_client.connect()
        
        self.signal_handler = signal_handler
        self._running = False
        self._subscriber_thread: Optional[threading.Thread] = None
        
        logger.info("初始化 Redis 订阅者")
    
    def _get_redis_config(self) -> RedisConnectionConfig:
        """获取 Redis 配置"""
        redis_config = self.config.get_redis_config()
        
        return RedisConnectionConfig(
            host=redis_config.host,
            port=redis_config.port,
            password=redis_config.password if redis_config.password else None,
            db=redis_config.db,
            max_connections=redis_config.max_connections,
            min_connections=redis_config.min_idle_connections,
            connect_timeout=redis_config.connection_timeout,
            read_timeout=redis_config.socket_timeout,
            retry_attempts=redis_config.max_attempts,
            retry_delay=redis_config.retry_delay,
        )
    
    def set_signal_handler(self, handler: Callable[[TradingSignal], None]) -> None:
        """
        设置信号处理函数
        
        Args:
            handler: 信号处理函数
        """
        self.signal_handler = handler
        logger.info("设置信号处理函数")
    
    def _handle_message(self, channel: str, data: Any) -> None:
        """
        处理接收到的消息
        
        Args:
            channel: 频道名称
            data: 消息数据
        """
        try:
            if channel != TRADING_SIGNAL_CHANNEL:
                logger.warning("接收到未知频道的消息", channel=channel)
                return
            
            if isinstance(data, str):
                data = json.loads(data)
            
            signal = TradingSignal.from_dict(data)
            
            if not signal.validate():
                logger.warning("信号验证失败，忽略", signal_data=data)
                return
            
            logger.info(
                "接收到交易信号",
                signal_id=signal.signal_id,
                token_id=signal.token_id,
                side=signal.side,
                price=signal.price,
                size=signal.size,
                confidence=signal.confidence,
                strategy=signal.strategy
            )
            
            if self.signal_handler:
                try:
                    self.signal_handler(signal)
                except Exception as e:
                    logger.error(
                        "信号处理函数执行失败",
                        signal_id=signal.signal_id,
                        error=str(e)
                    )
            else:
                logger.warning("未设置信号处理函数，信号被忽略")
                
        except json.JSONDecodeError as e:
            logger.error("解析信号 JSON 失败", error=str(e), data=data)
        except Exception as e:
            logger.error("处理信号消息失败", error=str(e), data=data)
    
    def start(self) -> None:
        """
        启动订阅者
        
        在独立线程中监听交易信号
        """
        if self._running:
            logger.warning("订阅者已在运行")
            return
        
        self._running = True
        
        self._subscriber_thread = threading.Thread(
            target=self._subscribe_loop,
            daemon=True
        )
        self._subscriber_thread.start()
        
        logger.info("Redis 订阅者已启动")
    
    def _subscribe_loop(self) -> None:
        """订阅循环"""
        while self._running:
            try:
                logger.info(
                    "开始订阅交易信号频道",
                    channel=TRADING_SIGNAL_CHANNEL
                )
                
                self.redis_client.subscribe_channel(
                    channels=TRADING_SIGNAL_CHANNEL,
                    message_handler=self._handle_message
                )
                
            except Exception as e:
                logger.error("订阅循环异常", error=str(e))
                
                if self._running:
                    retry_delay = 5
                    logger.info(f"将在 {retry_delay} 秒后重试订阅")
                    time.sleep(retry_delay)
    
    def stop(self) -> None:
        """
        停止订阅者
        """
        if not self._running:
            return
        
        self._running = False
        
        try:
            self.redis_client.unsubscribe_channel(TRADING_SIGNAL_CHANNEL)
            logger.info("已取消订阅交易信号频道")
        except Exception as e:
            logger.error("取消订阅失败", error=str(e))
        
        if self._subscriber_thread and self._subscriber_thread.is_alive():
            self._subscriber_thread.join(timeout=5)
        
        logger.info("Redis 订阅者已停止")
    
    def is_running(self) -> bool:
        """
        检查订阅者是否在运行
        
        Returns:
            是否在运行
        """
        return self._running
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取订阅者统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "running": self._running,
            "channel": TRADING_SIGNAL_CHANNEL,
            "redis_connected": self.redis_client._is_connected,
        }
