"""
损益追踪器

实时跟踪每笔交易的结算结果，维护账户状态，
并生成统计报表。

功能：
  - 交易记录持久化（JSON 文件）
  - 账户状态实时更新
  - 日/周/月统计
  - 连亏/连胜追踪
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from sniper_bot.core.models import AccountState, OrderResult, OrderStatus, SniperDecision


logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """单笔交易记录"""
    signal_id: str
    direction: str
    token_id: str
    entry_price: float
    size: float
    fee: float
    cost: float
    expected_value: float
    p_reversal: float
    time_remaining: float
    delta: float
    sigma: float
    slope_k: float
    r_squared: float
    timestamp: float
    # 结算后填充
    outcome: str = ""       # "WIN" / "LOSS" / "PENDING"
    pnl: float = 0.0


class PnLTracker:
    """
    损益追踪器

    维护 AccountState 并持久化交易记录
    """

    def __init__(
        self,
        initial_balance: float,
        data_dir: str = "data",
    ):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._trades_file = self._data_dir / "trades.jsonl"

        self.account = AccountState(
            usdc_balance=initial_balance,
            peak_balance=initial_balance,
        )

        self._pending_trades: dict[str, TradeRecord] = {}

        # 加载历史统计
        self._load_today_stats()

    def record_trade(
        self,
        decision: SniperDecision,
        result: OrderResult,
    ) -> TradeRecord:
        """
        记录新交易

        Args:
            decision: 仲裁器的 FIRE 决策
            result: 订单执行结果
        """
        record = TradeRecord(
            signal_id=decision.signal_id,
            direction=decision.direction or "",
            token_id=decision.token_id or "",
            entry_price=result.filled_price,
            size=result.filled_size,
            fee=result.fee,
            cost=result.cost,
            expected_value=decision.expected_value,
            p_reversal=decision.p_reversal,
            time_remaining=decision.time_remaining,
            delta=decision.delta,
            sigma=decision.sigma,
            slope_k=decision.slope_k,
            r_squared=decision.r_squared,
            timestamp=time.time(),
            outcome="PENDING",
        )

        # 更新账户余额（扣除成本）
        self.account.usdc_balance -= result.cost
        self.account.trades_today += 1

        # 挂起，等待结算
        self._pending_trades[decision.signal_id] = record

        self._persist(record)

        logger.info(
            "📝 交易记录: %s %s 价格=$%.2f 份额=%.0f 成本=$%.2f",
            decision.direction, decision.signal_id[:8],
            result.filled_price, result.filled_size, result.cost,
        )

        return record

    def settle_trade(
        self,
        signal_id: str,
        won: bool,
    ) -> Optional[TradeRecord]:
        """
        结算交易

        Args:
            signal_id: 信号 ID
            won: 是否获胜
        """
        record = self._pending_trades.pop(signal_id, None)
        if record is None:
            logger.warning("结算未知交易: %s", signal_id)
            return None

        if won:
            # 获胜：收回 size × $1.00
            pnl = record.size - record.cost
            record.outcome = "WIN"
            record.pnl = pnl
            self.account.usdc_balance += record.size  # 收回全部面值
            self.account.wins_today += 1
            self.account.consecutive_losses = 0
        else:
            # 亏损：成本已扣除
            pnl = -record.cost
            record.outcome = "LOSS"
            record.pnl = pnl
            self.account.losses_today += 1
            self.account.consecutive_losses += 1

        self.account.daily_pnl += pnl
        self.account.total_pnl += pnl

        # 更新峰值余额
        if self.account.usdc_balance > self.account.peak_balance:
            self.account.peak_balance = self.account.usdc_balance

        self._persist(record)

        emoji = "✅" if won else "❌"
        logger.info(
            "%s 结算: %s PnL=$%.2f 余额=$%.2f 日PnL=$%.2f",
            emoji, signal_id[:8], pnl,
            self.account.usdc_balance, self.account.daily_pnl,
        )

        return record

    def on_new_cycle(self) -> None:
        """新周期开始时调用"""
        self.account.cycles_since_last_loss += 1

    def reset_daily_stats(self) -> None:
        """日切时重置每日统计"""
        logger.info(
            "📊 日终统计: 交易=%d 胜=%d 负=%d 日PnL=$%.2f",
            self.account.trades_today,
            self.account.wins_today,
            self.account.losses_today,
            self.account.daily_pnl,
        )
        self.account.daily_pnl = 0.0
        self.account.trades_today = 0
        self.account.wins_today = 0
        self.account.losses_today = 0

    def get_stats(self) -> dict:
        """获取统计快照"""
        total = self.account.wins_today + self.account.losses_today
        return {
            "balance": self.account.usdc_balance,
            "daily_pnl": self.account.daily_pnl,
            "total_pnl": self.account.total_pnl,
            "trades_today": self.account.trades_today,
            "win_rate": self.account.win_rate_today,
            "drawdown": self.account.drawdown_pct,
            "consecutive_losses": self.account.consecutive_losses,
            "pending_trades": len(self._pending_trades),
        }

    def _persist(self, record: TradeRecord) -> None:
        """追加写入 JSONL 文件"""
        try:
            with open(self._trades_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("持久化交易记录失败: %s", e)

    def _load_today_stats(self) -> None:
        """从文件加载今日统计（断电恢复）"""
        if not self._trades_file.exists():
            return

        try:
            today_start = int(time.time()) // 86400 * 86400
            with open(self._trades_file, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line.strip())
                    if record.get("timestamp", 0) >= today_start:
                        if record.get("outcome") == "WIN":
                            self.account.wins_today += 1
                        elif record.get("outcome") == "LOSS":
                            self.account.losses_today += 1
                        self.account.daily_pnl += record.get("pnl", 0)
                        self.account.trades_today += 1
        except Exception as e:
            logger.warning("加载历史统计失败: %s", e)
