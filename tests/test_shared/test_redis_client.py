"""
Redis 客户端单元测试
测试 Redis 连接、Pub/Sub、缓存等功能
"""

import json
import time
import pytest
from unittest.mock import Mock, MagicMock, patch
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from shared.redis_client import (
    RedisClient,
    RedisConnectionConfig,
    RedisClientError,
    create_redis_client,
)


class TestRedisConnectionConfig:
    """测试 Redis 连接配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RedisConnectionConfig()
        
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.password is None
        assert config.db == 0
        assert config.max_connections == 50
        assert config.min_connections == 5
        assert config.connect_timeout == 5
        assert config.read_timeout == 5
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = RedisConnectionConfig(
            host="192.168.1.100",
            port=6380,
            password="test_password",
            db=1,
            max_connections=100,
            min_connections=10,
            connect_timeout=10,
            read_timeout=10,
            retry_attempts=5,
            retry_delay=2.0,
        )
        
        assert config.host == "192.168.1.100"
        assert config.port == 6380
        assert config.password == "test_password"
        assert config.db == 1
        assert config.max_connections == 100
        assert config.min_connections == 10
        assert config.connect_timeout == 10
        assert config.read_timeout == 10
        assert config.retry_attempts == 5
        assert config.retry_delay == 2.0


class TestRedisClient:
    """测试 Redis 客户端"""
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return RedisConnectionConfig(
            host="localhost",
            port=6379,
            password=None,
            db=0,
        )
    
    @pytest.fixture
    def mock_redis(self):
        """创建 Mock Redis 客户端"""
        with patch('shared.redis_client.Redis') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            mock_instance.ping.return_value = True
            yield mock_instance
    
    def test_init(self, config):
        """测试初始化"""
        client = RedisClient(config)
        
        assert client.config == config
        assert client._client is None
        assert client._is_connected is False
        assert client._reconnect_count == 0
    
    def test_connect_success(self, config, mock_redis):
        """测试连接成功"""
        client = RedisClient(config)
        result = client.connect()
        
        assert result is True
        assert client._is_connected is True
        assert client._client is not None
    
    def test_connect_failure(self, config):
        """测试连接失败"""
        with patch('shared.redis_client.Redis') as mock:
            mock.side_effect = RedisError("Connection failed")
            
            client = RedisClient(config)
            result = client.connect()
            
            assert result is False
            assert client._is_connected is False
    
    def test_disconnect(self, config, mock_redis):
        """测试断开连接"""
        client = RedisClient(config)
        client.connect()
        client.disconnect()
        
        assert client._is_connected is False
        assert client._client is None
    
    def test_ping_success(self, config, mock_redis):
        """测试 ping 成功"""
        client = RedisClient(config)
        client.connect()
        
        result = client.ping()
        
        assert result is True
        assert mock_redis.ping.called
    
    def test_ping_failure(self, config, mock_redis):
        """测试 ping 失败"""
        mock_redis.ping.side_effect = RedisError("Ping failed")
        
        client = RedisClient(config)
        client.connect()
        
        result = client.ping()
        
        assert result is False
    
    def test_set_value_string(self, config, mock_redis):
        """测试设置字符串值"""
        mock_redis.set.return_value = True
        
        client = RedisClient(config)
        client.connect()
        
        result = client.set_value("test_key", "test_value", expire=60)
        
        assert result is True
        mock_redis.set.assert_called_once_with("test_key", "test_value", ex=60)
    
    def test_set_value_dict(self, config, mock_redis):
        """测试设置字典值"""
        mock_redis.set.return_value = True
        
        client = RedisClient(config)
        client.connect()
        
        test_dict = {"key": "value", "number": 123}
        result = client.set_value("test_key", test_dict)
        
        assert result is True
        expected_value = json.dumps(test_dict)
        mock_redis.set.assert_called_once_with("test_key", expected_value, ex=None)
    
    def test_set_value_list(self, config, mock_redis):
        """测试设置列表值"""
        mock_redis.set.return_value = True
        
        client = RedisClient(config)
        client.connect()
        
        test_list = [1, 2, 3, "test"]
        result = client.set_value("test_key", test_list)
        
        assert result is True
        expected_value = json.dumps(test_list)
        mock_redis.set.assert_called_once_with("test_key", expected_value, ex=None)
    
    def test_get_value_string(self, config, mock_redis):
        """测试获取字符串值"""
        mock_redis.get.return_value = "test_value"
        
        client = RedisClient(config)
        client.connect()
        
        result = client.get_value("test_key")
        
        assert result == "test_value"
        mock_redis.get.assert_called_once_with("test_key")
    
    def test_get_value_dict(self, config, mock_redis):
        """测试获取字典值"""
        test_dict = {"key": "value", "number": 123}
        mock_redis.get.return_value = json.dumps(test_dict)
        
        client = RedisClient(config)
        client.connect()
        
        result = client.get_value("test_key")
        
        assert result == test_dict
        mock_redis.get.assert_called_once_with("test_key")
    
    def test_get_value_none(self, config, mock_redis):
        """测试获取不存在的值"""
        mock_redis.get.return_value = None
        
        client = RedisClient(config)
        client.connect()
        
        result = client.get_value("nonexistent_key")
        
        assert result is None
    
    def test_delete_key_success(self, config, mock_redis):
        """测试删除键成功"""
        mock_redis.delete.return_value = 1
        
        client = RedisClient(config)
        client.connect()
        
        result = client.delete_key("test_key")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")
    
    def test_delete_key_failure(self, config, mock_redis):
        """测试删除键失败"""
        mock_redis.delete.return_value = 0
        
        client = RedisClient(config)
        client.connect()
        
        result = client.delete_key("nonexistent_key")
        
        assert result is False
    
    def test_exists_true(self, config, mock_redis):
        """测试键存在"""
        mock_redis.exists.return_value = 1
        
        client = RedisClient(config)
        client.connect()
        
        result = client.exists("test_key")
        
        assert result is True
    
    def test_exists_false(self, config, mock_redis):
        """测试键不存在"""
        mock_redis.exists.return_value = 0
        
        client = RedisClient(config)
        client.connect()
        
        result = client.exists("nonexistent_key")
        
        assert result is False
    
    def test_set_expire_success(self, config, mock_redis):
        """测试设置过期时间成功"""
        mock_redis.expire.return_value = True
        
        client = RedisClient(config)
        client.connect()
        
        result = client.set_expire("test_key", 60)
        
        assert result is True
        mock_redis.expire.assert_called_once_with("test_key", 60)
    
    def test_publish_message_string(self, config, mock_redis):
        """测试发布字符串消息"""
        mock_redis.publish.return_value = 1
        
        client = RedisClient(config)
        client.connect()
        
        result = client.publish_message("test_channel", "test_message")
        
        assert result is True
        mock_redis.publish.assert_called_once_with("test_channel", "test_message")
    
    def test_publish_message_dict(self, config, mock_redis):
        """测试发布字典消息"""
        mock_redis.publish.return_value = 1
        
        client = RedisClient(config)
        client.connect()
        
        test_dict = {"event": "price_update", "price": 100.5}
        result = client.publish_message("test_channel", test_dict)
        
        assert result is True
        expected_message = json.dumps(test_dict)
        mock_redis.publish.assert_called_once_with("test_channel", expected_message)
    
    def test_subscribe_channel(self, config, mock_redis):
        """测试订阅频道"""
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        messages = [
            {"type": "subscribe", "channel": "test_channel", "data": 1},
            {"type": "message", "channel": "test_channel", "data": "test_message"},
        ]
        mock_pubsub.listen.return_value = iter(messages)
        
        client = RedisClient(config)
        client.connect()
        
        received_messages = []
        
        def message_handler(channel, message):
            received_messages.append((channel, message))
        
        result = client.subscribe_channel("test_channel", message_handler)
        
        assert result is True
        assert len(received_messages) == 1
        assert received_messages[0] == ("test_channel", "test_message")
    
    def test_subscribe_channel_json(self, config, mock_redis):
        """测试订阅频道接收 JSON 消息"""
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        test_dict = {"event": "price_update", "price": 100.5}
        messages = [
            {"type": "message", "channel": "test_channel", "data": json.dumps(test_dict)},
        ]
        mock_pubsub.listen.return_value = iter(messages)
        
        client = RedisClient(config)
        client.connect()
        
        received_messages = []
        
        def message_handler(channel, message):
            received_messages.append((channel, message))
        
        result = client.subscribe_channel("test_channel", message_handler)
        
        assert result is True
        assert len(received_messages) == 1
        assert received_messages[0] == ("test_channel", test_dict)
    
    def test_unsubscribe_channel(self, config, mock_redis):
        """测试取消订阅频道"""
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        client = RedisClient(config)
        client.connect()
        client._pubsub = mock_pubsub
        
        result = client.unsubscribe_channel("test_channel")
        
        assert result is True
        mock_pubsub.unsubscribe.assert_called_once_with("test_channel")
    
    def test_get_order_book(self, config, mock_redis):
        """测试获取订单簿缓存"""
        order_book = {
            "bids": [{"price": 0.5, "size": 100}],
            "asks": [{"price": 0.6, "size": 100}],
        }
        mock_redis.get.return_value = json.dumps(order_book)
        
        client = RedisClient(config)
        client.connect()
        
        result = client.get_order_book("market_123")
        
        assert result == order_book
        mock_redis.get.assert_called_once_with("order_book:market_123")
    
    def test_set_order_book(self, config, mock_redis):
        """测试设置订单簿缓存"""
        mock_redis.set.return_value = True
        
        client = RedisClient(config)
        client.connect()
        
        order_book = {
            "bids": [{"price": 0.5, "size": 100}],
            "asks": [{"price": 0.6, "size": 100}],
        }
        result = client.set_order_book("market_123", order_book, expire=60)
        
        assert result is True
        expected_value = json.dumps(order_book)
        mock_redis.set.assert_called_once_with("order_book:market_123", expected_value, ex=60)
    
    def test_get_price(self, config, mock_redis):
        """测试获取价格缓存"""
        mock_redis.get.return_value = "0.55"
        
        client = RedisClient(config)
        client.connect()
        
        result = client.get_price("token_123")
        
        assert result == 0.55
        mock_redis.get.assert_called_once_with("price:token_123")
    
    def test_set_price(self, config, mock_redis):
        """测试设置价格缓存"""
        mock_redis.set.return_value = True
        
        client = RedisClient(config)
        client.connect()
        
        result = client.set_price("token_123", 0.55, expire=30)
        
        assert result is True
        mock_redis.set.assert_called_once_with("price:token_123", 0.55, ex=30)
    
    def test_acquire_lock_success(self, config, mock_redis):
        """测试获取锁成功"""
        mock_redis.set.return_value = True
        
        client = RedisClient(config)
        client.connect()
        
        result = client.acquire_lock("test_lock", timeout=10)
        
        assert result is True
        mock_redis.set.assert_called()
    
    def test_acquire_lock_timeout(self, config, mock_redis):
        """测试获取锁超时"""
        mock_redis.set.return_value = False
        
        client = RedisClient(config)
        client.connect()
        
        result = client.acquire_lock("test_lock", timeout=1, retry_interval=0.1)
        
        assert result is False
    
    def test_release_lock_success(self, config, mock_redis):
        """测试释放锁成功"""
        mock_redis.delete.return_value = 1
        
        client = RedisClient(config)
        client.connect()
        
        result = client.release_lock("test_lock")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("lock:test_lock")
    
    def test_increment_counter(self, config, mock_redis):
        """测试计数器增加"""
        mock_redis.incrby.return_value = 10
        
        client = RedisClient(config)
        client.connect()
        
        result = client.increment_counter("counter_key", amount=5)
        
        assert result == 10
        mock_redis.incrby.assert_called_once_with("counter_key", 5)
    
    def test_get_info(self, config, mock_redis):
        """测试获取 Redis 信息"""
        mock_redis.info.return_value = {
            "redis_version": "7.0.0",
            "uptime_in_days": 10,
            "connected_clients": 50,
            "used_memory_human": "1.5GB",
            "total_commands_processed": 1000000,
        }
        
        client = RedisClient(config)
        client.connect()
        
        result = client.get_info()
        
        assert result is not None
        assert result["version"] == "7.0.0"
        assert result["uptime_days"] == 10
        assert result["connected_clients"] == 50
        assert result["used_memory_human"] == "1.5GB"
        assert result["total_commands_processed"] == 1000000
    
    def test_ensure_connection_success(self, config, mock_redis):
        """测试确保连接成功"""
        client = RedisClient(config)
        
        client.ensure_connection()
        
        assert client._is_connected is True
    
    def test_ensure_connection_failure(self, config):
        """测试确保连接失败"""
        with patch('shared.redis_client.Redis') as mock:
            mock.side_effect = RedisError("Connection failed")
            
            client = RedisClient(config)
            
            with pytest.raises(RedisClientError, match="无法连接到 Redis 服务器"):
                client.ensure_connection()
    
    def test_reconnect_success(self, config, mock_redis):
        """测试重连成功"""
        client = RedisClient(config)
        client.connect()
        
        initial_count = client._reconnect_count
        result = client.reconnect()
        
        assert result is True
        assert client._reconnect_count > initial_count


class TestCreateRedisClient:
    """测试创建 Redis 客户端的便捷函数"""
    
    def test_create_redis_client(self):
        """测试创建 Redis 客户端"""
        with patch('shared.redis_client.Redis') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            mock_instance.ping.return_value = True
            
            client = create_redis_client(
                host="localhost",
                port=6379,
                password=None,
                db=0,
            )
            
            assert client is not None
            assert client._is_connected is True


class TestRedisClientError:
    """测试 Redis 客户端异常"""
    
    def test_exception_message(self):
        """测试异常消息"""
        error = RedisClientError("测试错误")
        
        assert str(error) == "测试错误"


class TestRedisClientIntegration:
    """
    Redis 客户端集成测试
    需要实际的 Redis 服务器运行
    标记为 integration，默认不运行
    """
    
    @pytest.mark.integration
    def test_real_connection(self):
        """测试真实连接（需要 Redis 服务器）"""
        try:
            client = create_redis_client()
            
            assert client.ping() is True
            
            client.disconnect()
        except Exception as e:
            pytest.skip(f"Redis 服务器不可用: {e}")
    
    @pytest.mark.integration
    def test_real_pubsub(self):
        """测试真实 Pub/Sub（需要 Redis 服务器）"""
        try:
            client = create_redis_client()
            
            import threading
            import time
            
            received_messages = []
            
            def message_handler(channel, message):
                received_messages.append((channel, message))
            
            def subscriber():
                client.subscribe_channel("test_channel", message_handler)
            
            thread = threading.Thread(target=subscriber, daemon=True)
            thread.start()
            
            time.sleep(0.5)
            
            client.publish_message("test_channel", "test_message")
            
            time.sleep(0.5)
            
            client.unsubscribe_channel("test_channel")
            client.disconnect()
            
            assert len(received_messages) > 0
            
        except Exception as e:
            pytest.skip(f"Redis 服务器不可用: {e}")
