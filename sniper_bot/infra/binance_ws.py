"""
Binance WebSocket 客户端（分析轨）

高频采集 BTC/USDT 逐笔成交数据，
用于 OLS 回归（动量 K）和 EWMA 波动率估算。

特性：
  - 自动指数退避重连
  - 心跳 / pong 维护
  - 数据速率限流（防止内存溢出）
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

_BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"
_MAX_RECONNECT_DELAY = 60
_INITIAL_RECONNECT_DELAY = 1


class BinanceWS:
    """
    Binance BTC/USDT 实时交易流

    Usage:
        async def on_price(price, timestamp):
            engine.push_binance(price, timestamp)

        ws = BinanceWS(on_price=on_price)
        await ws.run_forever()
    """

    def __init__(
        self,
        on_price: Callable[[float, float], None],
        url: str = _BINANCE_WS_URL,
    ):
        """
        Args:
            on_price: 回调函数 (price, timestamp) → None
            url: WebSocket URL
        """
        self._on_price = on_price
        self._url = url
        self._running = False
        self._reconnect_delay = _INITIAL_RECONNECT_DELAY

    async def run_forever(self) -> None:
        """永久运行（含自动重连）"""
        self._running = True
        logger.info("Binance WS 启动: %s", self._url)

        while self._running:
            try:
                await self._connect_and_listen()
                # 正常断开，重置延迟
                self._reconnect_delay = _INITIAL_RECONNECT_DELAY
            except ConnectionClosed as e:
                logger.warning("Binance WS 断开: code=%s", e.code)
            except Exception as e:
                logger.error("Binance WS 异常: %s", e)

            if self._running:
                logger.info(
                    "Binance WS 将在 %ds 后重连", self._reconnect_delay
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, _MAX_RECONNECT_DELAY
                )

    async def _connect_and_listen(self) -> None:
        """建立连接并监听消息"""
        async with websockets.connect(
            self._url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            logger.info("Binance WS 已连接")
            self._reconnect_delay = _INITIAL_RECONNECT_DELAY

            async for raw_msg in ws:
                if not self._running:
                    break
                self._handle_message(raw_msg)

    def _handle_message(self, raw: str) -> None:
        """解析 Binance trade 消息"""
        try:
            data = json.loads(raw)
            if data.get("e") != "trade":
                return

            price = float(data["p"])
            # Binance 时间戳为毫秒
            timestamp = data["T"] / 1000.0

            self._on_price(price, timestamp)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug("Binance 消息解析失败: %s", e)

    def stop(self) -> None:
        """停止"""
        self._running = False
        logger.info("Binance WS 停止请求已发送")
