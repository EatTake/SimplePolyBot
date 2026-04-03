from __future__ import annotations

"""
信号适配层

桥接策略引擎输出的「分析结论型」信号与订单执行器需要的「执行指令型」信号。
将 (action/direction/confidence/max_buy_price) 转换为 (token_id/market_id/side/size/price)。
"""

import time
import uuid
from typing import Any, Dict, Optional

from shared.logger import get_logger
from shared.models import (
    SignalAction,
    SignalDirection,
    TradingSignal,
)


logger = get_logger(__name__)


DEFAULT_SIZE_MAP: Dict[float, float] = {
    0.8: 200.0,
    0.7: 150.0,
    0.6: 100.0,
    0.5: 50.0,
}


class SignalAdapter:
    """
    信号适配器

    将策略引擎输出的分析结论型信号转换为订单执行器可消费的执行指令型信号。

    映射规则:
        - direction=UP   → side="BUY", outcome="Yes" → 取 UP token_id
        - direction=DOWN → side="BUY", outcome="No"  → 取 DOWN token_id（买 No = 赌下跌）
        - confidence     → size 的映射函数（可配置）
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化信号适配器

        Args:
            config: 可选配置字典，包含 size_map / default_size / min_size / max_size
        """
        if config is None:
            config = {}

        self.size_map: Dict[float, float] = config.get("size_map", DEFAULT_SIZE_MAP.copy())
        self.default_size: float = config.get("default_size", 100.0)
        self.min_size: float = config.get("min_size", 10.0)
        self.max_size: float = config.get("max_size", 500.0)

        logger.info(
            "初始化信号适配器",
            size_map_keys=list(self.size_map.keys()),
            default_size=self.default_size,
            min_size=self.min_size,
            max_size=self.max_size,
        )

    def adapt(
        self,
        strategy_signal: Dict[str, Any],
        market_info: Dict[str, Any],
    ) -> TradingSignal:
        """
        核心转换方法：策略信号 + 市场信息 → 执行指令信号

        Args:
            strategy_signal: 策略引擎输出，包含 action/direction/confidence/max_buy_price 等
            market_info: 来自 MarketDiscovery.get_active_market()，含 tokens 字典

        Returns:
            统一的新格式 TradingSignal（来自 shared.models）
        """
        action_str = strategy_signal.get("action", "WAIT")
        direction_str = strategy_signal.get("direction")
        confidence = strategy_signal.get("confidence", 0.5)
        max_buy_price = strategy_signal.get("max_buy_price", 1.0)

        action = self._parse_action(action_str)
        direction_enum = self._parse_direction(direction_str)

        if action != SignalAction.BUY:
            return TradingSignal(
                signal_id=self._generate_signal_id(),
                token_id="",
                market_id=market_info.get("market_id", ""),
                side="HOLD",
                size=0.0,
                price=0.0,
                action=SignalAction.HOLD,
                confidence=confidence,
                timestamp=time.time(),
                direction=direction_enum,
                metadata={"raw_signal": strategy_signal},
            )

        token_id = self._resolve_token_id(direction_str, market_info)

        if token_id is None:
            logger.warning(
                "无法解析 token_id，降级为 HOLD",
                direction=direction_str,
                market_id=market_info.get("market_id"),
            )
            return TradingSignal(
                signal_id=self._generate_signal_id(),
                token_id="",
                market_id=market_info.get("market_id", ""),
                side="HOLD",
                size=0.0,
                price=0.0,
                action=SignalAction.HOLD,
                confidence=confidence,
                timestamp=time.time(),
                direction=direction_enum,
                metadata={"raw_signal": strategy_signal},
            )

        tokens = market_info.get("tokens", {})
        token_data = tokens.get(direction_str, {}) if isinstance(tokens, dict) else {}
        best_ask = token_data.get("best_ask", max_buy_price)

        price = min(max_buy_price, best_ask)
        size = self._map_confidence_to_size(confidence)

        result = TradingSignal(
            signal_id=self._generate_signal_id(),
            token_id=token_id,
            market_id=market_info.get("market_id", ""),
            side="BUY",
            size=size,
            price=round(price, 4),
            action=SignalAction.BUY,
            confidence=confidence,
            timestamp=time.time(),
            direction=direction_enum,
            metadata={"raw_signal": strategy_signal},
        )

        logger.info(
            "信号适配完成",
            signal_id=result.signal_id,
            action=action_str,
            direction=direction_str,
            side=result.side,
            token_id=token_id,
            size=size,
            price=price,
            confidence=confidence,
        )

        return result

    def _map_confidence_to_size(self, confidence: float) -> float:
        """
        置信度到订单大小的映射

        在 size_map 中查找 <= confidence 的最大阈值对应的大小；
        若无匹配则使用 default_size。结果钳制在 [min_size, max_size] 区间内。

        Args:
            confidence: 置信度值 (0.0 ~ 1.0)

        Returns:
            映射后的订单大小
        """
        sorted_thresholds = sorted(self.size_map.keys(), reverse=True)

        for threshold in sorted_thresholds:
            if confidence >= threshold:
                mapped_size = self.size_map[threshold]
                return max(self.min_size, min(self.max_size, mapped_size))

        size = max(self.min_size, min(self.max_size, self.default_size))
        return size

    def _generate_signal_id(self) -> str:
        """
        生成 UUID 格式的 signal_id

        Returns:
            唯一信号标识符
        """
        return str(uuid.uuid4())

    def _resolve_token_id(
        self,
        direction: Optional[str],
        market_info: Dict[str, Any],
    ) -> Optional[str]:
        """
        解析 token_id

        根据 direction 从 market_info.tokens 中获取对应的 token_id。

        Args:
            direction: 方向 ("UP" 或 "DOWN")
            market_info: 市场信息字典

        Returns:
            对应的 token_id，无法解析时返回 None
        """
        if not direction:
            return None

        tokens = market_info.get("tokens")

        if not tokens or not isinstance(tokens, dict):
            logger.warning(
                "market_info 缺少 tokens 字段或格式异常",
                market_id=market_info.get("market_id"),
            )
            return None

        direction_upper = direction.upper()

        if direction_upper not in tokens:
            logger.warning(
                "tokens 中未找到方向对应的条目",
                direction=direction_upper,
                available_keys=list(tokens.keys()),
            )
            return None

        entry = tokens[direction_upper]

        if isinstance(entry, dict):
            return entry.get("token_id")
        elif isinstance(entry, str):
            return entry

        return None

    @staticmethod
    def _parse_action(action_str: Optional[str]) -> SignalAction:
        """解析动作字符串为枚举"""
        try:
            return SignalAction(action_str.upper()) if action_str else SignalAction.WAIT
        except ValueError:
            return SignalAction.WAIT

    @staticmethod
    def _parse_direction(direction_str: Optional[str]) -> Optional[SignalDirection]:
        """解析方向字符串为枚举"""
        if not direction_str:
            return None
        try:
            return SignalDirection(direction_str.upper())
        except ValueError:
            return None
