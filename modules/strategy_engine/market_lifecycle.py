"""
市场生命周期管理模块

实现 5 分钟周期起始时间计算、周期内相对时间计算
管理周期切换逻辑（清空队列、获取新 Start Price）
"""

import time
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from shared.logger import get_logger
from shared.constants import FAST_MARKET_DURATION_SECONDS


logger = get_logger(__name__)


class MarketPhase(Enum):
    """市场周期阶段"""
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    ENDING = "ENDING"
    CLOSED = "CLOSED"


@dataclass
class MarketCycle:
    """
    市场周期信息
    
    包含周期的完整状态信息
    """
    cycle_id: int
    start_time: float
    end_time: float
    start_price: Optional[float]
    phase: MarketPhase
    relative_time: float
    time_remaining: float
    
    def to_dict(self) -> dict:
        """
        转换为字典格式
        
        Returns:
            周期信息字典
        """
        return {
            "cycle_id": self.cycle_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "start_price": self.start_price,
            "phase": self.phase.value,
            "relative_time": self.relative_time,
            "time_remaining": self.time_remaining,
        }


class MarketLifecycleManager:
    """
    市场生命周期管理器
    
    管理 Fast Market 的 5 分钟周期
    实现周期切换和状态管理
    """
    
    def __init__(
        self,
        cycle_duration: int = FAST_MARKET_DURATION_SECONDS,
        cycle_offset: int = 0,
    ):
        """
        初始化市场生命周期管理器
        
        Args:
            cycle_duration: 周期持续时间（秒），默认 300 秒（5 分钟）
            cycle_offset: 周期偏移量（秒），用于对齐特定时间点
        """
        self.cycle_duration = cycle_duration
        self.cycle_offset = cycle_offset
        
        self._current_cycle: Optional[MarketCycle] = None
        self._cycle_count = 0
        
        logger.info(
            "初始化市场生命周期管理器",
            cycle_duration=cycle_duration,
            cycle_offset=cycle_offset
        )
    
    def get_current_cycle(self) -> MarketCycle:
        """
        获取当前周期信息
        
        Returns:
            当前周期信息
        """
        current_time = time.time()
        
        cycle_start_time = self.calculate_cycle_start_time(current_time)
        cycle_end_time = cycle_start_time + self.cycle_duration
        
        if self._current_cycle is None or self._has_cycle_changed(cycle_start_time):
            self._cycle_count += 1
            
            self._current_cycle = MarketCycle(
                cycle_id=self._cycle_count,
                start_time=cycle_start_time,
                end_time=cycle_end_time,
                start_price=None,
                phase=MarketPhase.INITIALIZING,
                relative_time=0.0,
                time_remaining=self.cycle_duration,
            )
            
            logger.info(
                "新周期开始",
                cycle_id=self._cycle_count,
                start_time=cycle_start_time,
                end_time=cycle_end_time
            )
        
        self._update_cycle_state(current_time)
        
        return self._current_cycle
    
    def calculate_cycle_start_time(self, timestamp: float) -> float:
        """
        计算给定时间戳所属周期的起始时间
        
        Args:
            timestamp: 时间戳
        
        Returns:
            周期起始时间
        """
        adjusted_time = timestamp - self.cycle_offset
        
        cycles_elapsed = int(adjusted_time // self.cycle_duration)
        
        cycle_start = (cycles_elapsed * self.cycle_duration) + self.cycle_offset
        
        return cycle_start
    
    def calculate_relative_time(self, timestamp: Optional[float] = None) -> float:
        """
        计算周期内的相对时间
        
        Args:
            timestamp: 时间戳，默认为当前时间
        
        Returns:
            相对时间（秒）
        """
        if timestamp is None:
            timestamp = time.time()
        
        cycle_start = self.calculate_cycle_start_time(timestamp)
        
        relative_time = timestamp - cycle_start
        
        return relative_time
    
    def calculate_time_remaining(self, timestamp: Optional[float] = None) -> float:
        """
        计算周期剩余时间
        
        Args:
            timestamp: 时间戳，默认为当前时间
        
        Returns:
            剩余时间（秒）
        """
        if timestamp is None:
            timestamp = time.time()
        
        relative_time = self.calculate_relative_time(timestamp)
        
        time_remaining = self.cycle_duration - relative_time
        
        return max(0.0, time_remaining)
    
    def set_start_price(self, price: float) -> None:
        """
        设置当前周期的起始价格
        
        Args:
            price: 起始价格
        """
        if self._current_cycle is None:
            logger.warn("当前周期为空，无法设置起始价格")
            return
        
        self._current_cycle.start_price = price
        
        logger.info(
            "设置周期起始价格",
            cycle_id=self._current_cycle.cycle_id,
            start_price=price
        )
    
    def get_start_price(self) -> Optional[float]:
        """
        获取当前周期的起始价格
        
        Returns:
            起始价格，如果未设置则返回 None
        """
        if self._current_cycle is None:
            return None
        
        return self._current_cycle.start_price
    
    def _has_cycle_changed(self, new_cycle_start: float) -> bool:
        """
        检查周期是否已切换
        
        Args:
            new_cycle_start: 新周期的起始时间
        
        Returns:
            周期是否已切换
        """
        if self._current_cycle is None:
            return True
        
        return abs(new_cycle_start - self._current_cycle.start_time) > 1.0
    
    def _update_cycle_state(self, current_time: float) -> None:
        """
        更新周期状态
        
        Args:
            current_time: 当前时间戳
        """
        if self._current_cycle is None:
            return
        
        relative_time = self.calculate_relative_time(current_time)
        time_remaining = self.calculate_time_remaining(current_time)
        
        self._current_cycle.relative_time = relative_time
        self._current_cycle.time_remaining = time_remaining
        
        if time_remaining <= 0:
            self._current_cycle.phase = MarketPhase.CLOSED
        elif time_remaining <= 30:
            self._current_cycle.phase = MarketPhase.ENDING
        elif self._current_cycle.start_price is None:
            self._current_cycle.phase = MarketPhase.INITIALIZING
        else:
            self._current_cycle.phase = MarketPhase.ACTIVE
    
    def is_in_trading_window(self) -> bool:
        """
        检查是否在交易窗口内
        
        交易窗口: T-100s 至 T-10s
        
        Returns:
            是否在交易窗口内
        """
        time_remaining = self.calculate_time_remaining()
        
        return 10.0 <= time_remaining <= 100.0
    
    def get_next_cycle_info(self) -> Tuple[float, float]:
        """
        获取下一个周期的信息
        
        Returns:
            (下一周期起始时间, 距离下一周期的时间)
        """
        current_time = time.time()
        
        current_cycle_start = self.calculate_cycle_start_time(current_time)
        
        next_cycle_start = current_cycle_start + self.cycle_duration
        
        time_to_next = next_cycle_start - current_time
        
        return next_cycle_start, time_to_next
    
    def reset(self) -> None:
        """重置生命周期管理器"""
        self._current_cycle = None
        self._cycle_count = 0
        
        logger.info("市场生命周期管理器已重置")


def get_market_cycle(cycle_duration: int = 300) -> MarketCycle:
    """
    获取当前市场周期的便捷函数
    
    Args:
        cycle_duration: 周期持续时间
    
    Returns:
        市场周期信息
    """
    manager = MarketLifecycleManager(cycle_duration=cycle_duration)
    return manager.get_current_cycle()
