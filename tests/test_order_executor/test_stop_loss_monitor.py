"""
止损止盈监控模块单元测试

覆盖 StopLossMonitor 类的所有核心功能：
- 止损/止盈条件判断
- 订单执行调用
- 生命周期管理
- 统计信息
- 边界情况处理
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch, call

import pytest

from modules.order_executor.stop_loss_monitor import (
    StopLossMonitor,
    StopLossAlert,
    Position,
)


def _make_position(
    token_id: str = "token_001",
    current_price: float = 0.50,
    avg_cost: float = 0.50,
    quantity: float = 100.0,
) -> Position:
    """创建测试用持仓对象"""
    return Position(
        token_id=token_id,
        current_price=current_price,
        avg_cost=avg_cost,
        quantity=quantity,
        market_id="market_001",
        side="LONG",
    )


def _make_order_result(
    success: bool = True,
    order_id: str = "order_sl_001",
) -> Mock:
    """创建模拟 OrderResult"""
    result = Mock()
    result.success = success
    result.order_id = order_id
    result.status = "matched"
    result.filled_size = 100.0
    result.avg_price = 0.45
    result.fee = 0.45
    result.error_message = ""
    result.to_dict.return_value = {
        "success": success,
        "order_id": order_id,
        "status": "matched",
    }
    return result


def _make_monitor(
    config: Optional[Dict[str, Any]] = None,
) -> tuple:
    """创建测试用监控器实例（含 mock 依赖）"""
    mock_order_manager = Mock()
    mock_position_tracker = Mock()
    monitor = StopLossMonitor(
        order_manager=mock_order_manager,
        position_tracker=mock_position_tracker,
        config=config,
    )
    return monitor, mock_order_manager, mock_position_tracker


class TestStopLossAlert:
    """StopLossAlert 数据类测试"""

    def test_alert_creation_with_all_fields(self):
        """测试完整字段创建 StopLossAlert"""
        alert = StopLossAlert(
            token_id="token_001",
            reason="STOP_LOSS",
            trigger_price=0.45,
            cost_price=0.50,
            quantity=100.0,
            executed_at=1700000000.0,
            order_result={"success": True, "order_id": "sl_order_1"},
        )

        assert alert.token_id == "token_001"
        assert alert.reason == "STOP_LOSS"
        assert alert.trigger_price == 0.45
        assert alert.cost_price == 0.50
        assert alert.quantity == 100.0
        assert alert.executed_at == 1700000000.0
        assert alert.order_result is not None
        assert alert.order_result["success"] is True

    def test_alert_creation_without_order_result(self):
        """测试不含订单结果的 StopLossAlert 创建"""
        alert = StopLossAlert(
            token_id="token_002",
            reason="TAKE_PROFIT",
            trigger_price=0.60,
            cost_price=0.50,
            quantity=200.0,
            executed_at=1700000001.0,
        )

        assert alert.order_result is None

    def test_alert_stop_loss_reason(self):
        """测试 STOP_LOSS 原因值"""
        alert = StopLossAlert(
            token_id="t", reason="STOP_LOSS", trigger_price=0.4,
            cost_price=0.5, quantity=10.0, executed_at=0.0,
        )
        assert alert.reason == "STOP_LOSS"

    def test_alert_take_profit_reason(self):
        """测试 TAKE_PROFIT 原因值"""
        alert = StopLossAlert(
            token_id="t", reason="TAKE_PROFIT", trigger_price=0.6,
            cost_price=0.5, quantity=10.0, executed_at=0.0,
        )
        assert alert.reason == "TAKE_PROFIT"


class TestPosition:
    """Position 数据类测试"""

    def test_position_default_values(self):
        """测试 Position 默认值"""
        pos = Position(token_id="t1", current_price=0.5, avg_cost=0.5, quantity=100)
        assert pos.market_id == ""
        assert pos.side == "LONG"

    def test_position_custom_values(self):
        """测试 Position 自定义值"""
        pos = Position(
            token_id="t2", current_price=0.6, avg_cost=0.4, quantity=200,
            market_id="m1", side="SHORT",
        )
        assert pos.market_id == "m1"
        assert pos.side == "SHORT"


class TestStopLossMonitorInit:
    """初始化测试"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        monitor, _, _ = _make_monitor(config=None)

        assert monitor.enabled is True
        assert monitor.stop_loss_pct == 0.1
        assert monitor.take_profit_pct == 0.2
        assert monitor.check_interval == 5.0
        assert monitor.is_running() is False

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "stop_loss_take_profit": {
                "enabled": True,
                "stop_loss_percentage": 0.15,
                "take_profit_percentage": 0.3,
            }
        }
        monitor, _, _ = _make_monitor(config=config)

        assert monitor.enabled is True
        assert monitor.stop_loss_pct == 0.15
        assert monitor.take_profit_pct == 0.3

    def test_init_disabled_from_config(self):
        """测试从配置中禁用"""
        config = {
            "stop_loss_take_profit": {
                "enabled": False,
                "stop_loss_percentage": 0.1,
                "take_profit_percentage": 0.2,
            }
        }
        monitor, _, _ = _make_monitor(config=config)

        assert monitor.enabled is False

    def test_init_empty_config_dict(self):
        """测试空配置字典使用默认值"""
        monitor, _, _ = _make_monitor(config={})

        assert monitor.enabled is True
        assert monitor.stop_loss_pct == 0.1
        assert monitor.take_profit_pct == 0.2

    def test_init_stats_zeroed(self):
        """测试初始化时统计数据归零"""
        monitor, _, _ = _make_monitor()
        stats = monitor.get_stats()

        assert stats["check_count"] == 0
        assert stats["trigger_count"] == 0
        assert stats["stop_loss_count"] == 0
        assert stats["take_profit_count"] == 0


