"""
性能基准测试

测试关键路径的性能指标：
- OLS 回归计算性能
- Redis Pub/Sub 延迟
- 信号生成延迟
- 订单执行延迟
- 整体管道延迟
"""

import pytest
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from modules.strategy_engine.ols_regression import OLSRegression
from modules.strategy_engine.price_queue import PriceQueue
from modules.strategy_engine.safety_cushion import SafetyCushionCalculator
from modules.strategy_engine.signal_generator import SignalGenerator
from modules.strategy_engine.market_lifecycle import MarketLifecycleManager
from shared.redis_client import RedisClient, RedisConnectionConfig


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}
    
    def record(self, name: str, duration: float) -> None:
        if name not in self.measurements:
            self.measurements[name] = []
        self.measurements[name].append(duration)
    
    def get_stats(self, name: str) -> Dict[str, float]:
        if name not in self.measurements or len(self.measurements[name]) == 0:
            return {}
        
        values = self.measurements[name]
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "p95": sorted(values)[int(len(values) * 0.95)] if len(values) > 0 else 0,
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        return {name: self.get_stats(name) for name in self.measurements}


class TestOLSRegressionPerformance:
    """OLS 回归性能测试"""
    
    def test_ols_regression_performance_small_dataset(self):
        """测试小数据集 OLS 回归性能（10-50 个数据点）"""
        metrics = PerformanceMetrics()
        regression = OLSRegression(min_samples=10)
        
        for dataset_size in [10, 20, 30, 40, 50]:
            timestamps = [time.time() - i * 0.1 for i in range(dataset_size)]
            prices = [67000.0 + i * 10 for i in range(dataset_size)]
            
            start_time = time.perf_counter()
            result = regression.fit(timestamps, prices)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            metrics.record(f"ols_{dataset_size}_points", elapsed)
            
            assert result is not None
            assert elapsed < 10, f"OLS 回归耗时 {elapsed:.2f}ms 超过 10ms 阈值"
        
        stats = metrics.get_all_stats()
        print("\nOLS 回归性能统计（小数据集）:")
        for name, stat in stats.items():
            print(f"  {name}: 平均 {stat['mean']:.2f}ms, 中位数 {stat['median']:.2f}ms, 最大 {stat['max']:.2f}ms")
    
    def test_ols_regression_performance_medium_dataset(self):
        """测试中等数据集 OLS 回归性能（100-500 个数据点）"""
        metrics = PerformanceMetrics()
        regression = OLSRegression(min_samples=10)
        
        for dataset_size in [100, 200, 300, 400, 500]:
            timestamps = [time.time() - i * 0.1 for i in range(dataset_size)]
            prices = [67000.0 + i * 0.1 for i in range(dataset_size)]
            
            start_time = time.perf_counter()
            result = regression.fit(timestamps, prices)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            metrics.record(f"ols_{dataset_size}_points", elapsed)
            
            assert result is not None
            assert elapsed < 50, f"OLS 回归耗时 {elapsed:.2f}ms 超过 50ms 阈值"
        
        stats = metrics.get_all_stats()
        print("\nOLS 回归性能统计（中等数据集）:")
        for name, stat in stats.items():
            print(f"  {name}: 平均 {stat['mean']:.2f}ms, 中位数 {stat['median']:.2f}ms, 最大 {stat['max']:.2f}ms")
    
    def test_ols_regression_performance_large_dataset(self):
        """测试大数据集 OLS 回归性能（1000-5000 个数据点）"""
        metrics = PerformanceMetrics()
        regression = OLSRegression(min_samples=10)
        
        for dataset_size in [1000, 2000, 3000, 4000, 5000]:
            timestamps = [time.time() - i * 0.1 for i in range(dataset_size)]
            prices = [67000.0 + i * 0.01 for i in range(dataset_size)]
            
            start_time = time.perf_counter()
            result = regression.fit(timestamps, prices)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            metrics.record(f"ols_{dataset_size}_points", elapsed)
            
            assert result is not None
            assert elapsed < 100, f"OLS 回归耗时 {elapsed:.2f}ms 超过 100ms 阈值"
        
        stats = metrics.get_all_stats()
        print("\nOLS 回归性能统计（大数据集）:")
        for name, stat in stats.items():
            print(f"  {name}: 平均 {stat['mean']:.2f}ms, 中位数 {stat['median']:.2f}ms, 最大 {stat['max']:.2f}ms")


