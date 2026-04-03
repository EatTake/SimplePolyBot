from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from shared.constants import TRADE_RESULT_CHANNEL
from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    token_id: str
    market_id: str
    side: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    opened_at: float = 0.0
    updated_at: float = 0.0


class PositionTracker:
    def __init__(self, redis_client=None):
        self._positions: Dict[str, Position] = {}
        self._redis_client = redis_client
        self._lock = threading.Lock()
        self._subscriber_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def update_from_trade_result(self, result: Dict) -> None:
        with self._lock:
            token_id = result.get("token_id")
            if not token_id:
                logger.warning("交易结果缺少 token_id", trade_result=result)
                return

            status = result.get("status")
            if status not in ("MATCHED", "CONFIRMED", "MINED"):
                logger.debug(
                    "交易未成功，跳过持仓更新",
                    token_id=token_id,
                    status=status,
                )
                return

            side = result.get("side", "")
            filled_size = float(result.get("filled_size", 0))
            price = float(result.get("price", 0))
            market_id = result.get("market_id", "")
            now = time.time()

            if side == "BUY":
                self._handle_buy(token_id, market_id, filled_size, price, now)
            elif side == "SELL":
                self._handle_sell(token_id, filled_size, price, now)
            else:
                logger.warning(
                    "未知交易方向", token_id=token_id, side=side
                )

    def _handle_buy(
        self,
        token_id: str,
        market_id: str,
        quantity: float,
        price: float,
        now: float,
    ) -> None:
        existing = self._positions.get(token_id)

        if existing and existing.quantity > 0:
            total_cost = existing.avg_cost * existing.quantity + price * quantity
            new_quantity = existing.quantity + quantity
            existing.avg_cost = total_cost / new_quantity if new_quantity > 0 else 0.0
            existing.quantity = new_quantity
            existing.updated_at = now
            logger.info(
                "加仓更新",
                token_id=token_id,
                added_qty=quantity,
                new_total_qty=existing.quantity,
                new_avg_cost=existing.avg_cost,
            )
        else:
            self._positions[token_id] = Position(
                token_id=token_id,
                market_id=market_id,
                side="BUY",
                quantity=quantity,
                avg_cost=price,
                opened_at=now,
                updated_at=now,
            )
            logger.info(
                "新建多头持仓",
                token_id=token_id,
                quantity=quantity,
                avg_cost=price,
            )

    def _handle_sell(
        self,
        token_id: str,
        quantity: float,
        price: float,
        now: float,
    ) -> None:
        existing = self._positions.get(token_id)

        if not existing or existing.quantity <= 0:
            logger.warning(
                "卖出时无对应持仓", token_id=token_id, sell_qty=quantity
            )
            return

        realized = (price - existing.avg_cost) * min(quantity, existing.quantity)
        existing.realized_pnl += realized
        existing.quantity -= quantity
        existing.updated_at = now

        if existing.quantity <= 1e-9:
            closed = self._positions.pop(token_id, None)
            logger.info(
                "持仓平仓",
                token_id=token_id,
                realized_pnl=closed.realized_pnl if closed else realized,
            )
        else:
            logger.info(
                "减仓",
                token_id=token_id,
                sold_qty=quantity,
                remaining_qty=existing.quantity,
                realized_pnl_this_trade=realized,
                cumulative_realized_pnl=existing.realized_pnl,
            )

    def get_open_positions(self) -> List[Position]:
        with self._lock:
            return [p for p in self._positions.values() if p.quantity > 1e-9]

    def get_position(self, token_id: str) -> Optional[Position]:
        with self._lock:
            pos = self._positions.get(token_id)
            if pos and pos.quantity <= 1e-9:
                return None
            return pos

    def get_total_exposure(self) -> float:
        with self._lock:
            return sum(
                p.quantity * p.current_price
                for p in self._positions.values()
                if p.quantity > 1e-9
            )

    def get_daily_pnl(self) -> float:
        with self._lock:
            now = time.time()
            start_of_day = now - (now % 86400)
            daily_total = 0.0
            for p in self._positions.values():
                if p.opened_at >= start_of_day:
                    unrealized = self.calculate_unrealized_pnl(p)
                    daily_total += p.realized_pnl + unrealized
            return daily_total

    def update_prices(self, price_feed: Dict[str, float]) -> None:
        with self._lock:
            updated_count = 0
            for token_id, price in price_feed.items():
                pos = self._positions.get(token_id)
                if pos and pos.quantity > 1e-9:
                    pos.current_price = price
                    pos.unrealized_pnl = self.calculate_unrealized_pnl(pos)
                    updated_count += 1
            if updated_count > 0:
                logger.debug(
                    "批量价格更新",
                    updated_count=updated_count,
                    total_tokens=len(price_feed),
                )

    def calculate_unrealized_pnl(self, position: Position) -> float:
        if position.side == "BUY":
            return (position.current_price - position.avg_cost) * position.quantity
        return (position.avg_cost - position.current_price) * position.quantity

    def close_position(self, token_id: str) -> Optional[Position]:
        with self._lock:
            pos = self._positions.pop(token_id, None)
            if pos:
                logger.info(
                    "手动平仓",
                    token_id=token_id,
                    quantity=pos.quantity,
                    realized_pnl=pos.realized_pnl,
                )
            return pos

    def subscribe_to_trade_results(self, redis_client=None) -> None:
        client = redis_client or self._redis_client
        if client is None:
            raise ValueError("Redis 客户端不可用，无法订阅")

        self._stop_event.clear()
        pubsub = client.pubsub()
        pubsub.subscribe(TRADE_RESULT_CHANNEL)

        def _listen():
            logger.info(
                "开始订阅交易结果频道",
                channel=TRADE_RESULT_CHANNEL,
            )
            while not self._stop_event.is_set():
                try:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            self._handle_trade_result(data)
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.error(
                                "解析交易结果消息失败",
                                error=str(e),
                                raw_message=message.get("data"),
                            )
                except Exception as e:
                    if not self._stop_event.is_set():
                        logger.error(
                            "Redis 订阅异常",
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        time.sleep(1.0)

            pubsub.unsubscribe(TRADE_RESULT_CHANNEL)
            pubsub.close()
            logger.info("已停止订阅交易结果频道", channel=TRADE_RESULT_CHANNEL)

        self._subscriber_thread = threading.Thread(target=_listen, daemon=True)
        self._subscriber_thread.start()

    def unsubscribe(self) -> None:
        self._stop_event.set()
        if self._subscriber_thread and self._subscriber_thread.is_alive():
            self._subscriber_thread.join(timeout=5.0)
        logger.info("已取消交易结果订阅")

    def _handle_trade_result(self, data: Dict) -> None:
        try:
            result = data if isinstance(data, dict) else json.loads(data)
            self.update_from_trade_result(result)
        except Exception as e:
            logger.error(
                "处理交易结果回调失败",
                error=str(e),
                error_type=type(e).__name__,
                data=data,
            )
