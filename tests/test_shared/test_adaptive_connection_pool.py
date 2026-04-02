"""
AdaptiveConnectionPool 单元测试
测试自适应连接池的初始化、扩容、缩容、边界条件和状态查询
"""

import time
import pytest
from unittest.mock import Mock, MagicMock, patch

from shared.redis_client import (
    AdaptiveConnectionPool,
    RedisClient,
    RedisConnectionConfig,
)


class TestAdaptiveConnectionPoolInit:
    """测试 AdaptiveConnectionPool 初始化参数"""

    def test_default_init(self):
        """测试默认初始化参数"""
        pool = AdaptiveConnectionPool()

        assert pool.initial_size == 10
        assert pool.max_size == 100
        assert pool.load_threshold_high == 0.8
        assert pool.load_threshold_low == 0.3
        assert pool.current_size == 10
        assert pool.adjustment_history == []

    def test_custom_init(self):
        """测试自定义初始化参数"""
        pool = AdaptiveConnectionPool(
            initial_size=5,
            max_size=50,
            load_threshold_high=0.9,
            load_threshold_low=0.2,
        )

        assert pool.initial_size == 5
        assert pool.max_size == 50
        assert pool.load_threshold_high == 0.9
        assert pool.load_threshold_low == 0.2
        assert pool.current_size == 5

    def test_init_with_large_values(self):
        """测试大值初始化"""
        pool = AdaptiveConnectionPool(
            initial_size=100,
            max_size=1000,
        )

        assert pool.initial_size == 100
        assert pool.max_size == 1000
        assert pool.current_size == 100