class TestPriceQueuePerformance:
    """价格队列性能测试"""
    
    def test_price_queue_push_performance(self):
        """测试价格队列推入性能"""
        metrics = PerformanceMetrics()
        queue = PriceQueue(window_seconds=180)
        
        for _ in range(1000):
            start_time = time.perf_counter()
            queue.push(price=67000.0, timestamp=time.time())
            elapsed = (time.perf_counter() - start_time) * 1000
            metrics.record("queue_push", elapsed)
        
        stats = metrics.get_stats("queue_push")
        print("\n价格队列推入性能统计:")
        print(f"  平均: {stats['mean']:.4f}ms")
        print(f"  中位数: {stats['median']:.4f}ms")
        print(f"  P95: {stats['p95']:.4f}ms")
        print(f"  最大: {stats['max']:.4f}ms")
        
        assert stats['mean'] < 1, f"平均推入耗时 {stats['mean']:.4f}ms 超过 1ms 阈值"
    
    def test_price_queue_get_range_performance(self):
        """测试价格队列范围查询性能"""
        queue = PriceQueue(window_seconds=180)
        
        for i in range(1000):
            queue.push(price=67000.0 + i * 0.01, timestamp=time.time() - i * 0.1)
        
        metrics = PerformanceMetrics()
        
        for _ in range(100):
            start_time = time.perf_counter()
            timestamps, prices = queue.get_timestamps_and_prices()
            elapsed = (time.perf_counter() - start_time) * 1000
            metrics.record("queue_get_range", elapsed)
        
        stats = metrics.get_stats("queue_get_range")
        print("\n价格队列范围查询性能统计:")
        print(f"  平均: {stats['mean']:.4f}ms")
        print(f"  中位数: {stats['median']:.4f}ms")
        print(f"  P95: {stats['p95']:.4f}ms")
        print(f"  最大: {stats['max']:.4f}ms")
        
        assert stats['mean'] < 5, f"平均查询耗时 {stats['mean']:.4f}ms 超过 5ms 阈值"


class TestSafetyCushionPerformance:
    """安全垫计算性能测试"""
    
    def test_safety_cushion_calculation_performance(self):
        """测试安全垫计算性能"""
        metrics = PerformanceMetrics()
        calculator = SafetyCushionCalculator()
        
        for _ in range(1000):
            start_time = time.perf_counter()
            result = calculator.calculate(
                slope_k=0.5,
                time_remaining_seconds=120.0
            )
            elapsed = (time.perf_counter() - start_time) * 1000
            metrics.record("safety_cushion_calc", elapsed)
        
        stats = metrics.get_stats("safety_cushion_calc")
        print("\n安全垫计算性能统计:")
        print(f"  平均: {stats['mean']:.4f}ms")
        print(f"  中位数: {stats['median']:.4f}ms")
        print(f"  P95: {stats['p95']:.4f}ms")
        print(f"  最大: {stats['max']:.4f}ms")
        
        assert stats['mean'] < 1, f"平均计算耗时 {stats['mean']:.4f}ms 超过 1ms 阈值"


class TestSignalGeneratorPerformance:
    """信号生成器性能测试"""
    
    def test_signal_generation_performance(self):
        """测试信号生成性能"""
        metrics = PerformanceMetrics()
        generator = SignalGenerator()
        
        for _ in range(1000):
            start_time = time.perf_counter()
            signal = generator.generate_signal(
                current_price=67500.0,
                start_price=67000.0,
                slope_k=0.5,
                r_squared=0.85,
                time_remaining=120.0
            )
            elapsed = (time.perf_counter() - start_time) * 1000
            metrics.record("signal_generation", elapsed)
        
        stats = metrics.get_stats("signal_generation")
        print("\n信号生成性能统计:")
        print(f"  平均: {stats['mean']:.4f}ms")
        print(f"  中位数: {stats['median']:.4f}ms")
        print(f"  P95: {stats['p95']:.4f}ms")
        print(f"  最大: {stats['max']:.4f}ms")
        
        assert stats['mean'] < 5, f"平均生成耗时 {stats['mean']:.4f}ms 超过 5ms 阈值"


class TestMarketLifecyclePerformance:
    """市场生命周期管理性能测试"""
    
    def test_market_lifecycle_performance(self):
        """测试市场生命周期管理性能"""
        metrics = PerformanceMetrics()
        manager = MarketLifecycleManager(cycle_duration=300)
        
        for _ in range(1000):
            start_time = time.perf_counter()
            cycle = manager.get_current_cycle()
            elapsed = (time.perf_counter() - start_time) * 1000
            metrics.record("lifecycle_get_cycle", elapsed)
        
        stats = metrics.get_stats("lifecycle_get_cycle")
        print("\n市场生命周期管理性能统计:")
        print(f"  平均: {stats['mean']:.4f}ms")
        print(f"  中位数: {stats['median']:.4f}ms")
        print(f"  P95: {stats['p95']:.4f}ms")
        print(f"  最大: {stats['max']:.4f}ms")
        
        assert stats['mean'] < 1, f"平均耗时 {stats['mean']:.4f}ms 超过 1ms 阈值"


