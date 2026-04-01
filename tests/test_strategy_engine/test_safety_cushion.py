"""
动态安全垫计算模块测试
"""

import pytest
import math

from modules.strategy_engine.safety_cushion import (
    SafetyCushionCalculator,
    SafetyCushionResult,
    calculate_safety_cushion,
)


class TestSafetyCushionCalculator:
    """SafetyCushionCalculator 测试类"""
    
    def test_create_calculator(self):
        """测试创建计算器"""
        calculator = SafetyCushionCalculator(base_cushion=0.02, alpha=0.5)
        
        assert calculator.base_cushion == 0.02
        assert calculator.alpha == 0.5
    
    def test_calculate_base_cushion(self):
        """测试基础安全垫计算"""
        calculator = SafetyCushionCalculator(base_cushion=0.02, alpha=0.5)
        
        base = calculator.calculate_base_cushion()
        
        assert base == 0.02
    
    def test_calculate_buffer_cushion(self):
        """测试缓冲安全垫计算"""
        calculator = SafetyCushionCalculator(base_cushion=0.02, alpha=0.5)
        
        slope_k = 0.001
        time_remaining = 100.0
        
        buffer = calculator.calculate_buffer_cushion(slope_k, time_remaining)
        
        expected = 0.5 * abs(slope_k) * math.sqrt(time_remaining)
        assert buffer == pytest.approx(expected, rel=1e-6)
    
    def test_calculate_total_cushion(self):
        """测试总安全垫计算"""
        calculator = SafetyCushionCalculator(base_cushion=0.02, alpha=0.5)
        
        result = calculator.calculate(slope_k=0.001, time_remaining_seconds=100.0)
        
        assert isinstance(result, SafetyCushionResult)
        assert result.base_cushion == 0.02
        assert result.buffer_cushion > 0
        assert result.total_cushion == result.base_cushion + result.buffer_cushion
    
    def test_calculate_max_buy_price(self):
        """测试最大买入价格计算"""
        calculator = SafetyCushionCalculator(base_cushion=0.02, alpha=0.5)
        
        current_price = 0.50
        safety_cushion = 0.05
        
        max_buy_price = calculator.calculate_max_buy_price(current_price, safety_cushion)
        
        expected = current_price - safety_cushion
        assert max_buy_price == pytest.approx(expected, rel=1e-6)
    
    def test_max_buy_price_bounds(self):
        """测试最大买入价格边界"""
        calculator = SafetyCushionCalculator()
        
        max_price = calculator.calculate_max_buy_price(0.99, 0.5)
        assert max_price == 0.49
        
        max_price = calculator.calculate_max_buy_price(0.01, 0.5)
        assert max_price == 0.01
    
    def test_adjust_cushion_by_volatility(self):
        """测试根据波动率调整安全垫"""
        calculator = SafetyCushionCalculator()
        
        base_cushion = 0.02
        
        high_volatility = calculator.adjust_cushion_by_volatility(base_cushion, 0.8)
        assert high_volatility > base_cushion
        
        low_volatility = calculator.adjust_cushion_by_volatility(base_cushion, 0.2)
        assert low_volatility < base_cushion
    
    def test_calculate_dynamic_alpha(self):
        """测试动态 alpha 计算"""
        calculator = SafetyCushionCalculator(base_cushion=0.02, alpha=0.5)
        
        high_r_squared = calculator.calculate_dynamic_alpha(0.9, confidence_threshold=0.7)
        assert high_r_squared > 0.5
        
        low_r_squared = calculator.calculate_dynamic_alpha(0.5, confidence_threshold=0.7)
        assert low_r_squared < 0.5
    
    def test_negative_time_remaining(self):
        """测试负剩余时间"""
        calculator = SafetyCushionCalculator(base_cushion=0.02, alpha=0.5)
        
        result = calculator.calculate(slope_k=0.001, time_remaining_seconds=-10.0)
        
        assert result.time_remaining == 0.0
        assert result.buffer_cushion == 0.0
    
    def test_zero_slope(self):
        """测试零斜率"""
        calculator = SafetyCushionCalculator(base_cushion=0.02, alpha=0.5)
        
        result = calculator.calculate(slope_k=0.0, time_remaining_seconds=100.0)
        
        assert result.buffer_cushion == 0.0
        assert result.total_cushion == result.base_cushion
    
    def test_convenience_function(self):
        """测试便捷函数"""
        result = calculate_safety_cushion(
            slope_k=0.001,
            time_remaining_seconds=100.0,
            base_cushion=0.02,
            alpha=0.5,
        )
        
        assert isinstance(result, SafetyCushionResult)
        assert result.base_cushion == 0.02
        assert result.alpha == 0.5
    
    def test_result_validation(self):
        """测试结果验证"""
        with pytest.raises(ValueError):
            SafetyCushionResult(
                base_cushion=-0.01,
                buffer_cushion=0.01,
                total_cushion=0.0,
                slope_k=0.001,
                time_remaining=100.0,
                alpha=0.5,
            )
        
        with pytest.raises(ValueError):
            SafetyCushionResult(
                base_cushion=0.01,
                buffer_cushion=0.01,
                total_cushion=0.02,
                slope_k=0.001,
                time_remaining=100.0,
                alpha=1.5,
            )
