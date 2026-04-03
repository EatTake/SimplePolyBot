from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from shared.risk_manager import RiskManager, RiskCheckResult


class TestRiskCheckResult:
    """RiskCheckResult 数据类测试"""
    
    def test_default_values(self):
        result = RiskCheckResult(passed=True, reason="test")
        assert result.passed is True
        assert result.reason == "test"
        assert result.check_details == {}
    
    def test_with_details(self):
        details = {"key": "value"}
        result = RiskCheckResult(passed=False, reason="fail", check_details=details)
        assert result.passed is False
        assert result.check_details == details


class TestRiskManagerInit:
    """RiskManager 初始化测试"""
    
    def test_default_config(self):
        manager = RiskManager()
        assert manager.max_position_size == 5000.0
        assert manager.max_total_exposure == 20000.0
        assert manager.max_daily_loss == 500.0
        assert manager.max_drawdown == 0.15
        assert manager.min_balance == 100.0
    
    def test_custom_config(self):
        config = {
            "max_position_size": 1000,
            "max_total_exposure": 5000,
            "max_daily_loss": 200,
            "max_drawdown": 0.1,
            "min_balance": 50,
        }
        manager = RiskManager(config=config)
        assert manager.max_position_size == 1000.0
        assert manager.max_total_exposure == 5000.0
        assert manager.max_daily_loss == 200.0
        assert manager.max_drawdown == 0.1
        assert manager.min_balance == 50.0
    
    def test_partial_config(self):
        config = {"max_position_size": 3000}
        manager = RiskManager(config=config)
        assert manager.max_position_size == 3000.0
        assert manager.max_total_exposure == 20000.0
    
    def test_with_position_tracker(self):
        tracker = MagicMock()
        manager = RiskManager(position_tracker=tracker)
        assert manager.position_tracker is tracker
    
    def test_without_position_tracker(self):
        manager = RiskManager(position_tracker=None)
        assert manager.position_tracker is None


class TestSinglePositionLimit:
    """单仓位限制检查测试"""
    
    def setup_method(self):
        self.manager = RiskManager()
        self.tracker = MagicMock()
        self.tracker.get_position.return_value = 0
        self.tracker.get_positions.return_value = {}
        self.tracker.get_total_exposure.return_value = 0
        self.tracker.get_daily_pnl.return_value = 0
        self.tracker.get_balance.return_value = 10000
        self.manager.position_tracker = self.tracker
    
    def test_within_limit(self):
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_exact_at_limit(self):
        self.tracker.get_position.return_value = 4500
        result = self.manager.check_before_order("token1", "BUY", 0.5, 1000)
        assert result.passed is True
        assert result.check_details["new_position"] == 5000.0
    
    def test_exceeds_limit_by_small_amount(self):
        self.tracker.get_position.return_value = 4500
        result = self.manager.check_before_order("token1", "BUY", 0.5, 1001)
        assert result.passed is False
        assert "单仓位超限" in result.reason
    
    def test_exceeds_limit_significantly(self):
        self.tracker.get_position.return_value = 3000
        result = self.manager.check_before_order("token1", "BUY", 0.5, 5000)
        assert result.passed is False
        assert result.check_details["new_position"] == 5500.0
    
    def test_sell_order_ignores_position_increase(self):
        self.tracker.get_position.return_value = 6000
        result = self.manager.check_before_order("token1", "SELL", 0.5, 100)
        assert result.passed is True
    
    def test_zero_position_new_order(self):
        self.tracker.get_position.return_value = 0
        result = self.manager.check_before_order("token1", "BUY", 0.5, 11000)
        assert result.passed is False
        assert result.check_details["new_position"] == 5500.0