class TestEndToEndPerformance:
    """端到端性能测试"""
    
    def test_complete_strategy_cycle_performance(self):
        """测试完整策略周期性能"""
        metrics = PerformanceMetrics()
        
        queue = PriceQueue(window_seconds=180)
        regression = OLSRegression(min_samples=10)
        calculator = SafetyCushionCalculator()
        generator = SignalGenerator()
        lifecycle = MarketLifecycleManager(cycle_duration=300)
        
        for i in range(30):
            queue.push(price=67000.0 + i * 10, timestamp=time.time() - (30 - i) * 5)
        
        for _ in range(100):
            start_time = time.perf_counter()
            
            timestamps, prices = queue.get_timestamps_and_prices()
            result = regression.fit(timestamps, prices)
            
            if result:
                cycle = lifecycle.get_current_cycle()
                signal = generator.generate_signal(
                    current_price=prices[-1],
                    start_price=prices[0],
                    slope_k=result.slope,
                    r_squared=result.r_squared,
                    time_remaining=cycle.time_remaining
                )
            
            elapsed = (time.perf_counter() - start_time) * 1000
            metrics.record("complete_cycle", elapsed)
        
        stats = metrics.get_stats("complete_cycle")
        print("\n完整策略周期性能统计:")
        print(f"  平均: {stats['mean']:.2f}ms")
        print(f"  中位数: {stats['median']:.2f}ms")
        print(f"  P95: {stats['p95']:.2f}ms")
        print(f"  最大: {stats['max']:.2f}ms")
        
        assert stats['mean'] < 100, f"平均周期耗时 {stats['mean']:.2f}ms 超过 100ms 阈值"
    
    def test_high_frequency_trading_simulation(self):
        """测试高频交易模拟"""
        metrics = PerformanceMetrics()
        
        queue = PriceQueue(window_seconds=180)
        regression = OLSRegression(min_samples=10)
        generator = SignalGenerator()
        lifecycle = MarketLifecycleManager(cycle_duration=300)
        
        for iteration in range(100):
            queue.push(price=67000.0 + iteration * 0.1, timestamp=time.time())
            
            if queue.size() >= 10:
                start_time = time.perf_counter()
                
                timestamps, prices = queue.get_timestamps_and_prices()
                result = regression.fit(timestamps, prices)
                
                if result:
                    cycle = lifecycle.get_current_cycle()
                    signal = generator.generate_signal(
                        current_price=prices[-1],
                        start_price=prices[0],
                        slope_k=result.slope,
                        r_squared=result.r_squared,
                        time_remaining=cycle.time_remaining
                    )
                
                elapsed = (time.perf_counter() - start_time) * 1000
                metrics.record("hft_iteration", elapsed)
        
        stats = metrics.get_stats("hft_iteration")
        print("\n高频交易模拟性能统计:")
        print(f"  平均: {stats['mean']:.2f}ms")
        print(f"  中位数: {stats['median']:.2f}ms")
        print(f"  P95: {stats['p95']:.2f}ms")
        print(f"  最大: {stats['max']:.2f}ms")
        
        assert stats['mean'] < 100, f"平均迭代耗时 {stats['mean']:.2f}ms 超过 100ms 阈值"


class TestMemoryUsage:
    """内存使用测试"""
    
    def test_price_queue_memory_efficiency(self):
        """测试价格队列内存效率"""
        import sys
        
        queue = PriceQueue(window_seconds=180)
        initial_size = sys.getsizeof(queue)
        
        for i in range(10000):
            queue.push(price=67000.0 + i * 0.01, timestamp=time.time() - i * 0.1)
        
        final_size = sys.getsizeof(queue)
        
        print(f"\n价格队列内存使用:")
        print(f"  初始大小: {initial_size} bytes")
        print(f"  最终大小: {final_size} bytes")
        print(f"  队列大小: {queue.size()}")
        
        assert queue.size() > 0


class TestConcurrencyPerformance:
    """并发性能测试"""
    
    def test_concurrent_queue_operations(self):
        """测试并发队列操作"""
        import threading
        
        metrics = PerformanceMetrics()
        queue = PriceQueue(window_seconds=180)
        
        def push_data(thread_id: int):
            for i in range(100):
                start_time = time.perf_counter()
                queue.push(
                    price=67000.0 + thread_id * 100 + i,
                    timestamp=time.time()
                )
                elapsed = (time.perf_counter() - start_time) * 1000
                metrics.record("concurrent_push", elapsed)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=push_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        stats = metrics.get_stats("concurrent_push")
        print("\n并发队列操作性能统计:")
        print(f"  平均: {stats['mean']:.4f}ms")
        print(f"  中位数: {stats['median']:.4f}ms")
        print(f"  P95: {stats['p95']:.4f}ms")
        print(f"  最大: {stats['max']:.4f}ms")
        
        assert queue.size() > 0
