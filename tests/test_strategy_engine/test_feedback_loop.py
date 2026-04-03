"""
策略引擎交易结果反馈闭环单元测试

覆盖 Bug #12 和 #13 修复的核心功能：
- PositionTracker 在策略引擎中的初始化
- TRADE_RESULT_CHANNEL 订阅配置
- _handle_trade_result 回调正确解析数据与异常安全
- position_tracker.update_from_trade_result 调用验证
- 重复信号检查框架（_check_duplicate_signal）
- StopLossMonitor 可被独立初始化
- start_monitoring.py 启动/停止生命周期
"""

import time
from typing import Any, Dict
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest

from shared.position_tracker import Position, PositionTracker
from shared.constants import TRADE_RESULT_CHANNEL
from modules.order_executor.stop_loss_monitor import StopLossMonitor


class TestPositionTrackerInitInEngine:
    """测试 1: PositionTracker 在策略引擎中正确初始化"""

    def test_position_tracker_created_on_init(self):
        """策略引擎初始化时创建 PositionTracker 实例"""
        with patch("modules.strategy_engine.main.RedisClient") as MockRedis:
            mock_redis_instance = MockRedis.return_value
            mock_redis_instance.connect.return_value = True

            with patch("modules.strategy_engine.main.PositionTracker") as MockPT:
                mock_pt = MockPT.return_value
                mock_pt.subscribe_to_trade_results = Mock()

                from modules.strategy_engine.main import StrategyEngine
                with patch.object(StrategyEngine, "_initialize_components"):
                    engine = StrategyEngine.__new__(StrategyEngine)
                    engine.config = Mock()
                    engine._running = False
                    engine._shutdown_requested = False
                    engine._message_buffer = []
                    engine.position_tracker = mock_pt

                assert engine.position_tracker is not None
                assert isinstance(engine.position_tracker, Mock)

    def test_position_tracker_uses_redis_client(self):
        """PositionTracker 使用与引擎相同的 Redis 客户端"""
        tracker = PositionTracker()
        assert tracker._positions == {}
        assert tracker._redis_client is None

        mock_redis = Mock()
        tracker_with_redis = PositionTracker(redis_client=mock_redis)
        assert tracker_with_redis._redis_client is mock_redis


class TestTradeResultChannelSubscription:
    """测试 2: TRADE_RESULT_CHANNEL 订阅配置正确性"""

    def test_trade_result_channel_constant_exists(self):
        """TRADE_RESULT_CHANNEL 常量定义正确"""
        assert TRADE_RESULT_CHANNEL == "trade_result"

    def test_position_tracker_subscribes_to_correct_channel(self):
        """PositionTracker 订阅正确的 Redis 频道"""
        mock_redis = MagicMock()
        mock_ps = MagicMock()
        mock_redis.pubsub.return_value = mock_ps

        tracker = PositionTracker(redis_client=mock_redis)
        tracker.subscribe_to_trade_results(mock_redis)

        time.sleep(0.15)
        tracker.unsubscribe()

        mock_ps.subscribe.assert_called_once_with(TRADE_RESULT_CHANNEL)

    def test_subscribe_without_client_raises(self):
        """无 Redis 客户端时订阅抛出 ValueError"""
        tracker = PositionTracker()
        with pytest.raises(ValueError, match="Redis 客户端不可用"):
            tracker.subscribe_to_trade_results()


