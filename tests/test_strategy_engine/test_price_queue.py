"""
价格队列管理模块测试
"""

import time
import pytest

from modules.strategy_engine.price_queue import PriceQueue, PricePoint


class TestPricePoint:
    """PricePoint 测试类"""
    
    def test_create_price_point(self):
        """测试创建价格数据点"""
        point = PricePoint(timestamp=1000.0, price=50000.0)
        
        assert point.timestamp == 1000.0
        assert point.price == 50000.0
    
    def test_invalid_timestamp(self):
        """测试无效时间戳"""
        with pytest.raises(ValueError):
            PricePoint(timestamp=-1.0, price=50000.0)
    
    def test_invalid_price(self):
        """测试无效价格"""
        with pytest.raises(ValueError):
            PricePoint(timestamp=1000.0, price=-100.0)


class TestPriceQueue:
    """PriceQueue 测试类"""
    
    def test_create_queue(self):
        """测试创建队列"""
        queue = PriceQueue(window_seconds=180, max_size=10000)
        
        assert queue.window_seconds == 180
        assert queue.max_size == 10000
        assert queue.size() == 0
        assert queue.is_empty()
    
    def test_push_and_get(self):
        """测试推送和获取数据"""
        queue = PriceQueue(window_seconds=180)
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time)
        queue.push(price=50100.0, timestamp=current_time + 10)
        
        assert queue.size() == 2
        assert not queue.is_empty()
        
        prices = queue.get_prices()
        assert len(prices) == 2
        assert prices[0] == 50000.0
        assert prices[1] == 50100.0
    
    def test_get_latest_price(self):
        """测试获取最新价格"""
        queue = PriceQueue(window_seconds=180)
        
        assert queue.get_latest_price() is None
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time)
        queue.push(price=50100.0, timestamp=current_time + 10)
        
        assert queue.get_latest_price() == 50100.0
    
    def test_get_earliest_price(self):
        """测试获取最早价格"""
        queue = PriceQueue(window_seconds=180)
        
        assert queue.get_earliest_price() is None
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time)
        queue.push(price=50100.0, timestamp=current_time + 10)
        
        assert queue.get_earliest_price() == 50000.0
    
    def test_get_price_range(self):
        """测试获取价格范围"""
        queue = PriceQueue(window_seconds=180)
        
        min_price, max_price = queue.get_price_range()
        assert min_price is None
        assert max_price is None
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time)
        queue.push(price=50500.0, timestamp=current_time + 10)
        queue.push(price=50200.0, timestamp=current_time + 20)
        
        min_price, max_price = queue.get_price_range()
        assert min_price == 50000.0
        assert max_price == 50500.0
    
    def test_clear_queue(self):
        """测试清空队列"""
        queue = PriceQueue(window_seconds=180)
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time)
        queue.push(price=50100.0, timestamp=current_time + 10)
        
        assert queue.size() == 2
        
        queue.clear()
        
        assert queue.size() == 0
        assert queue.is_empty()
    
    def test_get_time_span(self):
        """测试获取时间跨度"""
        queue = PriceQueue(window_seconds=180)
        
        assert queue.get_time_span() == 0.0
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time)
        assert queue.get_time_span() == 0.0
        
        queue.push(price=50100.0, timestamp=current_time + 100)
        queue.push(price=50200.0, timestamp=current_time + 200)
        
        time_span = queue.get_time_span()
        assert time_span == pytest.approx(200.0, rel=1e-2)
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        queue = PriceQueue(window_seconds=180)
        
        stats = queue.get_statistics()
        assert stats["size"] == 0
        assert stats["min_price"] is None
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time)
        queue.push(price=50500.0, timestamp=current_time + 10)
        queue.push(price=50200.0, timestamp=current_time + 20)
        
        stats = queue.get_statistics()
        assert stats["size"] == 3
        assert stats["min_price"] == 50000.0
        assert stats["max_price"] == 50500.0
        assert stats["avg_price"] == pytest.approx(50233.33, rel=1e-2)
        assert stats["latest_price"] == 50200.0
    
    def test_timestamps_and_prices(self):
        """测试获取时间戳和价格数组"""
        queue = PriceQueue(window_seconds=180)
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time)
        queue.push(price=50100.0, timestamp=current_time + 10)
        
        timestamps, prices = queue.get_timestamps_and_prices()
        
        assert len(timestamps) == 2
        assert len(prices) == 2
        assert timestamps[0] == current_time
        assert prices[0] == 50000.0
    
    def test_get_latest_n(self):
        """测试获取最新 n 个数据点"""
        queue = PriceQueue(window_seconds=180)
        
        current_time = time.time()
        for i in range(5):
            queue.push(price=50000.0 + i * 100, timestamp=current_time + i * 10)
        
        latest_2 = queue.get_latest(2)
        assert len(latest_2) == 2
        assert latest_2[0].price == 50300.0
        assert latest_2[1].price == 50400.0
        
        latest_10 = queue.get_latest(10)
        assert len(latest_10) == 5
    
    def test_max_size_limit(self):
        """测试最大容量限制"""
        queue = PriceQueue(window_seconds=180, max_size=5)
        
        current_time = time.time()
        for i in range(10):
            queue.push(price=50000.0 + i * 100, timestamp=current_time + i * 10)
        
        assert queue.size() == 5
        
        prices = queue.get_prices()
        assert prices[0] == 50500.0
        assert prices[-1] == 50900.0
    
    def test_cleanup_expired(self):
        """测试过期数据清理"""
        queue = PriceQueue(window_seconds=10)
        
        current_time = time.time()
        queue.push(price=50000.0, timestamp=current_time - 20)
        queue.push(price=50100.0, timestamp=current_time - 5)
        queue.push(price=50200.0, timestamp=current_time)
        
        queue._cleanup_expired()
        
        assert queue.size() == 2
