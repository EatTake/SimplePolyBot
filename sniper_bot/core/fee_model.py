"""
Polymarket 手续费精确计算模块

实现官方动态 Taker Fee 公式：
  Fee = C × feeRate × p × (1 - p)

以及基于手续费的净期望值（Net EV）和盈亏平衡概率计算。

关键洞察：策略在 p > 0.80 时交易，此时 p(1-p) < 0.16，
手续费自然衰减，是本策略的天然数学优势。
"""

from __future__ import annotations

from typing import Optional


# Polymarket 各市场类型的手续费率
# 来源: https://docs.polymarket.com/trading/fees
_FEE_RATES: dict[str, dict[str, float]] = {
    "crypto":      {"fee_rate": 0.072, "exponent": 1.0},
    "sports":      {"fee_rate": 0.03,  "exponent": 1.0},
    "finance":     {"fee_rate": 0.04,  "exponent": 1.0},
    "politics":    {"fee_rate": 0.04,  "exponent": 1.0},
    "economics":   {"fee_rate": 0.03,  "exponent": 0.5},
    "culture":     {"fee_rate": 0.05,  "exponent": 1.0},
    "weather":     {"fee_rate": 0.025, "exponent": 0.5},
    "other":       {"fee_rate": 0.2,   "exponent": 2.0},
    "mentions":    {"fee_rate": 0.25,  "exponent": 2.0},
    "tech":        {"fee_rate": 0.04,  "exponent": 1.0},
    "geopolitics": {"fee_rate": 0.0,   "exponent": 0.0},
}


def taker_fee(
    shares: float,
    price: float,
    category: str = "crypto",
) -> float:
    """
    计算 Taker 手续费

    公式: Fee = C × feeRate × p × (p × (1 - p)) ^ exponent

    Args:
        shares: 合约份额数 C
        price: 成交价 p（范围 0~1）
        category: 市场类型

    Returns:
        手续费（USDC）

    Examples:
        >>> taker_fee(100, 0.85, "crypto")  # 约 $0.92
        >>> taker_fee(100, 0.75, "crypto")  # 约 $1.35
    """
    if price <= 0 or price >= 1 or shares <= 0:
        return 0.0

    config = _FEE_RATES.get(category, _FEE_RATES["crypto"])
    rate = config["fee_rate"]
    exp = config["exponent"]

    if rate == 0:
        return 0.0

    price_factor = price * (1.0 - price)
    fee = shares * rate * price * (price_factor ** exp)

    return max(0.0, fee)


def effective_fee_rate(
    price: float,
    category: str = "crypto",
) -> float:
    """
    计算有效手续费率（%）

    Args:
        price: 合约价格
        category: 市场类型

    Returns:
        有效费率百分比
    """
    if price <= 0 or price >= 1:
        return 0.0

    config = _FEE_RATES.get(category, _FEE_RATES["crypto"])
    rate = config["fee_rate"]
    exp = config["exponent"]

    price_factor = price * (1.0 - price)
    return rate * (price_factor ** exp) * 100.0


def net_expected_value(
    shares: float,
    buy_price: float,
    p_win: float,
    category: str = "crypto",
) -> float:
    """
    计算扣费后的净期望值

    Net EV = P_win × (1 - buy_price) × shares - Fee

    Args:
        shares: 份额数
        buy_price: 买入价（合约价格 0~1）
        p_win: 获胜概率
        category: 市场类型

    Returns:
        净期望值（USDC），正值说明有利可图
    """
    fee = taker_fee(shares, buy_price, category)

    # 期望毛利 = P_win × 份额利润
    gross_ev = p_win * (1.0 - buy_price) * shares

    # 期望亏损 = (1 - P_win) × 全部成本
    expected_loss = (1.0 - p_win) * buy_price * shares

    return gross_ev - expected_loss - fee


def break_even_probability(
    buy_price: float,
    category: str = "crypto",
) -> float:
    """
    计算盈亏平衡所需的最低获胜概率

    Args:
        buy_price: 买入价
        category: 市场类型

    Returns:
        最低获胜概率
    """
    if buy_price <= 0 or buy_price >= 1:
        return 1.0

    fee_per_share = taker_fee(1.0, buy_price, category)

    # 平衡条件: P_win × (1 - price) = (1 - P_win) × price + fee
    # => P_win = (price + fee) / (1)  → P_win = price + fee
    return min(1.0, buy_price + fee_per_share)


def time_based_max_price(time_remaining: float) -> float:
    """
    时间衰减买入价格限制（基础限价）

    连续函数：max_price = 0.95 - 0.002 × time_remaining
      T-10s  → 0.93
      T-50s  → 0.85
      T-100s → 0.75

    Args:
        time_remaining: 剩余秒数

    Returns:
        当前允许的最大买入价格（基础值）
    """
    base = 0.95 - 0.002 * time_remaining
    return max(0.60, min(0.93, base))


def dynamic_max_price(
    time_remaining: float,
    delta: float,
    min_delta: float,
) -> float:
    """
    动态限价 = 时间基础限价 + 安全垫厚度加成

    原理：
      当 delta >> min_delta 时（安全垫很厚），
      价格反转的概率极低，可以适当提高买入上限。

      安全垫系数 = delta / min_delta
        1.0x → 刚好达标，不加成
        2.0x → 安全垫 2 倍厚，加成 +$0.03
        3.0x → 安全垫 3 倍厚，加成 +$0.05
        5.0x+ → 安全垫 5 倍厚，加成封顶 +$0.08

    公式: bonus = min(0.08, 0.02 × (cushion_ratio - 1.0))

    Args:
        time_remaining: 剩余秒数
        delta: 当前偏移量 |current - start| ($)
        min_delta: 达到最低置信度所需的偏移量 ($)

    Returns:
        动态调整后的最大买入价格
    """
    base = time_based_max_price(time_remaining)

    if min_delta <= 0 or delta <= 0:
        return base

    cushion_ratio = delta / min_delta

    if cushion_ratio <= 1.0:
        # 安全垫不足或刚好达标，不加成
        return base

    # 加成公式: 每多 1 倍安全垫 → +$0.02，封顶 +$0.08
    bonus = min(0.08, 0.02 * (cushion_ratio - 1.0))

    adjusted = base + bonus

    # 硬上限
    return min(0.95, adjusted)