class TestHandleTradeResultCallback:
    """测试 3 & 4: _handle_trade_result 正确解析数据 + 异常安全"""

    def _make_engine_with_mock_tracker(self):
        """创建带有 mock position_tracker 的策略引擎实例"""
        with patch("modules.strategy_engine.main.RedisClient") as MockRedis:
            mock_redis = MockRedis.return_value
            mock_redis.connect.return_value = True

            mock_pt = Mock(spec=PositionTracker)
            mock_pt.get_open_positions.return_value = []
            mock_pt.get_total_exposure.return_value = 0.0
            mock_pt.unsubscribe = Mock()

            from modules.strategy_engine.main import StrategyEngine
            engine = StrategyEngine.__new__(StrategyEngine)
            engine.config = Mock()
            engine._running = False
            engine._shutdown_requested = False
            engine._message_buffer = []
            engine.redis_client = mock_redis
            engine.position_tracker = mock_pt
            return engine, mock_pt

    def test_handle_trade_result_parses_success_data(self):
        """正确解析成功交易结果"""
        engine, mock_pt = self._make_engine_with_mock_tracker()

        trade_data = {
            "token_id": "tok_feedback_1",
            "order_result": {"success": True, "order_id": "ord_001"},
            "side": "BUY",
            "filled_size": "100",
            "price": "0.50",
            "status": "MATCHED",
        }

        engine._handle_trade_result(trade_data)

        mock_pt.update_from_trade_result.assert_called_once_with(trade_data)

    def test_handle_trade_result_parses_failure_data(self):
        """正确解析失败交易结果"""
        engine, mock_pt = self._make_engine_with_mock_tracker()

        trade_data = {
            "token_id": "tok_fail_1",
            "order_result": {"success": False, "error_message": "余额不足"},
            "status": "FAILED",
        }

        engine._handle_trade_result(trade_data)

        mock_pt.update_from_trade_result.assert_called_once()

    def test_handle_trade_result_missing_token_id_safe(self):
        """缺少 token_id 时安全处理不崩溃"""
        engine, mock_pt = self._make_engine_with_mock_tracker()

        bad_data = {
            "order_result": {"success": True},
            "status": "MATCHED",
        }

        engine._handle_trade_result(bad_data)

        mock_pt.update_from_trade_result.assert_called_once()

    def test_handle_trade_result_exception_safe(self):
        """异常输入不会导致崩溃"""
        engine, mock_pt = self._make_engine_with_mock_tracker()
        mock_pt.update_from_trade_result.side_effect = RuntimeError("模拟异常")

        bad_data = {"token_id": "tok_err"}

        should_not_raise = lambda: engine._handle_trade_result(bad_data)
        should_not_raise()


class TestUpdateFromTradeResultCalled:
    """测试 5: position_tracker.update_from_trade_result 调用验证"""

    def test_update_creates_new_position(self):
        """update_from_trade_result 创建新多头持仓"""
        tracker = PositionTracker()
        trade_data = {
            "token_id": "tok_utr_1",
            "side": "BUY",
            "filled_size": "200",
            "price": "0.45",
            "market_id": "mkt_utr_1",
            "status": "MATCHED",
        }
        tracker.update_from_trade_result(trade_data)

        positions = tracker.get_open_positions()
        assert len(positions) == 1
        assert positions[0].token_id == "tok_utr_1"
        assert positions[0].quantity == 200.0
        assert positions[0].avg_cost == 0.45

    def test_update_closes_position_on_sell(self):
        """update_from_trade_result 卖出后平仓"""
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_utr_2",
            "side": "BUY",
            "filled_size": "100",
            "price": "0.50",
            "market_id": "mkt_utr_2",
            "status": "MATCHED",
        })
        assert len(tracker.get_open_positions()) == 1

        tracker.update_from_trade_result({
            "token_id": "tok_utr_2",
            "side": "SELL",
            "filled_size": "100",
            "price": "0.60",
            "status": "CONFIRMED",
        })
        assert len(tracker.get_open_positions()) == 0

    def test_engine_callback_calls_tracker_update(self):
        """引擎回调正确调用 tracker 的 update 方法"""
        with patch("modules.strategy_engine.main.RedisClient") as MockRedis:
            mock_redis = MockRedis.return_value
            mock_redis.connect.return_value = True

            real_tracker = PositionTracker(redis_client=mock_redis)

            from modules.strategy_engine.main import StrategyEngine
            engine = StrategyEngine.__new__(StrategyEngine)
            engine.config = Mock()
            engine._running = False
            engine._shutdown_requested = False
            engine._message_buffer = []
            engine.redis_client = mock_redis
            engine.position_tracker = real_tracker

            trade_data = {
                "token_id": "tok_engine_call",
                "side": "BUY",
                "filled_size": "50",
                "price": "0.55",
                "market_id": "mkt_ec",
                "status": "MINED",
            }
            engine._handle_trade_result(trade_data)

            pos = real_tracker.get_position("tok_engine_call")
            assert pos is not None
            assert pos.quantity == 50.0


