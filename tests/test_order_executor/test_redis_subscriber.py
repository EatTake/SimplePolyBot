"""
Redis 订阅者单元测试
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch
from modules.order_executor.redis_subscriber import RedisSubscriber, TradingSignal


class TestTradingSignal:
    """交易信号测试类"""
    
    def test_create_signal_from_dict(self):
        """测试从字典创建交易信号"""
        data = {
            "signal_id": "test_signal_001",
            "token_id": "token_123",
            "market_id": "market_456",
            "side": "BUY",
            "price": 0.50,
            "size": 100,
            "confidence": 0.85,
            "strategy": "base_cushion",
            "timestamp": int(time.time()),
            "metadata": {"category": "crypto"}
        }
        
        signal = TradingSignal.from_dict(data)
        
        assert signal.signal_id == "test_signal_001"
        assert signal.token_id == "token_123"
        assert signal.side == "BUY"
        assert signal.price == 0.50
        assert signal.size == 100
        assert signal.confidence == 0.85
        assert signal.strategy == "base_cushion"
    
    def test_signal_to_dict(self):
        """测试信号转换为字典"""
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="SELL",
            price=0.60,
            size=200,
            confidence=0.75,
            strategy="trend_following",
            timestamp=int(time.time())
        )
        
        data = signal.to_dict()
        
        assert data["signal_id"] == "test_001"
        assert data["token_id"] == "token_123"
        assert data["side"] == "SELL"
        assert data["price"] == 0.60
        assert data["size"] == 200
    
    def test_signal_validation_valid(self):
        """测试有效信号验证"""
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=100,
            confidence=0.85,
            strategy="test",
            timestamp=int(time.time())
        )
        
        assert signal.validate() is True
    
    def test_signal_validation_missing_signal_id(self):
        """测试缺少 signal_id 的信号验证"""
        signal = TradingSignal(
            signal_id="",
            token_id="token_123",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=100,
            confidence=0.85,
            strategy="test",
            timestamp=int(time.time())
        )
        
        assert signal.validate() is False
    
    def test_signal_validation_missing_token_id(self):
        """测试缺少 token_id 的信号验证"""
        signal = TradingSignal(
            signal_id="test_001",
            token_id="",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=100,
            confidence=0.85,
            strategy="test",
            timestamp=int(time.time())
        )
        
        assert signal.validate() is False
    
    def test_signal_validation_invalid_side(self):
        """测试无效方向的信号验证"""
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="INVALID",
            price=0.50,
            size=100,
            confidence=0.85,
            strategy="test",
            timestamp=int(time.time())
        )
        
        assert signal.validate() is False
    
    def test_signal_validation_invalid_size(self):
        """测试无效数量的信号验证"""
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=-100,
            confidence=0.85,
            strategy="test",
            timestamp=int(time.time())
        )
        
        assert signal.validate() is False
    
    def test_signal_validation_invalid_confidence(self):
        """测试无效置信度的信号验证"""
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=100,
            confidence=1.5,
            strategy="test",
            timestamp=int(time.time())
        )
        
        assert signal.validate() is False
    
    def test_signal_repr(self):
        """测试信号字符串表示"""
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=100,
            confidence=0.85,
            strategy="test",
            timestamp=int(time.time())
        )
        
        repr_str = repr(signal)
        
        assert "test_001" in repr_str
        assert "token_123" in repr_str
        assert "BUY" in repr_str


class TestRedisSubscriber:
    """Redis 订阅者测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.mock_redis_client = Mock()
        self.mock_redis_client._is_connected = True
        
    def test_subscriber_initialization(self):
        """测试订阅者初始化"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        assert subscriber.redis_client == self.mock_redis_client
        assert subscriber._running is False
    
    def test_set_signal_handler(self):
        """测试设置信号处理函数"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        handler = Mock()
        subscriber.set_signal_handler(handler)
        
        assert subscriber.signal_handler == handler
    
    def test_handle_message_valid_signal(self):
        """测试处理有效信号消息"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        handler = Mock()
        subscriber.set_signal_handler(handler)
        
        signal_data = {
            "signal_id": "test_001",
            "token_id": "token_123",
            "market_id": "market_456",
            "side": "BUY",
            "price": 0.50,
            "size": 100,
            "confidence": 0.85,
            "strategy": "test",
            "timestamp": int(time.time())
        }
        
        subscriber._handle_message("trading_signal", signal_data)
        
        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert isinstance(call_args, TradingSignal)
        assert call_args.signal_id == "test_001"
    
    def test_handle_message_json_string(self):
        """测试处理 JSON 字符串格式的信号"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        handler = Mock()
        subscriber.set_signal_handler(handler)
        
        signal_data = {
            "signal_id": "test_001",
            "token_id": "token_123",
            "market_id": "market_456",
            "side": "BUY",
            "price": 0.50,
            "size": 100,
            "confidence": 0.85,
            "strategy": "test",
            "timestamp": int(time.time())
        }
        
        subscriber._handle_message("trading_signal", json.dumps(signal_data))
        
        handler.assert_called_once()
    
    def test_handle_message_invalid_channel(self):
        """测试处理来自无效频道的消息"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        handler = Mock()
        subscriber.set_signal_handler(handler)
        
        subscriber._handle_message("invalid_channel", {"test": "data"})
        
        handler.assert_not_called()
    
    def test_handle_message_invalid_signal(self):
        """测试处理无效信号"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        handler = Mock()
        subscriber.set_signal_handler(handler)
        
        invalid_signal = {
            "signal_id": "",
            "token_id": "",
        }
        
        subscriber._handle_message("trading_signal", invalid_signal)
        
        handler.assert_not_called()
    
    def test_handle_message_no_handler(self):
        """测试没有设置处理函数时的消息处理"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        signal_data = {
            "signal_id": "test_001",
            "token_id": "token_123",
            "market_id": "market_456",
            "side": "BUY",
            "price": 0.50,
            "size": 100,
            "confidence": 0.85,
            "strategy": "test",
            "timestamp": int(time.time())
        }
        
        subscriber._handle_message("trading_signal", signal_data)
    
    def test_get_stats(self):
        """测试获取统计信息"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        stats = subscriber.get_stats()
        
        assert "running" in stats
        assert "channel" in stats
        assert "redis_connected" in stats
        assert stats["running"] is False
    
    def test_is_running(self):
        """测试检查运行状态"""
        subscriber = RedisSubscriber(redis_client=self.mock_redis_client)
        
        assert subscriber.is_running() is False
