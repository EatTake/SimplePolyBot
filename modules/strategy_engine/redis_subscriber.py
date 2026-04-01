"""
Redis 订阅者模块

订阅 Redis market_data 频道，接收实时价格数据并传递给处理逻辑
支持多线程安全订阅和消息解析
"""

import json
import threading
from typing import Callable, Optional, Dict, Any
import time

from shared.logger import get_logger
from shared.redis_client import RedisClient, RedisConnectionConfig
from shared.constants import MARKET_DATA_CHANNEL


logger = get_logger(__name__)


class RedisSubscriberError(Exception):
    """Redis 订阅者异常"""
    pass


class RedisSubscriber:
    """
    Redis 订阅者类
    
    负责订阅 Redis 频道并接收市场数据消息
    支持异步消息处理和错误恢复
    """
    
    def __init__(
        self,
        redis_client: RedisClient,
        message_handler: Callable[[Dict[str, Any]], None],
        channels: Optional[list[str]] = None,
    ):
        """
        初始化 Redis 订阅者
        
        Args:
            redis_client: Redis 客户端实例
            message_handler: 消息处理函数，接收解析后的消息字典
            channels: 要订阅的频道列表，默认为 [MARKET_DATA_CHANNEL]
        """
        self.redis_client = redis_client
        self.message_handler = message_handler
        self.channels = channels or [MARKET_DATA_CHANNEL]
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logger.info(
            "初始化 Redis 订阅者",
            channels=self.channels
        )
    
    def start(self) -> bool:
        """
        启动订阅者（异步方式）
        
        Returns:
            启动是否成功
        """
        if self._running:
            logger.warn("订阅者已在运行中")
            return True
        
        try:
            self._running = True
            self._stop_event.clear()
            
            self._thread = threading.Thread(
                target=self._subscribe_loop,
                daemon=True,
                name="RedisSubscriberThread"
            )
            self._thread.start()
            
            logger.info("Redis 订阅者已启动")
            return True
            
        except Exception as e:
            logger.error("启动 Redis 订阅者失败", error=str(e))
            self._running = False
            return False
    
    def stop(self) -> None:
        """停止订阅者"""
        if not self._running:
            return
        
        logger.info("正在停止 Redis 订阅者")
        
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info("Redis 订阅者已停止")
    
    def _subscribe_loop(self) -> None:
        """
        订阅循环（在独立线程中运行）
        
        持续监听 Redis 频道并处理消息
        """
        retry_count = 0
        max_retries = 10
        retry_delay = 1
        
        while self._running and retry_count < max_retries:
            try:
                self._subscribe_and_listen()
                retry_count = 0
                retry_delay = 1
                
            except Exception as e:
                retry_count += 1
                logger.error(
                    "订阅循环异常",
                    error=str(e),
                    retry_count=retry_count,
                    max_retries=max_retries
                )
                
                if retry_count < max_retries:
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 16)
                else:
                    logger.error("订阅循环达到最大重试次数，停止订阅")
                    self._running = False
    
    def _subscribe_and_listen(self) -> None:
        """
        订阅频道并监听消息
        
        使用 Redis Pub/Sub 机制接收消息
        """
        pubsub = None
        
        try:
            pubsub = self.redis_client.client.pubsub()
            pubsub.subscribe(*self.channels)
            
            logger.info("已订阅频道", channels=self.channels)
            
            for message in pubsub.listen():
                if not self._running or self._stop_event.is_set():
                    break
                
                if message["type"] == "message":
                    self._handle_message(message)
                    
        except Exception as e:
            logger.error("订阅监听异常", error=str(e))
            raise
            
        finally:
            if pubsub:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except Exception as e:
                    logger.error("关闭 PubSub 连接异常", error=str(e))
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """
        处理接收到的消息
        
        Args:
            message: Redis 消息对象
        """
        try:
            channel = message.get("channel", "")
            data = message.get("data")
            
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError:
                    parsed_data = {"raw": data}
            else:
                parsed_data = data
            
            parsed_data["_channel"] = channel
            parsed_data["_timestamp"] = time.time()
            
            self.message_handler(parsed_data)
            
        except Exception as e:
            logger.error(
                "消息处理异常",
                error=str(e),
                message=str(message)[:200]
            )
    
    def is_running(self) -> bool:
        """
        检查订阅者是否正在运行
        
        Returns:
            是否正在运行
        """
        return self._running and self._thread is not None and self._thread.is_alive()


def create_subscriber(
    redis_config: RedisConnectionConfig,
    message_handler: Callable[[Dict[str, Any]], None],
    channels: Optional[list[str]] = None,
) -> RedisSubscriber:
    """
    创建 Redis 订阅者的便捷函数
    
    Args:
        redis_config: Redis 连接配置
        message_handler: 消息处理函数
        channels: 要订阅的频道列表
    
    Returns:
        RedisSubscriber 实例
    """
    redis_client = RedisClient(redis_config)
    
    if not redis_client.connect():
        raise RedisSubscriberError("无法连接到 Redis 服务器")
    
    return RedisSubscriber(redis_client, message_handler, channels)
