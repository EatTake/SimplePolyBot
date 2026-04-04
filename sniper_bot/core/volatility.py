"""
EWMA 微观波动率实时估算模块

估算 BTC 的瞬时波动率 σ（$/√秒），
这是布朗桥模型中唯一的自由参数。

使用指数加权移动平均（Exponential Weighted Moving Average），
近期数据权重更高，能更快地捕捉波动率突变（regime change）。

与 SimplePolyBot 的区别：
  SimplePolyBot 完全不估算波动率，假设其为常数。
  本模块实时跟踪，使安全阈值随市场状态自适应。
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from sniper_bot.core.models import PricePoint, VolatilityEstimate


# RiskMetrics 标准衰减因子
_DEFAULT_LAMBDA = 0.94

# 最少需要的数据点数
_MIN_SAMPLES = 10


class VolatilityEstimator:
    """
    EWMA 实时波动率估算器

    接收 Binance 高频 BTC 价格流，输出 σ（$/√秒）
    """

    def __init__(
        self,
        decay_lambda: float = _DEFAULT_LAMBDA,
        min_samples: int = _MIN_SAMPLES,
    ):
        """
        Args:
            decay_lambda: EWMA 衰减因子，越大越平滑（0.9 ~ 0.99）
            min_samples: 最少样本数，不足则拒绝估算
        """
        if not (0 < decay_lambda < 1):
            raise ValueError(f"decay_lambda 必须在 (0, 1) 范围内: {decay_lambda}")

        self._lambda = decay_lambda
        self._min_samples = min_samples
        self._prices: list[float] = []
        self._timestamps: list[float] = []

    def update(self, price: float, timestamp: float) -> None:
        """
        推入新的价格数据点

        Args:
            price: BTC 美元价格
            timestamp: Unix 时间戳（秒）
        """
        if price <= 0:
            return  # 忽略无效价格

        self._prices.append(price)
        self._timestamps.append(timestamp)

    def update_from_point(self, point: PricePoint) -> None:
        """从 PricePoint 更新"""
        self.update(point.price, point.timestamp)

    def estimate(self) -> Optional[VolatilityEstimate]:
        """
        计算当前 EWMA 波动率

        Returns:
            VolatilityEstimate 或 None（数据不足时）

        算法：
            1. 计算对数收益率 r_i = ln(P_i / P_{i-1})
            2. 按 Δt 归一化为每秒收益率
            3. EWMA 加权计算方差
            4. σ_dollar = σ_normalized × 最新价格
        """
        n = len(self._prices)
        if n < self._min_samples:
            return None

        prices = np.array(self._prices)
        timestamps = np.array(self._timestamps)

        # 对数收益率
        log_returns = np.diff(np.log(prices))
        dt = np.diff(timestamps)

        # 过滤无效时间间隔（≤ 0 或 > 60 秒视为数据断裂）
        valid_mask = (dt > 0) & (dt <= 60.0)
        if valid_mask.sum() < self._min_samples - 1:
            return None

        log_returns = log_returns[valid_mask]
        dt = dt[valid_mask]

        # 按时间归一化（转换为 "每秒" 的尺度）
        normalized_returns = log_returns / np.sqrt(dt)

        # EWMA 权重（最新的权重最大）
        m = len(normalized_returns)
        exponents = np.arange(m - 1, -1, -1, dtype=np.float64)
        weights = np.power(self._lambda, exponents)
        weights /= weights.sum()

        # 加权方差
        weighted_var = np.average(normalized_returns ** 2, weights=weights)
        sigma_normalized = math.sqrt(max(weighted_var, 0.0))

        # 转换为 $/√秒
        latest_price = prices[-1]
        sigma_dollar = sigma_normalized * latest_price

        return VolatilityEstimate(
            sigma_dollar_per_sqrt_sec=sigma_dollar,
            sample_count=m,
            timestamp=timestamps[-1],
        )

    def clear(self) -> None:
        """清空所有数据（周期切换时调用）"""
        self._prices.clear()
        self._timestamps.clear()

    @property
    def sample_count(self) -> int:
        return len(self._prices)


def estimate_sigma_from_arrays(
    prices: np.ndarray,
    timestamps: np.ndarray,
    decay_lambda: float = _DEFAULT_LAMBDA,
) -> Optional[float]:
    """
    便捷函数：从价格和时间戳数组直接计算 σ

    Args:
        prices: BTC 价格数组
        timestamps: 时间戳数组（秒）
        decay_lambda: EWMA 衰减因子

    Returns:
        σ（$/√秒）或 None
    """
    if len(prices) < _MIN_SAMPLES:
        return None

    estimator = VolatilityEstimator(decay_lambda=decay_lambda)
    for p, t in zip(prices, timestamps):
        estimator.update(p, t)

    result = estimator.estimate()
    return result.sigma_dollar_per_sqrt_sec if result else None