class TestTotalExposureLimit:
    """总敞口限制检查测试"""
    
    def setup_method(self):
        self.manager = RiskManager()
        self.tracker = MagicMock()
        self.tracker.get_position.return_value = 0
        self.tracker.get_positions.return_value = {}
        self.tracker.get_total_exposure.return_value = 0
        self.tracker.get_daily_pnl.return_value = 0
        self.tracker.get_balance.return_value = 10000
        self.manager.position_tracker = self.tracker
    
    def test_within_total_exposure(self):
        self.tracker.get_total_exposure.return_value = 10000
        result = self.manager.check_before_order("token1", "BUY", 0.5, 1000)
        assert result.passed is True
    
    def test_exact_at_total_exposure_limit(self):
        self.tracker.get_total_exposure.return_value = 15000
        result = self.manager.check_before_order("token1", "BUY", 0.5, 10000)
        assert result.passed is True
        assert result.check_details["new_total_exposure"] == 20000.0
    
    def test_exceeds_total_exposure(self):
        self.tracker.get_position.return_value = 0
        self.tracker.get_total_exposure.return_value = 18000
        result = self.manager.check_before_order("token1", "BUY", 0.5, 5000)
        assert result.passed is False
        assert "总敞口超限" in result.reason
    
    def test_sell_order_no_exposure_increase(self):
        self.tracker.get_total_exposure.return_value = 25000
        result = self.manager.check_before_order("token1", "SELL", 0.5, 1000)
        assert result.passed is True
    
    def test_multiple_positions_sum(self):
        positions = {"token1": 8000, "token2": 8000, "token3": 4000}
        self.tracker.get_positions.return_value = positions
        self.tracker.get_total_exposure.return_value = 20000
        result = self.manager.check_before_order("token4", "BUY", 0.5, 100)
        assert result.passed is False


class TestDailyLossLimit:
    """日亏损限额检查测试"""
    
    def setup_method(self):
        self.manager = RiskManager()
        self.tracker = MagicMock()
        self.tracker.get_position.return_value = 0
        self.tracker.get_positions.return_value = {}
        self.tracker.get_total_exposure.return_value = 0
        self.tracker.get_daily_pnl.return_value = 0
        self.tracker.get_balance.return_value = 10000
        self.manager.position_tracker = self.tracker
    
    def test_no_loss(self):
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_small_loss_within_limit(self):
        self.tracker.get_daily_pnl.return_value = -200
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_exact_at_loss_limit(self):
        self.tracker.get_daily_pnl.return_value = -500
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_exceeds_loss_limit(self):
        self.tracker.get_daily_pnl.return_value = -600
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is False
        assert "日亏损超限" in result.reason
    
    def test_profit_not_blocked(self):
        self.tracker.get_daily_pnl.return_value = 1000
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_combined_with_manager_pnl(self):
        self.tracker.get_daily_pnl.return_value = -300
        self.manager.update_daily_pnl(-250)
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is False


class TestMinBalanceCheck:
    """余额保留检查测试"""
    
    def setup_method(self):
        self.manager = RiskManager()
        self.tracker = MagicMock()
        self.tracker.get_position.return_value = 0
        self.tracker.get_positions.return_value = {}
        self.tracker.get_total_exposure.return_value = 0
        self.tracker.get_daily_pnl.return_value = 0
        self.tracker.get_balance.return_value = 10000
        self.manager.position_tracker = self.tracker
    
    def test_sufficient_balance(self):
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_exact_at_min_balance(self):
        self.tracker.get_balance.return_value = 100
        result = self.manager.check_before_order("token1", "BUY", 0.5, 0)
        assert result.passed is True
    
    def test_below_min_balance(self):
        self.tracker.get_balance.return_value = 50
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is False
        assert "余额不足" in result.reason
    
    def test_sell_order_no_balance_check(self):
        self.tracker.get_balance.return_value = 10
        result = self.manager.check_before_order("token1", "SELL", 0.5, 1000)
        assert result.passed is True
    
    def test_large_order_depletes_balance(self):
        self.tracker.get_balance.return_value = 200
        result = self.manager.check_before_order("token1", "BUY", 0.9, 200)
        assert result.passed is False


