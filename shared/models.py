from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger()


class SignalAction(Enum):
    BUY = "BUY"
    WAIT = "WAIT"
    HOLD = "HOLD"


class SignalDirection(Enum):
    UP = "UP"
    DOWN = "DOWN"


def generate_signal_id() -> str:
    return str(uuid.uuid4())


@dataclass
class TradingSignal:
    signal_id: str
    token_id: str
    market_id: str
    side: str
    size: float
    price: float
    action: SignalAction
    confidence: float
    timestamp: float
    strategy: str = "fast_market"
    direction: Optional[SignalDirection] = None
    current_price: float = 0.0
    start_price: float = 0.0
    price_difference: float = 0.0
    max_buy_price: float = 0.0
    safety_cushion: float = 0.0
    slope_k: float = 0.0
    r_squared: float = 0.0
    time_remaining: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "token_id": self.token_id,
            "market_id": self.market_id,
            "side": self.side,
            "size": self.size,
            "price": self.price,
            "action": self.action.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "strategy": self.strategy,
            "direction": self.direction.value if self.direction else None,
            "current_price": self.current_price,
            "start_price": self.start_price,
            "price_difference": self.price_difference,
            "max_buy_price": self.max_buy_price,
            "safety_cushion": self.safety_cushion,
            "slope_k": self.slope_k,
            "r_squared": self.r_squared,
            "time_remaining": self.time_remaining,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TradingSignal:
        action_str = data.get("action", "WAIT")
        try:
            action = SignalAction(action_str)
        except ValueError:
            action = SignalAction.WAIT

        direction_str = data.get("direction")
        direction = None
        if direction_str:
            try:
                direction = SignalDirection(direction_str)
            except ValueError:
                pass

        return cls(
            signal_id=data.get("signal_id", ""),
            token_id=data.get("token_id", ""),
            market_id=data.get("market_id", ""),
            side=data.get("side", "BUY"),
            size=float(data.get("size", 0)),
            price=float(data.get("price", 0)),
            action=action,
            confidence=float(data.get("confidence", 0.0)),
            timestamp=float(data.get("timestamp", time.time())),
            strategy=data.get("strategy", "fast_market"),
            direction=direction,
            current_price=float(data.get("current_price", 0)),
            start_price=float(data.get("start_price", 0)),
            price_difference=float(data.get("price_difference", 0)),
            max_buy_price=float(data.get("max_buy_price", 0)),
            safety_cushion=float(data.get("safety_cushion", 0)),
            slope_k=float(data.get("slope_k", 0)),
            r_squared=float(data.get("r_squared", 0)),
            time_remaining=float(data.get("time_remaining", 0)),
            metadata=data.get("metadata", {}),
        )

    def validate(self) -> bool:
        if not self.token_id:
            logger.warning("信号缺少 token_id", signal_id=self.signal_id)
            return False

        if self.side not in ("BUY", "SELL"):
            logger.warning(
                "信号方向无效",
                signal_id=self.signal_id,
                side=self.side,
            )
            return False

        if self.size <= 0:
            logger.warning(
                "信号数量无效",
                signal_id=self.signal_id,
                size=self.size,
            )
            return False

        if not (0 <= self.confidence <= 1):
            logger.warning(
                "信号置信度无效",
                signal_id=self.signal_id,
                confidence=self.confidence,
            )
            return False

        if not (0 < self.price < 1):
            logger.warning(
                "信号价格超出范围",
                signal_id=self.signal_id,
                price=self.price,
            )
            return False

        return True

    def __repr__(self) -> str:
        return (
            f"TradingSignal(signal_id={self.signal_id}, "
            f"token_id={self.token_id}, "
            f"side={self.side}, "
            f"price={self.price}, "
            f"size={self.size}, "
            f"confidence={self.confidence})"
        )
