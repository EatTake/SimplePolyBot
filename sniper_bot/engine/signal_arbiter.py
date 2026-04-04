"""
多因子信号仲裁器

12 条门控条件的 AND 逻辑链——全部满足才发出 FIRE 信号。
这是策略层 → 执行层的唯一出口。

与 SimplePolyBot 的 SignalGenerator 的根本区别：
  1. 使用布朗桥反转概率替代经验安全垫
  2. 双源方向一致性检查（Chainlink vs Binance）
  3. 净期望值（扣费后）必须为正
  4. 凯利公式动态仓位而非固定份额
  5. 单周期只允许 1 笔交易
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np

from sniper_bot.core.brownian_bridge import analyze_reversal, minimum_delta_for_confidence
from sniper_bot.core.fee_model import net_expected_value, taker_fee, dynamic_max_price
from sniper_bot.core.kelly import calculate_position
from sniper_bot.core.models import (
    AccountState,
    FastMarket,
    SniperDecision,
    VolatilityEstimate,
    hold_decision,
)
from sniper_bot.core.momentum import ols_regression


logger = logging.getLogger(__name__)


class SignalArbiter:
    """
    多因子仲裁器

    接收所有分析层的输出，做出 FIRE / HOLD 决策
    """

    def __init__(
        self,
        min_confidence: float = 0.97,
        min_r_squared: float = 0.60,
        min_data_points: int = 30,
        max_reversal_prob: float = 0.03,
    ):
        """
        Args:
            min_confidence: 最低获胜置信度（= 1 - max_reversal_prob）
            min_r_squared: 最低 R² 值（趋势稳定性）
            min_data_points: 最少价格数据点
            max_reversal_prob: 最大可接受反转概率
        """
        self._min_confidence = min_confidence
        self._min_r_squared = min_r_squared
        self._min_data_points = min_data_points
        self._max_reversal_prob = max_reversal_prob

    def evaluate(
        self,
        *,
        chainlink_price: float,
        start_price: float,
        time_remaining: float,
        volatility: Optional[VolatilityEstimate],
        binance_timestamps: np.ndarray,
        binance_prices: np.ndarray,
        directions_agree: bool,
        best_ask: float,
        ask_depth: float,
        market: FastMarket,
        account: AccountState,
        already_fired: bool,
    ) -> SniperDecision:
        """
        执行完整的 12 条评估链

        每一条不满足都会立即返回 HOLD + 原因
        """
        reasons: list[str] = []

        # ===== 门控 1：单周期只允许 1 笔 =====
        if already_fired:
            return hold_decision("本周期已出手")

        # ===== 门控 2：狙击窗口 T-100 至 T-10 =====
        if not (10.0 <= time_remaining <= 100.0):
            return hold_decision(
                f"不在狙击窗口 (剩余 {time_remaining:.0f}s)"
            )

        # ===== 门控 3：数据充分性 =====
        if len(binance_prices) < self._min_data_points:
            return hold_decision(
                f"数据不足 ({len(binance_prices)}/{self._min_data_points})"
            )

        # ===== 门控 4：波动率已估算 =====
        if volatility is None:
            return hold_decision("波动率尚未估算")
        sigma = volatility.sigma_dollar_per_sqrt_sec
        if sigma <= 0:
            return hold_decision("波动率为零")
        reasons.append(f"σ = ${sigma:.4f}/√s")

        # ===== 门控 5：双源方向一致 =====
        if not directions_agree:
            return hold_decision("Chainlink 与 Binance 方向不一致")

        # 确定方向
        direction = "UP" if chainlink_price >= start_price else "DOWN"
        reasons.append(f"方向: {direction}")

        # ===== 核心计算：布朗桥反转概率 =====
        delta = abs(chainlink_price - start_price)
        reversal = analyze_reversal(chainlink_price, start_price, sigma, time_remaining)

        if reversal.p_reversal > self._max_reversal_prob:
            return hold_decision(
                f"反转概率 {reversal.p_reversal:.2%} > {self._max_reversal_prob:.0%}"
            )
        reasons.append(f"P_reversal = {reversal.p_reversal:.4%}")
        reasons.append(f"Δ = ${delta:.2f}")

        # ===== 门控 6：OLS 趋势稳定性 =====
        regression = ols_regression(binance_timestamps, binance_prices)
        if regression is None:
            return hold_decision("OLS 回归失败")

        if regression.r_squared < self._min_r_squared:
            return hold_decision(
                f"R² = {regression.r_squared:.2f} < {self._min_r_squared}"
            )
        reasons.append(f"R² = {regression.r_squared:.2f}, K = {regression.slope:.6f}")

        # ===== 门控 7：斜率方向与 Chainlink 一致 =====
        slope_direction = "UP" if regression.slope > 0 else "DOWN"
        if slope_direction != direction:
            return hold_decision(
                f"斜率方向 ({slope_direction}) 与 Chainlink ({direction}) 不一致"
            )

        # ===== 经济学检验 =====

        # 门控 8：动态限价 = 时间衰减 + 安全垫厚度加成
        min_delta = minimum_delta_for_confidence(
            sigma, time_remaining, 1.0 - self._max_reversal_prob
        )
        max_buy = dynamic_max_price(time_remaining, delta, min_delta)
        cushion_ratio = delta / min_delta if min_delta > 0 else 0.0

        # 门控 9：市场价格 ≤ 限价
        if best_ask > max_buy:
            return hold_decision(
                f"合约卖价 ${best_ask:.2f} > 限价 ${max_buy:.2f} (垫厚{cushion_ratio:.1f}x)"
            )
        reasons.append(f"合约价格 ${best_ask:.2f} ≤ 限价 ${max_buy:.2f}")

        # 门控 10：净期望值 > 0
        test_shares = 100.0
        nev = net_expected_value(test_shares, best_ask, reversal.p_win, "crypto")
        if nev <= 0:
            return hold_decision(f"净 EV ${nev:.2f} ≤ 0 (100份)")
        reasons.append(f"净 EV = ${nev:.2f}/100份")

        # ===== 仓位计算 =====
        positioning = calculate_position(
            p_win=reversal.p_win,
            buy_price=best_ask,
            usdc_balance=account.usdc_balance,
            available_depth=ask_depth,
        )

        if positioning.recommended_shares <= 0:
            return hold_decision(
                f"仓位为零 (限制因素: {positioning.limiting_factor})"
            )
        reasons.append(
            f"仓位: {positioning.recommended_shares:.0f}份 "
            f"(限制: {positioning.limiting_factor})"
        )

        # ===== 全部通过 → FIRE =====
        fee = taker_fee(positioning.recommended_shares, best_ask, "crypto")
        final_ev = net_expected_value(
            positioning.recommended_shares, best_ask, reversal.p_win, "crypto"
        )

        token_id = market.token_id_for_direction(direction)

        logger.info(
            "🔫 FIRE! 方向=%s 价格=$%.2f 份额=%.0f EV=$%.2f P_rev=%.4f%%",
            direction, best_ask, positioning.recommended_shares,
            final_ev, reversal.p_reversal * 100,
        )

        return SniperDecision(
            action="FIRE",
            direction=direction,
            token_id=token_id,
            confidence=reversal.p_win,
            max_buy_price=max_buy,
            recommended_size=positioning.recommended_shares,
            expected_value=final_ev,
            reasons=reasons,
            delta=delta,
            sigma=sigma,
            slope_k=regression.slope,
            r_squared=regression.r_squared,
            time_remaining=time_remaining,
            chainlink_price=chainlink_price,
            start_price=start_price,
            p_reversal=reversal.p_reversal,
            best_ask=best_ask,
        )
