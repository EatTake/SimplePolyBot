"""
买入信号生成器模块测试
"""

import pytest

from modules.strategy_engine.signal_generator import (
    SignalGenerator,
    TradingSignal,
    SignalAction,
    SignalDirection,
    generate_trading_signal,
)


class TestSignalGenerator:
    """SignalGenerator 测试类"""
    
    def test_create_generator(self):
        """测试创建信号生成器"""
        generator = SignalGenerator(
            min_time_remaining=10.0,
            max_time_remaining=100.0,
            min_price_difference=0.01,
        )
        
        assert generator.min_time_remaining == 10.0
        assert generator.max_time_remaining == 100.0
        assert generator.min_price_difference == 0.01
    
    def test_calculate_price_difference(self):
        """测试价格差额计算"""
        generator = SignalGenerator()
        
        diff = generator.calculate_price_difference(0.50, 0.45)
        assert diff == pytest.approx(0.05, rel=1e-6)
        
        diff = generator.calculate_price_difference(0.45, 0.50)
        assert diff == pytest.approx(0.05, rel=1e-6)
    
    def test_determine_direction(self):
        """测试方向判断"""
        generator = SignalGenerator()
        
        direction = generator.determine_direction(0.05)
        assert direction == SignalDirection.UP
        
        direction = generator.determine_direction(-0.05)
        assert direction == SignalDirection.DOWN
        
        direction = generator.determine_direction(0.0)
        assert direction is None
    
    def test_is_in_time_window(self):
        """测试时间窗口判断"""
        generator = SignalGenerator(min_time_remaining=10.0, max_time_remaining=100.0)
        
        assert generator.is_in_time_window(50.0)
        assert generator.is_in_time_window(10.0)
        assert generator.is_in_time_window(100.0)
        
        assert not generator.is_in_time_window(5.0)
        assert not generator.is_in_time_window(150.0)
    
    def test_calculate_max_buy_price(self):
        """测试最大买入价格计算"""
        generator = SignalGenerator()
        
        max_price = generator.calculate_max_buy_price(0.50, 0.05)
        assert max_price == 0.45
    
    def test_calculate_confidence(self):
        """测试置信度计算"""
        generator = SignalGenerator()
        
        confidence = generator.calculate_confidence(
            r_squared=0.9,
            abs_slope=0.001,
            price_difference=0.05,
        )
        
        assert 0 <= confidence <= 1
        assert confidence > 0.5
    
    def test_generate_buy_signal(self):
        """测试生成买入信号"""
        generator = SignalGenerator(
            min_time_remaining=10.0,
            max_time_remaining=100.0,
            min_price_difference=0.01,
            min_r_squared=0.5,
            min_confidence=0.6,
        )
        
        signal = generator.generate_signal(
            current_price=0.50,
            start_price=0.45,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
        )
        
        assert isinstance(signal, TradingSignal)
        assert signal.action == SignalAction.BUY
        assert signal.direction in [SignalDirection.UP, SignalDirection.DOWN]
        assert signal.current_price == 0.50
        assert signal.start_price == 0.45
        assert signal.price_difference == pytest.approx(0.05, rel=1e-6)
        assert signal.time_remaining == 50.0
    
    def test_generate_wait_signal_time_window(self):
        """测试时间窗口外生成等待信号"""
        generator = SignalGenerator(
            min_time_remaining=10.0,
            max_time_remaining=100.0,
        )
        
        signal = generator.generate_signal(
            current_price=0.50,
            start_price=0.45,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=5.0,
        )
        
        assert signal.action == SignalAction.WAIT
        assert signal.direction is None
    
    def test_generate_wait_signal_price_difference(self):
        """测试价格差额不足生成等待信号"""
        generator = SignalGenerator(min_price_difference=0.05)
        
        signal = generator.generate_signal(
            current_price=0.50,
            start_price=0.49,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
        )
        
        assert signal.action == SignalAction.WAIT
    
    def test_generate_wait_signal_r_squared(self):
        """测试 R² 不足生成等待信号"""
        generator = SignalGenerator(min_r_squared=0.8)
        
        signal = generator.generate_signal(
            current_price=0.50,
            start_price=0.45,
            slope_k=0.001,
            r_squared=0.5,
            time_remaining=50.0,
        )
        
        assert signal.action == SignalAction.WAIT
    
    def test_signal_to_dict(self):
        """测试信号转换为字典"""
        generator = SignalGenerator()
        
        signal = generator.generate_signal(
            current_price=0.50,
            start_price=0.45,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
        )
        
        signal_dict = signal.to_dict()
        
        assert isinstance(signal_dict, dict)
        assert "action" in signal_dict
        assert "direction" in signal_dict
        assert "current_price" in signal_dict
        assert "timestamp" in signal_dict
    
    def test_get_max_buy_price_limit(self):
        """测试最大买入价格限制"""
        generator = SignalGenerator()
        
        high_confidence_limit = generator.get_max_buy_price_limit(0.9)
        assert high_confidence_limit == 0.98
        
        medium_confidence_limit = generator.get_max_buy_price_limit(0.7)
        assert medium_confidence_limit == 0.95
        
        low_confidence_limit = generator.get_max_buy_price_limit(0.5)
        assert low_confidence_limit == 0.90
    
    def test_convenience_function(self):
        """测试便捷函数"""
        signal = generate_trading_signal(
            current_price=0.50,
            start_price=0.45,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
        )
        
        assert isinstance(signal, TradingSignal)
        assert signal.current_price == 0.50
        assert signal.start_price == 0.45
