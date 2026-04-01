"""
Redis 发布者模块测试
"""

import pytest
from unittest.mock import Mock, MagicMock

from modules.strategy_engine.redis_publisher import RedisPublisher, create_publisher
from modules.strategy_engine.signal_generator import (
    TradingSignal,
    SignalAction,
    SignalDirection,
)


class TestRedisPublisher:
    """RedisPublisher 测试类"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """创建模拟 Redis 客户端"""
        client = Mock()
        client.publish_message = Mock(return_value=True)
        return client
    
    @pytest.fixture
    def sample_signal(self):
        """创建示例信号"""
        return TradingSignal(
            action=SignalAction.BUY,
            direction=SignalDirection.UP,
            current_price=0.50,
            start_price=0.45,
            price_difference=0.05,
            max_buy_price=0.45,
            safety_cushion=0.05,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
            timestamp=1234567890.0,
            confidence=0.85,
        )
    
    def test_create_publisher(self, mock_redis_client):
        """测试创建发布者"""
        publisher = RedisPublisher(mock_redis_client, channel="test_channel")
        
        assert publisher.channel == "test_channel"
        assert publisher._published_count == 0
        assert publisher._error_count == 0
    
    def test_publish_signal(self, mock_redis_client, sample_signal):
        """测试发布信号"""
        publisher = RedisPublisher(mock_redis_client)
        
        success = publisher.publish_signal(sample_signal)
        
        assert success is True
        assert publisher._published_count == 1
        mock_redis_client.publish_message.assert_called_once()
    
    def test_publish_buy_signal(self, mock_redis_client):
        """测试发布买入信号"""
        publisher = RedisPublisher(mock_redis_client)
        
        success = publisher.publish_buy_signal(
            direction=SignalDirection.UP,
            max_price=0.45,
            current_price=0.50,
            confidence=0.85,
            timestamp=1234567890.0,
        )
        
        assert success is True
        assert publisher._published_count == 1
        
        call_args = mock_redis_client.publish_message.call_args
        message = call_args[0][1]
        
        assert message["action"] == "BUY"
        assert message["direction"] == "UP"
        assert message["max_price"] == 0.45
    
    def test_publish_wait_signal(self, mock_redis_client):
        """测试发布等待信号"""
        publisher = RedisPublisher(mock_redis_client)
        
        success = publisher.publish_wait_signal(timestamp=1234567890.0)
        
        assert success is True
        assert publisher._published_count == 1
        
        call_args = mock_redis_client.publish_message.call_args
        message = call_args[0][1]
        
        assert message["action"] == "WAIT"
        assert "timestamp" in message
    
    def test_publish_custom_message(self, mock_redis_client):
        """测试发布自定义消息"""
        publisher = RedisPublisher(mock_redis_client)
        
        custom_message = {
            "custom_field": "custom_value",
            "timestamp": 1234567890.0,
        }
        
        success = publisher.publish_custom_message(custom_message)
        
        assert success is True
        assert publisher._published_count == 1
    
    def test_publish_failure(self, mock_redis_client, sample_signal):
        """测试发布失败"""
        mock_redis_client.publish_message = Mock(return_value=False)
        
        publisher = RedisPublisher(mock_redis_client)
        
        success = publisher.publish_signal(sample_signal)
        
        assert success is False
        assert publisher._error_count == 1
        assert publisher._published_count == 0
    
    def test_publish_exception(self, mock_redis_client, sample_signal):
        """测试发布异常"""
        mock_redis_client.publish_message = Mock(side_effect=Exception("Redis error"))
        
        publisher = RedisPublisher(mock_redis_client)
        
        success = publisher.publish_signal(sample_signal)
        
        assert success is False
        assert publisher._error_count == 1
    
    def test_get_statistics(self, mock_redis_client, sample_signal):
        """测试获取统计信息"""
        publisher = RedisPublisher(mock_redis_client)
        
        publisher.publish_signal(sample_signal)
        publisher.publish_signal(sample_signal)
        
        mock_redis_client.publish_message = Mock(return_value=False)
        publisher.publish_signal(sample_signal)
        
        stats = publisher.get_statistics()
        
        assert stats["published_count"] == 2
        assert stats["error_count"] == 1
        assert stats["total_attempts"] == 3
    
    def test_reset_statistics(self, mock_redis_client, sample_signal):
        """测试重置统计信息"""
        publisher = RedisPublisher(mock_redis_client)
        
        publisher.publish_signal(sample_signal)
        
        assert publisher._published_count == 1
        
        publisher.reset_statistics()
        
        assert publisher._published_count == 0
        assert publisher._error_count == 0
    
    def test_format_signal_message_buy(self, mock_redis_client, sample_signal):
        """测试格式化买入信号消息"""
        publisher = RedisPublisher(mock_redis_client)
        
        message = publisher._format_signal_message(sample_signal)
        
        assert message["action"] == "BUY"
        assert message["direction"] == "UP"
        assert "max_price" in message
        assert "current_price" in message
        assert "confidence" in message
    
    def test_format_signal_message_wait(self, mock_redis_client):
        """测试格式化等待信号消息"""
        publisher = RedisPublisher(mock_redis_client)
        
        wait_signal = TradingSignal(
            action=SignalAction.WAIT,
            direction=None,
            current_price=0.50,
            start_price=0.45,
            price_difference=0.05,
            max_buy_price=0.45,
            safety_cushion=0.05,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
            timestamp=1234567890.0,
            confidence=0.85,
        )
        
        message = publisher._format_signal_message(wait_signal)
        
        assert message["action"] == "WAIT"
        assert "direction" not in message or message["direction"] is None
    
    def test_create_publisher_convenience(self, mock_redis_client):
        """测试便捷函数"""
        publisher = create_publisher(mock_redis_client, channel="custom_channel")
        
        assert isinstance(publisher, RedisPublisher)
        assert publisher.channel == "custom_channel"
