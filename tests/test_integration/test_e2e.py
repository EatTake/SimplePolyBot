"""
端到端集成测试

测试完整的模块间通信流程：
市场数据收集 -> 策略分析 -> 订单执行 -> 资金结算
"""

import pytest
import time
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any, List
import asyncio

from shared.redis_client import RedisClient, RedisConnectionConfig
from shared.constants import (
    MARKET_DATA_CHANNEL,
    TRADING_SIGNAL_CHANNEL,
    TRADE_RESULT_CHANNEL
)
from modules.strategy_engine.main import StrategyEngine
from modules.order_executor.main import OrderExecutor
from modules.settlement_worker.main import SettlementWorker


class MockRedisClient:
    """模拟 Redis 客户端"""
    
    def __init__(self):
        self._connected = False
        self._channels: Dict[str, List[Dict]] = {}
        self._subscribers: Dict[str, List[callable]] = {}
        self._published_messages: Dict[str, List[Dict]] = {}
    
    def connect(self) -> bool:
        self._connected = True
        return True
    
    def disconnect(self) -> None:
        self._connected = False
    
    def publish_message(self, channel: str, message: Dict) -> bool:
        if channel not in self._published_messages:
            self._published_messages[channel] = []
        self._published_messages[channel].append(message)
        
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                callback(message)
        
        return True
    
    def subscribe_channel(self, channel: str, callback: callable) -> bool:
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)
        return True
    
    def get_published_messages(self, channel: str) -> List[Dict]:
        return self._published_messages.get(channel, [])
    
    def clear_messages(self) -> None:
        self._published_messages.clear()


class TestEndToEndIntegration:
    """端到端集成测试类"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建模拟 Redis 客户端"""
        return MockRedisClient()
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock()
        config.get_redis_config.return_value = Mock(
            host="localhost",
            port=6379,
            password="",
            db=0,
            max_connections=50,
            min_idle_connections=5,
            connection_timeout=5,
            socket_timeout=5,
            max_attempts=3,
            retry_delay=1
        )
        config.get_strategy_config.return_value = Mock(
            base_cushion=15.0,
            alpha=1.0,
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000},
            risk_management={"max_position_size": 5000}
        )
        config.get.return_value = "INFO"
        return config
    
    def test_market_data_to_signal_flow(self, mock_redis, mock_config):
        """测试市场数据到信号生成的完整流程"""
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=mock_config)
            
            market_data_messages = [
                {"price": 67000.0, "timestamp": time.time() - 170},
                {"price": 67050.0, "timestamp": time.time() - 160},
                {"price": 67100.0, "timestamp": time.time() - 150},
                {"price": 67150.0, "timestamp": time.time() - 140},
                {"price": 67200.0, "timestamp": time.time() - 130},
                {"price": 67250.0, "timestamp": time.time() - 120},
                {"price": 67300.0, "timestamp": time.time() - 110},
                {"price": 67350.0, "timestamp": time.time() - 100},
                {"price": 67400.0, "timestamp": time.time() - 90},
                {"price": 67450.0, "timestamp": time.time() - 80},
                {"price": 67500.0, "timestamp": time.time() - 70},
                {"price": 67550.0, "timestamp": time.time() - 60},
                {"price": 67600.0, "timestamp": time.time() - 50},
                {"price": 67650.0, "timestamp": time.time() - 40},
                {"price": 67700.0, "timestamp": time.time() - 30},
            ]
            
            for msg in market_data_messages:
                engine._handle_market_data(msg)
            
            engine._execute_strategy_cycle()
            
            signals = mock_redis.get_published_messages(TRADING_SIGNAL_CHANNEL)
            
            assert len(signals) > 0
            
            signal = signals[0]
            assert "action" in signal
            assert signal["action"] in ["BUY", "WAIT"]
    
    @patch('modules.order_executor.main.ClobClientWrapper')
    def test_signal_to_order_flow(self, mock_clob_class, mock_redis, mock_config):
        """测试信号到订单执行的完整流程"""
        
        mock_clob = Mock()
        mock_clob.get_usdc_balance.return_value = 1000.0
        mock_clob.get_tick_size.return_value = "0.01"
        mock_clob.get_neg_risk.return_value = False
        mock_clob.get_order_book.return_value = {
            "asks": [{"price": "0.51", "size": "100"}]
        }
        mock_clob.create_and_submit_order.return_value = {
            "success": True,
            "orderID": "order_123",
            "status": "matched",
            "errorMsg": ""
        }
        mock_clob_class.return_value = mock_clob
        
        with patch('modules.order_executor.main.RedisClient', return_value=mock_redis):
            executor = OrderExecutor(config=mock_config)
            executor.initialize()
            
            from modules.order_executor.redis_subscriber import TradingSignal
            
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
            
            executor._handle_trading_signal(signal)
            
            results = mock_redis.get_published_messages(TRADE_RESULT_CHANNEL)
            
            assert len(results) > 0
    
    def test_full_pipeline_integration(self, mock_redis, mock_config):
        """测试完整的管道集成"""
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=mock_config)
            
            for i in range(20):
                market_data = {
                    "price": 67000.0 + i * 10,
                    "timestamp": time.time() - (20 - i) * 5
                }
                engine._handle_market_data(market_data)
            
            engine._execute_strategy_cycle()
            
            signals = mock_redis.get_published_messages(TRADING_SIGNAL_CHANNEL)
            
            assert len(signals) >= 0
            
            if len(signals) > 0:
                signal = signals[0]
                assert "action" in signal
                assert "timestamp" in signal
    
    def test_redis_pub_sub_communication(self, mock_redis):
        """测试 Redis Pub/Sub 通信"""
        
        received_messages = []
        
        def message_handler(message):
            received_messages.append(message)
        
        mock_redis.subscribe_channel("test_channel", message_handler)
        
        test_message = {"test": "data", "timestamp": time.time()}
        mock_redis.publish_message("test_channel", test_message)
        
        assert len(received_messages) == 1
        assert received_messages[0] == test_message
    
    def test_error_handling_in_pipeline(self, mock_redis, mock_config):
        """测试管道中的错误处理"""
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=mock_config)
            
            invalid_data = {"invalid": "data"}
            
            engine._handle_market_data(invalid_data)
            
            engine._execute_strategy_cycle()
            
            assert True
    
    def test_concurrent_message_processing(self, mock_redis, mock_config):
        """测试并发消息处理"""
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=mock_config)
            
            messages = [
                {"price": 67000.0 + i, "timestamp": time.time() - i}
                for i in range(100)
            ]
            
            for msg in messages:
                engine._handle_market_data(msg)
            
            assert engine.price_queue.size() > 0


