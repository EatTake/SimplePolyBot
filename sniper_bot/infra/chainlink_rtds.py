"""
Chainlink RTDS WebSocket 客户端（裁判轨）

通过 Polymarket Real-Time Data Socket 获取 Chainlink BTC/USD 预言机价格。
这是结算的唯一数据源，所以用它来计算 Δ（偏移量）是最准确的。

连接地址: wss://ws-live-data.polymarket.com
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed


logger = logging.getLogger(__name__)

_RTDS_URL = "wss://ws-live-data.polymarket.com"
_MAX_RECONNECT_DELAY = 30
_INITIAL_RECONNECT_DELAY = 1


class ChainlinkRTDS:
    """
    Polymarket RTDS (Real-Time Data Socket) 客户端

    获取 Chainlink BTC/USD 预言机的实时价格更新
    """

    def __init__(
        self,
        on_price: Callable[[float, float], None],
        url: str = _RTDS_URL,
    ):
        """
        Args:
            on_price: 回调函数 (price, timestamp) → None
            url: RTDS WebSocket URL
        """
        self._on_price = on_price
        self._url = url
        self._running = False
        self._reconnect_delay = _INITIAL_RECONNECT_DELAY

    async def run_forever(self) -> None:
        """永久运行（含自动重连）"""
        self._running = True
        logger.info("Chainlink RTDS 启动: %s", self._url)

        while self._running:
            try:
                await self._connect_and_listen()
                self._reconnect_delay = _INITIAL_RECONNECT_DELAY
            except ConnectionClosed as e:
                logger.warning("RTDS 断开: code=%s", e.code)
            except Exception as e:
                logger.error("RTDS 异常: %s", e)

            if self._running:
                logger.info(
                    "RTDS 将在 %ds 后重连", self._reconnect_delay
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, _MAX_RECONNECT_DELAY
                )

    async def _connect_and_listen(self) -> None:
        """建立连接、订阅并监听"""
        async with websockets.connect(
            self._url,
            ping_interval=15,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            logger.info("RTDS 已连接")
            self._reconnect_delay = _INITIAL_RECONNECT_DELAY

            # 订阅 BTC 价格流
            subscribe_msg = json.dumps({
                "type": "subscribe",
                "channel": "crypto_prices",
                "assets": ["BTC"],
            })
            await ws.send(subscribe_msg)
            logger.info("已订阅 Chainlink BTC/USD 价格流")

            async for raw_msg in ws:
                if not self._running:
                    break
                self._handle_message(raw_msg)

    def _handle_message(self, raw: str) -> None:
        """解析 RTDS 消息"""
        try:
            data = json.loads(raw)

            msg_type = data.get("type", "")

            if msg_type == "crypto_price":
                # 标准价格更新
                price = float(data["price"])
                # RTDS 时间戳可能是毫秒或秒
                ts = data.get("timestamp", time.time())
                if isinstance(ts, (int, float)) and ts > 1e12:
                    ts = ts / 1000.0
                self._on_price(price, ts)

            elif msg_type == "pong":
                # 心跳响应，忽略
                pass

            elif msg_type == "subscription_confirmed":
                logger.info("RTDS 订阅确认: %s", data.get("channel"))

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug("RTDS 消息解析失败: %s", e)

    def stop(self) -> None:
        """停止"""
        self._running = False
        logger.info("RTDS 停止请求已发送")
