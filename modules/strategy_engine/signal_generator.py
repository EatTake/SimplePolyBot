"""
买入信号生成器模块

实现差额计算、方向判断、信号触发条件判断
支持时间窗口判断（T-100s 至 T-10s）和最大买入价格查表
"""

import time
import math
from typing import Optional

from shared.logger import get_logger
from shared.config import Config
from shared.models import TradingSignal, SignalAction, SignalDirection, generate_signal_id
from modules.strategy_engine.safety_cushion import SafetyCushionCalculator, SafetyCushionResult


logger = get_logger(__name__)


def _sigmoid(x: float) -> float:
    """Sigmoid 函数，将任意值映射到 (0, 1)
    
    使用数值稳定的实现，防止 math.exp 溢出：
    - 当 x > 500 时直接返回 1.0（避免 exp(-x) 下溢）
    - 当 x < -500 时直接返回 0.0（避免 exp(-x) 上溢）
    
    Args:
        x: 输入值（任意实数）
    
    Returns:
        映射后的值，范围 (0, 1)
    """
    if x > 500:
        return 1.0
    if x < -500:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


class SignalGenerator:
    """
    买入信号生成器
    
    根据价格差额、趋势方向、安全垫等条件生成交易信号
    """
    
    def __init__(
        self,
        min_time_remaining: float = 10.0,
        max_time_remaining: float = 100.0,
        min_price_difference: float = 0.01,
        min_r_squared: float = 0.5,
        min_confidence: float = 0.6,
    ):
        """
        初始化信号生成器
        
        Args:
            min_time_remaining: 最小剩余时间（秒），默认 10 秒
            max_time_remaining: 最大剩余时间（秒），默认 100 秒
            min_price_difference: 最小价格差额，默认 0.01
            min_r_squared: 最小 R² 值，默认 0.5
            min_confidence: 最小置信度，默认 0.6
        """
        self.min_time_remaining = min_time_remaining
        self.max_time_remaining = max_time_remaining
        self.min_price_difference = min_price_difference
        self.min_r_squared = min_r_squared
        self.min_confidence = min_confidence
        
        config = Config.get_instance()
        try:
            strategy_config = config.get_strategy_config()
            self.max_buy_prices = strategy_config.max_buy_prices
        except Exception:
            self.max_buy_prices = {
                "default": 0.95,
                "high_confidence": 0.98,
                "low_volatility": 0.92,
                "fast_market": 0.90
            }
        
        self.safety_cushion_calculator = SafetyCushionCalculator()
        
        logger.info(
            "初始化信号生成器",
            min_time_remaining=min_time_remaining,
            max_time_remaining=max_time_remaining,
            min_price_difference=min_price_difference
        )
    
    def generate_signal(
        self,
        current_price: float,
        start_price: float,
        slope_k: float,
        r_squared: float,
        time_remaining: float,
        market_best_ask: float = 0.50,
    ) -> TradingSignal:
        """
        生成交易信号
        
        Args:
            current_price: 当前价格（BTC 绝对价格）
            start_price: 周期起始价格（BTC 绝对价格）
            slope_k: 回归斜率
            r_squared: 决定系数
            time_remaining: 剩余时间（秒）
            market_best_ask: Polymarket 合约最佳卖价（概率空间 0-1），默认 0.50
        
        Returns:
            交易信号
        """
        timestamp = time.time()
        
        price_difference = self.calculate_price_difference(current_price, start_price)
        
        direction = self.determine_direction(current_price - start_price)
        
        safety_cushion_result = self.safety_cushion_calculator.calculate(
            slope_k, time_remaining
        )
        
        max_buy_price = self.calculate_max_buy_price(
            market_best_ask=market_best_ask,
            safety_cushion=safety_cushion_result.total_cushion,
            time_remaining=time_remaining,
        )
        
        confidence = self.calculate_confidence(r_squared, abs(slope_k), price_difference)
        
        action = self.determine_action(
            price_difference=price_difference,
            time_remaining=time_remaining,
            r_squared=r_squared,
            confidence=confidence,
            max_buy_price=max_buy_price,
            safety_cushion=safety_cushion_result.total_cushion,
        )
        
        signal = TradingSignal(
            signal_id=generate_signal_id(),
            token_id="",
            market_id="",
            side="BUY" if direction else "HOLD",
            size=0.0,
            price=max_buy_price,
            action=action,
            confidence=confidence,
            timestamp=timestamp,
            strategy="fast_market",
            direction=direction if action == SignalAction.BUY else None,
            current_price=current_price,
            start_price=start_price,
            price_difference=price_difference,
            max_buy_price=max_buy_price,
            safety_cushion=safety_cushion_result.total_cushion,
            slope_k=slope_k,
            r_squared=r_squared,
            time_remaining=time_remaining,
        )
        
        logger.info(
            "生成交易信号",
            action=action.value,
            direction=direction.value if direction else None,
            price_difference=price_difference,
            time_remaining=time_remaining,
            confidence=confidence
        )
        
        return signal
    
    def calculate_price_difference(
        self,
        current_price: float,
        start_price: float,
    ) -> float:
        """
        计算价格差额
        
        Args:
            current_price: 当前价格
            start_price: 起始价格
        
        Returns:
            价格差额（绝对值）
        """
        difference = abs(current_price - start_price)
        
        logger.debug(
            "计算价格差额",
            current_price=current_price,
            start_price=start_price,
            difference=difference
        )
        
        return difference
    
    def determine_direction(self, price_difference: float) -> Optional[SignalDirection]:
        """
        判断价格方向
        
        Args:
            price_difference: 价格差额（可正可负）
        
        Returns:
            价格方向（UP 或 DOWN），如果差额为0则返回 None
        """
        if price_difference > 0:
            return SignalDirection.UP
        elif price_difference < 0:
            return SignalDirection.DOWN
        else:
            return None
    
    def determine_action(
        self,
        price_difference: float,
        time_remaining: float,
        r_squared: float,
        confidence: float,
        max_buy_price: float,
        safety_cushion: float = 0.0,
    ) -> SignalAction:
        """
        判断信号动作
        
        Args:
            price_difference: 价格差额（BTC 绝对价格空间）
            time_remaining: 剩余时间
            r_squared: R² 值
            confidence: 置信度
            max_buy_price: 最大买入价格（概率空间）
            safety_cushion: 安全垫（概率空间），默认 0.0
        
        Returns:
            信号动作
        """
        if not self.is_in_time_window(time_remaining):
            logger.debug(
                "不在时间窗口内",
                time_remaining=time_remaining,
                min_time=self.min_time_remaining,
                max_time=self.max_time_remaining
            )
            return SignalAction.WAIT
        
        if price_difference < self.min_price_difference:
            logger.debug(
                "价格差额不足",
                price_difference=price_difference,
                min_difference=self.min_price_difference
            )
            return SignalAction.WAIT
        
        if r_squared < self.min_r_squared:
            logger.debug(
                "R² 值不足",
                r_squared=r_squared,
                min_r_squared=self.min_r_squared
            )
            return SignalAction.WAIT
        
        if confidence < self.min_confidence:
            logger.debug(
                "置信度不足",
                confidence=confidence,
                min_confidence=self.min_confidence
            )
            return SignalAction.WAIT
        
        if max_buy_price > self.get_max_buy_price_limit(time_remaining, confidence):
            logger.debug(
                "最大买入价格超限",
                max_buy_price=max_buy_price,
                limit=self.get_max_buy_price_limit(time_remaining, confidence),
                time_remaining=time_remaining,
                confidence=confidence
            )
            return SignalAction.WAIT
        
        if price_difference < safety_cushion:
            logger.debug(
                "价格差额未超过安全垫（Bug #3 修复）",
                price_difference=price_difference,
                safety_cushion=safety_cushion
            )
            return SignalAction.WAIT
        
        return SignalAction.BUY
    
    def is_in_time_window(self, time_remaining: float) -> bool:
        """
        检查是否在有效时间窗口内
        
        Args:
            time_remaining: 剩余时间（秒）
        
        Returns:
            是否在时间窗口内
        """
        return self.min_time_remaining <= time_remaining <= self.max_time_remaining
    
    def time_decay_factor(self, time_remaining: float) -> float:
        """
        时间衰减因子：剩余时间越短，衰减越大（更保守）
        
        公式: decay = 0.5 + 0.5 * (time_remaining / FAST_MARKET_DURATION)
        - time_remaining=300s(刚开始) → decay≈1.0（激进）
        - time_remaining=10s(快结束) → decay≈0.52（保守）
        
        Args:
            time_remaining: 剩余时间（秒）
        
        Returns:
            衰减因子，范围 [0.5, 1.0]
        """
        from shared.constants import FAST_MARKET_DURATION_SECONDS
        
        ratio = max(0, min(1, time_remaining / FAST_MARKET_DURATION_SECONDS))
        return 0.5 + 0.5 * ratio
    
    def calculate_max_buy_price(
        self,
        market_best_ask: float,
        safety_cushion: float,
        time_remaining: float = 100.0,
    ) -> float:
        """
        计算最大买入价格（概率空间）
        
        新公式: max_buy = best_ask × (1 - cushion) × decay_factor
        
        所有量纲均为概率空间（0-1范围），不再混入 BTC 绝对价格
        
        Args:
            market_best_ask: Polymarket 合约最佳卖价（概率空间 0-1）
            safety_cushion: 安全垫（概率空间）
            time_remaining: 剩余时间（秒），默认 100.0
        
        Returns:
            最大买入价格（概率空间 0-1）
        """
        decay = self.time_decay_factor(time_remaining)
        
        cushion_adjusted = max(0.01, 1.0 - safety_cushion)
        
        max_buy = market_best_ask * cushion_adjusted * decay
        
        max_buy = max(0.01, min(0.99, max_buy))
        
        logger.debug(
            "计算最大买入价格（概率空间）",
            market_best_ask=market_best_ask,
            safety_cushion=safety_cushion,
            time_remaining=time_remaining,
            decay_factor=decay,
            cushion_adjusted=cushion_adjusted,
            max_buy_price=max_buy
        )
        
        return max_buy
    
    def get_max_buy_price_limit(
        self,
        time_remaining: float,
        confidence: Optional[float] = None,
    ) -> float:
        """
        根据剩余时间获取最大买入价格限制（Bug #7 修复：时间驱动）

        设计理念：
            Fast Market（如 Bitcoin Up or Down - 5 Minutes）的核心特征是时间敏感性。
            剩余时间越短，市场确定性越高（Chainlink Oracle 价格已基本确定），
            因此应该允许更高的买入价格以捕捉最后的机会。

            时间阶梯设计：
                - >80s (充足时间): base_limit=0.75
                  市场刚开始，价格波动大，不确定性高，保守入场避免追高
                - >40s (中间阶段): base_limit=0.85
                  趋势逐渐明朗，可以适当提高入场价格
                - >15s (接近结束): base_limit=0.90
                  价格方向基本确定，允许较高价格入场
                - ≤15s (最后时刻): base_limit=0.93
                  最后时刻，即使高价也值得追入，因为结果几乎确定

        Args:
            time_remaining: 剩余时间（秒），主驱动参数
            confidence: 置信度（可选），用于微调 ±0.02

        Returns:
            最大买入价格限制，范围 [0.60, 0.98]
        """
        if time_remaining > 80:
            base_limit = 0.75
        elif time_remaining > 40:
            base_limit = 0.85
        elif time_remaining > 15:
            base_limit = 0.90
        else:
            base_limit = 0.93

        if confidence is not None:
            if confidence >= 0.8:
                adjustment = 0.02
            elif confidence < 0.5:
                adjustment = -0.02
            else:
                adjustment = 0.0
            base_limit += adjustment

        return max(0.60, min(0.98, base_limit))
    
    def calculate_confidence(
        self,
        r_squared: float,
        abs_slope: float,
        price_difference: float,
    ) -> float:
        """计算信号置信度（Bug #4 修复版：使用 Sigmoid 归一化）
        
        综合考虑 R²、斜率和价格差额，使用 Sigmoid 函数进行归一化，
        确保典型 BTC 市场数据不会导致归一化系数饱和到 1.0。
        
        权重分配：
            - r_squared_weight = 0.5: R² 是拟合质量的核心指标，占主导地位
            - slope_weight = 0.3: 斜率反映趋势强度
            - difference_weight = 0.2: 价格差额反映波动幅度
        
        Sigmoid 参数选择理由：
            
            normalized_slope 使用 _sigmoid(50 * (abs_slope - 0.002))：
                - 典型 abs_slope 范围 [0.0005, 0.005]（BTC 5分钟窗口线性回归斜率）
                - 中心点选为 0.002，使典型值落在 Sigmoid 的线性敏感区 [0.3, 0.7]
                - 缩放因子 50 控制曲线陡峭度：±0.01 偏移产生约 ±0.25 的输出变化
                    * abs_slope=0.001 → 50*(0.001-0.002)=-0.05 → sigmoid≈0.49 (略低于中心)
                    * abs_slope=0.002 → 50*(0.002-0.002)=0   → sigmoid=0.50 (中心点)
                    * abs_slope=0.003 → 50*(0.003-0.002)=+0.05→ sigmoid≈0.51 (略高于中心)
            
            normalized_difference 使用 _sigmoid(0.02 * (price_difference - 50))：
                - 典型 price_difference(BTC) 范围 [10, 200]（5分钟内价格变动）
                - 中心点选为 50 USD，覆盖大部分正常市场波动场景
                - 缩放因子 0.02 使 ±50 USD 偏移产生约 ±0.5 的输出变化
                    * diff=20   → 0.02*(20-50)=-0.6   → sigmoid≈0.35 (低波动)
                    * diff=50   → 0.02*(50-50)=0      → sigmoid=0.50 (中等波动)
                    * diff=100  → 0.02*(100-50)=+1.0  → sigmoid≈0.73 (高波动)
                    * diff=200  → 0.02*(200-50)=+3.0  → sigmoid≈0.95 (极端波动)
        
        Args:
            r_squared: 决定系数，范围 [0, 1]
            abs_slope: 斜率绝对值（BTC 典型值 ~0.001-0.005）
            price_difference: 价格差额（BTC 典型值 ~10-200 USD）
        
        Returns:
            置信度，范围 [0, 1]
        """
        r_squared_weight = 0.5
        slope_weight = 0.3
        difference_weight = 0.2
        
        # Sigmoid 归一化：参数选择使典型 BTC 数据落在 [0.3, 0.7] 敏感区间
        # abs_slope 中心点 0.002，缩放因子 50
        normalized_slope = _sigmoid(50 * (abs_slope - 0.002))
        
        # price_difference 中心点 50 USD，缩放因子 0.02
        normalized_difference = _sigmoid(0.02 * (price_difference - 50))
        
        confidence = (
            r_squared * r_squared_weight +
            normalized_slope * slope_weight +
            normalized_difference * difference_weight
        )
        
        return max(0.0, min(1.0, confidence))


def generate_trading_signal(
    current_price: float,
    start_price: float,
    slope_k: float,
    r_squared: float,
    time_remaining: float,
) -> TradingSignal:
    """
    生成交易信号的便捷函数
    
    Args:
        current_price: 当前价格
        start_price: 起始价格
        slope_k: 回归斜率
        r_squared: 决定系数
        time_remaining: 剩余时间
    
    Returns:
        交易信号
    """
    generator = SignalGenerator()
    return generator.generate_signal(
        current_price, start_price, slope_k, r_squared, time_remaining
    )
