"""
价格队列管理模块

使用 collections.deque 实现 180 秒滚动队列
存储价格数据及其时间戳，支持线程安全操作
"""

import threading
from collections import deque
from typing import Optional, List, Tuple
from dataclasses import dataclass
import time

from shared.logger import get_logger


logger = get_logger(__name__)


@dataclass
class PricePoint:
    """
    价格数据点
    
    存储单个时间点的价格信息
    """
    timestamp: float
    price: float
    
    def __post_init__(self):
        """验证数据"""
        if self.timestamp < 0:
            raise ValueError(f"时间戳不能为负数: {self.timestamp}")
        if self.price < 0:
            raise ValueError(f"价格不能为负数: {self.price}")


class PriceQueue:
    """
    价格队列类
    
    实现基于时间的滚动队列，自动清理过期数据
    支持线程安全的 push 和 get 操作
    """
    
    def __init__(self, window_seconds: int = 180, max_size: int = 10000):
        """
        初始化价格队列
        
        Args:
            window_seconds: 时间窗口大小（秒），默认 180 秒
            max_size: 队列最大容量，防止内存溢出
        """
        self.window_seconds = window_seconds
        self.max_size = max_size
        
        self._queue: deque[PricePoint] = deque(maxlen=max_size)
        self._lock = threading.RLock()
        
        logger.info(
            "初始化价格队列",
            window_seconds=window_seconds,
            max_size=max_size
        )
    
    def push(self, price: float, timestamp: Optional[float] = None) -> bool:
        """
        推送价格数据到队列
        
        Args:
            price: 价格值
            timestamp: 时间戳（秒），默认为当前时间
        
        Returns:
            推送是否成功
        """
        try:
            if timestamp is None:
                timestamp = time.time()
            
            price_point = PricePoint(timestamp=timestamp, price=price)
            
            with self._lock:
                self._queue.append(price_point)
            
            logger.debug(
                "价格数据已入队",
                price=price,
                timestamp=timestamp,
                queue_size=len(self._queue)
            )
            
            return True
            
        except Exception as e:
            logger.error("价格数据入队失败", error=str(e), price=price)
            return False
    
    def get_all(self) -> List[PricePoint]:
        """
        获取队列中所有有效数据
        
        Returns:
            价格数据点列表
        """
        with self._lock:
            self._cleanup_expired()
            return list(self._queue)
    
    def get_prices(self) -> List[float]:
        """
        获取所有价格值（不含时间戳）
        
        Returns:
            价格值列表
        """
        with self._lock:
            self._cleanup_expired()
            return [point.price for point in self._queue]
    
    def get_timestamps_and_prices(self) -> Tuple[List[float], List[float]]:
        """
        获取时间戳和价格数组（用于回归分析）
        
        Returns:
            (时间戳列表, 价格列表)
        """
        with self._lock:
            self._cleanup_expired()
            
            timestamps = [point.timestamp for point in self._queue]
            prices = [point.price for point in self._queue]
            
            return timestamps, prices
    
    def get_latest(self, n: int = 1) -> List[PricePoint]:
        """
        获取最新的 n 个数据点
        
        Args:
            n: 数据点数量
        
        Returns:
            最新的价格数据点列表
        """
        with self._lock:
            self._cleanup_expired()
            
            if n <= 0:
                return []
            
            queue_list = list(self._queue)
            return queue_list[-n:] if n < len(queue_list) else queue_list
    
    def get_latest_price(self) -> Optional[float]:
        """
        获取最新价格
        
        Returns:
            最新价格，如果队列为空则返回 None
        """
        with self._lock:
            if self._queue:
                return self._queue[-1].price
            return None
    
    def get_earliest_price(self) -> Optional[float]:
        """
        获取最早价格
        
        Returns:
            最早价格，如果队列为空则返回 None
        """
        with self._lock:
            if self._queue:
                return self._queue[0].price
            return None
    
    def get_price_range(self) -> Tuple[Optional[float], Optional[float]]:
        """
        获取价格范围（最小值和最大值）
        
        Returns:
            (最小价格, 最大价格)，如果队列为空则返回 (None, None)
        """
        with self._lock:
            self._cleanup_expired()
            
            if not self._queue:
                return None, None
            
            prices = [point.price for point in self._queue]
            return min(prices), max(prices)
    
    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self._queue.clear()
            logger.info("价格队列已清空")
    
    def size(self) -> int:
        """
        获取队列当前大小
        
        Returns:
            队列中的数据点数量
        """
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """
        检查队列是否为空
        
        Returns:
            队列是否为空
        """
        with self._lock:
            return len(self._queue) == 0
    
    def get_time_span(self) -> float:
        """
        获取队列的时间跨度（秒）
        
        Returns:
            时间跨度，如果队列少于 2 个数据点则返回 0
        """
        with self._lock:
            if len(self._queue) < 2:
                return 0.0
            
            earliest = self._queue[0].timestamp
            latest = self._queue[-1].timestamp
            
            return latest - earliest
    
    def _cleanup_expired(self) -> int:
        """
        清理过期数据（内部方法）
        
        移除超出时间窗口的数据点
        
        Returns:
            清理的数据点数量
        """
        if not self._queue:
            return 0
        
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        expired_count = 0
        
        while self._queue and self._queue[0].timestamp < cutoff_time:
            self._queue.popleft()
            expired_count += 1
        
        if expired_count > 0:
            logger.debug(
                "清理过期价格数据",
                expired_count=expired_count,
                remaining_count=len(self._queue)
            )
        
        return expired_count
    
    def get_statistics(self) -> dict:
        """
        获取队列统计信息
        
        Returns:
            包含统计信息的字典
        """
        with self._lock:
            self._cleanup_expired()
            
            if not self._queue:
                return {
                    "size": 0,
                    "time_span": 0.0,
                    "min_price": None,
                    "max_price": None,
                    "avg_price": None,
                    "latest_price": None,
                }
            
            prices = [point.price for point in self._queue]
            
            return {
                "size": len(self._queue),
                "time_span": self.get_time_span(),
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": sum(prices) / len(prices),
                "latest_price": prices[-1],
            }
