"""
异步赎回守护协程

独立于主交易循环运行，定期检查已结算市场并赎回获胜代币。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sniper_bot.infra.gamma_client import GammaClient
from sniper_bot.infra.ctf_client import CTFClient


logger = logging.getLogger(__name__)


class SettlementDaemon:
    """
    赎回守护协程

    每 5 分钟检查一次已完结的市场，
    自动赎回获胜代币为 USDC.e
    """

    def __init__(
        self,
        gamma: GammaClient,
        ctf: CTFClient,
        wallet_address: str,
        check_interval: float = 300.0,
    ):
        self._gamma = gamma
        self._ctf = ctf
        self._wallet = wallet_address
        self._interval = check_interval
        self._running = False

    async def run_forever(self) -> None:
        """永久运行赎回检查"""
        self._running = True
        logger.info("赎回守护协程启动 (间隔 %ds)", self._interval)

        while self._running:
            try:
                await self._check_and_redeem()
            except Exception as e:
                logger.error("赎回检查异常: %s", e)

            await asyncio.sleep(self._interval)

    async def _check_and_redeem(self) -> None:
        """检查并赎回已结算市场"""
        # NOTE: 完整实现需要 Gamma API 的 resolved markets 端点
        # 此处提供框架，具体 API 字段需根据实际响应适配
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://gamma-api.polymarket.com/events",
                    params={
                        "tag": "crypto",
                        "active": "false",
                        "closed": "true",
                        "limit": 20,
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                events = resp.json()

            for event in events:
                title = event.get("title", "").lower()
                if "bitcoin" not in title or "5 minute" not in title:
                    continue

                condition_id = event.get("conditionId", "")
                if not condition_id:
                    continue

                # 检查是否已赎回（简化逻辑）
                # 完整实现需查询用户在该市场的持仓
                result = await self._ctf.redeem(
                    condition_id=condition_id,
                    amounts=[1, 1],
                )

                if result.usdc_received > 0:
                    logger.info(
                        "成功赎回 $%.2f 从 %s",
                        result.usdc_received, condition_id[:16],
                    )

        except Exception as e:
            logger.debug("赎回检查: %s", e)

    def stop(self) -> None:
        self._running = False
