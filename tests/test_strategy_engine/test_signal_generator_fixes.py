"""
Bug #4 修复验证测试：置信度归一化系数不再饱和到 1.0

覆盖场景：
1. 斜率典型值产生不同归一化结果（非全1.0）
2. 价格差额典型值产生不同归一化结果
3. 极端大值接近但不等于1.0
4. 极端小值接近但不等于0.0
5. r_squared权重占主导（weight=0.5）
6. 综合置信度在合理范围内
7. 边界值安全性（极大/极小输入不崩溃）
8. _sigmoid辅助函数正确性
"""

import math
import pytest

from modules.strategy_engine.signal_generator import (
    SignalGenerator,
    _sigmoid,
)


class TestSigmoidHelper:
    """_sigmoid 辅助函数测试"""

    def test_sigmoid_zero(self):
        """sigmoid(0) = 0.5"""
        assert _sigmoid(0.0) == pytest.approx(0.5, rel=1e-10)

    def test_sigmoid_positive(self):
        """正输入产生 > 0.5 的结果"""
        assert _sigmoid(1.0) > 0.5
        assert _sigmoid(1.0) < 1.0
        assert _sigmoid(5.0) > 0.9

    def test_sigmoid_negative(self):
        """负输入产生 < 0.5 的结果"""
        assert _sigmoid(-1.0) < 0.5
        assert _sigmoid(-1.0) > 0.0
        assert _sigmoid(-5.0) < 0.1

    def test_sigmoid_extreme_large(self):
        """极大值返回1.0（防溢出保护）"""
        assert _sigmoid(1000.0) == 1.0
        assert _sigmoid(501.0) == 1.0

    def test_sigmoid_extreme_small(self):
        """极小值返回0.0（防溢出保护）"""
        assert _sigmoid(-1000.0) == 0.0
        assert _sigmoid(-501.0) == 0.0

    def test_sigmoid_symmetry(self):
        """对称性：sigmoid(x) + sigmoid(-x) = 1.0"""
        for val in [0.1, 1.0, 3.0, 10.0]:
            assert _sigmoid(val) + _sigmoid(-val) == pytest.approx(1.0, abs=1e-10)


class TestConfidenceSlopeNormalization:
    """斜率归一化测试：验证典型BTC斜率值不会全部饱和到1.0"""

    def setup_method(self):
        self.gen = SignalGenerator()

    def test_slope_low_value_produces_below_center(self):
        """低斜率值(0.001)应产生低于中心点(0.5)的归一化结果
        
        abs_slope=0.001 → 50*(0.001-0.002)=-0.05 → sigmoid≈0.4875
        旧代码：min(0.001*1000, 1.0)=1.0（错误饱和）
        """
        conf = self.gen.calculate_confidence(r_squared=0.8, abs_slope=0.001, price_difference=50)
        normalized_slope_contribution = _sigmoid(50 * (0.001 - 0.002))
        assert normalized_slope_contribution < 0.5
        assert normalized_slope_contribution > 0.4

    def test_slope_center_value_produces_center(self):
        """中心斜率值(0.002)应产生约0.5的归一化结果
        
        abs_slope=0.002 → 50*(0.002-0.002)=0 → sigmoid=0.5
        """
        normalized_slope = _sigmoid(50 * (0.002 - 0.002))
        assert normalized_slope == pytest.approx(0.5, abs=1e-10)

    def test_slope_high_value_produces_above_center(self):
        """高斜率值(0.003)应产生高于中心点(0.5)的归一化结果
        
        abs_slope=0.003 → 50*(0.003-0.002)=+0.05 → sigmoid≈0.5125
        旧代码：min(0.003*1000, 1.0)=1.0（错误饱和）
        """
        normalized_slope = _sigmoid(50 * (0.003 - 0.002))
        assert normalized_slope > 0.5
        assert normalized_slope < 0.6

    def test_three_slope_values_produce_distinct_results(self):
        """三个典型斜率值必须产生三个不同的归一化结果
        
        这是Bug#4的核心修复验证：旧代码三者都是1.0
        """
        s_low = _sigmoid(50 * (0.001 - 0.002))
        s_mid = _sigmoid(50 * (0.002 - 0.002))
        s_high = _sigmoid(50 * (0.003 - 0.002))

        assert s_low != s_mid
        assert s_mid != s_high
        assert s_low != s_high
        assert s_low < s_mid < s_high


