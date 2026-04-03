"""
动态安全垫计算模块

实现 Base Cushion 和 Buffer Cushion 计算
根据市场波动和时间剩余动态调整安全垫厚度
"""

import math
from typing import Optional
from dataclasses import dataclass

from shared.logger import get_logger
from shared.config import Config


logger = get_logger(__name__)


@dataclass
class SafetyCushionResult:
    """
    安全垫计算结果
    
    包含各部分安全垫的详细计算
    """
    base_cushion: float
    buffer_cushion: float
    total_cushion: float
    slope_k: float
    time_remaining: float
    alpha: float
    
    def __post_init__(self):
        """验证结果"""
        if self.base_cushion < 0:
            raise ValueError(f"Base Cushion 不能为负数: {self.base_cushion}")
        if self.buffer_cushion < 0:
            raise ValueError(f"Buffer Cushion 不能为负数: {self.buffer_cushion}")
        if self.total_cushion < 0:
            raise ValueError(f"总安全垫不能为负数: {self.total_cushion}")
        if not (0 <= self.alpha <= 1):
            raise ValueError(f"Alpha 必须在 0-1 范围内: {self.alpha}")


class SafetyCushionCalculator:
    """
    动态安全垫计算器
    
    根据市场波动和时间剩余计算安全垫厚度
    公式: Total Cushion = Base Cushion + α × |K| × √Time Remaining
    """
    
    def __init__(
        self,
        base_cushion: Optional[float] = None,
        alpha: Optional[float] = None,
    ):
        """
        初始化安全垫计算器
        
        Args:
            base_cushion: 基础安全垫，默认从配置读取
            alpha: 价格调整系数，默认从配置读取
        """
        config = Config.get_instance()
        
        try:
            strategy_config = config.get_strategy_config()
            self.base_cushion = base_cushion if base_cushion is not None else strategy_config.base_cushion
            self.alpha = alpha if alpha is not None else strategy_config.alpha
        except Exception:
            self.base_cushion = base_cushion if base_cushion is not None else 0.02
            self.alpha = alpha if alpha is not None else 0.5
        
        logger.info(
            "初始化安全垫计算器",
            base_cushion=self.base_cushion,
            alpha=self.alpha
        )
    
    def calculate(
        self,
        slope_k: float,
        time_remaining_seconds: float,
    ) -> SafetyCushionResult:
        """
        计算动态安全垫
        
        Args:
            slope_k: 回归斜率（波动子因子）
            time_remaining_seconds: 剩余时间（秒）
        
        Returns:
            安全垫计算结果
        """
        base_cushion = self.calculate_base_cushion()
        
        if time_remaining_seconds < 0:
            logger.warn(
                "剩余时间为负数，设置为 0",
                time_remaining=time_remaining_seconds
            )
            time_remaining_seconds = 0
        
        buffer_cushion = self.calculate_buffer_cushion(slope_k, time_remaining_seconds)
        
        total_cushion = base_cushion + buffer_cushion
        
        logger.debug(
            "安全垫计算完成",
            base_cushion=base_cushion,
            buffer_cushion=buffer_cushion,
            total_cushion=total_cushion,
            slope_k=slope_k,
            time_remaining=time_remaining_seconds
        )
        
        return SafetyCushionResult(
            base_cushion=base_cushion,
            buffer_cushion=buffer_cushion,
            total_cushion=total_cushion,
            slope_k=slope_k,
            time_remaining=time_remaining_seconds,
            alpha=self.alpha
        )
    
    def calculate_base_cushion(self) -> float:
        """
        计算基础安全垫
        
        Base Cushion 是固定的安全垫部分
        
        Returns:
            基础安全垫值
        """
        return self.base_cushion
    
    def calculate_buffer_cushion(
        self,
        slope_k: float,
        time_remaining_seconds: float,
    ) -> float:
        """
        计算缓冲安全垫
        
        公式: Buffer Cushion = α × |K| × √Time Remaining
        
        Args:
            slope_k: 回归斜率
            time_remaining_seconds: 剩余时间（秒），必须 >= 0
        
        Returns:
            缓冲安全垫值
        """
        if time_remaining_seconds <= 0:
            return 0.0
        
        abs_slope = abs(slope_k)
        
        sqrt_time = math.sqrt(time_remaining_seconds)
        
        buffer_cushion = self.alpha * abs_slope * sqrt_time
        
        return buffer_cushion
    
    def calculate_max_buy_price(
        self,
        current_price: float,
        safety_cushion: float,
    ) -> float:
        """
        计算最大买入价格（旧版接口 - 建议使用 SignalGenerator 版本）
        
        ⚠️ 已知问题（Bug #1, #2）：
           此方法接收 current_price（BTC 绝对价格 ~$67,000），减去 safety_cushion（概率值 ~0.05）
           后仍约 $67,000，clamp 到 [0.01, 0.99] 后恒为 0.99
           
        ✅ 推荐替代方案：
           使用 SignalGenerator.calculate_max_buy_price(market_best_ask, safety_cushion, time_remaining)
           该版本在概率空间（0-1）计算，避免量纲混淆
        
        公式: Max Buy Price = Current Price - Safety Cushion（有 Bug）
        
        Args:
            current_price: 当前价格（注意：此参数应为概率空间值，但历史原因可能传入 BTC 绝对价格）
            safety_cushion: 安全垫厚度（概率空间）
        
        Returns:
            最大买入价格（clamp 到 [0.01, 0.99]）
        """
        import warnings
        warnings.warn(
            "SafetyCushionCalculator.calculate_max_buy_price() 存在量纲混淆 Bug (Bug #1, #2)。\n"
            "请使用 SignalGenerator.calculate_max_buy_price(market_best_ask, safety_cushion, time_remaining) 替代。",
            DeprecationWarning,
            stacklevel=2
        )
        
        max_buy_price = current_price - safety_cushion
        
        max_buy_price = max(0.01, min(0.99, max_buy_price))
        
        logger.debug(
            "计算最大买入价格（旧版接口 - 可能存在 Bug）",
            current_price=current_price,
            safety_cushion=safety_cushion,
            max_buy_price=max_buy_price
        )
        
        return max_buy_price
    
    def adjust_cushion_by_volatility(
        self,
        base_cushion: float,
        volatility_factor: float,
    ) -> float:
        """
        根据波动率调整安全垫
        
        高波动率增加安全垫，低波动率减少安全垫
        
        Args:
            base_cushion: 基础安全垫
            volatility_factor: 波动率因子（0-1）
        
        Returns:
            调整后的安全垫
        """
        adjustment = 1.0 + (volatility_factor - 0.5) * 0.5
        
        adjusted_cushion = base_cushion * adjustment
        
        logger.debug(
            "根据波动率调整安全垫",
            base_cushion=base_cushion,
            volatility_factor=volatility_factor,
            adjustment=adjustment,
            adjusted_cushion=adjusted_cushion
        )
        
        return adjusted_cushion
    
    def calculate_dynamic_alpha(
        self,
        r_squared: float,
        confidence_threshold: float = 0.7,
    ) -> float:
        """
        根据回归拟合优度动态调整 alpha
        
        R² 越高，alpha 越大（更信任趋势）
        
        Args:
            r_squared: 决定系数
            confidence_threshold: 置信度阈值
        
        Returns:
            调整后的 alpha
        """
        if r_squared >= confidence_threshold:
            dynamic_alpha = self.alpha * 1.2
        else:
            dynamic_alpha = self.alpha * 0.8
        
        dynamic_alpha = max(0.1, min(1.0, dynamic_alpha))
        
        logger.debug(
            "动态调整 alpha",
            original_alpha=self.alpha,
            r_squared=r_squared,
            dynamic_alpha=dynamic_alpha
        )
        
        return dynamic_alpha


def calculate_safety_cushion(
    slope_k: float,
    time_remaining_seconds: float,
    base_cushion: Optional[float] = None,
    alpha: Optional[float] = None,
) -> SafetyCushionResult:
    """
    计算安全垫的便捷函数
    
    Args:
        slope_k: 回归斜率
        time_remaining_seconds: 剩余时间（秒）
        base_cushion: 基础安全垫
        alpha: 价格调整系数
    
    Returns:
        安全垫计算结果
    """
    calculator = SafetyCushionCalculator(base_cushion, alpha)
    return calculator.calculate(slope_k, time_remaining_seconds)
