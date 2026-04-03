"""
策略引擎 Bug #8 修复测试

测试周期切换时 PriceQueue 清空逻辑
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Optional

from modules.strategy_engine.price_queue import PriceQueue
from modules.strategy_engine.market_lifecycle import (
    MarketLifecycleManager,
    MarketCycle,
    MarketPhase,
)


@dataclass
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


class TestBug8PriceQueueClearOnCycleSwitch:
    """
    Bug #8 测试：周期切换时清空 PriceQueue
    
    测试修复逻辑：
    - 首次运行时正常设置 start_price 并更新 _last_cycle_id
    - cycle_id 变化时清空 PriceQueue
    - cycle_id 不变时不清空 PriceQueue
    - 日志记录包含正确的旧/新 cycle_id
    """
    
    def _create_strategy_engine(self):
        """
        创建 StrategyEngine 实例（跳过 Redis 连接）
        
        使用 mock 替换 Redis 相关组件，避免实际连接
        """
        from modules.strategy_engine.main import StrategyEngine
        
        with patch.object(StrategyEngine, '_initialize_components'):
            engine = StrategyEngine(config=MockConfig())
            engine._last_cycle_id = None
            
            engine.price_queue = PriceQueue(window_seconds=180)
            engine.lifecycle_manager = MarketLifecycleManager(
                cycle_duration=300
            )
            
            engine.regression = Mock()
            engine.safety_cushion = Mock()
            engine.signal_generator = Mock()
            engine.publisher = Mock()
        
        return engine
    
    def test_first_run_sets_start_price_and_updates_cycle_id(self):
        """
        测试 1：首次运行时正常设置 start_price 并更新 _last_cycle_id
        
        场景：
        - _last_cycle_id 初始为 None
        - 第一次调用 _execute_strategy_cycle() 时 cycle_id=1
        - 应该正常设置 start_price，并更新 _last_cycle_id=1
        - 会调用 clear() 因为从 None 到 1 也是周期切换
        """
        engine = self._create_strategy_engine()
        
        assert engine._last_cycle_id is None
        
        for i in range(15):
            engine.price_queue.push(price=50000.0 + i * 10, timestamp=time.time() - (14 - i))
        
        with patch('modules.strategy_engine.main.logger') as mock_logger:
            with patch.object(engine.lifecycle_manager, 'get_current_cycle') as mock_get_cycle:
                mock_cycle = Mock(spec=MarketCycle)
                mock_cycle.cycle_id = 1
                mock_cycle.start_price = None
                mock_cycle.time_remaining = 200.0
                
                mock_get_cycle.return_value = mock_cycle
                
                with patch.object(engine.lifecycle_manager, 'set_start_price') as mock_set_price:
                    with patch.object(engine.signal_generator, 'generate_signal') as mock_signal:
                        with patch.object(engine.publisher, 'publish_signal') as mock_publish:
                            mock_signal.return_value = Mock()
                            
                            engine._execute_strategy_cycle()
                            
                            mock_set_price.assert_called_once()
                            
                            assert engine._last_cycle_id == 1
                            assert engine.price_queue.size() == 0
                            
                            mock_logger.info.assert_any_call(
                                "检测到周期切换，清空 PriceQueue",
                                old_cycle_id=None,
                                new_cycle_id=1,
                                queue_size_before_clear=15
                            )
    
    def test_cycle_change_clears_price_queue(self):
        """
        测试 2：cycle_id 变化时 PriceQueue 被清空
        
        场景：
        - 上一次 cycle_id = 1
        - 当前 cycle_id = 2
        - 应该检测到周期切换并清空 PriceQueue
        """
        engine = self._create_strategy_engine()
        
        engine._last_cycle_id = 1
        
        for i in range(15):
            engine.price_queue.push(price=50000.0 + i * 10, timestamp=time.time() - (14 - i))
        
        assert engine.price_queue.size() == 15
        
        with patch('modules.strategy_engine.main.logger') as mock_logger:
            with patch.object(engine.lifecycle_manager, 'get_current_cycle') as mock_get_cycle:
                mock_cycle = Mock(spec=MarketCycle)
                mock_cycle.cycle_id = 2
                mock_cycle.start_price = 50050.0
                mock_cycle.time_remaining = 250.0
                
                mock_get_cycle.return_value = mock_cycle
                
                with patch.object(engine.signal_generator, 'generate_signal') as mock_signal:
                    with patch.object(engine.publisher, 'publish_signal') as mock_publish:
                        mock_signal.return_value = Mock()
                        
                        engine._execute_strategy_cycle()
                        
                        assert engine.price_queue.size() == 0, \
                            f"期望 PriceQueue 被清空（size=0），但实际 size={engine.price_queue.size()}"
                        assert engine._last_cycle_id == 2
                        
                        mock_logger.info.assert_any_call(
                            "检测到周期切换，清空 PriceQueue",
                            old_cycle_id=1,
                            new_cycle_id=2,
                            queue_size_before_clear=15
                        )
    
    def test_same_cycle_does_not_clear_price_queue(self):
        """
        测试 3：cycle_id 不变时 PriceQueue 不被清空
        
        场景：
        - 上一次 cycle_id = 1
        - 当前 cycle_id = 1（相同）
        - 不应该触发清空操作
        """
        engine = self._create_strategy_engine()
        
        engine._last_cycle_id = 1
        
        for i in range(10):
            engine.price_queue.push(price=50000.0 + i * 5, timestamp=time.time() - (9 - i))
        
        initial_size = engine.price_queue.size()
        
        with patch('modules.strategy_engine.main.logger') as mock_logger:
            with patch.object(engine.lifecycle_manager, 'get_current_cycle') as mock_get_cycle:
                mock_cycle = Mock(spec=MarketCycle)
                mock_cycle.cycle_id = 1
                mock_cycle.start_price = 50025.0
                mock_cycle.time_remaining = 150.0
                
                mock_get_cycle.return_value = mock_cycle
                
                with patch.object(engine.signal_generator, 'generate_signal') as mock_signal:
                    with patch.object(engine.publisher, 'publish_signal') as mock_publish:
                        mock_signal.return_value = Mock()
                        
                        engine._execute_strategy_cycle()
                        
                        assert engine.price_queue.size() == initial_size, \
                            f"期望 PriceQueue 不变（size={initial_size}），但实际 size={engine.price_queue.size()}"
                        assert engine._last_cycle_id == 1
                        
                        clear_calls = [
                            call for call in mock_logger.info.call_args_list
                            if len(call[0]) > 0 and call[0][0] == "检测到周期切换，清空 PriceQueue"
                        ]
                        
                        assert len(clear_calls) == 0, "不应该有周期切换日志"
    
    def test_log_contains_correct_old_new_cycle_ids(self):
        """
        测试 4：日志记录包含正确的旧/新 cycle_id
        
        场景：
        - 从 cycle_id=3 切换到 cycle_id=5（模拟跨周期）
        - 日志应记录 old_cycle_id=3, new_cycle_id=5
        - 日志应记录清空前队列大小
        """
        engine = self._create_strategy_engine()
        
        engine._last_cycle_id = 3
        
        test_prices = [50000.0, 50010.0, 50020.0, 50030.0,
                      50040.0, 50050.0, 50060.0, 50070.0,
                      50080.0, 50090.0, 50100.0, 50110.0]
        
        for i, price in enumerate(test_prices):
            engine.price_queue.push(price=price, timestamp=time.time() - (len(test_prices) - i))
        
        queue_size_before = engine.price_queue.size()
        
        with patch('modules.strategy_engine.main.logger') as mock_logger:
            with patch.object(engine.lifecycle_manager, 'get_current_cycle') as mock_get_cycle:
                mock_cycle = Mock(spec=MarketCycle)
                mock_cycle.cycle_id = 5
                mock_cycle.start_price = 50055.0
                mock_cycle.time_remaining = 280.0
                
                mock_get_cycle.return_value = mock_cycle
                
                with patch.object(engine.signal_generator, 'generate_signal') as mock_signal:
                    with patch.object(engine.publisher, 'publish_signal') as mock_publish:
                        mock_signal.return_value = Mock()
                        
                        engine._execute_strategy_cycle()
                        
                        log_calls = mock_logger.info.call_args_list
                        
                        target_log = None
                        for call in log_calls:
                            if len(call[0]) > 0 and call[0][0] == "检测到周期切换，清空 PriceQueue":
                                target_log = call
                                break
                        
                        assert target_log is not None, "未找到周期切换日志"
                        
                        args, kwargs = target_log
                        
                        assert kwargs['old_cycle_id'] == 3, \
                            f"期望 old_cycle_id=3，实际={kwargs.get('old_cycle_id')}"
                        assert kwargs['new_cycle_id'] == 5, \
                            f"期望 new_cycle_id=5，实际={kwargs.get('new_cycle_id')}"
                        assert kwargs['queue_size_before_clear'] == queue_size_before, \
                            f"期望 queue_size_before_clear={queue_size_before}，实际={kwargs.get('queue_size_before_clear')}"
                        
                        assert engine.price_queue.size() == 0, \
                            f"期望 PriceQueue 被清空，但实际 size={engine.price_queue.size()}"
                        assert engine._last_cycle_id == 5, \
                            f"期望 _last_cycle_id=5，但实际={engine._last_cycle_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
