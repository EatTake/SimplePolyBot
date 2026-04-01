"""
OLS 线性回归模块测试
"""

import time
import pytest
import numpy as np

from modules.strategy_engine.ols_regression import OLSRegression, RegressionResult, perform_regression


class TestOLSRegression:
    """OLSRegression 测试类"""
    
    def test_create_regressor(self):
        """测试创建回归器"""
        regressor = OLSRegression(min_samples=10)
        
        assert regressor.min_samples == 10
    
    def test_fit_perfect_linear(self):
        """测试完美线性关系"""
        regressor = OLSRegression(min_samples=5)
        
        timestamps = [1000.0 + i * 10 for i in range(10)]
        prices = [50000.0 + i * 100 for i in range(10)]
        
        result = regressor.fit(timestamps, prices)
        
        assert result is not None
        assert result.slope == pytest.approx(10.0, rel=1e-2)
        assert result.r_squared == pytest.approx(1.0, rel=1e-6)
        assert result.sample_count == 10
    
    def test_fit_noisy_data(self):
        """测试噪声数据"""
        regressor = OLSRegression(min_samples=10)
        
        np.random.seed(42)
        timestamps = [1000.0 + i * 10 for i in range(50)]
        prices = [50000.0 + i * 100 + np.random.randn() * 50 for i in range(50)]
        
        result = regressor.fit(timestamps, prices)
        
        assert result is not None
        assert result.slope > 0
        assert result.r_squared > 0.9
        assert result.sample_count == 50
    
    def test_fit_insufficient_samples(self):
        """测试样本数量不足"""
        regressor = OLSRegression(min_samples=10)
        
        timestamps = [1000.0, 1010.0, 1020.0]
        prices = [50000.0, 50100.0, 50200.0]
        
        result = regressor.fit(timestamps, prices)
        
        assert result is None
    
    def test_fit_mismatched_lengths(self):
        """测试时间戳和价格数量不匹配"""
        regressor = OLSRegression(min_samples=5)
        
        timestamps = [1000.0, 1010.0, 1020.0]
        prices = [50000.0, 50100.0]
        
        result = regressor.fit(timestamps, prices)
        
        assert result is None
    
    def test_computation_time(self):
        """测试计算时间"""
        regressor = OLSRegression(min_samples=10)
        
        timestamps = [1000.0 + i * 10 for i in range(100)]
        prices = [50000.0 + i * 100 for i in range(100)]
        
        result = regressor.fit(timestamps, prices)
        
        assert result is not None
        assert result.computation_time_ms < 10.0
    
    def test_calculate_trend_strength(self):
        """测试趋势强度计算"""
        regressor = OLSRegression(min_samples=10)
        
        strength = regressor.calculate_trend_strength(slope=0.001, r_squared=0.9)
        
        assert 0 <= strength <= 1
        assert strength > 0
    
    def test_predict_price(self):
        """测试价格预测"""
        regressor = OLSRegression(min_samples=10)
        
        slope = 10.0
        intercept = 50000.0
        future_timestamp = 2000.0
        base_timestamp = 1000.0
        
        predicted = regressor.predict_price(
            slope, intercept, future_timestamp, base_timestamp
        )
        
        expected = slope * (future_timestamp - base_timestamp) + intercept
        assert predicted == pytest.approx(expected, rel=1e-6)
    
    def test_calculate_volatility_factor(self):
        """测试波动率因子计算"""
        regressor = OLSRegression(min_samples=10)
        
        volatility = regressor.calculate_volatility_factor(
            std_error=100.0, mean_price=50000.0
        )
        
        assert volatility == pytest.approx(0.002, rel=1e-6)
    
    def test_perform_regression_convenience(self):
        """测试便捷函数"""
        timestamps = [1000.0 + i * 10 for i in range(20)]
        prices = [50000.0 + i * 100 for i in range(20)]
        
        result = perform_regression(timestamps, prices, min_samples=10)
        
        assert result is not None
        assert result.slope == pytest.approx(10.0, rel=1e-2)
    
    def test_negative_slope(self):
        """测试负斜率"""
        regressor = OLSRegression(min_samples=5)
        
        timestamps = [1000.0 + i * 10 for i in range(10)]
        prices = [50000.0 - i * 100 for i in range(10)]
        
        result = regressor.fit(timestamps, prices)
        
        assert result is not None
        assert result.slope < 0
        assert result.r_squared == pytest.approx(1.0, rel=1e-6)
    
    def test_horizontal_line(self):
        """测试水平线（零斜率）"""
        regressor = OLSRegression(min_samples=5)
        
        timestamps = [1000.0 + i * 10 for i in range(10)]
        prices = [50000.0] * 10
        
        result = regressor.fit(timestamps, prices)
        
        assert result is not None
        assert result.slope == pytest.approx(0.0, abs=1e-6)
        assert result.r_squared == pytest.approx(1.0, rel=1e-6)
