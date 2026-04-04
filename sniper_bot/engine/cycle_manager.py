"""
5 分钟周期状态机

管理每个 5 分钟交易周期的完整生命周期：
  IDLE → DISCOVERY → ACCUMULATING → SNIPING → FIRED → IDLE

与 SimplePolyBot 的 MarketLifecycleManager 的区别：
  1. 集成市场发现（DISCOVERY 阶段）
  2. 周期切换时强制清空所有分析器状态
  3. FIRED 状态防止同周期重复下单
  4. 提供对外事件回调接口
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from sniper_bot.core.models import CyclePhase, CycleState, FastMarket


logger = logging.getLogger(__name__)

# 5 分钟 = 300 秒
_CYCLE_DURATION = 300

# 狙击窗口：T-100 至 T-10
_SNIPE_WINDOW_START = 100  # 剩余 100 秒时开始
_SNIPE_WINDOW_END = 10     # 剩余 10 秒时截止


class CycleManager:
    """
    5 分钟周期状态机

    职责：
      - 计算当前处于哪个周期、哪个阶段
      - 检测周期切换并触发 on_cycle_reset 回调
      - 提供 start_price、time_remaining 等核心状态
    """

    def __init__(
        self,
        cycle_duration: int = _CYCLE_DURATION,
        snipe_start: int = _SNIPE_WINDOW_START,
        snipe_end: int = _SNIPE_WINDOW_END,
        on_cycle_reset: Optional[Callable[[], None]] = None,
    ):
        """
        Args:
            cycle_duration: 周期长度（秒）
            snipe_start: 狙击窗口开始（距结束的秒数）
            snipe_end: 狙击窗口结束（距结束的秒数）
            on_cycle_reset: 周期切换时的回调（用于清空队列等）
        """
        self._duration = cycle_duration
        self._snipe_start = snipe_start
        self._snipe_end = snipe_end
        self._on_cycle_reset = on_cycle_reset

        self._cycle_count = 0
        self._current_start: float = 0.0
        self._phase = CyclePhase.IDLE
        self._market: Optional[FastMarket] = None
        self._fired_this_cycle = False

    def tick(self, now: Optional[float] = None) -> CycleState:
        """
        每秒调用一次，更新并返回当前周期状态

        Args:
            now: 当前 Unix 时间戳，默认 time.time()

        Returns:
            当前周期完整状态
        """
        if now is None:
            now = time.time()

        cycle_start = self._calculate_cycle_start(now)
        cycle_end = cycle_start + self._duration
        time_remaining = max(0.0, cycle_end - now)
        relative_time = now - cycle_start

        # 检测周期切换
        if abs(cycle_start - self._current_start) > 1.0:
            self._handle_cycle_reset(cycle_start)

        # 更新阶段
        self._phase = self._determine_phase(time_remaining, relative_time)

        return CycleState(
            cycle_id=self._cycle_count,
            phase=self._phase,
            start_timestamp=cycle_start,
            end_timestamp=cycle_end,
            time_remaining=time_remaining,
            relative_time=relative_time,
            market=self._market,
        )

    def set_market(self, market: FastMarket) -> None:
        """设置当前周期的市场信息"""
        self._market = market
        logger.info(
            "周期 %d: 市场已设置 condition=%s",
            self._cycle_count, market.condition_id[:16],
        )

    def set_start_price(self, price: float) -> None:
        """设置周期起始价格"""
        if self._market:
            self._market.start_price = price
            logger.info(
                "周期 %d: 起始价格 $%.2f",
                self._cycle_count, price,
            )

    def mark_fired(self) -> None:
        """标记本周期已出手"""
        self._fired_this_cycle = True
        self._phase = CyclePhase.FIRED
        logger.info("周期 %d: 已标记为 FIRED", self._cycle_count)

    @property
    def has_fired(self) -> bool:
        return self._fired_this_cycle

    @property
    def is_sniping(self) -> bool:
        return self._phase == CyclePhase.SNIPING

    @property
    def market(self) -> Optional[FastMarket]:
        return self._market

    def _calculate_cycle_start(self, now: float) -> float:
        """计算给定时间戳所属周期的起始时间"""
        cycles_elapsed = int(now // self._duration)
        return cycles_elapsed * self._duration

    def _handle_cycle_reset(self, new_start: float) -> None:
        """处理周期切换"""
        self._current_start = new_start
        self._cycle_count += 1
        self._market = None
        self._fired_this_cycle = False

        logger.info(
            "========== 周期 %d 开始 ==========",
            self._cycle_count,
        )

        # 触发外部回调（清空价格队列、波动率估算器等）
        if self._on_cycle_reset:
            try:
                self._on_cycle_reset()
            except Exception as e:
                logger.error("周期重置回调异常: %s", e)

    def _determine_phase(
        self,
        time_remaining: float,
        relative_time: float,
    ) -> CyclePhase:
        """根据剩余时间确定当前阶段"""
        if self._fired_this_cycle:
            return CyclePhase.FIRED

        if time_remaining <= 0:
            return CyclePhase.IDLE

        if self._market is None:
            return CyclePhase.DISCOVERY

        if time_remaining > self._snipe_start:
            return CyclePhase.ACCUMULATING

        if time_remaining >= self._snipe_end:
            return CyclePhase.SNIPING

        # T < 10s，太晚了
        return CyclePhase.COOLDOWN