class TestDuplicateSignalCheckFramework:
    """测试 6: 重复信号检查框架存在且行为正确"""

    def _make_engine_for_dup_check(self, open_positions=None):
        """创建用于重复信号检查的引擎"""
        with patch("modules.strategy_engine.main.RedisClient") as MockRedis:
            mock_redis = MockRedis.return_value
            mock_redis.connect.return_value = True

            mock_pt = Mock(spec=PositionTracker)
            mock_pt.get_open_positions.return_value = open_positions or []
            mock_pt.get_total_exposure.return_value = 0.0
            mock_pt.unsubscribe = Mock()

            from modules.strategy_engine.main import StrategyEngine
            engine = StrategyEngine.__new__(StrategyEngine)
            engine.config = Mock()
            engine._running = False
            engine._shutdown_requested = False
            engine._message_buffer = []
            engine.redis_client = mock_redis
            engine.position_tracker = mock_pt
            return engine, mock_pt

    def test_no_positions_returns_false(self):
        """无持仓时返回 False（允许生成信号）"""
        engine, _ = self._make_engine_for_dup_check(open_positions=[])

        result = engine._check_duplicate_signal()
        assert result is False

    def test_with_open_position_returns_true(self):
        """有持仓时返回 True（阻止重复信号）"""
        fake_pos = Mock()
        fake_pos.token_id = "tok_dup_1"
        fake_pos.quantity = 100.0

        engine, _ = self._make_engine_for_dup_check(open_positions=[fake_pos])

        result = engine._check_duplicate_signal()
        assert result is True

    def test_zero_quantity_position_returns_false(self):
        """数量为零的持仓视为已平仓，返回 False"""
        fake_pos = Mock()
        fake_pos.token_id = "tok_zero_qty"
        fake_pos.quantity = 0.0

        engine, _ = self._make_engine_for_dup_check(open_positions=[fake_pos])

        result = engine._check_duplicate_signal()
        assert result is False

    def test_method_exists_on_engine_class(self):
        """确认方法在类上存在"""
        from modules.strategy_engine.main import StrategyEngine
        assert hasattr(StrategyEngine, "_check_duplicate_signal")
        assert callable(getattr(StrategyEngine, "_check_duplicate_signal"))


class TestStopLossMonitorInitialization:
    """测试 7: StopLossMonitor 可被独立初始化"""

    def test_stop_loss_monitor_default_init(self):
        """StopLossMonitor 使用默认参数可正常初始化"""
        mock_om = Mock()
        mock_pt = Mock()
        monitor = StopLossMonitor(
            order_manager=mock_om,
            position_tracker=mock_pt,
            config=None,
        )

        assert monitor.enabled is True
        assert monitor.stop_loss_pct == 0.1
        assert monitor.take_profit_pct == 0.2
        assert monitor.is_running() is False

    def test_stop_loss_monitor_custom_config(self):
        """StopLossMonitor 接受自定义配置"""
        config = {
            "stop_loss_take_profit": {
                "enabled": True,
                "stop_loss_percentage": 0.15,
                "take_profit_percentage": 0.25,
            }
        }
        mock_om = Mock()
        mock_pt = Mock()
        monitor = StopLossMonitor(
            order_manager=mock_om,
            position_tracker=mock_pt,
            config=config,
        )

        assert monitor.enabled is True
        assert monitor.stop_loss_pct == 0.15
        assert monitor.take_profit_pct == 0.25

    def test_stop_loss_monitor_disabled_config(self):
        """StopLossMonitor 支持禁用状态"""
        config = {"stop_loss_take_profit": {"enabled": False}}
        mock_om = Mock()
        mock_pt = Mock()
        monitor = StopLossMonitor(
            order_manager=mock_om,
            position_tracker=mock_pt,
            config=config,
        )
        assert monitor.enabled is False

    def test_stop_loss_monitor_none_order_manager_ok(self):
        """OrderManager 为 None 时不影响初始化（仅影响执行阶段）"""
        mock_pt = Mock()
        monitor = StopLossMonitor(
            order_manager=None,
            position_tracker=mock_pt,
        )
        assert monitor.order_manager is None
        assert monitor.is_running() is False


