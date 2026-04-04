"""
布朗桥反转概率计算模块

核心数学：给定 BTC 当前偏移 Δ、波动率 σ、剩余时间 T，
精确计算价格在剩余时间内穿越起始价格的概率。

公式推导（反射原理）：
  P(布朗运动在 [0, T] 内穿越水平 Δ) = exp(-2Δ² / (σ²T))

这取代了 SimplePolyBot 中基于经验公式的安全垫模型，
用精确的概率论代替人工参数调优。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from sniper_bot.core.models import ReversalAnalysis


# 极小常量，防止除零
_EPSILON = 1e-12


def reversal_probability(
    delta: float,
    sigma: float,
    time_remaining: float,
) -> float:
    """
    计算布朗桥反转概率

    使用布朗运动的反射原理（Reflection Principle），给出
    在剩余时间 T 内，价格从当前水平穿越 start_price 的精确概率。

    Args:
        delta: |current_price - start_price|，单位 $，必须 ≥ 0
        sigma: 微观波动率，单位 $/√秒，必须 > 0
        time_remaining: 剩余秒数，必须 ≥ 0

    Returns:
        反转概率 ∈ [0, 1]

    NOTE:
        当 delta = 0 时返回 1.0（价格恰好在起始点，完全不确定）
        当 time_remaining = 0 时返回 0.0（没有时间反转）
        当 sigma → 0 时返回 0.0（无波动，不可能反转）
    """
    if delta < 0:
        raise ValueError(f"delta 必须 ≥ 0，收到: {delta}")

    # 边界条件
    if time_remaining <= 0:
        return 0.0

    if delta <= _EPSILON:
        return 1.0  # 价格在起始点，50/50

    if sigma <= _EPSILON:
        return 0.0  # 无波动，保持当前方向

    # 核心公式：P = exp(-2Δ² / (σ²T))
    exponent = -2.0 * (delta ** 2) / ((sigma ** 2) * time_remaining)

    # 防止 exponent 过小导致下溢
    if exponent < -700:
        return 0.0

    return math.exp(exponent)


def analyze_reversal(
    current_price: float,
    start_price: float,
    sigma: float,
    time_remaining: float,
) -> ReversalAnalysis:
    """
    完整的反转分析：计算偏移、概率、获胜概率

    Args:
        current_price: 当前 BTC 价格（Chainlink）
        start_price: 周期起始 BTC 价格
        sigma: 微观波动率（$/√秒）
        time_remaining: 剩余秒数

    Returns:
        ReversalAnalysis 包含完整分析结果
    """
    delta = abs(current_price - start_price)
    p_rev = reversal_probability(delta, sigma, time_remaining)

    return ReversalAnalysis(
        delta=delta,
        sigma=sigma,
        time_remaining=time_remaining,
        p_reversal=p_rev,
        p_win=1.0 - p_rev,
    )


def minimum_delta_for_confidence(
    sigma: float,
    time_remaining: float,
    target_confidence: float = 0.97,
) -> float:
    """
    反向计算：给定置信度目标，需要多大的偏移量才能达到？

    用于预判 "BTC 还需要涨/跌多少美元，信号才会触发"

    Args:
        sigma: 微观波动率（$/√秒）
        time_remaining: 剩余秒数
        target_confidence: 目标获胜置信度，默认 97%

    Returns:
        所需的最小偏移量 Δ（$）

    公式推导：
        P_reversal = exp(-2Δ²/(σ²T)) ≤ 1 - target_confidence
        => Δ ≥ σ × √(T × ln(1/(1-target)) / 2)
    """
    if sigma <= _EPSILON or time_remaining <= 0:
        return float("inf")

    target_reversal = 1.0 - target_confidence
    if target_reversal <= 0:
        return float("inf")

    # Δ = σ × √(-T × ln(P_reversal) / 2)
    min_delta = sigma * math.sqrt(
        -time_remaining * math.log(target_reversal) / 2.0
    )

    return min_delta