class TestCheckPosition:
    """持仓检查逻辑测试"""

    def test_stop_loss_trigger_exact_boundary(self):
        """测试止损精确边界触发 (price < cost * 0.9)"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.449, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result == "STOP_LOSS"

    def test_stop_loss_trigger_deep_decline(self):
        """测试深度下跌触发止损"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.30, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result == "STOP_LOSS"

    def test_stop_loss_no_trigger_at_boundary(self):
        """测试止损边界值不触发 (price == cost * 0.9)"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.45, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result is None

    def test_stop_loss_no_trigger_above_threshold(self):
        """测试高于止损阈值不触发"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.46, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result is None

    def test_take_profit_trigger_exact_boundary(self):
        """测试止盈精确边界触发 (price > cost * 1.2)"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.601, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result == "TAKE_PROFIT"

    def test_take_profit_trigger_large_gain(self):
        """测试大幅上涨触发止盈"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.80, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result == "TAKE_PROFIT"

    def test_take_profit_no_trigger_at_boundary(self):
        """测试止盈边界值不触发 (price == cost * 1.2)"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.60, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result is None

    def test_take_profit_no_trigger_below_threshold(self):
        """测试低于止盈阈值不触发"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.59, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result is None

    def test_no_trigger_in_normal_range(self):
        """测试正常价格范围内不触发任何条件"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.50, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result is None

    def test_slight_loss_no_trigger(self):
        """测试小幅亏损不触发止损"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.46, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result is None

    def test_slight_gain_no_trigger(self):
        """测试小幅盈利不止盈"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.58, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result is None

    def test_custom_stop_loss_percentage(self):
        """测试自定义止损百分比"""
        config = {"stop_loss_take_profit": {"stop_loss_percentage": 0.20}}
        monitor, _, _ = _make_monitor(config=config)
        position = _make_position(current_price=0.39, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result == "STOP_LOSS"

    def test_custom_take_profit_percentage(self):
        """测试自定义止盈百分比"""
        config = {"stop_loss_take_profit": {"take_profit_percentage": 0.50}}
        monitor, _, _ = _make_monitor(config=config)
        position = _make_position(current_price=0.76, avg_cost=0.50)

        result = monitor._check_position(position)
        assert result == "TAKE_PROFIT"

    def test_missing_current_price_returns_none(self):
        """测试缺少 current_price 属性返回 None"""
        monitor, _, _ = _make_monitor()
        bad_pos = Mock(spec=[])
        del bad_pos.current_price
        bad_pos.avg_cost = 0.50

        result = monitor._check_position(bad_pos)
        assert result is None

    def test_missing_avg_cost_returns_none(self):
        """测试缺少 avg_cost 属性返回 None"""
        monitor, _, _ = _make_monitor()
        bad_pos = Mock(spec=[])
        bad_pos.current_price = 0.40
        del bad_pos.avg_cost

        result = monitor._check_position(bad_pos)
        assert result is None

    def test_zero_avg_cost_returns_none(self):
        """测试零成本价返回 None"""
        monitor, _, _ = _make_monitor()
        position = _make_position(current_price=0.30, avg_cost=0.0)

        result = monitor._check_position(position)
        assert result is None


class TestExecuteStopOrder:
    """执行止损/止盈订单测试"""

    def test_execute_stop_loss_order_calls_sell(self):
        """测试止损触发调用 execute_sell_order"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result()
        position = _make_position()

        result = monitor._execute_stop_order(position, "STOP_LOSS")

        mock_om.execute_sell_order.assert_called_once_with(
            token_id="token_001",
            size=100.0,
            order_type="FAK",
        )
        assert result is not None

    def test_execute_take_profit_order_calls_sell(self):
        """测试止盈触发调用 execute_sell_order"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result(order_id="tp_001")
        position = _make_position(quantity=200.0)

        result = monitor._execute_stop_order(position, "TAKE_PROFIT")

        mock_om.execute_sell_order.assert_called_once_with(
            token_id="token_001",
            size=200.0,
            order_type="FAK",
        )
        assert result.order_id == "tp_001"

    def test_execute_increments_stop_loss_count(self):
        """测试止损执行增加统计计数"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result()
        position = _make_position()

        monitor._execute_stop_order(position, "STOP_LOSS")
        stats = monitor.get_stats()

        assert stats["stop_loss_count"] == 1
        assert stats["trigger_count"] == 1
        assert stats["take_profit_count"] == 0

    def test_execute_increments_take_profit_count(self):
        """测试止盈执行增加统计计数"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result()
        position = _make_position()

        monitor._execute_stop_order(position, "TAKE_PROFIT")
        stats = monitor.get_stats()

        assert stats["take_profit_count"] == 1
        assert stats["trigger_count"] == 1
        assert stats["stop_loss_count"] == 0

    def test_execute_creates_alert_record(self):
        """测试执行后创建告警记录"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result()
        position = _make_position(current_price=0.44, avg_cost=0.50, quantity=150.0)

        monitor._execute_stop_order(position, "STOP_LOSS")

        alerts = monitor.get_alert_history()
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.token_id == "token_001"
        assert alert.reason == "STOP_LOSS"
        assert alert.trigger_price == 0.44
        assert alert.cost_price == 0.50
        assert alert.quantity == 150.0
        assert alert.order_result is not None

    def test_execute_handles_sell_exception(self):
        """测试卖出异常时的容错处理"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.side_effect = Exception("网络错误")
        position = _make_position()

        result = monitor._execute_stop_order(position, "STOP_LOSS")

        assert result is None
        alerts = monitor.get_alert_history()
        assert len(alerts) == 1
        assert alerts[0].order_result is None

    def test_execute_failed_order_still_records_alert(self):
        """测试失败订单仍记录告警"""
        monitor, mock_om, _ = _make_monitor()
        failed_result = _make_order_result(success=False)
        mock_om.execute_sell_order.return_value = failed_result
        position = _make_position()

        monitor._execute_stop_order(position, "TAKE_PROFIT")

        alerts = monitor.get_alert_history()
        assert len(alerts) == 1
        assert alerts[0].reason == "TAKE_PROFIT"


class TestMonitorLoop:
    """监控循环集成测试"""

    def test_start_sets_running_true(self):
        """测试启动后运行状态为 True"""
        monitor, mock_om, mock_pt = _make_monitor()
        mock_pt.get_open_positions.return_value = []

        monitor.start()
        time.sleep(0.1)

        assert monitor.is_running() is True

        monitor.stop()

    def test_stop_sets_running_false(self):
        """测试停止后运行状态为 False"""
        monitor, mock_om, mock_pt = _make_monitor()
        mock_pt.get_open_positions.return_value = []

        monitor.start()
        time.sleep(0.1)
        monitor.stop()

        assert monitor.is_running() is False

    def test_double_start_is_safe(self):
        """测试重复启动安全性"""
        monitor, mock_om, mock_pt = _make_monitor()
        mock_pt.get_open_positions.return_value = []

        monitor.start()
        time.sleep(0.1)
        monitor.start()

        assert monitor.is_running() is True
        monitor.stop()

    def test_double_stop_is_safe(self):
        """测试重复停止安全性"""
        monitor, _, _ = _make_monitor()

        monitor.stop()
        monitor.stop()
        assert monitor.is_running() is False

    def test_disabled_does_not_start_thread(self):
        """测试禁用状态不启动线程"""
        config = {"stop_loss_take_profit": {"enabled": False}}
        monitor, _, mock_pt = _make_monitor(config=config)

        monitor.start()
        time.sleep(0.1)

        assert monitor.is_running() is False
        assert monitor._thread is None

    def test_loop_checks_positions_periodically(self):
        """测试循环定期检查持仓"""
        monitor, mock_om, mock_pt = _make_monitor(config=None)
        monitor.check_interval = 0.05
        mock_pt.get_open_positions.return_value = []
        mock_om.execute_sell_order.return_value = _make_order_result()

        monitor.start()
        time.sleep(0.25)
        monitor.stop()

        assert mock_pt.get_open_positions.call_count >= 2
        stats = monitor.get_stats()
        assert stats["check_count"] >= 2

    def test_loop_triggers_on_stop_loss_condition(self):
        """测试循环检测到止损条件并执行"""
        monitor, mock_om, mock_pt = _make_monitor()
        monitor.check_interval = 0.05
        losing_position = _make_position(current_price=0.40, avg_cost=0.50)
        mock_pt.get_open_positions.return_value = [losing_position]
        mock_om.execute_sell_order.return_value = _make_order_result()

        monitor.start()
        time.sleep(0.2)
        monitor.stop()

        assert mock_om.execute_sell_order.call_count >= 1
        stats = monitor.get_stats()
        assert stats["stop_loss_count"] >= 1

    def test_empty_positions_handled_safely(self):
        """测试空持仓列表安全处理"""
        monitor, mock_om, mock_pt = _make_monitor()
        monitor.check_interval = 0.05
        mock_pt.get_open_positions.return_value = []

        monitor.start()
        time.sleep(0.15)
        monitor.stop()

        mock_om.execute_sell_order.assert_not_called()
        stats = monitor.get_stats()
        assert stats["trigger_count"] == 0


class TestStatsAndHistory:
    """统计与历史记录测试"""

    def test_get_stats_returns_all_keys(self):
        """测试 get_stats 返回所有必需字段"""
        monitor, _, _ = _make_monitor()
        stats = monitor.get_stats()

        expected_keys = {
            "is_running", "enabled", "stop_loss_pct", "take_profit_pct",
            "check_interval", "check_count", "trigger_count",
            "stop_loss_count", "take_profit_count", "alert_history_size",
        }
        assert set(stats.keys()) == expected_keys

    def test_get_alert_history_respects_limit(self):
        """测试 get_alert_history 遵守数量限制"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result()

        for i in range(10):
            pos = _make_position(token_id=f"token_{i}")
            monitor._execute_stop_order(pos, "STOP_LOSS" if i % 2 == 0 else "TAKE_PROFIT")

        alerts = monitor.get_alert_history(limit=3)
        assert len(alerts) == 3

    def test_get_alert_history_all_by_default(self):
        """测试默认获取全部历史"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result()

        for i in range(5):
            pos = _make_position(token_id=f"token_{i}")
            monitor._execute_stop_order(pos, "STOP_LOSS")

        alerts = monitor.get_alert_history()
        assert len(alerts) == 5

    def test_reset_stats_clears_everything(self):
        """测试 reset_stats 清空所有数据"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result()

        pos = _make_position()
        monitor._execute_stop_order(pos, "STOP_LOSS")
        monitor._check_count = 10

        monitor.reset_stats()
        stats = monitor.get_stats()

        assert stats["check_count"] == 0
        assert stats["trigger_count"] == 0
        assert stats["stop_loss_count"] == 0
        assert stats["take_profit_count"] == 0
        assert stats["alert_history_size"] == 0

    def test_alert_history_auto_trims(self):
        """测试历史记录自动裁剪（超过上限）"""
        monitor, mock_om, _ = _make_monitor()
        mock_om.execute_sell_order.return_value = _make_order_result()

        for i in range(1100):
            pos = _make_position(token_id=f"t_{i}")
            monitor._execute_stop_order(pos, "STOP_LOSS")

        assert len(monitor._alert_history) <= 1000


