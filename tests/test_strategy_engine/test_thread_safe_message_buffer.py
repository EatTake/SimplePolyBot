"""
策略引擎 Bug #9 修复测试

测试 _message_buffer 线程安全性
验证从 List 改为 queue.Queue 后的并发安全行为
"""

import queue
import time
import threading
import pytest
from unittest.mock import Mock, patch, MagicMock


class MockConfig:
    """Mock 配置类"""
    def get_redis_config(self):
        redis_config = Mock()
        redis_config.host = "localhost"
        redis_config.port = 6379
        redis_config.password = None
        redis_config.db = 0
        redis_config.max_connections = 10
        redis_config.min_idle_connections = 1
        redis_config.connection_timeout = 5
        redis_config.socket_timeout = 5
        redis_config.max_attempts = 3
        redis_config.retry_delay = 0.5
        return redis_config


def create_strategy_engine():
    """
    创建 StrategyEngine 实例（跳过 Redis 连接）
    
    使用 mock 替换 Redis 相关组件，避免实际连接
    """
    from modules.strategy_engine.main import StrategyEngine
    
    with patch.object(StrategyEngine, '_initialize_components'):
        engine = StrategyEngine(config=MockConfig())
    
    return engine


class TestMessageBufferThreadSafety:
    """
    Bug #9 测试：_message_buffer 线程安全性
    
    测试修复逻辑：
    - _message_buffer 是 queue.Queue 类型（线程安全）
    - 多线程并发写入不会导致数据丢失或竞态条件
    - 缓冲区满时正确丢弃消息并记录警告
    - flush 操作原子性地清空缓冲区
    """
    
    def test_message_buffer_is_queue_type(self):
        """
        测试 1：_message_buffer 是 queue.Queue 类型
        
        验证初始化后 _message_buffer 是线程安全的 Queue 实例
        """
        engine = create_strategy_engine()
        
        assert isinstance(engine._message_buffer, queue.Queue)
        assert engine._message_buffer.maxsize == 1000
    
    def test_single_thread_message_put_and_get(self):
        """
        测试 2：单线程环境下消息的 put 和 get 操作
        
        验证基本功能正常：
        - put_nowait 成功添加消息
        - get_nowait 成功取出消息
        - empty() 正确判断队列状态
        """
        engine = create_strategy_engine()
        
        test_messages = [
            {"price": 50000.0, "timestamp": time.time()},
            {"price": 50001.0, "timestamp": time.time() + 1},
            {"price": 50002.0, "timestamp": time.time() + 2},
        ]
        
        for msg in test_messages:
            engine._message_buffer.put_nowait(msg)
        
        assert engine._message_buffer.qsize() == 3
        
        retrieved_messages = []
        while not engine._message_buffer.empty():
            retrieved_messages.append(engine._message_buffer.get_nowait())
        
        assert len(retrieved_messages) == 3
        assert retrieved_messages == test_messages
        assert engine._message_buffer.empty()
    
    def test_concurrent_writes_no_data_loss(self):
        """
        测试 3：多线程并发写入无数据丢失
        
        场景：
        - 启动多个线程同时向 _message_buffer 写入消息
        - 每个线程写入固定数量的消息
        - 验证所有消息都被成功接收，无丢失
        """
        engine = create_strategy_engine()
        
        num_threads = 10
        messages_per_thread = 100
        total_expected = num_threads * messages_per_thread
        
        errors = []
        
        def writer_thread(thread_id):
            """写入线程函数"""
            try:
                for i in range(messages_per_thread):
                    msg = {
                        "price": 50000.0 + thread_id * 100 + i,
                        "timestamp": time.time(),
                        "thread_id": thread_id,
                        "msg_index": i
                    }
                    engine._message_buffer.put_nowait(msg)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=writer_thread, args=(i,))
            for i in range(num_threads)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join(timeout=5.0)
        
        assert len(errors) == 0, f"写入过程中发生错误: {errors}"
        
        actual_count = engine._message_buffer.qsize()
        assert actual_count == total_expected, (
            f"预期 {total_expected} 条消息，实际 {actual_count} 条"
        )
    
    def test_concurrent_write_and_read_safety(self):
        """
        测试 4：多线程并发读写安全性
        
        场景：
        - 多个线程持续写入消息
        - 主线程持续读取并处理消息
        - 验证无异常、无数据损坏、无死锁
        """
        engine = create_strategy_engine()
        
        num_writer_threads = 5
        messages_per_writer = 200
        write_duration = 1.0  # 写入持续时间（秒）
        
        received_messages = []
        stop_event = threading.Event()
        errors = []
        
        def writer_thread(thread_id):
            """写入线程函数"""
            try:
                start_time = time.time()
                msg_count = 0
                while (time.time() - start_time) < write_duration and not stop_event.is_set():
                    msg = {
                        "price": 50000.0 + thread_id + msg_count * 0.001,
                        "timestamp": time.time(),
                    }
                    try:
                        engine._message_buffer.put_nowait(msg)
                        msg_count += 1
                    except queue.Full:
                        pass  # 缓冲区满时跳过
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        def reader_thread():
            """读取线程函数"""
            try:
                while not stop_event.is_set() or not engine._message_buffer.empty():
                    try:
                        msg = engine._message_buffer.get_nowait()
                        received_messages.append(msg)
                    except queue.Empty:
                        time.sleep(0.001)
            except Exception as e:
                errors.append(("reader", str(e)))
        
        writer_threads = [
            threading.Thread(target=writer_thread, args=(i,))
            for i in range(num_writer_threads)
        ]
        
        reader = threading.Thread(target=reader_thread)
        
        reader.start()
        for t in writer_threads:
            t.start()
        
        for t in writer_threads:
            t.join(timeout=write_duration + 2.0)
        
        stop_event.set()
        reader.join(timeout=2.0)
        
        assert len(errors) == 0, f"并发读写过程中发生错误: {errors}"
        assert len(received_messages) > 0, "应该接收到至少一条消息"
    
    def test_buffer_full_drops_message_with_warning(self):
        """
        测试 5：缓冲区满时丢弃消息并记录警告
        
        场景：
        - 创建 maxsize=10 的小容量队列
        - 尝试放入超过容量的消息
        - 验证超出部分被丢弃并触发 warning 日志
        """
        from modules.strategy_engine.main import StrategyEngine
        
        with patch.object(StrategyEngine, '_initialize_components'):
            engine = StrategyEngine(config=MockConfig())
            engine._message_buffer = queue.Queue(maxsize=10)
        
        for i in range(10):
            engine._message_buffer.put_nowait({"price": i})
        
        assert engine._message_buffer.full()
        
        with patch('modules.strategy_engine.main.logger') as mock_logger:
            try:
                engine._message_buffer.put_nowait({"price": 999})
                assert False, "应该抛出 queue.Full 异常"
            except queue.Full:
                pass
            
            mock_logger.warning.assert_not_called()
        
        with patch('modules.strategy_engine.main.logger') as mock_logger:
            engine._handle_market_data({"price": 999, "timestamp": time.time()})
            
            warning_calls = [
                call for call in mock_logger.warning.call_args_list
                if "消息缓冲区已满" in str(call)
            ]
            
            assert len(warning_calls) == 1, "应该记录一次缓冲区满警告"
    
    def test_flush_message_buffer_clears_all_messages(self):
        """
        测试 6：_flush_message_buffer 清空所有消息
        
        验证：
        - flush 前队列有消息
        - flush 后队列为空
        - 所有消息都被传递给 _process_messages_batch
        """
        engine = create_strategy_engine()
        
        test_messages = [
            {"price": 50000.0, "timestamp": time.time()},
            {"price": 50001.0, "timestamp": time.time() + 1},
        ]
        
        for msg in test_messages:
            engine._message_buffer.put_nowait(msg)
        
        processed_batches = []
        
        with patch.object(engine, '_process_messages_batch') as mock_process:
            engine._flush_message_buffer()
            
            mock_process.assert_called_once()
            processed_batch = mock_process.call_args[0][0]
            
            assert len(processed_batch) == 2
            assert processed_batch == test_messages
        
        assert engine._message_buffer.empty()
    
    def test_flush_empty_buffer_does_not_trigger_processing(self):
        """
        测试 7：空缓冲区 flush 不触发批量处理
        
        验证：
        - 空队列调用 _flush_message_buffer 不触发 _process_messages_batch
        - _last_batch_process_time 不更新
        """
        engine = create_strategy_engine()
        
        initial_time = engine._last_batch_process_time
        
        with patch.object(engine, '_process_messages_batch') as mock_process:
            engine._flush_message_buffer()
            
            mock_process.assert_not_called()
            assert engine._last_batch_process_time == initial_time
    
    def test_check_and_flush_buffer_uses_qsize(self):
        """
        测试 8：_check_and_flush_buffer 使用 qsize() 方法
        
        验证：
        - 当 qsize() >= batch_size_threshold 时触发 flush
        - 当 qsize() < batch_size_threshold 且未超时时，不触发 flush
        """
        engine = create_strategy_engine()
        
        engine._batch_size_threshold = 5
        engine._last_batch_process_time = time.time()
        
        with patch.object(engine, '_flush_message_buffer') as mock_flush:
            for i in range(4):
                engine._message_buffer.put_nowait({"price": i})
            
            engine._check_and_flush_buffer()
            
            mock_flush.assert_not_called()
            
            engine._message_buffer.put_nowait({"price": 4})
            
            engine._check_and_flush_buffer()
            
            mock_flush.assert_called_once()
    
    def test_handle_market_data_uses_put_nowait(self):
        """
        测试 9：_handle_market_data 使用 put_nowait 写入
        
        验证：
        - 调用 _handle_market_data 后消息在队列中
        - 使用的是非阻塞式 put_nowait
        """
        engine = create_strategy_engine()
        
        test_data = {"price": 50000.0, "timestamp": time.time()}
        
        with patch.object(engine, '_check_and_flush_buffer'):
            engine._handle_market_data(test_data)
        
        assert engine._message_buffer.qsize() == 1
        
        retrieved = engine._message_buffer.get_nowait()
        assert retrieved == test_data
    
    def test_stress_test_high_throughput(self):
        """
        测试 10：高吞吐量压力测试
        
        场景：
        - 单线程快速写入 10000 条消息
        - 另一个线程持续读取
        - 验证系统稳定性和性能
        """
        engine = create_strategy_engine()
        
        total_messages = 10000
        received_count = [0]
        errors = []
        stop_event = threading.Event()
        
        def high_speed_writer():
            """高速写入线程"""
            try:
                for i in range(total_messages):
                    msg = {"price": 50000.0 + i * 0.0001, "timestamp": time.time()}
                    while True:
                        try:
                            engine._message_buffer.put_nowait(msg)
                            break
                        except queue.Full:
                            time.sleep(0.0001)
            except Exception as e:
                errors.append(("writer", str(e)))
            finally:
                stop_event.set()
        
        def continuous_reader():
            """持续读取线程"""
            try:
                while not stop_event.is_set() or not engine._message_buffer.empty():
                    try:
                        engine._message_buffer.get_nowait()
                        received_count[0] += 1
                    except queue.Empty:
                        time.sleep(0.0001)
            except Exception as e:
                errors.append(("reader", str(e)))
        
        writer = threading.Thread(target=high_speed_writer)
        reader = threading.Thread(target=continuous_reader)
        
        writer.start()
        reader.start()
        
        writer.join(timeout=30.0)
        reader.join(timeout=10.0)
        
        assert len(errors) == 0, f"压力测试中发生错误: {errors}"
        assert received_count[0] == total_messages, (
            f"预期接收 {total_messages} 条消息，实际接收 {received_count[0]} 条"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