class TestAllChecksPass:
    """全部通过的正常场景测试"""
    
    def test_normal_buy_order(self):
        tracker = MagicMock()
        tracker.get_position.return_value = 1000
        tracker.get_positions.return_value = {"token1": 1000}
        tracker.get_total_exposure.return_value = 5000
        tracker.get_daily_pnl.return_value = -100
        tracker.get_balance.return_value = 15000
        
        manager = RiskManager(position_tracker=tracker)
        result = manager.check_before_order("token2", "BUY", 0.6, 500)
        
        assert result.passed is True
        assert result.reason == "所有风控检查通过"
        assert result.check_details["order_value"] == 300.0
    
    def test_normal_sell_order(self):
        tracker = MagicMock()
        tracker.get_position.return_value = 2000
        tracker.get_positions.return_value = {"token1": 2000}
        tracker.get_total_exposure.return_value = 8000
        tracker.get_daily_pnl.return_value = 50
        tracker.get_balance.return_value = 12000
        
        manager = RiskManager(position_tracker=tracker)
        result = manager.check_before_order("token1", "SELL", 0.7, 300)
        
        assert result.passed is True
    
    def test_multiple_tokens_different_positions(self):
        tracker = MagicMock()
        tracker.get_position.side_effect = lambda tid: {"token1": 3000, "token2": 1000}.get(tid, 0)
        tracker.get_positions.return_value = {"token1": 3000, "token2": 1000}
        tracker.get_total_exposure.return_value = 4000
        tracker.get_daily_pnl.return_value = 0
        tracker.get_balance.return_value = 20000
        
        manager = RiskManager(position_tracker=tracker)
        
        result1 = manager.check_before_order("token1", "BUY", 0.5, 1000)
        assert result1.passed is True
        
        result2 = manager.check_before_order("token3", "BUY", 0.5, 1000)
        assert result2.passed is True


class TestBoundaryValues:
    """边界值精确等于限制的测试"""
    
    def setup_method(self):
        self.manager = RiskManager()
        self.tracker = MagicMock()
        self.tracker.get_position.return_value = 0
        self.tracker.get_positions.return_value = {}
        self.tracker.get_total_exposure.return_value = 0
        self.tracker.get_daily_pnl.return_value = 0
        self.tracker.get_balance.return_value = 10000
        self.manager.position_tracker = self.tracker
    
    def test_position_exactly_at_max(self):
        self.tracker.get_position.return_value = 4999.99
        result = self.manager.check_before_order("token1", "BUY", 0.5, 0.02)
        assert result.passed is True
    
    def test_total_exposure_exactly_at_max(self):
        self.tracker.get_total_exposure.return_value = 19999.99
        result = self.manager.check_before_order("token1", "BUY", 0.5, 0.02)
        assert result.passed is True
    
    def test_daily_loss_exactly_at_max(self):
        self.tracker.get_daily_pnl.return_value = -499.99
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_balance_exactly_at_min(self):
        self.tracker.get_balance.return_value = 100.01
        result = self.manager.check_before_order("token1", "BUY", 0.5, 0.02)
        assert result.passed is True
    
    def test_position_one_cent_over(self):
        self.tracker.get_position.return_value = 4999.99
        result = self.manager.check_before_order("token1", "BUY", 0.5, 0.03)
        assert result.passed is False


class TestNoPositionTrackerDegradation:
    """position_tracker 为 None 时的降级行为测试"""
    
    def test_none_tracker_allows_order(self):
        manager = RiskManager(position_tracker=None)
        result = manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_none_tracker_check_details_empty(self):
        manager = RiskManager(position_tracker=None)
        result = manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.check_details["current_position"] == 0.0
        assert result.check_details["total_exposure"] == 0.0
    
    def test_none_tracker_sell_always_passes(self):
        manager = RiskManager(position_tracker=None)
        result = manager.check_before_order("token1", "SELL", 0.5, 99999)
        assert result.passed is True
    
    def test_none_tracker_large_buy_within_limit(self):
        manager = RiskManager(position_tracker=None)
        result = manager.check_before_order("token1", "BUY", 0.5, 10000)
        assert result.passed is True
        assert result.check_details["new_position"] == 5000.0
    
    def test_none_tracker_large_buy_exceeds_limit(self):
        manager = RiskManager(position_tracker=None)
        result = manager.check_before_order("token1", "BUY", 0.99, 99999)
        assert result.passed is False
        assert "单仓位超限" in result.reason


