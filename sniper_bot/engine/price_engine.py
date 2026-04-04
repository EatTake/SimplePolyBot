"""
双轨价格引擎

管理 Chainlink（裁判轨）和 Binance（分析轨）两条独立的价格队列。
确保"用什么数据做什么事"的权责分离。

与 SimplePolyBot 的 PriceQueue 的区别：
  1. 双轨分离：Chainlink 用于计算 Δ，Binance 用于计算 K 和 σ
  2. 内置线程安全（asyncio 场景下实际无竞态，但保留锁以兼容混合场景）
  3. 周期切换时由 CycleManager 回调统一清空
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional

import numpy as np

from sniper_bot.core.models import PricePoint


class PriceTrack:
    """
    单轨价格队列

    基于时间窗口的滚动队列，自动清理过期数据
    """

    def __init__(
        self,
        source: str,
        window_seconds: int = 180,
        max_size: int = 10000,
    ):
        self.source = source
        self._window = window_seconds
        self._queue: deque[PricePoint] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def push(self, price: float, timestamp: Optional[float] = None) -> None:
        """推入价格数据"""
        if timestamp is None:
            timestamp = time.time()

        point = PricePoint(source=self.source, price=price, timestamp=timestamp)
        with self._lock:
            self._queue.append(point)

    def get_arrays(self) -> tuple[np.ndarray, np.ndarray]:
        """
        获取时间戳和价格的 NumPy 数组（用于 OLS 回归和波动率计算）

        Returns:
            (timestamps, prices) 两个一维数组
        """
        with self._lock:
            self._cleanup()
            if not self._queue:
                return np.array([]), np.array([])

            timestamps = np.array([p.timestamp for p in self._queue])
            prices = np.array([p.price for p in self._queue])
            return timestamps, prices

    def latest_price(self) -> Optional[float]:
        """获取最新价格"""
        with self._lock:
            return self._queue[-1].price if self._queue else None

    def earliest_price(self) -> Optional[float]:
        """获取最早价格"""
        with self._lock:
            self._cleanup()
            return self._queue[0].price if self._queue else None

    @property
    def size(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self._queue.clear()

    def _cleanup(self) -> None:
        """清理超出时间窗口的数据"""
        cutoff = time.time() - self._window
        while self._queue and self._queue[0].timestamp < cutoff:
            self._queue.popleft()


class PriceEngine:
    """
    双轨价格引擎

    Usage:
        engine = PriceEngine()
        engine.push_chainlink(67234.50, timestamp)
        engine.push_binance(67234.20, timestamp)

        delta = engine.get_delta(start_price=67200.0)
        timestamps, prices = engine.binance.get_arrays()
    """

    def __init__(self, window_seconds: int = 180):
        self.chainlink = PriceTrack("chainlink", window_seconds)
        self.binance = PriceTrack("binance", window_seconds)

    def push_chainlink(self, price: float, timestamp: Optional[float] = None) -> None:
        """推入 Chainlink（裁判轨）价格"""
        self.chainlink.push(price, timestamp)

    def push_binance(self, price: float, timestamp: Optional[float] = None) -> None:
        """推入 Binance（分析轨）价格"""
        self.binance.push(price, timestamp)

    def get_delta(self, start_price: float) -> Optional[float]:
        """
        计算 BTC 当前偏移量（使用 Chainlink 裁判价格）

        Args:
            start_price: 周期起始价格

        Returns:
            |current_chainlink - start_price| 或 None
        """
        current = self.chainlink.latest_price()
        if current is None:
            return None
        return abs(current - start_price)

    def get_direction(self, start_price: float) -> Optional[str]:
        """
        判断当前方向（使用 Chainlink 裁判价格）

        Returns:
            "UP", "DOWN" 或 None
        """
        current = self.chainlink.latest_price()
        if current is None:
            return None

        if current >= start_price:
            return "UP"
        return "DOWN"

    def directions_agree(self, start_price: float) -> bool:
        """
        检查 Chainlink 和 Binance 的方向是否一致

        这是重要的基差风险过滤器
        """
        chainlink_current = self.chainlink.latest_price()
        binance_current = self.binance.latest_price()

        if chainlink_current is None or binance_current is None:
            return False

        chainlink_up = chainlink_current >= start_price
        binance_up = binance_current >= start_price

        return chainlink_up == binance_up

    def clear_all(self) -> None:
        """清空双轨数据（周期切换时调用）"""
        self.chainlink.clear()
        self.binance.clear()