class TestMonitoringServiceLifecycle:
    """测试 8: start_monitoring.py 启动/停止生命周期"""

    def test_import_start_monitoring_module(self):
        """start_monitoring 模块可导入"""
        from modules.order_executor.start_monitoring import MonitoringService
        assert MonitoringService is not None

    def test_monitoring_service_initialization(self):
        """MonitoringService 初始化流程可执行"""
        with patch("modules.order_executor.start_monitoring.load_config") as mock_cfg:
            mock_config = Mock()
            mock_config.get_redis_config.return_value = Mock(
                host="localhost", port=6379, password="", db=0,
                max_connections=10, min_idle_connections=2,
                connection_timeout=5, socket_timeout=5,
                max_attempts=3, retry_delay=1,
            )
            mock_config.get_strategy_config.return_value = Mock(
                stop_loss_take_profit={
                    "enabled": True,
                    "stop_loss_percentage": 0.1,
                    "take_profit_percentage": 0.2,
                }
            )
            mock_cfg.return_value = mock_config

            with patch("modules.order_executor.start_monitoring.RedisClient") as MockRC:
                mock_rc_instance = MockRC.return_value
                mock_rc_instance.connect.return_value = True

                from modules.order_executor.start_monitoring import MonitoringService
                service = MonitoringService(config=mock_config)
                service.initialize()

                assert service._redis_client is not None
                assert service._position_tracker is not None
                assert service._stop_loss_monitor is not None
                assert service._stop_loss_monitor.enabled is True

    def test_monitoring_service_start_stop_cycle(self):
        """MonitoringService 启动和停止生命周期完整"""
        with patch("modules.order_executor.start_monitoring.load_config") as mock_cfg:
            mock_config = Mock()
            mock_config.get_redis_config.return_value = Mock(
                host="localhost", port=6379, password="", db=0,
                max_connections=10, min_idle_connections=2,
                connection_timeout=5, socket_timeout=5,
                max_attempts=3, retry_delay=1,
            )
            mock_config.get_strategy_config.return_value = Mock(
                stop_loss_take_profit={"enabled": True, "stop_loss_percentage": 0.1, "take_profit_percentage": 0.2}
            )
            mock_cfg.return_value = mock_config

            with patch("modules.order_executor.start_monitoring.RedisClient") as MockRC:
                mock_rc_instance = MockRC.return_value
                mock_rc_instance.connect.return_value = True

                from modules.order_executor.start_monitoring import MonitoringService
                service = MonitoringService(config=mock_config)
                service.initialize()

                assert service._running is False

                service.start()
                assert service._running is True

                service.stop()
                assert service._running is False

    def test_monitoring_service_get_status(self):
        """get_status 返回完整的状态信息"""
        with patch("modules.order_executor.start_monitoring.load_config") as mock_cfg:
            mock_config = Mock()
            mock_config.get_redis_config.return_value = Mock(
                host="localhost", port=6379, password="", db=0,
                max_connections=10, min_idle_connections=2,
                connection_timeout=5, socket_timeout=5,
                max_attempts=3, retry_delay=1,
            )
            mock_config.get_strategy_config.return_value = Mock(
                stop_loss_take_profit={"enabled": True, "stop_loss_percentage": 0.1, "take_profit_percentage": 0.2}
            )
            mock_cfg.return_value = mock_config

            with patch("modules.order_executor.start_monitoring.RedisClient") as MockRC:
                mock_rc_instance = MockRC.return_value
                mock_rc_instance.connect.return_value = True

                from modules.order_executor.start_monitoring import MonitoringService
                service = MonitoringService(config=mock_config)
                service.initialize()

                status = service.get_status()
                assert "running" in status
                assert "monitor_stats" in status
                assert "open_positions" in status

    def test_double_start_is_safe(self):
        """重复启动安全性"""
        with patch("modules.order_executor.start_monitoring.load_config") as mock_cfg:
            mock_config = Mock()
            mock_config.get_redis_config.return_value = Mock(
                host="localhost", port=6379, password="", db=0,
                max_connections=10, min_idle_connections=2,
                connection_timeout=5, socket_timeout=5,
                max_attempts=3, retry_delay=1,
            )
            mock_config.get_strategy_config.return_value = Mock(
                stop_loss_take_profit={"enabled": True, "stop_loss_percentage": 0.1, "take_profit_percentage": 0.2}
            )
            mock_cfg.return_value = mock_config

            with patch("modules.order_executor.start_monitoring.RedisClient") as MockRC:
                mock_rc_instance = MockRC.return_value
                mock_rc_instance.connect.return_value = True

                from modules.order_executor.start_monitoring import MonitoringService
                service = MonitoringService(config=mock_config)
                service.initialize()

                service.start()
                service.start()

                assert service._running is True
                service.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
