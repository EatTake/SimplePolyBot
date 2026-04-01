"""
OLS 线性回归模块

使用 NumPy 实现线性回归拟合
计算斜率 K（波动子因子）与决定系数 R²
优化计算性能（目标 < 10ms）
"""

import time
from typing import Tuple, Optional, List
from dataclasses import dataclass

import numpy as np

from shared.logger import get_logger


logger = get_logger(__name__)


@dataclass
class RegressionResult:
    """
    回归分析结果
    
    包含斜率、截距、R² 等统计量
    """
    slope: float
    intercept: float
    r_squared: float
    std_error: float
    sample_count: int
    computation_time_ms: float
    
    def __post_init__(self):
        """验证结果"""
        if self.sample_count < 2:
            raise ValueError(f"样本数量必须 >= 2，当前: {self.sample_count}")
        if self.computation_time_ms < 0:
            raise ValueError(f"计算时间不能为负数: {self.computation_time_ms}")


class OLSRegression:
    """
    OLS 线性回归类
    
    使用普通最小二乘法进行线性回归分析
    针对价格趋势预测进行优化
    """
    
    def __init__(self, min_samples: int = 10):
        """
        初始化 OLS 回归器
        
        Args:
            min_samples: 最小样本数量，少于此数量不进行回归
        """
        self.min_samples = min_samples
        
        logger.info("初始化 OLS 回归器", min_samples=min_samples)
    
    def fit(
        self,
        timestamps: List[float],
        prices: List[float],
    ) -> Optional[RegressionResult]:
        """
        拟合线性回归模型
        
        Args:
            timestamps: 时间戳列表（自变量）
            prices: 价格列表（因变量）
        
        Returns:
            回归结果，如果数据不足则返回 None
        """
        start_time = time.time()
        
        try:
            if len(timestamps) != len(prices):
                raise ValueError(
                    f"时间戳和价格数量不匹配: {len(timestamps)} vs {len(prices)}"
                )
            
            n = len(timestamps)
            
            if n < self.min_samples:
                logger.warn(
                    "样本数量不足，跳过回归",
                    sample_count=n,
                    min_samples=self.min_samples
                )
                return None
            
            x = np.array(timestamps, dtype=np.float64)
            y = np.array(prices, dtype=np.float64)
            
            x_normalized = x - x[0]
            
            slope, intercept, r_squared, std_error = self._ols_fit(x_normalized, y)
            
            computation_time = (time.time() - start_time) * 1000
            
            result = RegressionResult(
                slope=slope,
                intercept=intercept,
                r_squared=r_squared,
                std_error=std_error,
                sample_count=n,
                computation_time_ms=computation_time
            )
            
            logger.debug(
                "回归拟合完成",
                slope=slope,
                r_squared=r_squared,
                sample_count=n,
                computation_time_ms=computation_time
            )
            
            return result
            
        except ValueError as e:
            logger.error("回归拟合失败：数据验证错误", error=str(e))
            return None
        except np.linalg.LinAlgError as e:
            logger.error("回归拟合失败：线性代数错误", error=str(e))
            return None
        except Exception as e:
            logger.error("回归拟合失败：未知错误", error=str(e))
            return None
    
    def _ols_fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[float, float, float, float]:
        """
        OLS 拟合核心算法
        
        使用矩阵运算实现高效计算
        
        Args:
            x: 自变量数组（已归一化）
            y: 因变量数组
        
        Returns:
            (斜率, 截距, R², 标准误差)
        """
        n = len(x)
        
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        x_dev = x - x_mean
        y_dev = y - y_mean
        
        slope = np.sum(x_dev * y_dev) / np.sum(x_dev * x_dev)
        
        intercept = y_mean - slope * x_mean
        
        y_pred = slope * x + intercept
        
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum(y_dev ** 2)
        
        if ss_tot == 0:
            r_squared = 1.0 if ss_res == 0 else 0.0
        else:
            r_squared = 1 - (ss_res / ss_tot)
        
        if n > 2:
            std_error = np.sqrt(ss_res / (n - 2))
        else:
            std_error = 0.0
        
        return float(slope), float(intercept), float(r_squared), float(std_error)
    
    def calculate_trend_strength(self, slope: float, r_squared: float) -> float:
        """
        计算趋势强度
        
        结合斜率和 R² 评估趋势的可靠性
        
        Args:
            slope: 回归斜率
            r_squared: 决定系数
        
        Returns:
            趋势强度值（0-1）
        """
        abs_slope = abs(slope)
        
        slope_factor = min(abs_slope * 1000, 1.0)
        
        trend_strength = slope_factor * r_squared
        
        return float(trend_strength)
    
    def predict_price(
        self,
        slope: float,
        intercept: float,
        future_timestamp: float,
        base_timestamp: float,
    ) -> float:
        """
        预测未来价格
        
        Args:
            slope: 回归斜率
            intercept: 回归截距
            future_timestamp: 未来时间戳
            base_timestamp: 基准时间戳（用于归一化）
        
        Returns:
            预测价格
        """
        normalized_time = future_timestamp - base_timestamp
        predicted_price = slope * normalized_time + intercept
        
        return float(predicted_price)
    
    def calculate_volatility_factor(self, std_error: float, mean_price: float) -> float:
        """
        计算波动率因子
        
        基于标准误差和平均价格计算相对波动率
        
        Args:
            std_error: 回归标准误差
            mean_price: 平均价格
        
        Returns:
            波动率因子
        """
        if mean_price == 0:
            return 0.0
        
        volatility = std_error / mean_price
        
        return float(volatility)


def perform_regression(
    timestamps: List[float],
    prices: List[float],
    min_samples: int = 10,
) -> Optional[RegressionResult]:
    """
    执行线性回归的便捷函数
    
    Args:
        timestamps: 时间戳列表
        prices: 价格列表
        min_samples: 最小样本数量
    
    Returns:
        回归结果
    """
    regressor = OLSRegression(min_samples=min_samples)
    return regressor.fit(timestamps, prices)