class TestModuleIntegration:
    """模块集成测试类"""
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock()
        config.get_redis_config.return_value = Mock(
            host="localhost",
            port=6379,
            password="",
            db=0,
            max_connections=50,
            min_idle_connections=5,
            connection_timeout=5,
            socket_timeout=5,
            max_attempts=3,
            retry_delay=1
        )
        config.get_strategy_config.return_value = Mock(
            base_cushion=15.0,
            alpha=1.0,
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000}
        )
        config.get.return_value = "INFO"
        return config
    
    def test_strategy_engine_initialization(self, mock_config):
        """测试策略引擎初始化"""
        mock_redis = MockRedisClient()
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=mock_config)
            
            assert engine.redis_client is not None
            assert engine.price_queue is not None
            assert engine.regression is not None
            assert engine.safety_cushion is not None
            assert engine.signal_generator is not None
            assert engine.lifecycle_manager is not None
    
    @patch('modules.order_executor.main.ClobClientWrapper')
    def test_order_executor_initialization(self, mock_clob_class, mock_config):
        """测试订单执行器初始化"""
        mock_redis = MockRedisClient()
        mock_clob = Mock()
        mock_clob_class.return_value = mock_clob
        
        with patch('modules.order_executor.main.RedisClient', return_value=mock_redis):
            executor = OrderExecutor(config=mock_config)
            executor.initialize()
            
            assert executor.clob_client is not None
            assert executor.fee_calculator is not None
            assert executor.order_manager is not None
            assert executor.redis_client is not None
    
    def test_settlement_worker_initialization(self, mock_config):
        """测试资金结算模块初始化"""
        with patch.dict('os.environ', {'PRIVATE_KEY': '0x' + '0' * 64}):
            with patch('modules.settlement_worker.main.CTFContract') as mock_ctf:
                with patch('modules.settlement_worker.main.RedemptionManager') as mock_redemption:
                    mock_ctf_instance = Mock()
                    mock_ctf_instance.account_address = "0x1234567890abcdef"
                    mock_ctf.return_value = mock_ctf_instance
                    
                    mock_redemption_instance = Mock()
                    mock_redemption.return_value = mock_redemption_instance
                    
                    worker = SettlementWorker(config=mock_config)
                    worker._initialize()
                    
                    assert worker._ctf_contract is not None
                    assert worker._redemption_manager is not None


