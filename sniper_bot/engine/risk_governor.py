"""
风控总闸

所有 FIRE 决策必须经过 RiskGovernor 审批。
与 SimplePolyBot 的关键区别：每个参数都被强制检查和执行。

风控层级：
  1. 余额底线
  2. 单笔限额
  3. 日亏损上限
  4. 最大回撤
  5. 连亏冷却
  6. 频率限制
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sniper_bot.core.models import AccountState, RiskLimits, SniperDecision


logger = logging.getLogger(__name__)


@dataclass
class RiskVerdict:
    """风控审批结果"""
    approved: bool
    original_size: float
    adjusted_size: float
    reason: str = ""


class RiskGovernor:
    """
    风控总闸

    SimplePolyBot 的 OrderManager 加载了 risk_management 参数但从未使用。
    本模块的每一个参数都有对应的硬拒绝逻辑。
    """

    def __init__(self, limits: Optional[RiskLimits] = None):
        self.limits = limits or RiskLimits()
        self._trades_this_hour: list[float] = []  # 时间戳列表

    def approve(
        self,
        decision: SniperDecision,
        account: AccountState,
    ) -> RiskVerdict:
        """
        审批交易决策

        Args:
            decision: 仲裁器的 FIRE 决策
            account: 当前账户状态

        Returns:
            RiskVerdict 包含审批结果和可能的仓位调整
        """
        original_size = decision.recommended_size

        # ===== 1. 余额底线 =====
        if account.usdc_balance < self.limits.min_balance:
            return self._reject(
                original_size,
                f"余额 ${account.usdc_balance:.2f} < 底线 ${self.limits.min_balance:.2f}",
            )

        # ===== 2. 单笔限额 =====
        cost = original_size * decision.max_buy_price
        if cost > self.limits.max_single_bet:
            adjusted_size = self.limits.max_single_bet / decision.max_buy_price
            logger.info(
                "单笔限额调整: %.0f → %.0f 份",
                original_size, adjusted_size,
            )
        else:
            adjusted_size = original_size

        # 确保调整后的交易成本不超过可用余额
        adjusted_cost = adjusted_size * decision.max_buy_price
        if adjusted_cost > account.usdc_balance * 0.9:  # 保留 10% 安全边际
            adjusted_size = (account.usdc_balance * 0.9) / decision.max_buy_price

        # ===== 3. 日亏损上限 =====
        if account.daily_pnl <= -self.limits.max_daily_loss:
            return self._reject(
                original_size,
                f"日亏损 ${abs(account.daily_pnl):.2f} 已触及上限 ${self.limits.max_daily_loss:.2f}",
            )

        # ===== 4. 最大回撤 =====
        if account.drawdown_pct >= self.limits.max_drawdown_pct:
            return self._reject(
                original_size,
                f"回撤 {account.drawdown_pct:.1%} 已触及上限 {self.limits.max_drawdown_pct:.0%}",
            )

        # ===== 5. 连亏冷却 =====
        max_consec = self.limits.max_consecutive_losses_before_cooldown
        cooldown = self.limits.cooldown_after_consecutive_losses

        if account.consecutive_losses >= max_consec:
            if account.cycles_since_last_loss < cooldown:
                return self._reject(
                    original_size,
                    f"连亏 {account.consecutive_losses} 次，冷却中 "
                    f"({account.cycles_since_last_loss}/{cooldown} 周期)",
                )

        # ===== 6. 频率限制 =====
        import time
        now = time.time()
        hour_ago = now - 3600
        self._trades_this_hour = [t for t in self._trades_this_hour if t > hour_ago]

        if len(self._trades_this_hour) >= self.limits.max_bets_per_hour:
            return self._reject(
                original_size,
                f"小时内交易 {len(self._trades_this_hour)} 次，达到上限",
            )

        # ===== 全部通过 =====
        self._trades_this_hour.append(now)

        if adjusted_size < 10:
            return self._reject(original_size, "调整后仓位低于最低 10 份")

        logger.info(
            "✅ 风控通过: %.0f → %.0f 份, 余额 $%.0f, 日PnL $%.0f",
            original_size, adjusted_size,
            account.usdc_balance, account.daily_pnl,
        )

        return RiskVerdict(
            approved=True,
            original_size=original_size,
            adjusted_size=adjusted_size,
        )

    def _reject(self, original_size: float, reason: str) -> RiskVerdict:
        logger.warning("🚫 风控拒绝: %s", reason)
        return RiskVerdict(
            approved=False,
            original_size=original_size,
            adjusted_size=0.0,
            reason=reason,
        )