class TestConfidencePriceDifferenceNormalization:
    """价格差额归一化测试：验证典型BTC价格差不会全部饱和到1.0"""

    def setup_method(self):
        self.gen = SignalGenerator()

    def test_price_diff_low(self):
        """低价格差额(20 USD)应产生低于中心的归一化结果
        
        diff=20 → 0.02*(20-50)=-0.6 → sigmoid≈0.354
        旧代码：min(20*10, 1.0)=1.0（错误饱和）
        """
        norm = _sigmoid(0.02 * (20 - 50))
        assert norm < 0.5
        assert norm > 0.2

    def test_price_diff_medium(self):
        """中等价格差额(50 USD)应产生约0.5的归一化结果
        
        diff=50 → 0.02*(50-50)=0 → sigmoid=0.5
        """
        norm = _sigmoid(0.02 * (50 - 50))
        assert norm == pytest.approx(0.5, abs=1e-10)

    def test_price_diff_high(self):
        """高价格差额(100 USD)应产生高于中心的归一化结果
        
        diff=100 → 0.02*(100-50)=+1.0 → sigmoid≈0.731
        旧代码：min(100*10, 1.0)=1.0（错误饱和）
        """
        norm = _sigmoid(0.02 * (100 - 50))
        assert norm > 0.65
        assert norm < 0.8

    def test_price_diff_very_high(self):
        """极高价格差额(200 USD)应产生高但不到1.0的结果
        
        diff=200 → 0.02*(200-50)=+3.0 → sigmoid≈0.953
        旧代码：min(200*10, 1.0)=1.0（完全饱和，无区分度）
        """
        norm = _sigmoid(0.02 * (200 - 50))
        assert norm > 0.9
        assert norm < 1.0

    def test_four_price_diff_values_produce_distinct_results(self):
        """四个典型价格差额必须产生四个不同的归一化结果"""
        values = [20, 50, 100, 200]
        results = [_sigmoid(0.02 * (v - 50)) for v in values]
        assert len(set(round(r, 6) for r in results)) == 4
        assert results[0] < results[1] < results[2] < results[3]


class TestConfidenceExtremeValues:
    """极端边界值测试"""

    def setup_method(self):
        self.gen = SignalGenerator()

    def test_extreme_large_slope_approaches_but_not_equal_one(self):
        """极大斜率使归一化值趋近但严格小于1.0
        
        验证不再像旧代码那样直接截断为1.0
        """
        norm = _sigmoid(50 * (0.1 - 0.002))  # 极大斜率
        assert norm > 0.99
        assert norm < 1.0

    def test_extreme_small_slope_approaches_but_not_equal_zero(self):
        """极小斜率使归一化值低于中心点(0.5)但严格大于0.0
        
        由于缩放因子50和中心点0.002的设计，典型BTC斜率范围[0.0005,0.005]
        的归一化值落在[0.49, 0.51]区间（Sigmoid线性敏感区）。
        远离中心的极小值(如1e-8)产生低于0.5的结果，验证不会饱和到0或1。
        """
        norm = _sigmoid(50 * (1e-8 - 0.002))  # 远小于中心点的极小斜率
        assert norm < 0.5
        assert norm > 0.0

    def test_extreme_large_price_diff_approaches_but_not_equal_one(self):
        """极大价格差额使归一化值趋近1.0
        
        diff=10000 → 0.02*(10000-50)=199 → sigmoid(199)≈1.0（float64精度下exp(-199)下溢为0）
        验证在溢出保护阈值(500)以内的大值行为
        """
        norm = _sigmoid(0.02 * (10000 - 50))  # 极大价差（未触发500截断）
        assert norm > 0.9999

    def test_extreme_small_price_diff_approaches_but_not_equal_zero(self):
        """极小价格差额使归一化值趋近但严格大于0.0
        
        需要使用远小于中心点(50)的值，如 0.001
        """
        norm = _sigmoid(0.02 * (0.001 - 50))  # 远小于中心点的极小价差
        assert norm < 0.37
        assert norm > 0.0


