"""
批量消息处理模块测试
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from modules.strategy_engine.main import StrategyEngine


class TestProcessMessagesBatch:
    """_process_messages_batch 方法测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建 StrategyEngine 测试实例（跳过 Redis 连接）"""
        with patch.object(StrategyEngine, '_initialize_components'):
            with patch.object(StrategyEngine, '_setup_signal_handlers'):
                engine = StrategyEngine.__new__(StrategyEngine)
                engine.config = Mock()
                engine._running = False
                engine._shutdown_requested = False
                engine._message_buffer = []
                engine._last_batch_process_time = time.time()
                engine._batch_size_threshold = 10
                engine._batch_timeout_seconds = 1.0
                engine.price_queue = Mock()
                return engine
    
    def test_small_batch_sequential_processing(self, engine, caplog):
        """测试小批量（<10条）顺序处理"""
        messages = [
            {"price": 50000.0 + i, "timestamp": time.time() + i}
            for i in range(5)
        ]
        
        engine._process_messages_batch(messages)
        
        assert engine.price_queue.push.call_count == 5
        
        for i, call in enumerate(engine.price_queue.push.call_args_list):
            assert call[1]["price"] == 50000.0 + i
    
    def test_large_batch_parallel_processing(self, engine, caplog):
        """测试大批量（>=10条）并行处理"""
        messages = [
            {"price": 50000.0 + i, "timestamp": time.time() + i}
            for i in range(15)
        ]
        
        engine._process_messages_batch(messages)
        
        assert engine.price_queue.push.call_count == 15
    
    def test_batch_processing_correctness(self, engine):
        """测试处理结果正确性"""
        messages = [
            {"price": 50000.0 + i * 100, "timestamp": 1000.0 + i}
            for i in range(12)
        ]
        
        engine._process_messages_batch(messages)
        
        processed_prices = [call[1]["price"] for call in engine.price_queue.push.call_args_list]
        expected_prices = [50000.0 + i * 100 for i in range(12)]
        
        assert sorted(processed_prices) == sorted(expected_prices)
    
    def test_exception_handling_single_failure(self, engine, caplog):
        """测试异常处理：单条失败不影响其他"""
        messages = [
            {"price": 50000.0, "timestamp": 1000.0},
            {},  # 缺少 price 字段，会触发警告但不会抛出异常
            {"price": 50200.0, "timestamp": 1002.0},
        ]
        
        engine._process_messages_batch(messages)
        
        assert engine.price_queue.push.call_count == 2
    
    def test_exception_handling_with_error(self, engine, caplog):
        """测试异常处理：模拟 _handle_single_message 抛出异常（大批量并行场景）"""
        original_handle = engine._handle_single_message
        
        call_count = [0]
        
        def mock_handle(data):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("模拟错误")
            original_handle(data)
        
        engine._handle_single_message = mock_handle
        
        messages = [
            {"price": 50000.0 + i, "timestamp": 1000.0 + i}
            for i in range(12)  # 使用 >= 10 条消息以触发并行处理
        ]
        
        engine._process_messages_batch(messages)
        
        assert engine.price_queue.push.call_count == 11  # 12 - 1 条失败的
    
    def test_performance_monitoring_log(self, engine, caplog):
        """测试性能监控日志"""
        messages = [{"price": 50000.0, "timestamp": 1000.0} for _ in range(8)]
        
        with caplog.at_level("INFO"):
            engine._process_messages_batch(messages)
        
        assert len(caplog.records) > 0, "应该有日志记录"
        
        info_records = [r for r in caplog.records if r.levelno == 20]  # INFO level
        assert len(info_records) > 0, "应该有 INFO 级别的日志"
    
    def test_empty_message_list(self, engine, caplog):
        """测试空消息列表"""
        with caplog.at_level("INFO"):
            engine._process_messages_batch([])
        
        assert engine.price_queue.push.call_count == 0
        
        assert len(caplog.records) > 0, "应该有日志记录"
    
    def test_boundary_batch_size(self, engine):
        """测试边界批量大小（恰好等于阈值）"""
        messages = [
            {"price": 50000.0 + i, "timestamp": 1000.0 + i}
            for i in range(10)
        ]
        
        engine._process_messages_batch(messages)
        
        assert engine.price_queue.push.call_count == 10


class TestMessageBuffer:
    """消息缓冲区管理测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建 StrategyEngine 测试实例"""
        with patch.object(StrategyEngine, '_initialize_components'):
            with patch.object(StrategyEngine, '_setup_signal_handlers'):
                engine = StrategyEngine.__new__(StrategyEngine)
                engine.config = Mock()
                engine._running = False
                engine._shutdown_requested = False
                engine._message_buffer = []
                engine._last_batch_process_time = time.time()
                engine._batch_size_threshold = 10
                engine._batch_timeout_seconds = 1.0
                engine.price_queue = Mock()
                engine._process_messages_batch = Mock()
                return engine
    
    def test_buffer_accumulation(self, engine):
        """测试缓冲区积累"""
        for i in range(5):
            engine._handle_market_data({"price": 50000.0 + i})
        
        assert len(engine._message_buffer) == 5
        assert not engine._process_messages_batch.called
    
    def test_auto_flush_on_threshold(self, engine):
        """测试达到阈值自动刷新"""
        for i in range(10):
            engine._handle_market_data({"price": 50000.0 + i})
        
        assert len(engine._message_buffer) == 0
        assert engine._process_messages_batch.called
    
    def test_flush_clears_buffer(self, engine):
        """测试刷新清空缓冲区"""
        engine._message_buffer = [{"price": 50000.0}, {"price": 50100.0}]
        
        engine._flush_message_buffer()
        
        assert len(engine._message_buffer) == 0
        assert engine._process_messages_batch.called
    
    def test_check_and_flush_by_size(self, engine):
        """测试基于大小的刷新检查"""
        engine._message_buffer = [{"price": 50000.0} for _ in range(10)]
        
        engine._check_and_flush_buffer()
        
        assert engine._process_messages_batch.called
    
    def test_check_and_flush_by_time(self, engine):
        """测试基于时间的刷新检查"""
        engine._message_buffer = [{"price": 50000.0}]
        engine._last_batch_process_time = time.time() - 2.0  # 超过超时时间
        
        engine._check_and_flush_buffer()
        
        assert engine._process_messages_batch.called
    
    def test_no_flush_when_conditions_not_met(self, engine):
        """测试条件不满足时不刷新"""
        engine._message_buffer = [{"price": 50000.0}]
        engine._last_batch_process_time = time.time()  # 刚刚刷新过
        
        engine._check_and_flush_buffer()
        
        assert not engine._process_messages_batch.called


class TestHandleSingleMessage:
    """_handle_single_message 方法测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建 StrategyEngine 测试实例"""
        with patch.object(StrategyEngine, '_initialize_components'):
            with patch.object(StrategyEngine, '_setup_signal_handlers'):
                engine = StrategyEngine.__new__(StrategyEngine)
                engine.config = Mock()
                engine.price_queue = Mock()
                return engine
    
    def test_normal_message_handling(self, engine):
        """测试正常消息处理"""
        data = {"price": 50000.0, "timestamp": 1000.0}
        
        engine._handle_single_message(data)
        
        engine.price_queue.push.assert_called_once_with(
            price=50000.0,
            timestamp=1000.0
        )
    
    def test_missing_price_field(self, engine, caplog):
        """测试缺少价格字段"""
        data = {"timestamp": 1000.0}
        
        with caplog.at_level("WARNING"):
            engine._handle_single_message(data)
        
        engine.price_queue.push.assert_not_called()
        
        warning_records = [r for r in caplog.records if r.levelno == 30]  # WARNING level
        assert len(warning_records) > 0, "应该有 WARNING 级别的日志"
    
    def test_missing_timestamp_uses_current(self, engine):
        """测试缺少时间戳使用当前时间"""
        data = {"price": 50000.0}
        
        with patch('modules.strategy_engine.main.time') as mock_time:
            mock_time.time.return_value = 2000.0
            engine._handle_single_message(data)
            
            engine.price_queue.push.assert_called_once_with(
                price=50000.0,
                timestamp=2000.0
            )
    
    def test_prefer_explicit_timestamp_over_underscore(self, engine):
        """测试优先使用显式时间戳而非下划线时间戳"""
        data = {
            "price": 50000.0,
            "timestamp": 1000.0,
            "_timestamp": 2000.0
        }
        
        engine._handle_single_message(data)
        
        engine.price_queue.push.assert_called_once_with(
            price=50000.0,
            timestamp=1000.0
        )


class TestBatchProcessingIntegration:
    """批量处理集成测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建完整的 StrategyEngine 测试实例"""
        with patch.object(StrategyEngine, '_initialize_components'):
            with patch.object(StrategyEngine, '_setup_signal_handlers'):
                engine = StrategyEngine.__new__(StrategyEngine)
                engine.config = Mock()
                engine._running = False
                engine._shutdown_requested = False
                engine._message_buffer = []
                engine._last_batch_process_time = time.time()
                engine._batch_size_threshold = 10
                engine._batch_timeout_seconds = 1.0
                engine.price_queue = Mock()
                return engine
    
    def test_rapid_message_ingestion(self, engine):
        """测试快速消息摄入场景"""
        start_time = time.time()
        
        for i in range(25):
            engine._handle_market_data({
                "price": 50000.0 + i,
                "timestamp": start_time + i * 0.01
            })
        
        total_pushed = sum(
            1 for call in engine.price_queue.push.call_args_list 
            if call[0] == () and 'price' in call[1]
        )
        
        remaining_in_buffer = len(engine._message_buffer)
        
        assert total_pushed + remaining_in_buffer == 25
    
    def test_intermittent_message_flow(self, engine):
        """测试间歇性消息流"""
        for batch in range(3):
            for i in range(3):
                engine._handle_market_data({
                    "price": 50000.0 + batch * 3 + i,
                    "timestamp": time.time()
                })
            
            if batch < 2:
                time.sleep(0.05)
        
        total_in_system = (
            len(engine._message_buffer) + 
            sum(1 for call in engine.price_queue.push.call_args_list if call[0] == () and 'price' in call[1])
        )
        
        assert total_in_system == 9
    
    def test_concurrent_safety(self, engine):
        """测试并发安全性"""
        import threading
        
        def send_messages(count, offset):
            for i in range(count):
                engine._handle_market_data({
                    "price": 50000.0 + offset + i,
                    "timestamp": time.time()
                })
        
        threads = []
        for t in range(4):
            thread = threading.Thread(target=send_messages, args=(5, t * 5))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
        
        total_pushed = sum(
            1 for call in engine.price_queue.push.call_args_list 
            if call[0] == () and 'price' in call[1]
        )
        
        total_in_buffer_or_processed = len(engine._message_buffer) + total_pushed
        
        assert total_in_buffer_or_processed == 20
