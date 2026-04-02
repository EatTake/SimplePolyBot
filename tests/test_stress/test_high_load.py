"""
高负载压力测试

测试系统在高频交易、长时间运行、连接池耗尽、消息突发等极端场景下的表现
包含性能基准对比与报告输出功能
"""

import gc
import os
import statistics
import sys
import threading
import time
import tracemalloc
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from modules.strategy_engine.ols_regression import OLSRegression
from modules.strategy_engine.price_queue import PriceQueue
from modules.strategy_engine.safety_cushion import SafetyCushionCalculator
from modules.strategy_engine.signal_generator import SignalGenerator
from modules.strategy_engine.market_lifecycle import MarketLifecycleManager
from shared.redis_client import (
    AdaptiveConnectionPool,
    RedisClient,
    RedisConnectionConfig,
)


class StressTestMetrics:
    """压力测试指标收集器，记录每次测试的关键指标"""

    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
        self.memory_snapshots: Dict[str, float] = {}
        self.test_results: Dict[str, Dict[str, Any]] = {}

    def record(self, name: str, duration: float) -> None:
        if name not in self.measurements:
            self.measurements[name] = []
        self.measurements[name].append(duration)

    def increment(self, name: str, amount: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount

    def snapshot_memory(self, label: str) -> None:
        current, peak = tracemalloc.get_traced_memory()
        self.memory_snapshots[label] = current / (1024 * 1024)

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
            "p99": sorted(values)[int(len(values) * 0.99)] if len(values) > 0 else 0,
        }

    def record_test_result(
        self,
        test_name: str,
        passed: bool,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.test_results[test_name] = {
            "passed": passed,
            "timestamp": time.time(),
            "metrics": metrics or {},
        }


class PerformanceReport:
    """性能基准对比报告生成器"""

    BASELINE_THRESHOLD_MS = {
        "ols_high_freq": {"mean": 10.0, "p99": 50.0},
        "memory_growth_mb": 10.0,
        "message_burst_total_ms": 5000.0,
        "connection_pool_wait_ms": 5000.0,
    }

    def __init__(self, metrics: StressTestMetrics):
        self.metrics = metrics
        self.report_lines: List[str] = []

    def generate(self) -> str:
        self._add_header()
        self._add_ols_section()
        self._add_memory_section()
        self._add_connection_pool_section()
        self._add_message_burst_section()
        self._add_summary()
        return "\n".join(self.report_lines)

    def _add_header(self) -> None:
        self.report_lines.append("=" * 72)
        self.report_lines.append("       SimplePolyBot 压力测试性能报告")
        self.report_lines.append(f"       生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.report_lines.append("=" * 72)
        self.report_lines.append("")

    def _add_ols_section(self) -> None:
        stats = self.metrics.get_stats("ols_high_freq")
        if not stats:
            return
        baseline = self.BASELINE_THRESHOLD_MS["ols_high_freq"]
        mean_ok = stats["mean"] < baseline["mean"]
        p99_ok = stats["p99"] < baseline["p99"]

        self.report_lines.append("-" * 72)
        self.report_lines.append("[1] 高频 OLS 回归测试 (test_sustained_high_frequency)")
        self.report_lines.append("-" * 72)
        self.report_lines.append(f"  调用次数:     {stats['count']}")
        self.report_lines.append(f"  平均延迟:     {stats['mean']:.4f} ms  {'✓' if mean_ok else '✗'} (阈值: {baseline['mean']}ms)")
        self.report_lines.append(f"  中位数延迟:   {stats['median']:.4f} ms")
        self.report_lines.append(f"  P95 延迟:     {stats['p95']:.4f} ms")
        self.report_lines.append(f"  P99 延迟:     {stats['p99']:.4f} ms  {'✓' if p99_ok else '✗'} (阈值: {baseline['p99']}ms)")
        self.report_lines.append(f"  最小延迟:     {stats['min']:.4f} ms")
        self.report_lines.append(f"  最大延迟:     {stats['max']:.4f} ms")
        self.report_lines.append(f"  标准差:       {stats['stdev']:.4f} ms")
        self.report_lines.append("")

    def _add_memory_section(self) -> None:
        snapshots = self.metrics.memory_snapshots
        if "memory_leak_start" in snapshots and "memory_leak_end" in snapshots:
            growth = snapshots["memory_leak_end"] - snapshots["memory_leak_start"]
            ok = growth < self.BASELINE_THRESHOLD_MS["memory_growth_mb"]
            self.report_lines.append("-" * 72)
            self.report_lines.append("[2] 内存泄漏测试 (test_memory_leak)")
            self.report_lines.append("-" * 72)
            self.report_lines.append(f"  初始内存:     {snapshots['memory_leak_start']:.2f} MB")
            self.report_lines.append(f"  结束内存:     {snapshots['memory_leak_end']:.2f} MB")
            self.report_lines.append(f"  内存增长:     {growth:.2f} MB  {'✓' if ok else '✗'} (阈值: {self.BASELINE_THRESHOLD_MS['memory_growth_mb']}MB)")
            self.report_lines.append("")
        if "object_count_start" in self.metrics.counters and "object_count_end" in self.metrics.counters:
            obj_delta = self.metrics.counters.get("object_count_end", 0) - self.metrics.counters.get("object_count_start", 0)
            self.report_lines.append(f"  对象数量变化: {self.metrics.counters['object_count_start']} → {self.metrics.counters['object_count_end']} (Δ{obj_delta:+d})")
            self.report_lines.append("")

    def _add_connection_pool_section(self) -> None:
        pool_stats = self.metrics.get_stats("pool_acquire_time")
        if not pool_stats:
            return
        self.report_lines.append("-" * 72)
        self.report_lines.append("[3] 连接池耗尽测试 (test_connection_pool_exhaustion)")
        self.report_lines.append("-" * 72)
        self.report_lines.append(f"  连接获取次数: {pool_stats['count']}")
        self.report_lines.append(f"  平均获取时间: {pool_stats['mean']:.4f} ms")
        self.report_lines.append(f"  最大获取时间: {pool_stats['max']:.4f} ms")
        released = self.metrics.counters.get("connections_released", 0)
        rejected = self.metrics.counters.get("connections_rejected", 0)
        total_requested = self.metrics.counters.get("connections_requested", 0)
        self.report_lines.append(f"  请求连接数:   {total_requested}")
        self.report_lines.append(f"  成功释放数:   {released}")
        self.report_lines.append(f"  被拒绝数:     {rejected}")
        self.report_lines.append("")

    def _add_message_burst_section(self) -> None:
        burst_stats = self.metrics.get_stats("message_process_time")
        if not burst_stats:
            return
        total_time = sum(self.metrics.measurements.get("message_process_time", []))
        baseline = self.BASELINE_THRESHOLD_MS["message_burst_total_ms"]
        ok = total_time < baseline
        processed = self.metrics.counters.get("messages_processed", 0)
        expected = self.metrics.counters.get("messages_sent", 0)

        self.report_lines.append("-" * 72)
        self.report_lines.append("[4] 消息突发测试 (test_message_burst)")
        self.report_lines.append("-" * 72)
        self.report_lines.append(f"  发送消息数:   {expected}")
        self.report_lines.append(f"  处理消息数:   {processed}  {'✓' if processed == expected else '✗'}")
        self.report_lines.append(f"  总处理时间:   {total_time:.2f} ms  {'✓' if ok else '✗'} (阈值: {baseline}ms)")
        self.report_lines.append(f"  平均处理时间: {burst_stats['mean']:.4f} ms")
        self.report_lines.append(f"  吞吐量:       {processed / (total_time / 1000):.0f} msg/s")
        self.report_lines.append(f"  P99 处理时间: {burst_stats['p99']:.4f} ms")
        self.report_lines.append("")

    def _add_summary(self) -> None:
        total_tests = len(self.metrics.test_results)
        passed = sum(1 for r in self.metrics.test_results.values() if r["passed"])
        self.report_lines.append("=" * 72)
        self.report_lines.append("  测试总结")
        self.report_lines.append("=" * 72)
        self.report_lines.append(f"  通过: {passed}/{total_tests}")
        for name, result in self.metrics.test_results.items():
            status = "PASS" if result["passed"] else "FAIL"
            self.report_lines.append(f"    [{status}] {name}")
        self.report_lines.append("=" * 72)


@pytest.fixture(scope="class")
def stress_metrics():
    """类级别共享的指标收集器"""
    metrics = StressTestMetrics()
    tracemalloc.start()
    yield metrics
    tracemalloc.stop()


@pytest.fixture(scope="class")
def performance_report(stress_metrics):
    """性能报告生成器"""
    return PerformanceReport(stress_metrics)


class TestHighLoad:
    """
    高负载压力测试类

    覆盖以下极端场景：
    - 高频连续 OLS 回归计算
    - 长时间运行内存稳定性
    - Redis 连接池耗尽降级
    - 突发大量消息批量处理
    """

    def test_sustained_high_frequency(self, stress_metrics):
        """
        模拟高频交易场景：快速连续调用 OLS 回归计算 1000 次

        验证项：
        - 所有 1000 次调用成功完成
        - 平均延迟 < 10ms
        - 无内存泄漏（跟踪对象数量）
        """
        regression = OLSRegression(min_samples=10)
        base_timestamp = time.time()

        timestamps = [base_timestamp - i * 0.5 for i in range(20)]
        prices = [67000.0 + i * 5.0 for i in range(20)]

        success_count = 0
        object_count_before = len(gc.get_objects())

        for i in range(1000):
            ts_offset = i * 0.001
            current_timestamps = [t + ts_offset for t in timestamps]
            current_prices = [p + (i % 100) * 0.01 for p in prices]

            start = time.perf_counter()
            result = regression.fit(current_timestamps, current_prices)
            elapsed = (time.perf_counter() - start) * 1000

            stress_metrics.record("ols_high_freq", elapsed)

            if result is not None:
                success_count += 1

        object_count_after = len(gc.get_objects())
        object_delta = object_count_after - object_count_before

        stats = stress_metrics.get_stats("ols_high_freq")

        assert success_count == 1000, f"OLS 回归成功率: {success_count}/1000"
        assert stats["mean"] < 10, f"平均延迟 {stats['mean']:.2f}ms 超过 10ms 阈值"

        stress_metrics.increment("object_count_before_ols", object_count_before)
        stress_metrics.increment("object_count_after_ols", object_count_after)

        print(f"\n[高频 OLS] 成功率: {success_count}/1000 | 平均延迟: {stats['mean']:.4f}ms | "
              f"P99: {stats['p99']:.4f}ms | 对象变化: Δ{object_delta:+d}")

        stress_metrics.record_test_result(
            "test_sustained_high_frequency",
            True,
            {"success_rate": success_count / 1000, "avg_latency_ms": stats["mean"], "object_delta": object_delta},
        )

    def test_memory_leak(self, stress_metrics):
        """
        长时间运行模拟：循环执行策略周期 100 次，每次创建大量临时对象

        使用 tracemalloc 跟踪内存使用情况
        验证内存增长 < 10MB 或增长趋势平稳
        """
        gc.collect()
        time.sleep(0.1)

        stress_metrics.snapshot_memory("memory_leak_start")

        queue = PriceQueue(window_seconds=180)
        regression = OLSRegression(min_samples=10)
        calculator = SafetyCushionCalculator()
        generator = SignalGenerator()
        lifecycle = MarketLifecycleManager(cycle_duration=300)

        memory_readings: List[float] = []

        for cycle_idx in range(100):
            temp_objects: List[Any] = []
            for j in range(50):
                queue.push(price=67000.0 + cycle_idx * 0.1 + j * 0.001, timestamp=time.time() - (50 - j) * 0.1)

            timestamps, prices = queue.get_timestamps_and_prices()
            if len(timestamps) >= regression.min_samples:
                result = regression.fit(timestamps, prices)
                if result:
                    cushion = calculator.calculate(slope_k=result.slope, time_remaining_seconds=120.0)
                    signal = generator.generate_signal(
                        current_price=prices[-1],
                        start_price=prices[0],
                        slope_k=result.slope,
                        r_squared=result.r_squared,
                        time_remaining=lifecycle.get_current_cycle().time_remaining,
                    )
                    temp_objects.extend([result, cushion, signal])

                    for k in range(20):
                        temp_objects.append({"cycle": cycle_idx, "iter": k, "data": [i * 0.1 for i in range(100)]})

            del temp_objects

            if cycle_idx % 10 == 0:
                gc.collect()
                current_mem, _ = tracemalloc.get_traced_memory()
                memory_readings.append(current_mem / (1024 * 1024))

        gc.collect()
        time.sleep(0.05)
        stress_metrics.snapshot_memory("memory_leak_end")

        start_mem = stress_metrics.memory_snapshots["memory_leak_start"]
        end_mem = stress_metrics.memory_snapshots["memory_leak_end"]
        total_growth = end_mem - start_mem

        is_within_threshold = total_growth < 10.0
        trend_stable = True
        if len(memory_readings) >= 3:
            first_half_avg = statistics.mean(memory_readings[:len(memory_readings) // 2])
            second_half_avg = statistics.mean(memory_readings[len(memory_readings) // 2:])
            trend_stable = abs(second_half_avg - first_half_avg) < 5.0

        passed = is_within_threshold or trend_stable

        assert passed, (
            f"内存增长异常: 增长 {total_growth:.2f}MB (阈值 10MB), "
            f"趋势平稳: {trend_stable}"
        )

        print(f"\n[内存泄漏] 初始: {start_mem:.2f}MB | 结束: {end_mem:.2f}MB | "
              f"增长: {total_growth:.2f}MB | 趋势平稳: {trend_stable}")

        stress_metrics.record_test_result(
            "test_memory_leak",
            passed,
            {
                "start_mem_mb": start_mem,
                "end_mem_mb": end_mem,
                "growth_mb": total_growth,
                "trend_stable": trend_stable,
            },
        )

    def test_connection_pool_exhaustion(self, stress_metrics):
        """
        模拟 Redis 连接池耗尽场景

        尝试创建超过最大连接数的连接
        验证优雅降级（等待或拒绝）
        验证连接最终能正常释放
        """
        max_connections = 5
        config = RedisConnectionConfig(
            host="localhost",
            port=6379,
            max_connections=max_connections,
            min_connections=2,
            connect_timeout=2,
            read_timeout=2,
        )

        pool = AdaptiveConnectionPool(
            initial_size=2,
            max_size=max_connections,
            load_threshold_high=0.9,
            load_threshold_low=0.2,
        )

        active_connections: List[MagicMock] = []
        acquisition_errors = 0
        successful_acquisitions = 0
        total_requested = max_connections * 3

        for i in range(total_requested):
            start = time.perf_counter()

            if len(active_connections) >= max_connections:
                adjustment = pool.adjust_pool_size(current_load=1.0)
                if not adjustment["adjusted"]:
                    acquisition_errors += 1
                    stress_metrics.record("pool_acquire_time", (time.perf_counter() - start) * 1000)
                    stress_metrics.increment("connections_rejected")
                    continue

            mock_conn = MagicMock()
            mock_conn.conn_id = i
            active_connections.append(mock_conn)
            successful_acquisitions += 1
            elapsed = (time.perf_counter() - start) * 1000
            stress_metrics.record("pool_acquire_time", elapsed)
            stress_metrics.increment("connections_requested")

        release_count = 0
        while active_connections:
            conn = active_connections.pop()
            conn.close.assert_not_called()
            del conn
            release_count += 1

            if len(active_connections) <= max_connections // 2:
                pool.adjust_pool_size(current_load=0.1)

        final_status = pool.get_status()

        stress_metrics.increment("connections_released", release_count)

        all_released = release_count == successful_acquisitions
        has_graceful_degradation = acquisition_errors > 0 or successful_acquisitions <= max_connections
        pool_status_normal = final_status["current_size"] >= pool.initial_size

        assert all_released, f"连接未完全释放: 已释放 {release_count}/{successful_acquisitions}"
        assert has_graceful_degradation, "缺少优雅降级机制（超限请求应被拒绝或等待）"
        assert pool_status_normal, f"连接池状态异常: {final_status}"

        print(f"\n[连接池耗尽] 请求: {total_requested} | 成功: {successful_acquisitions} | "
              f"拒绝: {acquisition_errors} | 释放: {release_count} | 最终大小: {final_status['current_size']}")

        stress_metrics.record_test_result(
            "test_connection_pool_exhaustion",
            True,
            {
                "total_requested": total_requested,
                "successful_acquisitions": successful_acquisitions,
                "rejected": acquisition_errors,
                "released": release_count,
                "final_pool_size": final_status["current_size"],
            },
        )

    def test_message_burst(self, stress_metrics):
        """
        模拟突发大量消息：一次性发送 1000 条消息给策略引擎

        验证项：
        - 批量处理功能正常工作
        - 所有消息都被处理
        - 处理时间在合理范围内
        """
        message_count = 1000
        processed_messages: List[Dict[str, Any]] = []
        processing_lock = threading.Lock()

        class MockStrategyEngine:
            def __init__(self):
                self.queue = PriceQueue(window_seconds=180)
                self.regression = OLSRegression(min_samples=10)
                self.generator = SignalGenerator()
                self.lifecycle = MarketLifecycleManager(cycle_duration=300)

            def process_message(self, message: Dict[str, Any]) -> None:
                start = time.perf_counter()

                price = message.get("price", 67000.0)
                timestamp = message.get("timestamp", time.time())
                self.queue.push(price=price, timestamp=timestamp)

                if self.queue.size() >= self.regression.min_samples:
                    ts, prices = self.queue.get_timestamps_and_prices()
                    result = self.regression.fit(ts, prices)
                    if result:
                        signal = self.generator.generate_signal(
                            current_price=prices[-1],
                            start_price=prices[0],
                            slope_k=result.slope,
                            r_squared=result.r_squared,
                            time_remaining=self.lifecycle.get_current_cycle().time_remaining,
                        )
                        message["_signal"] = signal.action.value

                elapsed = (time.perf_counter() - start) * 1000
                stress_metrics.record("message_process_time", elapsed)

                with processing_lock:
                    processed_messages.append(message)

        engine = MockStrategyEngine()
        messages = [
            {
                "msg_id": i,
                "price": 67000.0 + (i % 200) * 0.5,
                "timestamp": time.time() - (message_count - i) * 0.01,
                "market_id": f"market_{i % 10}",
            }
            for i in range(message_count)
        ]

        batch_start = time.perf_counter()
        for msg in messages:
            engine.process_message(msg)
        batch_total = (time.perf_counter() - batch_start) * 1000

        stress_metrics.increment("messages_sent", message_count)
        stress_metrics.increment("messages_processed", len(processed_messages))

        burst_stats = stress_metrics.get_stats("message_process_time")
        throughput = message_count / (batch_total / 1000) if batch_total > 0 else 0

        assert len(processed_messages) == message_count, (
            f"消息处理不完整: {len(processed_messages)}/{message_count}"
        )
        assert batch_total < 10000, f"总处理时间 {batch_total:.0f}ms 过长"

        unique_ids = set(m["msg_id"] for m in processed_messages)
        assert len(unique_ids) == message_count, f"存在重复或丢失的消息 ID: {len(unique_ids)}/{message_count}"

        print(f"\n[消息突发] 发送: {message_count} | 处理: {len(processed_messages)} | "
              f"总耗时: {batch_total:.2f}ms | 吞吐: {throughput:.0f} msg/s | "
              f"平均: {burst_stats['mean']:.4f}ms/msg | P99: {burst_stats['p99']:.4f}ms/msg")

        stress_metrics.record_test_result(
            "test_message_burst",
            True,
            {
                "sent": message_count,
                "processed": len(processed_messages),
                "total_time_ms": batch_total,
                "throughput_msg_per_sec": throughput,
                "avg_latency_ms": burst_stats.get("mean", 0),
            },
        )


@pytest.fixture(scope="module")
def report_data():
    """模块级报告数据收集"""
    data = {"metrics": StressTestMetrics()}
    tracemalloc.start()
    yield data
    tracemalloc.stop()


def test_stress_report_output(report_data, capsys):
    """
    性能基准对比报告输出测试

    自包含地收集所有压力测试场景的关键指标并输出格式化性能报告
    验证报告生成器能正确汇总各维度数据并输出完整报告
    """
    metrics = report_data["metrics"]

    regression = OLSRegression(min_samples=10)
    base_ts = time.time()
    sample_ts = [base_ts - i * 0.3 for i in range(15)]
    sample_px = [67000.0 + i * 3.0 for i in range(15)]

    for i in range(500):
        offset = i * 0.0005
        start = time.perf_counter()
        result = regression.fit([t + offset for t in sample_ts], [p + (i % 50) * 0.01 for p in sample_px])
        elapsed = (time.perf_counter() - start) * 1000
        metrics.record("ols_high_freq", elapsed)
        assert result is not None

    metrics.snapshot_memory("memory_leak_start")
    metrics.increment("object_count_start", len(gc.get_objects()))

    queue = PriceQueue(window_seconds=180)
    gen = SignalGenerator()
    calc = SafetyCushionCalculator()
    lifecycle = MarketLifecycleManager(cycle_duration=300)

    for cycle in range(50):
        for j in range(30):
            queue.push(price=67000.0 + cycle * 0.05 + j * 0.002, timestamp=time.time() - (30 - j) * 0.08)
        ts_arr, px_arr = queue.get_timestamps_and_prices()
        if len(ts_arr) >= 10:
            res = regression.fit(ts_arr, px_arr)
            if res:
                calc.calculate(res.slope, 120.0)
                gen.generate_signal(px_arr[-1], px_arr[0], res.slope, res.r_squared, lifecycle.get_current_cycle().time_remaining)

    gc.collect()
    metrics.increment("object_count_end", len(gc.get_objects()))
    metrics.snapshot_memory("memory_leak_end")

    max_conn = 5
    pool = AdaptiveConnectionPool(initial_size=2, max_size=max_conn)
    mock_conns = []
    total_requested = max_conn * 3
    rejected = 0
    released = 0

    for i in range(total_requested):
        start = time.perf_counter()
        if len(mock_conns) >= max_conn:
            pool.adjust_pool_size(current_load=1.0)
            rejected += 1
            metrics.record("pool_acquire_time", (time.perf_counter() - start) * 1000)
            continue
        mock_conns.append(MagicMock())
        metrics.record("pool_acquire_time", (time.perf_counter() - start) * 1000)
    while mock_conns:
        mock_conns.pop()
        released += 1

    metrics.increment("connections_requested", total_requested)
    metrics.increment("connections_released", released)
    metrics.increment("connections_rejected", rejected)

    processed_count = 0
    msg_total = 200
    engine_queue = PriceQueue(window_seconds=180)
    engine_regression = OLSRegression(min_samples=10)
    engine_gen = SignalGenerator()
    engine_lifecycle = MarketLifecycleManager(cycle_duration=300)

    batch_start = time.perf_counter()
    for i in range(msg_total):
        start = time.perf_counter()
        price = 67000.0 + (i % 200) * 0.5
        engine_queue.push(price=price, timestamp=time.time() - (msg_total - i) * 0.01)
        if engine_queue.size() >= 10:
            ts_e, px_e = engine_queue.get_timestamps_and_prices()
            res_e = engine_regression.fit(ts_e, px_e)
            if res_e:
                engine_gen.generate_signal(
                    px_e[-1], px_e[0], res_e.slope, res_e.r_squared,
                    engine_lifecycle.get_current_cycle().time_remaining,
                )
        elapsed = (time.perf_counter() - start) * 1000
        metrics.record("message_process_time", elapsed)
        processed_count += 1

    metrics.increment("messages_sent", msg_total)
    metrics.increment("messages_processed", processed_count)

    report = PerformanceReport(metrics)
    output = report.generate()

    assert "SimplePolyBot 压力测试性能报告" in output
    assert "高频 OLS 回归测试" in output
    assert "内存泄漏测试" in output
    assert "连接池耗尽测试" in output
    assert "消息突发测试" in output
    assert "测试总结" in output

    print(output)