class TestAdaptiveConnectionPoolExpand:
    """测试高负载扩容逻辑（>80% 时翻倍）"""

    def test_expand_on_high_load(self):
        """测试负载超过阈值时触发扩容"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        result = pool.adjust_pool_size(0.85)

        assert result["adjusted"] is True
        assert result["old_size"] == 10
        assert result["new_size"] == 20
        assert result["direction"] == "expand"
        assert pool.current_size == 20

    def test_expand_doubles_pool_size(self):
        """测试扩容时连接池大小翻倍"""
        pool = AdaptiveConnectionPool(initial_size=8, max_size=100)

        result = pool.adjust_pool_size(0.90)

        assert result["new_size"] == 16

    def test_expand_capped_at_max_size(self):
        """测试扩容不超过最大值"""
        pool = AdaptiveConnectionPool(initial_size=60, max_size=100)

        result = pool.adjust_pool_size(0.85)

        assert result["adjusted"] is True
        assert result["new_size"] == 100
        assert pool.current_size == 100

    def test_no_expand_at_max_capacity(self):
        """测试已达最大容量时不再扩容"""
        pool = AdaptiveConnectionPool(initial_size=50, max_size=50)
        pool.current_size = 50

        result = pool.adjust_pool_size(0.95)

        assert result["adjusted"] is False
        assert pool.current_size == 50

    def test_no_expand_at_boundary_load(self):
        """测试负载恰等于高阈值时不扩容"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        result = pool.adjust_pool_size(0.80)

        assert result["adjusted"] is False

    def test_multiple_expansions(self):
        """测试连续多次扩容"""
        pool = AdaptiveConnectionPool(initial_size=5, max_size=100)

        r1 = pool.adjust_pool_size(0.85)
        assert r1["new_size"] == 10

        r2 = pool.adjust_pool_size(0.85)
        assert r2["new_size"] == 20

        r3 = pool.adjust_pool_size(0.85)
        assert r3["new_size"] == 40

    def test_expand_records_history(self):
        """测试扩容操作记录到调整历史"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        pool.adjust_pool_size(0.85)

        assert len(pool.adjustment_history) == 1
        record = pool.adjustment_history[0]
        assert record["old_size"] == 10
        assert record["new_size"] == 20
        assert record["direction"] == "expand"
        assert record["load"] == 0.85
        assert isinstance(record["timestamp"], float)


class TestAdaptiveConnectionPoolShrink:
    """测试低负载缩容逻辑（<30% 时减半）"""

    def test_shrink_on_low_load(self):
        """测试负载低于阈值时触发缩容"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)
        pool.current_size = 20

        result = pool.adjust_pool_size(0.25)

        assert result["adjusted"] is True
        assert result["old_size"] == 20
        assert result["new_size"] == 10
        assert result["direction"] == "shrink"
        assert pool.current_size == 10

    def test_shrink_halves_pool_size(self):
        """测试缩容时连接池大小减半"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)
        pool.current_size = 32

        result = pool.adjust_pool_size(0.20)

        assert result["new_size"] == 16

    def test_shrink_floored_at_initial_size(self):
        """测试缩容不低于初始大小"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)
        pool.current_size = 15

        result = pool.adjust_pool_size(0.25)

        assert result["adjusted"] is True
        assert result["new_size"] == 10
        assert pool.current_size == 10

    def test_no_shrink_at_initial_size(self):
        """测试当前大小等于初始大小时不缩容"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        result = pool.adjust_pool_size(0.10)

        assert result["adjusted"] is False
        assert pool.current_size == 10

    def test_no_shrink_at_boundary_load(self):
        """测试负载恰等于低阈值时不缩容"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)
        pool.current_size = 20

        result = pool.adjust_pool_size(0.30)

        assert result["adjusted"] is False

    def test_shrink_records_history(self):
        """测试缩容操作记录到调整历史"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)
        pool.current_size = 20

        pool.adjust_pool_size(0.25)

        assert len(pool.adjustment_history) == 1
        record = pool.adjustment_history[0]
        assert record["old_size"] == 20
        assert record["new_size"] == 10
        assert record["direction"] == "shrink"


class TestAdaptiveConnectionPoolNoAdjustment:
    """测试负载在中间范围时不调整"""

    def test_mid_range_load_no_adjustment(self):
        """测试中间范围负载不触发调整"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        result = pool.adjust_pool_size(0.55)

        assert result["adjusted"] is False
        assert result["current_size"] == 10
        assert pool.current_size == 10

    def test_just_above_low_threshold_no_adjustment(self):
        """测试略高于低阈值但不低于低阈值时，且未超过高阈值时不调整"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        result = pool.adjust_pool_size(0.35)

        assert result["adjusted"] is False

    def test_just_below_high_threshold_no_adjustment(self):
        """测试略低于高阈值但高于低阈值时不调整"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        result = pool.adjust_pool_size(0.79)

        assert result["adjusted"] is False

    def test_no_adjustment_does_not_record_history(self):
        """测试无调整时不记录历史"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        pool.adjust_pool_size(0.50)

        assert len(pool.adjustment_history) == 0


class TestAdaptiveConnectionPoolStatus:
    """测试状态查询功能"""

    def test_get_status_basic_fields(self):
        """测试状态查询返回基本字段"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        status = pool.get_status()

        assert status["current_size"] == 10
        assert status["max_size"] == 100
        assert status["initial_size"] == 10
        assert status["load_threshold_high"] == 0.8
        assert status["load_threshold_low"] == 0.3

    def test_get_status_utilization_calculation(self):
        """测试利用率计算正确性"""
        pool = AdaptiveConnectionPool(initial_size=25, max_size=100)

        status = pool.get_status()

        assert status["utilization"] == round(25 / 100, 4)

    def test_get_status_after_expand(self):
        """测试扩容后的状态更新"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)
        pool.adjust_pool_size(0.85)

        status = pool.get_status()

        assert status["current_size"] == 20
        assert status["total_adjustments"] == 1

    def test_get_status_after_shrink(self):
        """测试缩容后的状态更新"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)
        pool.current_size = 40
        pool.adjust_pool_size(0.20)

        status = pool.get_status()

        assert status["current_size"] == 20
        assert status["total_adjustments"] == 1