class TestCheckIntervalConfigurable:
    """检查间隔可配置性测试"""

    def test_default_check_interval(self):
        """测试默认检查间隔"""
        monitor, _, _ = _make_monitor()
        assert monitor.check_interval == 5.0

    def test_custom_check_interval(self):
        """测试自定义检查间隔"""
        monitor, _, _ = _make_monitor()
        monitor.check_interval = 1.5
        assert monitor.check_interval == 1.5

    def test_short_check_interval_in_loop(self):
        """测试短间隔在循环中的效果"""
        monitor, mock_om, mock_pt = _make_monitor()
        monitor.check_interval = 0.03
        mock_pt.get_open_positions.return_value = []

        monitor.start()
        time.sleep(0.18)
        monitor.stop()

        stats = monitor.get_stats()
        assert stats["check_count"] >= 3


class TestPositionTrackerIntegration:
    """PositionTracker 集成测试"""

    def test_get_open_positions_called_each_cycle(self):
        """测试每次循环都调用 get_open_positions"""
        monitor, mock_om, mock_pt = _make_monitor()
        monitor.check_interval = 0.05
        mock_pt.get_open_positions.return_value = []

        monitor.start()
        time.sleep(0.2)
        monitor.stop()

        assert mock_pt.get_open_positions.call_count >= 2

    def test_multiple_positions_checked_individually(self):
        """测试多个持仓逐一检查"""
        monitor, mock_om, mock_pt = _make_monitor()
        positions = [
            _make_position("t1", current_price=0.40, avg_cost=0.50),
            _make_position("t2", current_price=0.55, avg_cost=0.50),
            _make_position("t3", current_price=0.35, avg_cost=0.50),
        ]
        mock_pt.get_open_positions.return_value = positions
        mock_om.execute_sell_order.return_value = _make_order_result()

        monitor._check_positions()

        assert mock_om.execute_sell_order.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
