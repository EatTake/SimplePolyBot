"""
OLS 线性回归动量分析模块

计算 180 秒价格窗口内的趋势斜率 K 和决定系数 R²。
K 反映动量强度和方向，R² 反映趋势的稳定性。

本模块保留了 SimplePolyBot 中经过验证的 NumPy 向量化 OLS，
但改进了时间戳归一化和边界处理。
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from sniper_bot.core.models import RegressionResult


# 最少数据点要求
_MIN_SAMPLES = 10

# 最大数据点（防止意外内存溢出）
_MAX_SAMPLES = 10000


def ols_regression(
    timestamps: np.ndarray,
    prices: np.ndarray,
) -> Optional[RegressionResult]:
    """
    普通最小二乘法线性回归

    对 (timestamp, price) 序列拟合 y = K * x + b
    其中 x 归一化为相对时间（秒），避免大数浮点问题。

    Args:
        timestamps: 时间戳数组（秒），长度 ≥ MIN_SAMPLES
        prices: BTC 价格数组，长度与 timestamps 一致

    Returns:
        RegressionResult 或 None（数据不足时）
    """
    n = len(timestamps)
    if n < _MIN_SAMPLES or n != len(prices):
        return None

    if n > _MAX_SAMPLES:
        timestamps = timestamps[-_MAX_SAMPLES:]
        prices = prices[-_MAX_SAMPLES:]
        n = _MAX_SAMPLES

    # 时间戳归一化：相对于第一个点的秒数
    t0 = timestamps[0]
    x = timestamps - t0

    # 检查时间跨度
    time_span = x[-1]
    if time_span <= 0:
        return None

    y = prices.astype(np.float64)

    # 向量化 OLS
    n_f = float(n)
    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.dot(x, y)
    sum_x2 = np.dot(x, x)

    # 斜率 K = (n·Σxy - Σx·Σy) / (n·Σx² - (Σx)²)
    denominator = n_f * sum_x2 - sum_x * sum_x
    if abs(denominator) < 1e-12:
        return None

    slope = (n_f * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n_f

    # R² = 1 - SS_res / SS_tot
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    y_mean = sum_y / n_f
    ss_tot = np.sum((y - y_mean) ** 2)

    if ss_tot < 1e-12:
        r_squared = 1.0  # 所有点价格相同 → 完美拟合
    else:
        r_squared = 1.0 - ss_res / ss_tot
        r_squared = max(0.0, min(1.0, r_squared))

    return RegressionResult(
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r_squared),
        sample_count=n,
        timestamp=float(timestamps[-1]),
    )


def compute_trend_score(
    slope: float,
    r_squared: float,
    direction_sign: float,
) -> float:
    """
    计算趋势评分

    综合斜率方向一致性和 R² 稳定性

    Args:
        slope: OLS 斜率 K
        r_squared: 决定系数
        direction_sign: +1 (UP) 或 -1 (DOWN)

    Returns:
        趋势评分 ∈ [-1, 1]
          > 0 表示趋势与预期方向一致
          < 0 表示趋势与预期方向相反
    """
    # 斜率方向与预期方向的一致性
    direction_agreement = 1.0 if (slope * direction_sign) > 0 else -1.0

    # 加权评分：R² 衡量信号质量
    return direction_agreement * r_squared
