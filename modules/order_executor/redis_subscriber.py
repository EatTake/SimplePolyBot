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
from shared.models import TradingSignal, generate_signal_id

logger = structlog.get_logger()


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
