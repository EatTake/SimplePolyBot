"""
OrderManager 与 RiskManager 集成测试

验证 OrderManager 正确集成风控检查：
- 买单在执行前经过完整风控流程
- 卖单经过宽松版风控（仅日亏损检查）
- 风控拒绝时返回正确的 OrderResult
- 统计信息包含风控状态
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from contextlib import ExitStack

from modules.order_executor.order_manager import (
    OrderManager,
    OrderResult,
)
from modules.order_executor.clob_client import ClobClientWrapper
from modules.order_executor.fee_calculator import FeeCalculator


def _build_mock_clob_client(
    usdc_balance: float = 10000.0,
    token_balance: float = 1000.0,
    tick_size: str = "0.01",
    order_response: dict | None = None,
) -> Mock:
    client = Mock(spec=ClobClientWrapper)
    client.get_usdc_balance.return_value = usdc_balance
    client.get_token_balance.return_value = token_balance
    client.get_tick_size.return_value = tick_size
    client.get_neg_risk.return_value = False
    client.get_order_book.return_value = {
        "bids": [{"price": "0.49", "size": "1000"}],
        "asks": [{"price": "0.51", "size": "1000"}],
    }
    client.create_and_submit_order.return_value = order_response or {
        "success": True,
        "orderID": "order_test_001",
        "status": "matched",
        "errorMsg": "",
    }
    return client


def _build_mock_config(
    risk_config: dict | None = None,
    min_order_size: float = 10,
    max_order_size: float = 10000,
) -> Mock:
    config = Mock()
    config.get_strategy_config.return_value = Mock(
        max_buy_prices={"default": 0.95},
        order_sizes={"min": min_order_size, "max": max_order_size},
        risk_management=risk_config or {
            "max_position_size": 5000.0,
            "max_total_exposure": 20000.0,
            "max_daily_loss": 500.0,
            "max_drawdown": 0.15,
            "min_balance": 100.0,
        },
    )
    return config


class TestRiskIntegrationInit:
    """OrderManager 初始化时正确创建 RiskManager 和 PositionTracker"""

    def test_position_tracker_created(self):
        client = _build_mock_clob_client()
        config = _build_mock_config()
        om = OrderManager(clob_client=client, config=config)
        assert om.position_tracker is not None
        assert om.risk_manager is not None

    def test_risk_manager_uses_passed_config(self):
        custom_risk = {"max_position_size": 999, "max_daily_loss": 50}
        client = _build_mock_clob_client()
        config = _build_mock_config(risk_config=custom_risk)
        om = OrderManager(clob_client=client, config=config)
        assert om.risk_manager.max_position_size == 999.0
        assert om.risk_manager.max_daily_loss == 50.0

    def test_risk_management_dict_still_accessible(self):
        client = _build_mock_clob_client()
        config = _build_mock_config()
        om = OrderManager(clob_client=client, config=config)
        assert isinstance(om.risk_management, dict)


class TestBuyOrderPassesRiskCheck:
    """正常买单通过所有风控检查"""

    def setup_method(self):
        self.client = _build_mock_clob_client()
        self.config = _build_mock_config()
        self.om = OrderManager(clob_client=self.client, config=self.config)
        self.pt = self.om.position_tracker

    def test_normal_buy_passes(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="token_a", size=100, max_price=0.60)
        assert result.success is True
        assert result.order_id == "order_test_001"

    def test_small_buy_passes(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="token_b", size=10, max_price=0.50)
        assert result.success is True

    def test_metadata_contains_risk_check_on_success(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="token_c", size=100, max_price=0.60)
        assert "risk_check" in result.metadata
        rc = result.metadata["risk_check"]
        assert "token_id" in rc
        assert "side" in rc
        assert "order_value" in rc


class TestBuyOrderPositionLimitRejected:
    """单仓位超限 → 买单被风控拒绝"""

    def setup_method(self):
        self.client = _build_mock_clob_client()
        self.config = _build_mock_config(risk_config={
            "max_position_size": 500.0,
            "max_total_exposure": 20000.0,
            "max_daily_loss": 500.0,
            "max_drawdown": 0.15,
            "min_balance": 100.0,
        })
        self.om = OrderManager(clob_client=self.client, config=self.config)
        self.pt = self.om.position_tracker

    def test_single_position_exceeded_rejected(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=400.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=400.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="token_x", size=200, max_price=0.60)
        assert result.success is False
        assert "Risk check failed" in result.error_message
        assert "单仓位超限" in result.error_message

    def test_rejected_result_has_risk_details(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=450.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=450.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="token_y", size=100, max_price=0.60)
        assert "risk_check" in result.metadata
        details = result.metadata["risk_check"]
        assert details["new_position"] > 500.0


class TestBuyOrderTotalExposureRejected:
    """总敞口超限 → 买单被风控拒绝"""

    def setup_method(self):
        self.client = _build_mock_clob_client()
        self.config = _build_mock_config(risk_config={
            "max_position_size": 100000.0,
            "max_total_exposure": 1000.0,
            "max_daily_loss": 500.0,
            "max_drawdown": 0.15,
            "min_balance": 100.0,
        })
        self.om = OrderManager(clob_client=self.client, config=self.config)
        self.pt = self.om.position_tracker

    def test_total_exposure_exceeded_rejected(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=900.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="token_z", size=200, max_price=0.60)
        assert result.success is False
        assert "总敞口超限" in result.error_message

    def test_exposure_details_in_metadata(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=950.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="token_z", size=100, max_price=0.60)
        details = result.metadata["risk_check"]
        assert details["new_total_exposure"] > 1000.0


class TestBuyOrderDailyLossRejected:
    """日亏损超限 → 买单被风控拒绝（买卖方向均受影响）"""

    def setup_method(self):
        self.client = _build_mock_clob_client()
        self.config = _build_mock_config(risk_config={
            "max_position_size": 100000.0,
            "max_total_exposure": 100000.0,
            "max_daily_loss": 100.0,
            "max_drawdown": 0.15,
            "min_balance": 100.0,
        })
        self.om = OrderManager(clob_client=self.client, config=self.config)
        self.pt = self.om.position_tracker

    def test_daily_loss_exceeded_rejects_buy(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=-150.0))
            result = self.om.execute_buy_order(token_id="token_d", size=100, max_price=0.50)
        assert result.success is False
        assert "日亏损超限" in result.error_message

    def test_daily_loss_at_limit_still_passes(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=-99.99))
            result = self.om.execute_buy_order(token_id="token_d", size=100, max_price=0.50)
        assert result.success is True


class TestBuyOrderBalanceInsufficient:
    """余额不足（预估剩余 < min_balance）→ 被风控拒绝"""

    def setup_method(self):
        self.client = _build_mock_clob_client(usdc_balance=150.0)
        self.config = _build_mock_config(risk_config={
            "max_position_size": 100000.0,
            "max_total_exposure": 100000.0,
            "max_daily_loss": 1000.0,
            "max_drawdown": 0.15,
            "min_balance": 100.0,
        })
        self.om = OrderManager(clob_client=self.client, config=self.config)
        self.pt = self.om.position_tracker
        self.pt.get_balance = Mock(return_value=150.0)

    def test_low_balance_rejects_large_order(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_balance', return_value=150.0))
            result = self.om.execute_buy_order(token_id="token_e", size=100, max_price=0.90)
        assert result.success is False
        assert "余额不足" in result.error_message

    def test_small_order_with_enough_remaining_passes(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_balance', return_value=150.0))
            result = self.om.execute_buy_order(token_id="token_e", size=10, max_price=0.50)
        assert result.success is True


class TestSellOrderRiskBehavior:
    """卖单风控行为：比买单更宽松，但仍检查日亏损"""

    def setup_method(self):
        self.client = _build_mock_clob_client()
        self.config = _build_mock_config(risk_config={
            "max_position_size": 100.0,
            "max_total_exposure": 1000.0,
            "max_daily_loss": 500.0,
            "max_drawdown": 0.15,
            "min_balance": 100.0,
        })
        self.om = OrderManager(clob_client=self.client, config=self.config)
        self.pt = self.om.position_tracker

    def test_sell_passes_despite_high_position(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=99999.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=99999.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_sell_order(token_id="token_s", size=100, min_price=0.40)
        assert result.success is True

    def test_sell_rejected_when_daily_loss_exceeded(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=-600.0))
            result = self.om.execute_sell_order(token_id="token_s", size=100, min_price=0.40)
        assert result.success is False
        assert "Risk check failed" in result.error_message

    def test_sell_metadata_contains_risk_info(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_sell_order(token_id="token_s2", size=100, min_price=0.40)
        assert "risk_check" in result.metadata
        assert result.metadata["risk_check"]["side"] == "SELL"


class TestStatisticsWithRiskInfo:
    """get_statistics 包含风控状态信息"""

    def test_empty_history_has_risk_status(self):
        client = _build_mock_clob_client()
        config = _build_mock_config()
        om = OrderManager(clob_client=client, config=config)
        stats = om.get_statistics()
        assert "risk_status" in stats
        rs = stats["risk_status"]
        assert "risk_parameters" in rs
        assert "current_state" in rs

    def test_after_order_stats_include_risk(self):
        client = _build_mock_clob_client()
        config = _build_mock_config()
        om = OrderManager(clob_client=client, config=config)
        pt = om.position_tracker
        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            om.execute_buy_order(token_id="t1", size=100, max_price=0.60)
        stats = om.get_statistics()
        assert "risk_status" in stats
        assert stats["total_orders"] == 1

    def test_risk_parameters_reflect_config(self):
        custom = {"max_position_size": 777, "max_daily_loss": 42}
        client = _build_mock_clob_client()
        config = _build_mock_config(risk_config=custom)
        om = OrderManager(clob_client=client, config=config)
        stats = om.get_statistics()
        rp = stats["risk_status"]["risk_parameters"]
        assert rp["max_position_size"] == 777.0
        assert rp["max_daily_loss"] == 42.0


class TestPositionTrackerAutoUpdate:
    """验证 position_tracker 在 OrderManager 中可用并可被外部更新"""

    def test_position_tracker_accessible(self):
        client = _build_mock_clob_client()
        config = _build_mock_config()
        om = OrderManager(clob_client=client, config=config)
        assert om.position_tracker is om.risk_manager.position_tracker

    def test_position_update_affects_risk_check(self):
        client = _build_mock_clob_client()
        config = _build_mock_config(risk_config={
            "max_position_size": 300.0,
            "max_total_exposure": 100000.0,
            "max_daily_loss": 1000.0,
            "max_drawdown": 0.15,
            "min_balance": 10.0,
        })
        om = OrderManager(clob_client=client, config=config)
        pt = om.position_tracker

        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            r1 = om.execute_buy_order(token_id="p1", size=100, max_price=0.50)
        assert r1.success is True

        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', return_value=50.0))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=50.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            r2 = om.execute_buy_order(token_id="p1", size=100, max_price=0.60)
        assert r2.success is True

        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', return_value=240.0))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=240.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            r3 = om.execute_buy_order(token_id="p1", size=100, max_price=0.70)
        assert r3.success is False
        assert "单仓位超限" in r3.error_message


class TestBoundaryExactAtLimits:
    """边界值精确等于限制时应通过（size >= MIN_ORDER_SIZE=10）"""

    def setup_method(self):
        self.client = _build_mock_clob_client(usdc_balance=99999.0)
        self.config = _build_mock_config(risk_config={
            "max_position_size": 1000.0,
            "max_total_exposure": 5000.0,
            "max_daily_loss": 300.0,
            "max_drawdown": 0.15,
            "min_balance": 50.0,
        })
        self.om = OrderManager(clob_client=self.client, config=self.config)
        self.pt = self.om.position_tracker

    def test_position_exact_at_max_passes(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=995.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=995.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="b1", size=10, max_price=0.50)
        assert result.success is True

    def test_position_one_over_fails(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=995.1))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=995.1))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="b1", size=10, max_price=0.51)
        assert result.success is False

    def test_total_exposure_exact_at_max_passes(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=4995.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_buy_order(token_id="b2", size=10, max_price=0.50)
        assert result.success is True

    def test_daily_loss_exact_at_limit_passes(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=-299.99))
            result = self.om.execute_buy_order(token_id="b3", size=10, max_price=0.50)
        assert result.success is True

    def test_daily_loss_one_cent_over_fails(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=-300.01))
            result = self.om.execute_buy_order(token_id="b3", size=10, max_price=0.50)
        assert result.success is False
        assert "日亏损超限" in result.error_message

    def test_balance_exact_at_min_passes(self):
        self.pt.get_balance = Mock(return_value=50.1)
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_balance', return_value=50.1))
            result = self.om.execute_buy_order(token_id="b4", size=10, max_price=0.01)
        assert result.success is True


class TestRiskCheckDetailsCompleteness:
    """验证被拒绝订单的 metadata 包含完整的检查详情"""

    def test_rejected_buy_has_full_details(self):
        client = _build_mock_clob_client()
        config = _build_mock_config(risk_config={
            "max_position_size": 10.0,
            "max_total_exposure": 100000.0,
            "max_daily_loss": 1000.0,
            "max_drawdown": 0.15,
            "min_balance": 10.0,
        }, min_order_size=5)
        om = OrderManager(clob_client=client, config=config)
        pt = om.position_tracker

        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', return_value=9.0))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=9.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            result = om.execute_buy_order(token_id="detail_test", size=10, max_price=0.50)

        assert result.success is False
        details = result.metadata["risk_check"]
        expected_keys = {
            "token_id", "side", "price", "size", "order_value",
            "current_position", "total_exposure", "daily_pnl",
            "current_balance", "new_position", "new_total_exposure",
            "estimated_remaining",
        }
        assert expected_keys.issubset(details.keys())

    def test_successful_buy_has_risk_details(self):
        client = _build_mock_clob_client()
        config = _build_mock_config()
        om = OrderManager(clob_client=client, config=config)
        pt = om.position_tracker
        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            result = om.execute_buy_order(token_id="ok", size=100, max_price=0.60)
        assert result.success is True
        assert "risk_check" in result.metadata
        rc = result.metadata["risk_check"]
        assert "token_id" in rc
        assert "side" in rc
        assert "order_value" in rc


class TestMultipleSequentialOrders:
    """连续多笔订单的风控状态累积测试"""

    def test_multiple_buys_within_limits(self):
        client = _build_mock_clob_client(usdc_balance=50000.0)
        config = _build_mock_config(risk_config={
            "max_position_size": 3000.0,
            "max_total_exposure": 10000.0,
            "max_daily_loss": 1000.0,
            "max_drawdown": 0.15,
            "min_balance": 100.0,
        })
        om = OrderManager(clob_client=client, config=config)
        pt = om.position_tracker

        positions = {"t1": 0.0, "t2": 0.0}

        def mock_get_pos(tid):
            return positions.get(tid, 0.0)

        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', side_effect=mock_get_pos))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            r1 = om.execute_buy_order(token_id="t1", size=100, max_price=0.50)
            assert r1.success is True
            positions["t1"] = 50.0

        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', side_effect=mock_get_pos))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=50.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            r2 = om.execute_buy_order(token_id="t2", size=100, max_price=0.50)
            assert r2.success is True
            positions["t2"] = 50.0

        with ExitStack() as stack:
            stack.enter_context(patch.object(pt, 'get_position', side_effect=mock_get_pos))
            stack.enter_context(patch.object(pt, 'get_total_exposure', return_value=100.0))
            stack.enter_context(patch.object(pt, 'get_daily_pnl', return_value=0.0))
            r3 = om.execute_buy_order(token_id="t1", size=5000, max_price=0.60)
            assert r3.success is False
            assert "单仓位超限" in r3.error_message


class TestSellOrderWithDailyLossOnly:
    """卖单只受日亏损限制，不受仓位/敞口/余额限制"""

    def setup_method(self):
        self.client = _build_mock_clob_client(token_balance=10000.0)
        self.config = _build_mock_config(risk_config={
            "max_position_size": 1.0,
            "max_total_exposure": 1.0,
            "max_daily_loss": 500.0,
            "max_drawdown": 0.15,
            "min_balance": 99999.0,
        })
        self.om = OrderManager(clob_client=self.client, config=self.config)
        self.pt = self.om.position_tracker

    def test_sell_ignores_tiny_position_limit(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=99999.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=99999.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_sell_order(token_id="s1", size=500, min_price=0.30)
        assert result.success is True

    def test_sell_ignores_tiny_exposure_limit(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=99999.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            result = self.om.execute_sell_order(token_id="s2", size=500, min_price=0.30)
        assert result.success is True

    def test_sell_ignores_min_balance(self):
        self.pt.get_balance = Mock(return_value=1.0)
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_balance', return_value=1.0))
            result = self.om.execute_sell_order(token_id="s3", size=500, min_price=0.30)
        assert result.success is True

    def test_sell_blocked_only_by_daily_loss(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.pt, 'get_position', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_total_exposure', return_value=0.0))
            stack.enter_context(patch.object(self.pt, 'get_daily_pnl', return_value=-600.0))
            result = self.om.execute_sell_order(token_id="s4", size=500, min_price=0.30)
        assert result.success is False
        assert "日亏损超限" in result.error_message