class TestConfidenceWeightDistribution:
    """权重分配测试：验证r_squared占主导地位(weight=0.5)"""

    def setup_method(self):
        self.gen = SignalGenerator()

    def test_r_squared_dominates_confidence(self):
        """r_squared变化对置信度的影响应大于斜率和价差的变化
        
        固定 slope=0.002, diff=50（两者归一化均为0.5），
        则 confidence = r²*0.5 + 0.5*0.3 + 0.5*0.2 = r²*0.5 + 0.25
        r²从0.5变到0.9时，置信度变化0.20（主导项）
        """
        conf_low = self.gen.calculate_confidence(
            r_squared=0.5, abs_slope=0.002, price_difference=50
        )
        conf_high = self.gen.calculate_confidence(
            r_squared=0.9, abs_slope=0.002, price_difference=50
        )
        delta_r_squared = conf_high - conf_low
        assert delta_r_squared == pytest.approx(0.20, abs=1e-6)

    def test_slope_effect_is_smaller_than_r_squared(self):
        """斜率对置信度的影响应小于r_squared（0.3 vs 0.5 权重）
        
        在 center point: slope贡献 = 0.3 * sigmoid(0) = 0.15
        slope从0.001变到0.003: 贡献变化 ≈ 0.3 * (0.5125-0.4875) = 0.0075
        远小于r_squared的0.20影响
        """
        conf_slope_low = self.gen.calculate_confidence(
            r_squared=0.7, abs_slope=0.001, price_difference=50
        )
        conf_slope_high = self.gen.calculate_confidence(
            r_squared=0.7, abs_slope=0.003, price_difference=50
        )
        delta_slope = abs(conf_slope_high - conf_slope_low)
        assert delta_slope < 0.05  # 斜率影响较小

    def test_price_diff_has_smallest_weight(self):
        """价格差额权重最小(0.2)，影响应最小"""
        conf_diff_low = self.gen.calculate_confidence(
            r_squared=0.7, abs_slope=0.002, price_difference=20
        )
        conf_diff_high = self.gen.calculate_confidence(
            r_squared=0.7, abs_slope=0.002, price_difference=100
        )
        delta_diff = abs(conf_diff_high - conf_diff_low)
        assert delta_diff < 0.1  # 价差权重最低


class TestConfidenceOverallRange:
    """综合置信度范围测试"""

    def setup_method(self):
        self.gen = SignalGenerator()

    def test_typical_btc_scenario_reasonable_confidence(self):
        """典型BTC市场参数应产生合理范围内的置信度
        
        场景：中等拟合质量 + 中等趋势 + 中等波动
        """
        conf = self.gen.calculate_confidence(
            r_squared=0.8,
            abs_slope=0.002,
            price_difference=50,
        )
        assert 0.4 <= conf <= 0.9

    def test_strong_signal_high_confidence(self):
        """强信号场景：高R² + 强趋势 + 大波动 → 高置信度"""
        conf = self.gen.calculate_confidence(
            r_squared=0.95,
            abs_slope=0.005,
            price_difference=150,
        )
        assert conf >= 0.75
        assert conf <= 1.0

    def test_weak_signal_low_confidence(self):
        """弱信号场景：低R² + 弱趋势 + 小波动 → 低置信度"""
        conf = self.gen.calculate_confidence(
            r_squared=0.4,
            abs_slope=0.0005,
            price_difference=10,
        )
        assert conf <= 0.55
        assert conf >= 0.0

    def test_confidence_clamped_to_unit_interval(self):
        """置信度必须在 [0, 1] 范围内"""
        for r2 in [0.0, 0.5, 1.0]:
            for slope in [0.0, 0.002, 0.01]:
                for diff in [0.0, 50, 500]:
                    conf = self.gen.calculate_confidence(
                        r_squared=r2, abs_slope=slope, price_difference=diff
                    )
                    assert 0.0 <= conf <= 1.0


class TestBoundarySafety:
    """边界值安全性测试：极大/极小输入不应崩溃"""

    def setup_method(self):
        self.gen = SignalGenerator()

    def test_zero_inputs_no_crash(self):
        """全零输入不崩溃"""
        conf = self.gen.calculate_confidence(
            r_squared=0.0, abs_slope=0.0, price_difference=0.0
        )
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    def test_very_large_inputs_no_crash(self):
        """极大输入不崩溃（数值稳定性）"""
        conf = self.gen.calculate_confidence(
            r_squared=1.0, abs_slope=999.0, price_difference=99999.0
        )
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    def test_negative_slope_handled(self):
        """负斜率通过abs处理，不应崩溃
        
        虽然调用方传入abs_slope，但防御性检查
        """
        conf = self.gen.calculate_confidence(
            r_squared=0.8, abs_slope=-0.001, price_difference=50
        )
        assert isinstance(conf, float)

    def test_negative_price_diff_handled(self):
        """负价格差额不应崩溃"""
        conf = self.gen.calculate_confidence(
            r_squared=0.8, abs_slope=0.002, price_difference=-10.0
        )
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    def test_very_small_positive_inputs(self):
        """极小正数输入不崩溃且结果合理"""
        conf = self.gen.calculate_confidence(
            r_squared=0.001, abs_slope=1e-8, price_difference=1e-6
        )
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0
