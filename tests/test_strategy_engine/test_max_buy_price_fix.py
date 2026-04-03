"""
Bug #1, #2, #3 修复验证测试

重构 max_buy_price 计算逻辑的核心测试：
- 新公式不再恒定返回 0.99（核心验证）
- 概率空间计算，避免量纲混淆
- 时间衰减因子正确性
- 安全垫比较逻辑
"""

import pytest
import warnings

from modules.strategy_engine.signal_generator import (
    SignalGenerator,
    TradingSignal,
    SignalAction,
    SignalDirection,
)
from modules.strategy_engine.safety_cushion import SafetyCushionCalculator


class TestTimeDecayFactor:
    """时间衰减因子测试"""
    
    def test_decay_at_start(self):
        """刚开始时（300s）衰减因子接近 1.0"""
        generator = SignalGenerator()
        decay = generator.time_decay_factor(300.0)
        assert decay == pytest.approx(1.0, rel=1e-6)
    
    def test_decay_at_middle(self):
        """中间时间（150s）衰减因子约 0.75"""
        generator = SignalGenerator()
        decay = generator.time_decay_factor(150.0)
        assert decay == pytest.approx(0.75, rel=1e-6)
    
    def test_decay_near_end(self):
        """快结束时（10s）衰减因子约 0.517"""
        generator = SignalGenerator()
        decay = generator.time_decay_factor(10.0)
        expected = 0.5 + 0.5 * (10.0 / 300.0)
        assert decay == pytest.approx(expected, rel=1e-6)
    
    def test_decay_at_zero(self):
        """剩余时间为 0 时衰减因子为 0.5"""
        generator = SignalGenerator()
        decay = generator.time_decay_factor(0.0)
        assert decay == pytest.approx(0.5, rel=1e-6)
    
    def test_decay_negative_time(self):
        """负数时间处理为 0"""
        generator = SignalGenerator()
        decay = generator.time_decay_factor(-10.0)
        assert decay == pytest.approx(0.5, rel=1e-6)
    
    def test_decay_exceeds_duration(self):
        """超过持续时间时 clamp 到 1.0"""
        generator = SignalGenerator()
        decay = generator.time_decay_factor(500.0)
        assert decay == pytest.approx(1.0, rel=1e-6)


class TestCalculateMaxBuyPriceNewFormula:
    """新公式 calculate_max_buy_price 测试 - 核心修复验证"""
    
    def test_no_longer_returns_constant_099_best_ask_05(self):
        """
        核心验证：best_ask=0.5 时不应恒定返回 0.99
        
        旧 Bug: current_price(BTC ~67000) - cushion(~0.05) ≈ 67000 → clamp → 0.99
        新公式: best_ask(0.5) × (1-cushion) × decay → 合理值 < 0.5
        """
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.50,
            safety_cushion=0.05,
            time_remaining=100.0,
        )
        
        assert max_price < 0.50, f"新公式应返回 < 0.50，实际返回 {max_price}"
        assert max_price != 0.99, "新公式不应再返回 0.99"
    
    def test_no_longer_returns_constant_099_best_ask_07(self):
        """best_ask=0.7 时也不应返回 0.99"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.70,
            safety_cushion=0.05,
            time_remaining=100.0,
        )
        
        assert max_price < 0.70, f"新公式应返回 < 0.70，实际返回 {max_price}"
        assert max_price != 0.99
    
    def test_no_longer_returns_constant_099_best_ask_09(self):
        """best_ask=0.9 时也不应返回 0.99（即使高价格）"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.90,
            safety_cushion=0.10,
            time_remaining=50.0,
        )
        
        assert max_price < 0.90, f"新公式应返回 < 0.90，实际返回 {max_price}"
    
    def test_low_best_ask_with_cushion(self):
        """低 best_ask (0.3) + cushion 应产生更低的价格"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.30,
            safety_cushion=0.10,
            time_remaining=100.0,
        )
        
        assert 0.01 <= max_price <= 0.30
        assert max_price < 0.27  # 0.3 * 0.9 * decay(<1.0) < 0.27


class TestMaxBuyPriceVariousCombinations:
    """各种 market_best_ask × safety_cushion 组合测试"""
    
    @pytest.mark.parametrize("best_ask", [0.3, 0.5, 0.7, 0.9])
    @pytest.mark.parametrize("cushion", [0.02, 0.05, 0.10, 0.20])
    def test_combinations_in_valid_range(self, best_ask, cushion):
        """所有组合都应在 [0.01, 0.99] 范围内"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=best_ask,
            safety_cushion=cushion,
            time_remaining=100.0,
        )
        
        assert 0.01 <= max_price <= 0.99, \
            f"best_ask={best_ask}, cushion={cushion} → max_price={max_price} 超出范围"
    
    @pytest.mark.parametrize("best_ask", [0.3, 0.5, 0.7, 0.9])
    def test_higher_cushion_lower_price(self, best_ask):
        """更高的安全垫应该产生更低的最高买入价"""
        generator = SignalGenerator()
        
        price_low_cushion = generator.calculate_max_buy_price(
            market_best_ask=best_ask,
            safety_cushion=0.02,
            time_remaining=100.0,
        )
        
        price_high_cushion = generator.calculate_max_buy_price(
            market_best_ask=best_ask,
            safety_cushion=0.20,
            time_remaining=100.0,
        )
        
        assert price_high_cushion < price_low_cushion, \
            f"best_ask={best_ask}: 高安全垫({price_high_cushion}) 应 < 低安全垫({price_low_cushion})"
    
    @pytest.mark.parametrize("cushion", [0.02, 0.05, 0.10])
    def test_higher_best_ask_higher_price(self, cushion):
        """更高的 best_ask 应该产生更高的最高买入价"""
        generator = SignalGenerator()
        
        price_low_ask = generator.calculate_max_buy_price(
            market_best_ask=0.3,
            safety_cushion=cushion,
            time_remaining=100.0,
        )
        
        price_high_ask = generator.calculate_max_buy_price(
            market_best_ask=0.7,
            safety_cushion=cushion,
            time_remaining=100.0,
        )
        
        assert price_high_ask > price_low_ask


