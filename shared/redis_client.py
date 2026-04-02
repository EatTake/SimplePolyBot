"""
Redis 客户端封装模块
提供 Redis 连接、Pub/Sub、缓存等功能
用于 Polymarket 量化交易系统
"""

import asyncio
import json
import time
from typing import Any, Callable, Dict, List, Optional, Union
import redis
from redis import Redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
import structlog

logger = structlog.get_logger()


class AdaptiveConnectionPool:
    """
    自适应连接池管理器
    根据系统负载动态调整连接池大小，支持扩容和缩容操作
    
    扩容策略：当负载超过高阈值时，连接池大小翻倍（不超过最大值）
    缩容策略：当负载低于低阈值时，连接池大小减半（不低于初始值）
    """

    def __init__(
        self,
        initial_size: int = 10,
        max_size: int = 100,
        load_threshold_high: float = 0.8,
        load_threshold_low: float = 0.3,
    ):
        self.initial_size = initial_size
        self.max_size = max_size
        self.load_threshold_high = load_threshold_high
        self.load_threshold_low = load_threshold_low
        self.current_size = initial_size
        self.adjustment_history: List[Dict] = []

    def adjust_pool_size(self, current_load: float) -> Dict[str, Any]:
        """
        根据当前负载调整连接池大小
        
        Args:
            current_load: 当前负载 (0.0 - 1.0)
        
        Returns:
            调整结果字典，包含 adjusted、old_size、new_size、direction 等字段
        """
        old_size = self.current_size

        if current_load > self.load_threshold_high and self.current_size < self.max_size:
            new_size = min(int(self.current_size * 2), self.max_size)
            self.current_size = new_size
            record = {
                "timestamp": time.time(),
                "old_size": old_size,
                "new_size": new_size,
                "direction": "expand",
                "load": current_load,
            }
            self.adjustment_history.append(record)
            return {
                "adjusted": True,
                "old_size": old_size,
                "new_size": new_size,
                "direction": "expand",
            }
        elif current_load < self.load_threshold_low and self.current_size > self.initial_size:
            new_size = max(self.current_size // 2, self.initial_size)
            self.current_size = new_size
            record = {
                "timestamp": time.time(),
                "old_size": old_size,
                "new_size": new_size,
                "direction": "shrink",
                "load": current_load,
            }
            self.adjustment_history.append(record)
            return {
                "adjusted": True,
                "old_size": old_size,
                "new_size": new_size,
                "direction": "shrink",
            }

        return {"adjusted": False, "current_size": self.current_size}

    def get_status(self) -> Dict[str, Any]:
        """
        获取当前连接池状态
        
        Returns:
            包含当前状态信息的字典
        """
        return {
            "current_size": self.current_size,
            "max_size": self.max_size,
            "initial_size": self.initial_size,
            "utilization": round(self.current_size / self.max_size, 4),
            "load_threshold_high": self.load_threshold_high,
            "load_threshold_low": self.load_threshold_low,
            "total_adjustments": len(self.adjustment_history),
        }


class RedisClientError(Exception):
    """Redis 客户端异常"""
    pass


class RedisConnectionConfig:
    """Redis 连接配置"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        max_connections: int = 50,
        min_connections: int = 5,
        connect_timeout: int = 5,
        read_timeout: int = 5,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay


class RedisClient:
    """
    Redis 客户端封装类
    提供连接管理、Pub/Sub、缓存等功能
    """
    
    def __init__(self, config: RedisConnectionConfig):
        """
        初始化 Redis 客户端
        
        Args:
            config: Redis 连接配置
        """
        self.config = config
        self._client: Optional[Redis] = None
        self._pubsub = None
        self._is_connected = False
        self._reconnect_count = 0
        self._operation_count = 0
        self.adaptive_pool = AdaptiveConnectionPool(
            initial_size=config.min_connections,
            max_size=config.max_connections,
        )
        
        logger.info(
            "初始化 Redis 客户端",
            host=config.host,
            port=config.port,
            db=config.db
        )
    
    def connect(self) -> bool:
        """
        连接 Redis 服务器
        
        Returns:
            连接是否成功
        """
        try:
            self._client = Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                max_connections=self.config.max_connections,
                socket_connect_timeout=self.config.connect_timeout,
                socket_timeout=self.config.read_timeout,
                decode_responses=True,
                retry_on_timeout=True,
            )
            
            self._is_connected = True
            
            logger.info("Redis 连接成功")
            return True
            
        except RedisError as e:
            logger.error("Redis 连接失败", error=str(e))
            self._is_connected = False
            return False
    
    def disconnect(self) -> None:
        """断开 Redis 连接"""
        if self._pubsub:
            self._pubsub.close()
            self._pubsub = None
        
        if self._client:
            self._client.close()
            self._client = None
        
        self._is_connected = False
        logger.info("Redis 连接已断开")
    
    def reconnect(self) -> bool:
        """
        重连 Redis 服务器
        
        Returns:
            重连是否成功
        """
        self._reconnect_count += 1
        
        logger.warn(
            "尝试重连 Redis",
            attempt=self._reconnect_count,
            max_attempts=self.config.retry_attempts
        )
        
        self.disconnect()
        time.sleep(self.config.retry_delay)
        
        return self.connect()
    
    def ensure_connection(self) -> None:
        """确保 Redis 连接可用"""
        if not self._is_connected or not self._client:
            if not self.connect():
                raise RedisClientError("无法连接到 Redis 服务器")
        
        try:
            self._client.ping()
        except RedisError:
            logger.warn("Redis 连接已断开，尝试重连")
            if not self.reconnect():
                raise RedisClientError("Redis 重连失败")
    
    @property
    def client(self) -> Redis:
        """获取 Redis 客户端实例"""
        self.ensure_connection()
        return self._client
    
    def ping(self) -> bool:
        """
        测试 Redis 连接
        
        Returns:
            连接是否正常
        """
        try:
            return self.client.ping()
        except RedisError as e:
            logger.error("Redis ping 失败", error=str(e))
            return False
    
    def set_value(
        self,
        key: str,
        value: Union[str, int, float, Dict, List],
        expire: Optional[int] = None,
    ) -> bool:
        """
        设置键值对
        
        Args:
            key: 键名
            value: 值（支持字符串、数字、字典、列表）
            expire: 过期时间（秒）
        
        Returns:
            设置是否成功
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = self.client.set(key, value, ex=expire)
            logger.debug("设置键值对", key=key, expire=expire)
            return result
            
        except RedisError as e:
            logger.error("设置键值对失败", key=key, error=str(e))
            return False
    
    def get_value(self, key: str) -> Optional[Union[str, Dict, List]]:
        """
        获取键值
        
        Args:
            key: 键名
        
        Returns:
            键值（自动解析 JSON）
        """
        try:
            value = self.client.get(key)
            
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except RedisError as e:
            logger.error("获取键值失败", key=key, error=str(e))
            return None
    
    def delete_key(self, key: str) -> bool:
        """
        删除键
        
        Args:
            key: 键名
        
        Returns:
            删除是否成功
        """
        try:
            result = self.client.delete(key)
            logger.debug("删除键", key=key, result=result)
            return result > 0
            
        except RedisError as e:
            logger.error("删除键失败", key=key, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键名
        
        Returns:
            键是否存在
        """
        try:
            return self.client.exists(key) > 0
        except RedisError as e:
            logger.error("检查键存在失败", key=key, error=str(e))
            return False
    
    def set_expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 键名
            seconds: 过期时间（秒）
        
        Returns:
            设置是否成功
        """
        try:
            return self.client.expire(key, seconds)
        except RedisError as e:
            logger.error("设置过期时间失败", key=key, error=str(e))
            return False
    
    def publish_message(self, channel: str, message: Union[str, Dict, List]) -> bool:
        """
        发布消息到指定频道
        
        Args:
            channel: 频道名称
            message: 消息内容（支持字符串、字典、列表）
        
        Returns:
            发布是否成功
        """
        try:
            self._operation_count += 1
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            
            result = self.client.publish(channel, message)
            logger.debug("发布消息", channel=channel, subscribers=result)
            return True
            
        except RedisError as e:
            logger.error("发布消息失败", channel=channel, error=str(e))
            return False
    
    def subscribe_channel(
        self,
        channels: Union[str, List[str]],
        message_handler: Callable[[str, Any], None],
    ) -> bool:
        """
        订阅频道并接收消息
        
        Args:
            channels: 频道名称（单个或多个）
            message_handler: 消息处理函数 (channel, message) -> None
        
        Returns:
            订阅是否成功
        """
        try:
            self._operation_count += 1
            if isinstance(channels, str):
                channels = [channels]
            
            if not self._pubsub:
                self._pubsub = self.client.pubsub()
            
            self._pubsub.subscribe(*channels)
            
            logger.info("订阅频道", channels=channels)
            
            for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
                    
                    try:
                        message_handler(channel, data)
                    except Exception as e:
                        logger.error(
                            "消息处理异常",
                            channel=channel,
                            error=str(e)
                        )
            
            return True
            
        except RedisError as e:
            logger.error("订阅频道失败", channels=channels, error=str(e))
            return False
    
    def unsubscribe_channel(self, channels: Union[str, List[str]]) -> bool:
        """
        取消订阅频道
        
        Args:
            channels: 频道名称（单个或多个）
        
        Returns:
            取消订阅是否成功
        """
        try:
            if isinstance(channels, str):
                channels = [channels]
            
            if self._pubsub:
                self._pubsub.unsubscribe(*channels)
                logger.info("取消订阅频道", channels=channels)
            
            return True
            
        except RedisError as e:
            logger.error("取消订阅失败", channels=channels, error=str(e))
            return False
    
    def get_order_book(self, market_id: str) -> Optional[Dict]:
        """
        获取订单簿缓存
        
        Args:
            market_id: 市场 ID
        
        Returns:
            订单簿数据
        """
        key = f"order_book:{market_id}"
        return self.get_value(key)
    
    def set_order_book(
        self,
        market_id: str,
        order_book: Dict,
        expire: int = 60,
    ) -> bool:
        """
        设置订单簿缓存
        
        Args:
            market_id: 市场 ID
            order_book: 订单簿数据
            expire: 过期时间（秒）
        
        Returns:
            设置是否成功
        """
        key = f"order_book:{market_id}"
        return self.set_value(key, order_book, expire)
    
    def get_price(self, token_id: str) -> Optional[float]:
        """
        获取代币价格缓存
        
        Args:
            token_id: 代币 ID
        
        Returns:
            价格
        """
        key = f"price:{token_id}"
        value = self.get_value(key)
        return float(value) if value else None
    
    def set_price(
        self,
        token_id: str,
        price: float,
        expire: int = 30,
    ) -> bool:
        """
        设置代币价格缓存
        
        Args:
            token_id: 代币 ID
            price: 价格
            expire: 过期时间（秒）
        
        Returns:
            设置是否成功
        """
        key = f"price:{token_id}"
        return self.set_value(key, price, expire)
    
    def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        retry_interval: float = 0.1,
    ) -> bool:
        """
        获取分布式锁
        
        Args:
            lock_name: 锁名称
            timeout: 超时时间（秒）
            retry_interval: 重试间隔（秒）
        
        Returns:
            是否成功获取锁
        """
        lock_key = f"lock:{lock_name}"
        identifier = str(time.time())
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            if self.client.set(lock_key, identifier, nx=True, ex=timeout):
                logger.debug("获取锁成功", lock_name=lock_name)
                return True
            
            time.sleep(retry_interval)
        
        logger.warn("获取锁超时", lock_name=lock_name)
        return False
    
    def release_lock(self, lock_name: str) -> bool:
        """
        释放分布式锁
        
        Args:
            lock_name: 锁名称
        
        Returns:
            是否成功释放锁
        """
        lock_key = f"lock:{lock_name}"
        result = self.delete_key(lock_key)
        
        if result:
            logger.debug("释放锁成功", lock_name=lock_name)
        else:
            logger.warn("释放锁失败", lock_name=lock_name)
        
        return result
    
    def increment_counter(self, key: str, amount: int = 1) -> Optional[int]:
        """
        增加计数器
        
        Args:
            key: 键名
            amount: 增加量
        
        Returns:
            增加后的值
        """
        try:
            result = self.client.incrby(key, amount)
            logger.debug("计数器增加", key=key, amount=amount, result=result)
            return result
        except RedisError as e:
            logger.error("计数器增加失败", key=key, error=str(e))
            return None
    
    def get_info(self) -> Optional[Dict]:
        """
        获取 Redis 服务器信息
        
        Returns:
            Redis 信息
        """
        try:
            info = self.client.info()
            return {
                "version": info.get("redis_version"),
                "uptime_days": info.get("uptime_in_days"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_commands_processed": info.get("total_commands_processed"),
            }
        except RedisError as e:
            logger.error("获取 Redis 信息失败", error=str(e))
            return None


class AsyncRedisClient:
    """
    异步 Redis 客户端封装类
    提供异步连接管理、Pub/Sub、缓存等功能
    """
    
    def __init__(self, config: RedisConnectionConfig):
        """
        初始化异步 Redis 客户端
        
        Args:
            config: Redis 连接配置
        """
        self.config = config
        self._client = None
        self._is_connected = False
        
        logger.info(
            "初始化异步 Redis 客户端",
            host=config.host,
            port=config.port,
            db=config.db
        )
    
    async def connect(self) -> bool:
        """
        异步连接 Redis 服务器
        
        Returns:
            连接是否成功
        """
        try:
            import aioredis
            
            self._client = await aioredis.from_url(
                f"redis://{self.config.host}:{self.config.port}",
                password=self.config.password,
                db=self.config.db,
                max_connections=self.config.max_connections,
                decode_responses=True,
            )
            
            self._is_connected = True
            logger.info("异步 Redis 连接成功")
            return True
            
        except Exception as e:
            logger.error("异步 Redis 连接失败", error=str(e))
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """异步断开 Redis 连接"""
        if self._client:
            await self._client.close()
            self._client = None
        
        self._is_connected = False
        logger.info("异步 Redis 连接已断开")
    
    async def publish_message(
        self,
        channel: str,
        message: Union[str, Dict, List],
    ) -> bool:
        """
        异步发布消息到指定频道
        
        Args:
            channel: 频道名称
            message: 消息内容
        
        Returns:
            发布是否成功
        """
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            
            await self._client.publish(channel, message)
            logger.debug("异步发布消息", channel=channel)
            return True
            
        except Exception as e:
            logger.error("异步发布消息失败", channel=channel, error=str(e))
            return False
    
    async def subscribe_channel(
        self,
        channels: Union[str, List[str]],
        message_handler: Callable[[str, Any], None],
    ) -> bool:
        """
        异步订阅频道并接收消息
        
        Args:
            channels: 频道名称
            message_handler: 消息处理函数
        
        Returns:
            订阅是否成功
        """
        try:
            if isinstance(channels, str):
                channels = [channels]
            
            pubsub = self._client.pubsub()
            await pubsub.subscribe(*channels)
            
            logger.info("异步订阅频道", channels=channels)
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
                    
                    try:
                        if asyncio.iscoroutinefunction(message_handler):
                            await message_handler(channel, data)
                        else:
                            message_handler(channel, data)
                    except Exception as e:
                        logger.error(
                            "异步消息处理异常",
                            channel=channel,
                            error=str(e)
                        )
            
            return True
            
        except Exception as e:
            logger.error("异步订阅频道失败", channels=channels, error=str(e))
            return False


def create_redis_client(
    host: str = "localhost",
    port: int = 6379,
    password: Optional[str] = None,
    db: int = 0,
) -> RedisClient:
    """
    创建 Redis 客户端的便捷函数
    
    Args:
        host: Redis 主机地址
        port: Redis 端口
        password: Redis 密码
        db: 数据库编号
    
    Returns:
        Redis 客户端实例
    """
    config = RedisConnectionConfig(
        host=host,
        port=port,
        password=password,
        db=db,
    )
    
    client = RedisClient(config)
    client.connect()
    
    return client
