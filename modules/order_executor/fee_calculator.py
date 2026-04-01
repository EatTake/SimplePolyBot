"""
动态手续费计算模块

实现 Polymarket Taker Fee 计算公式
公式: Fee = C × feeRate × p × (p × (1 - p))^exponent

其中:
- C: 交易份额数量 (shares)
- feeRate: 手续费率 (根据市场类型)
- exponent: 指数参数 (根据市场类型)
- p: 交易价格
"""

from typing import Dict, Optional
from decimal import Decimal, ROUND_HALF_UP
import structlog

logger = structlog.get_logger()


class FeeCalculator:
    """
    动态手续费计算器
    
    根据 Polymarket 官方手续费结构计算交易手续费
    支持不同市场类型的手续费率配置
    """
    
    FEE_RATES: Dict[str, Dict[str, float]] = {
        "crypto": {"fee_rate": 0.072, "exponent": 1.0, "maker_rebate": 0.20},
        "sports": {"fee_rate": 0.03, "exponent": 1.0, "maker_rebate": 0.25},
        "finance": {"fee_rate": 0.04, "exponent": 1.0, "maker_rebate": 0.50},
        "politics": {"fee_rate": 0.04, "exponent": 1.0, "maker_rebate": 0.25},
        "economics": {"fee_rate": 0.03, "exponent": 0.5, "maker_rebate": 0.25},
        "culture": {"fee_rate": 0.05, "exponent": 1.0, "maker_rebate": 0.25},
        "weather": {"fee_rate": 0.025, "exponent": 0.5, "maker_rebate": 0.25},
        "other": {"fee_rate": 0.2, "exponent": 2.0, "maker_rebate": 0.25},
        "mentions": {"fee_rate": 0.25, "exponent": 2.0, "maker_rebate": 0.25},
        "tech": {"fee_rate": 0.04, "exponent": 1.0, "maker_rebate": 0.25},
        "geopolitics": {"fee_rate": 0.0, "exponent": 0.0, "maker_rebate": 0.0},
    }
    
    def __init__(self, default_category: str = "crypto"):
        """
        初始化手续费计算器
        
        Args:
            default_category: 默认市场类型
        """
        self.default_category = default_category
        logger.info(
            "初始化手续费计算器",
            default_category=default_category
        )
    
    def calculate_taker_fee(
        self,
        shares: float,
        price: float,
        category: Optional[str] = None,
        fee_rate_bps: Optional[int] = None,
    ) -> float:
        """
        计算 Taker 手续费
        
        公式: Fee = C × feeRate × p × (p × (1 - p))^exponent
        
        Args:
            shares: 交易份额数量 (C)
            price: 交易价格 (p)，范围 0-1
            category: 市场类型，用于获取手续费率
            fee_rate_bps: 手续费率（基点），如果提供则直接使用
        
        Returns:
            手续费金额（USDC）
        """
        if fee_rate_bps is not None:
            fee_rate = fee_rate_bps / 10000.0
            exponent = 1.0
        else:
            category = category or self.default_category
            fee_config = self.FEE_RATES.get(category, self.FEE_RATES[self.default_category])
            fee_rate = fee_config["fee_rate"]
            exponent = fee_config["exponent"]
        
        if fee_rate == 0:
            return 0.0
        
        price_decimal = Decimal(str(price))
        price_factor = price_decimal * (Decimal("1") - price_decimal)
        
        if price_factor == 0:
            return 0.0
        
        fee = (
            Decimal(str(shares))
            * Decimal(str(fee_rate))
            * price_decimal
            * (price_factor ** Decimal(str(exponent)))
        )
        
        fee = float(fee.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        
        if fee < 0.0001:
            fee = 0.0
        
        logger.debug(
            "计算 Taker 手续费",
            shares=shares,
            price=price,
            category=category,
            fee_rate=fee_rate,
            exponent=exponent,
            fee=fee
        )
        
        return fee
    
    def calculate_effective_rate(
        self,
        shares: float,
        price: float,
        category: Optional[str] = None,
        fee_rate_bps: Optional[int] = None,
    ) -> float:
        """
        计算有效手续费率
        
        有效手续费率 = 手续费 / 交易金额
        
        Args:
            shares: 交易份额数量
            price: 交易价格
            category: 市场类型
            fee_rate_bps: 手续费率（基点）
        
        Returns:
            有效手续费率（百分比）
        """
        trade_value = shares * price
        
        if trade_value == 0:
            return 0.0
        
        fee = self.calculate_taker_fee(shares, price, category, fee_rate_bps)
        effective_rate = (fee / trade_value) * 100
        
        return effective_rate
    
    def calculate_net_expected_value(
        self,
        shares: float,
        buy_price: float,
        estimated_probability: float,
        category: Optional[str] = None,
        fee_rate_bps: Optional[int] = None,
    ) -> float:
        """
        计算净期望值
        
        净期望值 = (估计概率 × 1 - 买入价格) × 份额 - 手续费
        
        Args:
            shares: 交易份额数量
            buy_price: 买入价格
            estimated_probability: 估计的事件发生概率
            category: 市场类型
            fee_rate_bps: 手续费率（基点）
        
        Returns:
            净期望值（USDC）
        """
        fee = self.calculate_taker_fee(shares, buy_price, category, fee_rate_bps)
        
        gross_ev = (estimated_probability - buy_price) * shares
        
        net_ev = gross_ev - fee
        
        logger.debug(
            "计算净期望值",
            shares=shares,
            buy_price=buy_price,
            estimated_probability=estimated_probability,
            fee=fee,
            gross_ev=gross_ev,
            net_ev=net_ev
        )
        
        return net_ev
    
    def get_fee_config(self, category: str) -> Dict[str, float]:
        """
        获取指定市场类型的手续费配置
        
        Args:
            category: 市场类型
        
        Returns:
            手续费配置字典
        """
        return self.FEE_RATES.get(category, self.FEE_RATES[self.default_category])
    
    def estimate_max_buy_price(
        self,
        estimated_probability: float,
        category: Optional[str] = None,
        min_ev_threshold: float = 0.01,
    ) -> float:
        """
        估算最大买入价格
        
        基于估计概率和最小期望值阈值，计算最大可接受的买入价格
        
        Args:
            estimated_probability: 估计的事件发生概率
            category: 市场类型
            min_ev_threshold: 最小期望值阈值（USDC/份额）
        
        Returns:
            最大买入价格
        """
        category = category or self.default_category
        fee_config = self.FEE_RATES.get(category, self.FEE_RATES[self.default_category])
        fee_rate = fee_config["fee_rate"]
        
        if fee_rate == 0:
            return estimated_probability - min_ev_threshold
        
        max_price = estimated_probability - min_ev_threshold - (fee_rate * 0.25)
        
        max_price = max(0.01, min(0.99, max_price))
        
        logger.debug(
            "估算最大买入价格",
            estimated_probability=estimated_probability,
            category=category,
            min_ev_threshold=min_ev_threshold,
            max_price=max_price
        )
        
        return max_price
    
    def calculate_break_even_probability(
        self,
        buy_price: float,
        category: Optional[str] = None,
    ) -> float:
        """
        计算盈亏平衡概率
        
        计算达到盈亏平衡所需的最小事件发生概率
        
        Args:
            buy_price: 买入价格
            category: 市场类型
        
        Returns:
            盈亏平衡概率
        """
        category = category or self.default_category
        fee_config = self.FEE_RATES.get(category, self.FEE_RATES[self.default_category])
        fee_rate = fee_config["fee_rate"]
        
        if fee_rate == 0:
            return buy_price
        
        fee_adjustment = fee_rate * buy_price * (1 - buy_price)
        break_even_prob = buy_price + fee_adjustment
        
        break_even_prob = min(1.0, break_even_prob)
        
        logger.debug(
            "计算盈亏平衡概率",
            buy_price=buy_price,
            category=category,
            break_even_prob=break_even_prob
        )
        
        return break_even_prob