class TestUpdateDailyPnl:
    """update_daily_pnl 方法测试"""
    
    def test_initial_zero(self):
        manager = RiskManager()
        assert manager._daily_pnl == 0.0
    
    def test_add_profit(self):
        manager = RiskManager()
        manager.update_daily_pnl(100.0)
        assert manager._daily_pnl == 100.0
    
    def test_add_loss(self):
        manager = RiskManager()
        manager.update_daily_pnl(-50.0)
        assert manager._daily_pnl == -50.0
    
    def test_cumulative_updates(self):
        manager = RiskManager()
        manager.update_daily_pnl(100.0)
        manager.update_daily_pnl(-30.0)
        manager.update_daily_pnl(50.0)
        assert manager._daily_pnl == 120.0
    
    def test_zero_update(self):
        manager = RiskManager()
        manager.update_daily_pnl(0.0)
        assert manager._daily_pnl == 0.0
    
    def test_large_value(self):
        manager = RiskManager()
        manager.update_daily_pnl(999999.99)
        assert manager._daily_pnl == 999999.99


class TestResetDailyStats:
    """reset_daily_stats 方法测试"""
    
    def test_reset_from_nonzero(self):
        manager = RiskManager()
        manager.update_daily_pnl(500.0)
        manager.reset_daily_stats()
        assert manager._daily_pnl == 0.0
    
    def test_reset_from_negative(self):
        manager = RiskManager()
        manager.update_daily_pnl(-200.0)
        manager.reset_daily_stats()
        assert manager._daily_pnl == 0.0
    
    def test_double_reset(self):
        manager = RiskManager()
        manager.update_daily_pnl(100.0)
        manager.reset_daily_stats()
        manager.reset_daily_stats()
        assert manager._daily_pnl == 0.0
    
    def test_reset_then_update(self):
        manager = RiskManager()
        manager.update_daily_pnl(1000.0)
        manager.reset_daily_stats()
        manager.update_daily_pnl(50.0)
        assert manager._daily_pnl == 50.0


class TestGetRiskStatus:
    """get_risk_status 方法测试"""
    
    def test_basic_structure(self):
        manager = RiskManager()
        status = manager.get_risk_status()
        
        assert "risk_parameters" in status
        assert "current_state" in status
        assert status["risk_parameters"]["max_position_size"] == 5000.0
        assert status["risk_parameters"]["max_total_exposure"] == 20000.0
        assert status["risk_parameters"]["max_daily_loss"] == 500.0
        assert status["risk_parameters"]["max_drawdown"] == 0.15
        assert status["risk_parameters"]["min_balance"] == 100.0
    
    def test_current_state_basic(self):
        manager = RiskManager()
        status = manager.get_risk_status()
        
        assert status["current_state"]["daily_pnl"] == 0.0
        assert status["current_state"]["position_tracker_available"] is False
    
    def test_with_tracker(self):
        tracker = MagicMock()
        tracker.get_positions.return_value = {"token1": 1000}
        tracker.get_total_exposure.return_value = 1000
        tracker.get_balance.return_value = 9000
        tracker.get_daily_pnl.return_value = -50
        
        manager = RiskManager(position_tracker=tracker)
        status = manager.get_risk_status()
        
        assert status["current_state"]["position_tracker_available"] is True
        assert status["current_state"]["positions"] == {"token1": 1000}
        assert status["current_state"]["total_exposure"] == 1000
        assert status["current_state"]["balance"] == 9000
        assert status["current_state"]["tracker_daily_pnl"] == -50
    
    def test_after_pnl_update(self):
        manager = RiskManager()
        manager.update_daily_pnl(123.45)
        status = manager.get_risk_status()
        assert status["current_state"]["daily_pnl"] == 123.45
    
    def test_custom_config_reflected(self):
        config = {
            "max_position_size": 1000,
            "max_total_exposure": 3000,
            "max_daily_loss": 100,
            "max_drawdown": 0.05,
            "min_balance": 20,
        }
        manager = RiskManager(config=config)
        status = manager.get_risk_status()
        
        assert status["risk_parameters"]["max_position_size"] == 1000.0
        assert status["risk_parameters"]["max_total_exposure"] == 3000.0
        assert status["risk_parameters"]["max_daily_loss"] == 100.0