class TestAdjustmentHistory:
    """测试调整历史记录功能"""

    def test_history_accumulates(self):
        """测试多次调整的历史记录累积"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        pool.adjust_pool_size(0.85)
        pool.adjust_pool_size(0.85)
        pool.current_size = 40
        pool.adjust_pool_size(0.20)

        assert len(pool.adjustment_history) == 3
        assert pool.adjustment_history[0]["direction"] == "expand"
        assert pool.adjustment_history[1]["direction"] == "expand"
        assert pool.adjustment_history[2]["direction"] == "shrink"

    def test_history_preserves_timestamps(self):
        """测试历史记录保留时间戳"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        before = time.time()
        pool.adjust_pool_size(0.85)
        after = time.time()

        timestamp = pool.adjustment_history[0]["timestamp"]
        assert before <= timestamp <= after

    def test_history_ordering(self):
        """测试历史记录按时间顺序排列"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        pool.adjust_pool_size(0.85)
        time.sleep(0.01)
        pool.adjust_pool_size(0.85)

        assert (
            pool.adjustment_history[0]["timestamp"]
            <= pool.adjustment_history[1]["timestamp"]
        )


class TestEdgeCases:
    """测试边界条件"""

    def test_zero_load_triggers_shrink(self):
        """测试零负载触发缩容"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)
        pool.current_size = 20

        result = pool.adjust_pool_size(0.0)

        assert result["adjusted"] is True
        assert result["direction"] == "shrink"

    def test_full_load_triggers_expand(self):
        """测试满负载触发扩容"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=100)

        result = pool.adjust_pool_size(1.0)

        assert result["adjusted"] is True
        assert result["direction"] == "expand"

    def test_equal_initial_and_max_size_no_change(self):
        """测试初始大小等于最大大小时无法调整"""
        pool = AdaptiveConnectionPool(initial_size=10, max_size=10)

        expand_result = pool.adjust_pool_size(0.99)
        shrink_result = pool.adjust_pool_size(0.01)

        assert expand_result["adjusted"] is False
        assert shrink_result["adjusted"] is False
        assert pool.current_size == 10

    def test_odd_number_shrink_floor_division(self):
        """测试奇数缩容使用向下取整除法"""
        pool = AdaptiveConnectionPool(initial_size=5, max_size=100)
        pool.current_size = 11

        result = pool.adjust_pool_size(0.20)

        assert result["new_size"] == 5

    def test_single_connection_pool(self):
        """测试单连接池场景"""
        pool = AdaptiveConnectionPool(initial_size=1, max_size=16)

        result = pool.adjust_pool_size(0.85)
        assert result["new_size"] == 2

        pool.current_size = 2
        result = pool.adjust_pool_size(0.20)
        assert result["new_size"] == 1


class TestIntegrationWithRedisClient:
    """测试与 RedisClient 的集成"""

    @pytest.fixture
    def config(self):
        return RedisConnectionConfig(
            host="localhost",
            port=6379,
            min_connections=5,
            max_connections=50,
        )

    @pytest.fixture
    def mock_redis(self):
        with patch("shared.redis_client.Redis") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            mock_instance.ping.return_value = True
            yield mock_instance

    def test_redis_client_has_adaptive_pool(self, config, mock_redis):
        """测试 RedisClient 初始化后拥有 adaptive_pool 属性"""
        client = RedisClient(config)
        client.connect()

        assert hasattr(client, "adaptive_pool")
        assert isinstance(client.adaptive_pool, AdaptiveConnectionPool)
        assert client.adaptive_pool.initial_size == 5
        assert client.adaptive_pool.max_size == 50

    def test_publish_increments_operation_count(self, config, mock_redis):
        """测试 publish 操作增加计数器"""
        mock_redis.publish.return_value = 1

        client = RedisClient(config)
        client.connect()

        assert client._operation_count == 0
        client.publish_message("test", "msg")
        assert client._operation_count == 1

    def test_subscribe_increments_operation_count(self, config, mock_redis):
        """测试 subscribe 操作增加计数器"""
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([])

        client = RedisClient(config)
        client.connect()

        client.subscribe_channel("ch", lambda c, m: None)
        assert client._operation_count >= 1

    def test_adaptive_pool_adjust_from_client(self, config, mock_redis):
        """测试通过客户端的 adaptive_pool 进行调整"""
        client = RedisClient(config)
        client.connect()

        result = client.adaptive_pool.adjust_pool_size(0.85)

        assert result["adjusted"] is True
        assert result["direction"] == "expand"

    def test_adaptive_pool_status_from_client(self, config, mock_redis):
        """测试通过客户端获取 adaptive_pool 状态"""
        client = RedisClient(config)
        client.connect()

        status = client.adaptive_pool.get_status()

        assert "current_size" in status
        assert "max_size" in status
        assert "utilization" in status