class TestMaxBuyPriceExtremeValues:
    """极端值安全性测试"""
    
    def test_minimum_best_ask(self):
        """最小 best_ask (0.01)"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.01,
            safety_cushion=0.05,
            time_remaining=100.0,
        )
        
        assert max_price >= 0.01  # clamp 到下界
    
    def test_maximum_best_ask(self):
        """最大 best_ask (0.99)"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.99,
            safety_cushion=0.05,
            time_remaining=100.0,
        )
        
        assert max_price <= 0.99  # clamp 到上界
    
    def test_zero_cushion(self):
        """零安全垫"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.50,
            safety_cushion=0.0,
            time_remaining=100.0,
        )
        
        decay = generator.time_decay_factor(100.0)
        expected = 0.50 * 1.0 * decay  # cushion_adjusted = max(0.01, 1.0 - 0) = 1.0
        assert max_price == pytest.approx(expected, rel=1e-6)
    
    def test_very_large_cushion(self):
        """非常大的安全垫 (0.5)"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.50,
            safety_cushion=0.5,
            time_remaining=100.0,
        )
        
        assert max_price >= 0.01  # cushion_adjusted = max(0.01, 0.5) = 0.5
        assert max_price < 0.50  # 应该显著降低
    
    def test_cushion_exceeds_one(self):
        """安全垫超过 1（异常值）"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(
            market_best_ask=0.50,
            safety_cushion=1.5,
            time_remaining=100.0,
        )
        
        assert max_price >= 0.01  # cushion_adjusted = max(0.01, -0.5) = 0.01


class TestMaxBuyPriceTimeDecayEffect:
    """时间衰减对最高买入价的影响"""
    
    def test_early_time_higher_price(self):
        """早期（剩余时间长）→ 更高的最高买入价"""
        generator = SignalGenerator()
        
        early_price = generator.calculate_max_buy_price(
            market_best_ask=0.50,
            safety_cushion=0.05,
            time_remaining=250.0,
        )
        
        late_price = generator.calculate_max_buy_price(
            market_best_ask=0.50,
            safety_cushion=0.05,
            time_remaining=20.0,
        )
        
        assert early_price > late_price, \
            f"早期价格({early_price}) 应 > 晚期价格({late_price})"
    
    def test_time_decay_monotonic(self):
        """时间衰减应该是单调的：剩余时间越少，价格越低"""
        generator = SignalGenerator()
        
        times = [300.0, 200.0, 100.0, 50.0, 20.0, 10.0]
        prices = [
            generator.calculate_max_buy_price(
                market_best_ask=0.50,
                safety_cushion=0.05,
                time_remaining=t,
            )
            for t in times
        ]
        
        for i in range(len(prices) - 1):
            assert prices[i] >= prices[i+1], \
                f"时间递减但价格不单调: t={times[i]}→{prices[i]}, t={times[i+1]}→{prices[i+1]}"


class TestDetermineActionSafetyCushionCheck:
    """Bug #3 修复：determine_action() 包含安全垫比较"""
    
    def test_action_wait_when_price_diff_below_cushion(self):
        """价格差额低于安全垫时返回 WAIT"""
        generator = SignalGenerator(
            min_price_difference=0.01,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        action = generator.determine_action(
            price_difference=0.03,  # BTC 价格差 $30
            time_remaining=50.0,
            r_squared=0.9,
            confidence=0.8,
            max_buy_price=0.45,
            safety_cushion=0.05,  # 安全垫 0.05（概率空间）
        )
        
        assert action == SignalAction.WAIT, \
            f"价格差额(0.03) < 安全垫(0.05) 应返回 WAIT，实际返回 {action}"
    
    def test_action_buy_when_price_diff_above_cushion(self):
        """价格差额高于安全垫时可以返回 BUY"""
        generator = SignalGenerator(
            min_price_difference=0.01,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        action = generator.determine_action(
            price_difference=100.0,  # BTC 价格差 $100（远超安全垫）
            time_remaining=50.0,
            r_squared=0.9,
            confidence=0.8,
            max_buy_price=0.45,
            safety_cushion=0.05,
        )
        
        assert action == SignalAction.BUY, \
            f"价格差额(100.0) > 安全垫(0.05) 且其他条件满足，应返回 BUY"
    
    def test_action_wait_zero_cushion_default(self):
        """默认 safety_cushion=0 不影响判断"""
        generator = SignalGenerator(
            min_price_difference=0.01,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        action = generator.determine_action(
            price_difference=0.005,  # 低于 min_price_difference 但高于 0
            time_remaining=50.0,
            r_squared=0.9,
            confidence=0.8,
            max_buy_price=0.45,
            safety_cushion=0.0,  # 默认值
        )
        
        assert action == SignalAction.WAIT  # 被 min_price_difference 拦截


class TestGenerateSignalBackwardCompatibility:
    """向后兼容性测试：缺少 market_best_ask 时使用默认值"""
    
    def test_generate_signal_without_market_best_ask(self):
        """不传 market_best_ask 时使用默认值 0.50"""
        generator = SignalGenerator(
            min_time_remaining=10.0,
            max_time_remaining=100.0,
            min_price_difference=0.01,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        signal = generator.generate_signal(
            current_price=67000.50,  # BTC 绝对价格
            start_price=67000.00,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
        )
        
        assert isinstance(signal, TradingSignal)
        assert signal.max_buy_price < 0.50, \
            f"默认 best_ask=0.50 时 max_buy_price 应 < 0.50，实际 {signal.max_buy_price}"
        assert signal.max_buy_price != 0.99, \
            "新公式不应再返回 0.99（即使使用默认 best_ask）"
    
    def test_generate_signal_with_market_best_ask(self):
        """显式传入 market_best_ask"""
        generator = SignalGenerator(
            min_time_remaining=10.0,
            max_time_remaining=100.0,
            min_price_difference=0.01,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        signal = generator.generate_signal(
            current_price=67000.50,
            start_price=67000.00,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
            market_best_ask=0.60,
        )
        
        assert isinstance(signal, TradingSignal)
        assert signal.max_buy_price < 0.60, \
            f"best_ask=0.60 时 max_buy_price 应 < 0.60，实际 {signal.max_buy_price}"


class TestSafetyCushionDeprecationWarning:
    """safety_cushion.py 旧版接口的弃用警告测试"""
    
    def test_old_interface_raises_deprecation_warning(self):
        """旧版 calculate_max_buy_price 应发出 DeprecationWarning"""
        calculator = SafetyCushionCalculator()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            result = calculator.calculate_max_buy_price(
                current_price=67000.0,
                safety_cushion=0.05,
            )
            
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "Bug #1, #2" in str(w[0].message) or "量纲混淆" in str(w[0].message)
    
    def test_old_interface_still_returns_clamped_value(self):
        """旧版接口仍能工作（虽然结果可能有 Bug）"""
        calculator = SafetyCushionCalculator()
        
        result = calculator.calculate_max_buy_price(
            current_price=67000.0,
            safety_cushion=0.05,
        )
        
        assert 0.01 <= result <= 0.99
        assert result == 0.99  # 旧 Bug：恒定返回 0.99


class TestEdgeCases:
    """边界情况和特殊场景测试"""
    
    def test_very_small_price_difference_with_large_cushion(self):
        """极小价格差额 + 大安全垫 → WAIT"""
        generator = SignalGenerator(
            min_price_difference=0.001,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        action = generator.determine_action(
            price_difference=0.0005,
            time_remaining=50.0,
            r_squared=0.9,
            confidence=0.8,
            max_buy_price=0.40,
            safety_cushion=0.10,
        )
        
        assert action == SignalAction.WAIT
    
    def test_exact_cushion_boundary(self):
        """价格差额恰好等于安全垫的边界情况"""
        generator = SignalGenerator(
            min_price_difference=0.001,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        action = generator.determine_action(
            price_difference=0.05,
            time_remaining=50.0,
            r_squared=0.9,
            confidence=0.8,
            max_buy_price=0.45,
            safety_cushion=0.05,
        )
        
        assert action == SignalAction.BUY  # 条件是严格 <，相等时不触发
    
    def test_slightly_above_cushion(self):
        """价格差额略高于安全垫"""
        generator = SignalGenerator(
            min_price_difference=0.001,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        action = generator.determine_action(
            price_difference=0.0501,
            time_remaining=50.0,
            r_squared=0.9,
            confidence=0.8,
            max_buy_price=0.45,
            safety_cushion=0.05,
        )
        
        assert action == SignalAction.BUY  # 其他条件满足时可以 BUY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
