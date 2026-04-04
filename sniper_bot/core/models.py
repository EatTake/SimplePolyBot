"""
统一数据模型

所有模块共用的类型定义 — SniperBot 的契约层
消除 SimplePolyBot 中信号数据结构不匹配的致命缺陷
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Optional


# ──────────────────────────────────────────────
#  基础数据结构
# ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class PricePoint:
    """
    单个价格数据点

    frozen + slots 确保不可变、低内存占用
    """
    source: Literal["chainlink", "binance"]
    price: float
    timestamp: float

    def __post_init__(self) -> None:
        if self.price < 0:
            raise ValueError(f"价格不能为负: {self.price}")
        if self.timestamp < 0:
            raise ValueError(f"时间戳不能为负: {self.timestamp}")


# ──────────────────────────────────────────────
#  周期管理
# ──────────────────────────────────────────────

class CyclePhase(Enum):
    """5 分钟周期状态"""
    IDLE = "IDLE"                     # 周期间隙
    DISCOVERY = "DISCOVERY"           # 发现市场
    ACCUMULATING = "ACCUMULATING"     # 数据积累
    SNIPING = "SNIPING"              # 狙击窗口
    FIRED = "FIRED"                  # 已出手
    COOLDOWN = "COOLDOWN"            # 冷却


@dataclass
class FastMarket:
    """
    已发现的 5 分钟市场

    包含交易所需的全部标识信息
    """
    event_id: str
    condition_id: str
    up_token_id: str
    down_token_id: str
    end_timestamp: float
    slug: str = ""
    start_price: Optional[float] = None

    @property
    def duration(self) -> float:
        """周期总时长（秒）"""
        return 300.0

    def token_id_for_direction(self, direction: str) -> str:
        """根据方向获取对应的 token_id"""
        if direction == "UP":
            return self.up_token_id
        elif direction == "DOWN":
            return self.down_token_id
        raise ValueError(f"无效方向: {direction}")


@dataclass
class CycleState:
    """当前周期的完整状态"""
    cycle_id: int
    phase: CyclePhase
    start_timestamp: float
    end_timestamp: float
    time_remaining: float
    relative_time: float
    market: Optional[FastMarket] = None

    @property
    def start_price(self) -> Optional[float]:
        return self.market.start_price if self.market else None


# ──────────────────────────────────────────────
#  分析结果
# ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class VolatilityEstimate:
    """波动率估算结果"""
    sigma_dollar_per_sqrt_sec: float   # σ（$/√秒）
    sample_count: int
    timestamp: float


@dataclass(frozen=True, slots=True)
class RegressionResult:
    """OLS 回归结果"""
    slope: float         # K（$/秒）
    intercept: float
    r_squared: float
    sample_count: int
    timestamp: float


@dataclass(frozen=True, slots=True)
class ReversalAnalysis:
    """布朗桥反转概率分析"""
    delta: float            # |current - start|（$）
    sigma: float            # 波动率（$/√秒）
    time_remaining: float   # 剩余秒数
    p_reversal: float       # 反转概率
    p_win: float            # 获胜概率 = 1 - p_reversal


# ──────────────────────────────────────────────
#  交易决策 — 全系统唯一的信号契约
# ──────────────────────────────────────────────

@dataclass
class SniperDecision:
    """
    多因子仲裁器的最终决策

    这是策略层 → 执行层的唯一接口
    与 SimplePolyBot 的两套 TradingSignal 不同，
    全系统共用此单一定义
    """
    action: Literal["FIRE", "HOLD"]
    direction: Optional[Literal["UP", "DOWN"]]
    token_id: Optional[str]               # Polymarket 合约 token_id
    confidence: float                     # 1 - p_reversal
    max_buy_price: float                  # 时间衰减阶梯限价
    recommended_size: float               # 凯利公式推荐仓位（份）
    expected_value: float                 # 扣费后净 EV（$）
    reasons: list[str] = field(default_factory=list)
    signal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)

    # ---- 附带的分析快照（用于日志和回测）----
    delta: float = 0.0
    sigma: float = 0.0
    slope_k: float = 0.0
    r_squared: float = 0.0
    time_remaining: float = 0.0
    chainlink_price: float = 0.0
    start_price: float = 0.0
    p_reversal: float = 1.0
    best_ask: float = 0.0


# ──────────────────────────────────────────────
#  执行结果
# ──────────────────────────────────────────────

class OrderStatus(Enum):
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


@dataclass
class OrderResult:
    """订单执行结果"""
    status: OrderStatus
    order_id: str = ""
    filled_size: float = 0.0
    filled_price: float = 0.0
    fee: float = 0.0
    reason: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def cost(self) -> float:
        return self.filled_size * self.filled_price + self.fee

    @property
    def potential_profit(self) -> float:
        """若获胜，净利润"""
        return self.filled_size - self.cost


@dataclass
class RedemptionResult:
    """赎回结果"""
    condition_id: str
    redeemed_amount: float
    usdc_received: float
    tx_hash: str = ""
    timestamp: float = field(default_factory=time.time)


# ──────────────────────────────────────────────
#  风控
# ──────────────────────────────────────────────

@dataclass
class AccountState:
    """账户实时状态"""
    usdc_balance: float
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    peak_balance: float = 0.0
    consecutive_losses: int = 0
    cycles_since_last_loss: int = 0
    trades_today: int = 0
    wins_today: int = 0
    losses_today: int = 0

    @property
    def drawdown_pct(self) -> float:
        if self.peak_balance <= 0:
            return 0.0
        return (self.peak_balance - self.usdc_balance) / self.peak_balance

    @property
    def win_rate_today(self) -> float:
        total = self.wins_today + self.losses_today
        return self.wins_today / total if total > 0 else 0.0


@dataclass(frozen=True)
class RiskLimits:
    """风控参数 — 不可变"""
    max_single_bet: float = 200.0
    max_daily_loss: float = 500.0
    max_drawdown_pct: float = 0.15
    min_balance: float = 100.0
    max_bets_per_hour: int = 12
    cooldown_after_consecutive_losses: int = 2
    max_consecutive_losses_before_cooldown: int = 2


# ──────────────────────────────────────────────
#  便捷工厂函数
# ──────────────────────────────────────────────

def hold_decision(reason: str) -> SniperDecision:
    """快速构造 HOLD 决策"""
    return SniperDecision(
        action="HOLD",
        direction=None,
        token_id=None,
        confidence=0.0,
        max_buy_price=0.0,
        recommended_size=0.0,
        expected_value=0.0,
        reasons=[reason],
    )
