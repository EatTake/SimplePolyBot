"""
市场生命周期管理模块测试
"""

import time
import pytest

from modules.strategy_engine.market_lifecycle import (
    MarketLifecycleManager,
    MarketCycle,
    MarketPhase,
    get_market_cycle,
)


class TestMarketLifecycleManager:
    """MarketLifecycleManager 测试类"""
    
    def test_create_manager(self):
        """测试创建管理器"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        assert manager.cycle_duration == 300
        assert manager.cycle_offset == 0
    
    def test_calculate_cycle_start_time(self):
        """测试周期起始时间计算"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        timestamp = 1000.0
        cycle_start = manager.calculate_cycle_start_time(timestamp)
        
        assert cycle_start == 900.0
        
        timestamp = 1200.0
        cycle_start = manager.calculate_cycle_start_time(timestamp)
        assert cycle_start == 1200.0
    
    def test_calculate_relative_time(self):
        """测试相对时间计算"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        relative_time = manager.calculate_relative_time(timestamp=1000.0)
        
        assert relative_time == 100.0
    
    def test_calculate_time_remaining(self):
        """测试剩余时间计算"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        time_remaining = manager.calculate_time_remaining(timestamp=1000.0)
        
        assert time_remaining == 200.0
    
    def test_get_current_cycle(self):
        """测试获取当前周期"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        cycle = manager.get_current_cycle()
        
        assert isinstance(cycle, MarketCycle)
        assert cycle.cycle_id >= 1
        assert cycle.phase in MarketPhase
        assert cycle.relative_time >= 0
        assert cycle.time_remaining >= 0
    
    def test_set_and_get_start_price(self):
        """测试设置和获取起始价格"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        manager.get_current_cycle()
        
        assert manager.get_start_price() is None
        
        manager.set_start_price(50000.0)
        
        assert manager.get_start_price() == 50000.0
    
    def test_cycle_transition(self):
        """测试周期切换"""
        manager = MarketLifecycleManager(cycle_duration=1, cycle_offset=0)
        
        cycle1 = manager.get_current_cycle()
        cycle1_id = cycle1.cycle_id
        
        time.sleep(1.5)
        
        cycle2 = manager.get_current_cycle()
        
        assert cycle2.cycle_id > cycle1_id
    
    def test_is_in_trading_window(self):
        """测试交易窗口判断"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        current_time = time.time()
        cycle_start = manager.calculate_cycle_start_time(current_time)
        
        test_time = cycle_start + 200
        time_remaining = manager.calculate_time_remaining(test_time)
        
        assert 10.0 <= time_remaining <= 100.0
    
    def test_get_next_cycle_info(self):
        """测试获取下一周期信息"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        next_start, time_to_next = manager.get_next_cycle_info()
        
        assert next_start > time.time()
        assert time_to_next > 0
        assert time_to_next <= 300
    
    def test_reset(self):
        """测试重置"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        manager.get_current_cycle()
        manager.set_start_price(50000.0)
        
        manager.reset()
        
        assert manager._current_cycle is None
        assert manager._cycle_count == 0
    
    def test_cycle_to_dict(self):
        """测试周期转换为字典"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        cycle = manager.get_current_cycle()
        cycle_dict = cycle.to_dict()
        
        assert isinstance(cycle_dict, dict)
        assert "cycle_id" in cycle_dict
        assert "start_time" in cycle_dict
        assert "end_time" in cycle_dict
        assert "phase" in cycle_dict
    
    def test_market_phases(self):
        """测试市场阶段"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=0)
        
        cycle = manager.get_current_cycle()
        
        assert cycle.phase in [
            MarketPhase.INITIALIZING,
            MarketPhase.ACTIVE,
            MarketPhase.ENDING,
            MarketPhase.CLOSED,
        ]
    
    def test_convenience_function(self):
        """测试便捷函数"""
        cycle = get_market_cycle(cycle_duration=300)
        
        assert isinstance(cycle, MarketCycle)
        assert cycle.cycle_id >= 1
    
    def test_cycle_offset(self):
        """测试周期偏移"""
        manager = MarketLifecycleManager(cycle_duration=300, cycle_offset=100)
        
        timestamp = 1100.0
        cycle_start = manager.calculate_cycle_start_time(timestamp)
        
        assert cycle_start == 1000.0
