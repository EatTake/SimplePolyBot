"""
手续费计算器单元测试
"""

import pytest
from modules.order_executor.fee_calculator import FeeCalculator


class TestFeeCalculator:
    """手续费计算器测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.calculator = FeeCalculator()
    
    def test_calculate_taker_fee_crypto_market(self):
        """测试加密货币市场手续费计算"""
        shares = 100
        price = 0.50
        
        fee = self.calculator.calculate_taker_fee(shares, price, category="crypto")
        
        expected_fee = 100 * 0.072 * 0.50 * (0.50 * 0.50) ** 1.0
        expected_fee = round(expected_fee, 4)
        
        assert fee == expected_fee
        assert fee > 0
    
    def test_calculate_taker_fee_sports_market(self):
        """测试体育市场手续费计算"""
        shares = 100
        price = 0.50
        
        fee = self.calculator.calculate_taker_fee(shares, price, category="sports")
        
        expected_fee = 100 * 0.03 * 0.50 * (0.50 * 0.50) ** 1.0
        expected_fee = round(expected_fee, 4)
        
        assert fee == expected_fee
        assert fee > 0
    
    def test_calculate_taker_fee_geopolitics_market(self):
        """测试地缘政治市场（无手续费）"""
        shares = 100
        price = 0.50
        
        fee = self.calculator.calculate_taker_fee(shares, price, category="geopolitics")
        
        assert fee == 0.0
    
    def test_calculate_taker_fee_extreme_prices(self):
        """测试极端价格的手续费计算"""
        shares = 100
        
        fee_low = self.calculator.calculate_taker_fee(shares, 0.01, category="crypto")
        fee_high = self.calculator.calculate_taker_fee(shares, 0.99, category="crypto")
        fee_mid = self.calculator.calculate_taker_fee(shares, 0.50, category="crypto")
        
        assert fee_low < fee_mid
        assert fee_high < fee_mid
        assert fee_mid > 0
    
    def test_calculate_taker_fee_with_fee_rate_bps(self):
        """测试使用自定义手续费率"""
        shares = 100
        price = 0.50
        fee_rate_bps = 100
        
        fee = self.calculator.calculate_taker_fee(
            shares, price, fee_rate_bps=fee_rate_bps
        )
        
        expected_fee = 100 * 0.01 * 0.50 * (0.50 * 0.50) ** 1.0
        expected_fee = round(expected_fee, 4)
        
        assert fee == expected_fee
    
    def test_calculate_effective_rate(self):
        """测试有效手续费率计算"""
        shares = 100
        price = 0.50
        
        effective_rate = self.calculator.calculate_effective_rate(
            shares, price, category="crypto"
        )
        
        assert effective_rate > 0
        assert effective_rate < 5
    
    def test_calculate_net_expected_value_positive(self):
        """测试正净期望值计算"""
        shares = 100
        buy_price = 0.45
        estimated_probability = 0.60
        
        net_ev = self.calculator.calculate_net_expected_value(
            shares, buy_price, estimated_probability, category="crypto"
        )
        
        gross_ev = (estimated_probability - buy_price) * shares
        assert net_ev < gross_ev
        assert net_ev > 0
    
    def test_calculate_net_expected_value_negative(self):
        """测试负净期望值计算"""
        shares = 100
        buy_price = 0.70
        estimated_probability = 0.50
        
        net_ev = self.calculator.calculate_net_expected_value(
            shares, buy_price, estimated_probability, category="crypto"
        )
        
        assert net_ev < 0
    
    def test_get_fee_config(self):
        """测试获取手续费配置"""
        crypto_config = self.calculator.get_fee_config("crypto")
        
        assert "fee_rate" in crypto_config
        assert "exponent" in crypto_config
        assert "maker_rebate" in crypto_config
        assert crypto_config["fee_rate"] == 0.072
    
    def test_estimate_max_buy_price(self):
        """测试估算最大买入价格"""
        estimated_probability = 0.70
        
        max_price = self.calculator.estimate_max_buy_price(
            estimated_probability, category="crypto"
        )
        
        assert max_price < estimated_probability
        assert 0 < max_price < 1
    
    def test_estimate_max_buy_price_geopolitics(self):
        """测试地缘政治市场的最大买入价格估算"""
        estimated_probability = 0.70
        
        max_price = self.calculator.estimate_max_buy_price(
            estimated_probability, category="geopolitics"
        )
        
        assert max_price < estimated_probability
    
    def test_calculate_break_even_probability(self):
        """测试盈亏平衡概率计算"""
        buy_price = 0.50
        
        break_even = self.calculator.calculate_break_even_probability(
            buy_price, category="crypto"
        )
        
        assert break_even > buy_price
        assert break_even <= 1.0
    
    def test_calculate_break_even_probability_geopolitics(self):
        """测试地缘政治市场的盈亏平衡概率"""
        buy_price = 0.50
        
        break_even = self.calculator.calculate_break_even_probability(
            buy_price, category="geopolitics"
        )
        
        assert break_even == buy_price
    
    def test_fee_symmetry(self):
        """测试手续费对称性（价格 0.3 和 0.7 的 p*(1-p) 部分相同）"""
        shares = 100
        
        fee_low = self.calculator.calculate_taker_fee(shares, 0.30, category="crypto")
        fee_high = self.calculator.calculate_taker_fee(shares, 0.70, category="crypto")
        
        ratio = fee_high / fee_low if fee_low > 0 else 0
        expected_ratio = 0.70 / 0.30
        
        assert abs(ratio - expected_ratio) < 0.01
    
    def test_fee_precision(self):
        """测试手续费精度（4 位小数）"""
        shares = 10
        price = 0.1234
        
        fee = self.calculator.calculate_taker_fee(shares, price, category="crypto")
        
        fee_str = str(fee)
        if '.' in fee_str:
            decimal_places = len(fee_str.split('.')[1])
            assert decimal_places <= 4
