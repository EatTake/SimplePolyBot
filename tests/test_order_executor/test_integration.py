"""
订单执行器集成测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from modules.order_executor.main import OrderExecutor
from modules.order_executor.redis_subscriber import TradingSignal
from modules.order_executor.order_manager import OrderResult


class TestOrderExecutor:
    """订单执行器集成测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.mock_config = Mock()
        self.mock_config.get_redis_config.return_value = Mock(
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
        self.mock_config.get_strategy_config.return_value = Mock(
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000},
            risk_management={"max_position_size": 5000}
        )
        self.mock_config.get.return_value = "INFO"
    
    @patch('modules.order_executor.main.ClobClientWrapper')
    @patch('modules.order_executor.main.RedisClient')
    def test_executor_initialization(self, mock_redis, mock_clob):
        """测试执行器初始化"""
        mock_clob_instance = Mock()
        mock_clob.return_value = mock_clob_instance
        
        mock_redis_instance = Mock()
        mock_redis_instance._is_connected = True
        mock_redis.return_value = mock_redis_instance
        
        executor = OrderExecutor(config=self.mock_config)
        executor.initialize()
        
        assert executor.clob_client is not None
        assert executor.fee_calculator is not None
        assert executor.order_manager is not None
        assert executor.redis_client is not None
        assert executor.redis_subscriber is not None
    
    def test_executor_status(self):
        """测试执行器状态"""
        executor = OrderExecutor(config=self.mock_config)
        
        status = executor.get_status()
        
        assert "running" in status
        assert "components" in status
        assert status["running"] is False
    
    @patch('modules.order_executor.main.ClobClientWrapper')
    @patch('modules.order_executor.main.RedisClient')
    def test_handle_trading_signal_buy(self, mock_redis, mock_clob):
        """测试处理买入信号"""
        mock_clob_instance = Mock()
        mock_clob_instance.get_usdc_balance.return_value = 1000.0
        mock_clob_instance.get_tick_size.return_value = "0.01"
        mock_clob_instance.get_neg_risk.return_value = False
        mock_clob_instance.get_order_book.return_value = {
            "asks": [{"price": "0.51", "size": "100"}]
        }
        mock_clob_instance.create_and_submit_order.return_value = {
            "success": True,
            "orderID": "order_123",
            "status": "matched",
            "errorMsg": ""
        }
        mock_clob.return_value = mock_clob_instance
        
        mock_redis_instance = Mock()
        mock_redis_instance._is_connected = True
        mock_redis_instance.publish_message.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        executor = OrderExecutor(config=self.mock_config)
        executor.initialize()
        
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=100,
            confidence=0.85,
            strategy="test",
            timestamp=1234567890
        )
        
        executor._handle_trading_signal(signal)
        
        mock_clob_instance.create_and_submit_order.assert_called_once()
    
    @patch('modules.order_executor.main.ClobClientWrapper')
    @patch('modules.order_executor.main.RedisClient')
    def test_handle_trading_signal_low_confidence(self, mock_redis, mock_clob):
        """测试处理低置信度信号"""
        mock_clob_instance = Mock()
        mock_clob.return_value = mock_clob_instance
        
        mock_redis_instance = Mock()
        mock_redis_instance._is_connected = True
        mock_redis.return_value = mock_redis_instance
        
        executor = OrderExecutor(config=self.mock_config)
        executor.initialize()
        
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=100,
            confidence=0.50,
            strategy="test",
            timestamp=1234567890
        )
        
        executor._handle_trading_signal(signal)
        
        mock_clob_instance.create_and_submit_order.assert_not_called()
    
    @patch('modules.order_executor.main.ClobClientWrapper')
    @patch('modules.order_executor.main.RedisClient')
    def test_publish_trade_result(self, mock_redis, mock_clob):
        """测试发布交易结果"""
        mock_clob_instance = Mock()
        mock_clob.return_value = mock_clob_instance
        
        mock_redis_instance = Mock()
        mock_redis_instance._is_connected = True
        mock_redis_instance.publish_message.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        executor = OrderExecutor(config=self.mock_config)
        executor.initialize()
        
        signal = TradingSignal(
            signal_id="test_001",
            token_id="token_123",
            market_id="market_456",
            side="BUY",
            price=0.50,
            size=100,
            confidence=0.85,
            strategy="test",
            timestamp=1234567890
        )
        
        result = OrderResult(
            success=True,
            order_id="order_123",
            status="matched",
            filled_size=100,
            avg_price=0.50,
            fee=0.90
        )
        
        executor._publish_trade_result(signal, result)
        
        mock_redis_instance.publish_message.assert_called_once()
    
    def test_signal_handler_setup(self):
        """测试信号处理器设置"""
        executor = OrderExecutor(config=self.mock_config)
        
        assert executor._shutdown_requested is False
    
    def test_stop_executor(self):
        """测试停止执行器"""
        executor = OrderExecutor(config=self.mock_config)
        executor._running = True
        
        executor.stop()
        
        assert executor._running is False