class TestTrackerExceptionHandling:
    """position_tracker 异常处理测试"""
    
    def test_get_position_raises_exception(self):
        tracker = MagicMock()
        tracker.get_position.side_effect = Exception("Connection error")
        tracker.get_positions.return_value = {}
        tracker.get_total_exposure.return_value = 0
        tracker.get_daily_pnl.return_value = 0
        tracker.get_balance.return_value = 10000
        
        manager = RiskManager(position_tracker=tracker)
        result = manager.check_before_order("token1", "BUY", 0.5, 100)
        
        assert result.passed is True
        assert result.check_details["current_position"] == 0.0
    
    def test_get_balance_raises_exception(self):
        tracker = MagicMock()
        tracker.get_position.return_value = 0
        tracker.get_positions.return_value = {}
        tracker.get_total_exposure.return_value = 0
        tracker.get_daily_pnl.return_value = 0
        tracker.get_balance.side_effect = Exception("DB error")
        
        manager = RiskManager(position_tracker=tracker)
        result = manager.check_before_order("token1", "BUY", 0.5, 100)
        
        assert result.passed is True
        assert result.check_details["current_balance"] == 0.0


class TestCaseInsensitiveSide:
    """买卖方向大小写测试"""
    
    def setup_method(self):
        self.manager = RiskManager()
        self.tracker = MagicMock()
        self.tracker.get_position.return_value = 0
        self.tracker.get_positions.return_value = {}
        self.tracker.get_total_exposure.return_value = 0
        self.tracker.get_daily_pnl.return_value = 0
        self.tracker.get_balance.return_value = 10000
        self.manager.position_tracker = self.tracker
    
    def test_uppercase_buy(self):
        result = self.manager.check_before_order("token1", "BUY", 0.5, 100)
        assert result.passed is True
    
    def test_lowercase_buy(self):
        result = self.manager.check_before_order("token1", "buy", 0.5, 100)
        assert result.passed is True
    
    def test_mixed_case_buy(self):
        result = self.manager.check_before_order("token1", "Buy", 0.5, 100)
        assert result.passed is True
    
    def test_uppercase_sell(self):
        result = self.manager.check_before_order("token1", "SELL", 0.5, 100)
        assert result.passed is True
    
    def test_lowercase_sell(self):
        result = self.manager.check_before_order("token1", "sell", 0.5, 100)
        assert result.passed is True


class TestCheckDetailsCompleteness:
    """check_details 完整性测试"""
    
    def test_all_fields_present_on_pass(self):
        tracker = MagicMock()
        tracker.get_position.return_value = 1000
        tracker.get_positions.return_value = {"token1": 1000}
        tracker.get_total_exposure.return_value = 5000
        tracker.get_daily_pnl.return_value = -50
        tracker.get_balance.return_value = 8000
        
        manager = RiskManager(position_tracker=tracker)
        result = manager.check_before_order("token1", "BUY", 0.6, 500)
        
        expected_keys = [
            "token_id", "side", "price", "size", "order_value",
            "current_position", "total_exposure", "daily_pnl",
            "current_balance", "new_position", "new_total_exposure",
            "estimated_remaining"
        ]
        for key in expected_keys:
            assert key in result.check_details, f"Missing key: {key}"
    
    def test_all_fields_present_on_fail(self):
        tracker = MagicMock()
        tracker.get_position.return_value = 6000
        tracker.get_positions.return_value = {"token1": 6000}
        tracker.get_total_exposure.return_value = 6000
        tracker.get_daily_pnl.return_value = 0
        tracker.get_balance.return_value = 10000
        
        manager = RiskManager(position_tracker=tracker)
        result = manager.check_before_order("token1", "BUY", 0.5, 100)
        
        assert not result.passed
        assert "token_id" in result.check_details
        assert "new_position" in result.check_details
