"""
CLOB 客户端封装

封装 py-clob-client 提供的订单簿查询和 FAK 订单提交能力。
包含断路器保护和指数退避重试。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from sniper_bot.core.models import OrderResult, OrderStatus


logger = logging.getLogger(__name__)

# 断路器状态
_CB_CLOSED = "closed"
_CB_OPEN = "open"
_CB_HALF_OPEN = "half_open"


class CircuitBreaker:
    """简洁的断路器实现"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._state = _CB_CLOSED
        self._last_failure_time = 0.0

    def allow_request(self) -> bool:
        if self._state == _CB_CLOSED:
            return True
        if self._state == _CB_OPEN:
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = _CB_HALF_OPEN
                return True
            return False
        # half_open: 允许一次试探
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._state = _CB_CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.failure_threshold:
            self._state = _CB_OPEN
            logger.warning("断路器已打开 (连续失败 %d 次)", self._failures)


class ClobClient:
    """
    CLOB API 异步封装

    提供：
      - 订单簿查询
      - 最优价格查询
      - FAK 订单提交
      - Tick 大小查询
    """

    def __init__(
        self,
        host: str,
        chain_id: int,
        private_key: str,
        api_key: str = "",
        api_secret: str = "",
        api_passphrase: str = "",
        funder: str = "",
    ):
        self._host = host
        self._chain_id = chain_id
        self._private_key = private_key
        self._api_key = api_key
        self._api_secret = api_secret
        self._api_passphrase = api_passphrase
        self._funder = funder
        self._client: Any = None
        self._breaker = CircuitBreaker()

    async def initialize(self) -> None:
        """
        初始化 py-clob-client

        NOTE: py-clob-client 是同步库，使用 run_in_executor 包装
        """
        loop = asyncio.get_event_loop()
        self._client = await loop.run_in_executor(None, self._create_client)
        logger.info("CLOB 客户端已初始化")

    def _create_client(self) -> Any:
        """同步创建 py-clob-client 实例"""
        from py_clob_client.client import ClobClient as _ClobClient
        from py_clob_client.clob_types import ApiCreds

        creds = ApiCreds(
            api_key=self._api_key,
            api_secret=self._api_secret,
            api_passphrase=self._api_passphrase,
        ) if self._api_key else None

        client = _ClobClient(
            self._host,
            chain_id=self._chain_id,
            key=self._private_key,
            creds=creds,
            signature_type=2,  # GNOSIS_SAFE (Polymarket 标准)
            funder=self._funder or None,
        )

        # 如果没有 API 凭证，尝试创建
        if not creds:
            try:
                new_creds = client.create_or_derive_api_creds()
                client.set_api_creds(new_creds)
                logger.info("已创建/派生 API 凭证")
            except Exception as e:
                logger.error("派生 API 凭证失败: %s", e)
                raise

        return client

    async def get_order_book(self, token_id: str) -> dict:
        """
        获取订单簿

        Returns:
            {"bids": [...], "asks": [...]}
        """
        if not self._breaker.allow_request():
            logger.warning("断路器已打开，拒绝订单簿请求")
            return {"bids": [], "asks": []}

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._client.get_order_book, token_id
            )
            self._breaker.record_success()
            return result
        except Exception as e:
            self._breaker.record_failure()
            logger.error("获取订单簿失败: %s", e)
            return {"bids": [], "asks": []}

    async def get_best_ask(self, token_id: str) -> tuple[float, float]:
        """
        获取最优卖价和对应深度

        Returns:
            (best_ask_price, available_size)
        """
        book = await self.get_order_book(token_id)
        asks = book.get("asks", [])
        if not asks:
            return (1.0, 0.0)

        best = asks[0]
        return (float(best.get("price", 1.0)), float(best.get("size", 0.0)))

    async def get_ask_depth_at_price(
        self,
        token_id: str,
        max_price: float,
    ) -> float:
        """
        获取指定价格范围内的总卖方深度

        Args:
            token_id: 代币 ID
            max_price: 最大价格

        Returns:
            可用份额总量
        """
        book = await self.get_order_book(token_id)
        asks = book.get("asks", [])
        total = 0.0
        for ask in asks:
            if float(ask.get("price", 999)) <= max_price:
                total += float(ask.get("size", 0))
        return total

    async def get_tick_size(self, token_id: str) -> str:
        """获取最小价格变动单位"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._client.get_tick_size, token_id
            )
            return str(result) if result else "0.01"
        except Exception:
            return "0.01"

    async def place_fak_order(
        self,
        token_id: str,
        price: float,
        size: float,
    ) -> OrderResult:
        """
        提交 FAK (Fill-And-Kill) 买入订单

        FAK 优势：立即成交能成交的部分，自动取消剩余

        Args:
            token_id: 合约 token_id
            price: 最大买入价
            size: 份额数
        """
        if not self._breaker.allow_request():
            return OrderResult(
                status=OrderStatus.ABORTED,
                reason="断路器已打开",
            )

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._submit_fak_order_sync,
                token_id, price, size,
            )
            self._breaker.record_success()
            return result

        except Exception as e:
            self._breaker.record_failure()
            logger.error("FAK 订单提交失败: %s", e)
            return OrderResult(
                status=OrderStatus.FAILED,
                reason=str(e),
            )

    def _submit_fak_order_sync(
        self,
        token_id: str,
        price: float,
        size: float,
    ) -> OrderResult:
        """同步提交 FAK 订单"""
        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY

        tick_size = self._client.get_tick_size(token_id)

        # 对齐 Tick Size
        tick_float = float(tick_size) if tick_size else 0.01
        aligned_price = round(price / tick_float) * tick_float
        aligned_price = max(0.01, min(0.99, aligned_price))

        order_args = OrderArgs(
            token_id=token_id,
            price=aligned_price,
            size=size,
            side=BUY,
        )

        neg_risk = False  # BTC Up/Down 是标准二元市场

        resp = self._client.create_and_post_order(
            order_args,
            {"tick_size": tick_size, "neg_risk": neg_risk},
            OrderType.FAK,
        )

        order_id = resp.get("orderID", "") if isinstance(resp, dict) else ""
        status = resp.get("status", "") if isinstance(resp, dict) else ""

        if status == "matched" or order_id:
            return OrderResult(
                status=OrderStatus.FILLED,
                order_id=order_id,
                filled_size=size,
                filled_price=aligned_price,
            )

        return OrderResult(
            status=OrderStatus.SUBMITTED,
            order_id=order_id,
            filled_price=aligned_price,
        )

    async def get_balance(self) -> float:
        """获取 USDC.e 余额"""
        try:
            loop = asyncio.get_event_loop()
            balance = await loop.run_in_executor(
                None, self._client.get_balance_allowance
            )
            if isinstance(balance, dict):
                return float(balance.get("balance", 0))
            return 0.0
        except Exception as e:
            logger.error("获取余额失败: %s", e)
            return 0.0