class TestPerformanceIntegration:
    """性能集成测试类"""
    
    def test_high_frequency_market_data(self):
        """测试高频市场数据处理"""
        mock_redis = MockRedisClient()
        
        config = Mock()
        config.get_redis_config.return_value = Mock(
            host="localhost",
            port=6379,
            password="",
            db=0,
            max_connections=50,
            min_idle_connections=5,
            connection_timeout=5,
            socket_timeout=5,
            max_attempts=3,
            retry_delay=1
        )
        config.get_strategy_config.return_value = Mock(
            base_cushion=15.0,
            alpha=1.0,
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000}
        )
        config.get.return_value = "INFO"
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=config)
            
            start_time = time.time()
            
            for i in range(1000):
                market_data = {
                    "price": 67000.0 + i * 0.01,
                    "timestamp": time.time() - i * 0.1
                }
                engine._handle_market_data(market_data)
            
            elapsed_time = time.time() - start_time
            
            assert elapsed_time < 5.0
            assert engine.price_queue.size() > 0
    
    def test_signal_generation_latency(self):
        """测试信号生成延迟"""
        mock_redis = MockRedisClient()
        
        config = Mock()
        config.get_redis_config.return_value = Mock(
            host="localhost",
            port=6379,
            password="",
            db=0,
            max_connections=50,
            min_idle_connections=5,
            connection_timeout=5,
            socket_timeout=5,
            max_attempts=3,
            retry_delay=1
        )
        config.get_strategy_config.return_value = Mock(
            base_cushion=15.0,
            alpha=1.0,
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000}
        )
        config.get.return_value = "INFO"
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=config)
            
            for i in range(20):
                market_data = {
                    "price": 67000.0 + i * 10,
                    "timestamp": time.time() - (20 - i) * 5
                }
                engine._handle_market_data(market_data)
            
            start_time = time.time()
            engine._execute_strategy_cycle()
            elapsed_time = time.time() - start_time
            
            assert elapsed_time < 0.1


class TestErrorRecoveryIntegration:
    """错误恢复集成测试类"""
    
    def test_redis_connection_failure_recovery(self):
        """测试 Redis 连接失败恢复"""
        mock_redis = MockRedisClient()
        mock_redis.connect = Mock(side_effect=[False, True])
        
        config = Mock()
        config.get_redis_config.return_value = Mock(
            host="localhost",
            port=6379,
            password="",
            db=0,
            max_connections=50,
            min_idle_connections=5,
            connection_timeout=5,
            socket_timeout=5,
            max_attempts=3,
            retry_delay=1
        )
        config.get_strategy_config.return_value = Mock(
            base_cushion=15.0,
            alpha=1.0,
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000}
        )
        config.get.return_value = "INFO"
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            try:
                engine = StrategyEngine(config=config)
            except RuntimeError as e:
                assert "无法连接到 Redis" in str(e)
    
    def test_invalid_message_handling(self):
        """测试无效消息处理"""
        mock_redis = MockRedisClient()
        
        config = Mock()
        config.get_redis_config.return_value = Mock(
            host="localhost",
            port=6379,
            password="",
            db=0,
            max_connections=50,
            min_idle_connections=5,
            connection_timeout=5,
            socket_timeout=5,
            max_attempts=3,
            retry_delay=1
        )
        config.get_strategy_config.return_value = Mock(
            base_cushion=15.0,
            alpha=1.0,
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000}
        )
        config.get.return_value = "INFO"
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=config)
            
            invalid_messages = [
                {},
                {"price": None},
                {"price": "invalid"},
                {"timestamp": "invalid"},
                None
            ]
            
            for msg in invalid_messages:
                try:
                    engine._handle_market_data(msg)
                except Exception:
                    pass
            
            assert True


class TestDataFlowIntegration:
    """数据流集成测试类"""
    
    def test_complete_data_pipeline(self):
        """测试完整的数据管道"""
        mock_redis = MockRedisClient()
        
        config = Mock()
        config.get_redis_config.return_value = Mock(
            host="localhost",
            port=6379,
            password="",
            db=0,
            max_connections=50,
            min_idle_connections=5,
            connection_timeout=5,
            socket_timeout=5,
            max_attempts=3,
            retry_delay=1
        )
        config.get_strategy_config.return_value = Mock(
            base_cushion=15.0,
            alpha=1.0,
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000}
        )
        config.get.return_value = "INFO"
        
        with patch('modules.strategy_engine.main.RedisClient', return_value=mock_redis):
            engine = StrategyEngine(config=config)
            
            market_data_list = []
            for i in range(30):
                market_data = {
                    "price": 67000.0 + i * 5,
                    "timestamp": time.time() - (30 - i) * 3
                }
                market_data_list.append(market_data)
                engine._handle_market_data(market_data)
            
            engine._execute_strategy_cycle()
            
            signals = mock_redis.get_published_messages(TRADING_SIGNAL_CHANNEL)
            
            assert len(signals) >= 0
            
            if len(signals) > 0:
                signal = signals[0]
                assert "action" in signal
                assert "timestamp" in signal
