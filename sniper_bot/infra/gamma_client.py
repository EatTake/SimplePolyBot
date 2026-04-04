"""
Gamma API 客户端 — 市场发现

通过 Gamma API 自动发现当前活跃的 "Bitcoin Up or Down - 5 Minutes" 市场，
获取 Up/Down 代币的 token_id 和 condition_id。

这是 SimplePolyBot 完全缺失的环节 — 没有市场发现，策略引擎不知道买哪个合约。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from sniper_bot.core.models import FastMarket


@dataclass
class MarketDiscoveryResult:
    """市场发现结果，包含交易状态"""
    market: FastMarket
    accepting_orders: bool = False
    closed: bool = False
    slug: str = ""


logger = logging.getLogger(__name__)

_GAMMA_URL = "https://gamma-api.polymarket.com"
_REQUEST_TIMEOUT = 10.0


class GammaClient:
    """
    Gamma API 异步客户端

    核心方法：find_active_btc_5m_market()
    """

    def __init__(self, base_url: str = _GAMMA_URL):
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=_REQUEST_TIMEOUT,
            headers={"Accept": "application/json"},
        )

    async def find_active_btc_5m_market(self) -> Optional[FastMarket]:
        """
        查找当前活跃的 "Bitcoin Up or Down - 5 Minutes" 市场

        搜索策略：
          1. 按标签 "crypto" 过滤活跃事件
          2. 在标题中模糊匹配 "Bitcoin" + "Up" + "Down" + "5"
          3. 提取 Up/Down 两个 outcome 的 token_id

        Returns:
            FastMarket 或 None（无活跃市场时）
        """
        try:
            events = await self._fetch_events(
                tag="crypto",
                active=True,
                limit=100,
            )

            for event in events:
                title = event.get("title", "")

                # 模糊匹配标题
                title_lower = title.lower()
                if not (
                    "bitcoin" in title_lower
                    and ("up" in title_lower or "down" in title_lower)
                    and "5" in title_lower
                    and "minute" in title_lower
                ):
                    continue

                # 解析市场信息
                market = self._parse_fast_market(event)
                if market:
                    logger.info(
                        "发现 5 分钟市场: '%s' condition=%s",
                        title, market.condition_id[:16],
                    )
                    return market

            logger.debug("未找到活跃的 BTC 5 分钟市场")
            return None

        except Exception as e:
            logger.error("Gamma API 查询失败: %s", e)
            return None

    async def find_market_by_slug(self, slug: str) -> Optional[MarketDiscoveryResult]:
        """
        通过精确 slug 查询 5 分钟 BTC 市场

        slug 格式: btc-updown-5m-{5分钟对齐的 Unix 时间戳}
        例: btc-updown-5m-1775177700

        这是生产系统的首选市场发现路径：
          1. 从当前周期起始时间计算 slug
          2. 精确查询 Gamma API
          3. 解析 clobTokenIds 和交易状态

        Returns:
            MarketDiscoveryResult 或 None（未找到 / API 失败时）
        """
        try:
            resp = await self._client.get("/events", params={"slug": slug})
            resp.raise_for_status()
            events = resp.json()

            if not events or not isinstance(events, list) or len(events) == 0:
                logger.debug("Gamma API slug 查询无结果: %s", slug)
                return None

            event = events[0]
            markets = event.get("markets", [])
            if not markets:
                logger.warning("事件无市场数据: %s", slug)
                return None

            market_data = markets[0]

            # NOTE: clobTokenIds 在 Gamma API 中是 JSON 字符串，不是数组
            clob_ids_raw = market_data.get("clobTokenIds", "[]")
            if isinstance(clob_ids_raw, str):
                clob_ids = json.loads(clob_ids_raw)
            else:
                clob_ids = clob_ids_raw

            if len(clob_ids) < 2:
                logger.warning("clobTokenIds 不足 2 个: %s", slug)
                return None

            condition_id = market_data.get("conditionId", "")
            event_id = event.get("id", "")

            # 解析结束时间
            end_ts = self._parse_end_time(
                market_data.get("endDate", ""), event
            )

            # 解析 eventStartTime 用于精确定时
            start_time_str = event.get("startTime", "")
            if start_time_str:
                try:
                    from datetime import datetime, timezone
                    dt = datetime.fromisoformat(
                        start_time_str.replace("Z", "+00:00")
                    )
                    end_ts = dt.timestamp() + 300
                except (ValueError, TypeError):
                    pass

            fast_market = FastMarket(
                event_id=event_id,
                condition_id=condition_id,
                up_token_id=clob_ids[0],
                down_token_id=clob_ids[1],
                end_timestamp=end_ts,
                slug=slug,
            )

            result = MarketDiscoveryResult(
                market=fast_market,
                accepting_orders=market_data.get("acceptingOrders", False),
                closed=market_data.get("closed", False),
                slug=slug,
            )

            logger.info(
                "✅ 精确发现市场: %s (ID=%s, accepting=%s)",
                slug, event_id, result.accepting_orders,
            )
            return result

        except Exception as e:
            logger.error("Gamma slug 精确查询失败 (%s): %s", slug, e)
            return None

    async def get_event_by_slug(self, slug: str) -> Optional[dict]:
        """通过 slug 精确查询事件"""
        try:
            resp = await self._client.get(f"/events/slug/{slug}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Gamma slug 查询失败: %s", e)
            return None

    async def _fetch_events(
        self,
        tag: str = "",
        active: bool = True,
        limit: int = 50,
    ) -> list[dict]:
        """获取事件列表"""
        params: dict = {"limit": limit, "active": str(active).lower()}
        if tag:
            params["tag"] = tag

        resp = await self._client.get("/events", params=params)
        resp.raise_for_status()
        data = resp.json()

        return data if isinstance(data, list) else []

    def _parse_fast_market(self, event: dict) -> Optional[FastMarket]:
        """
        从事件数据中提取 FastMarket

        BTC Up/Down 双结果市场结构：
          event.markets[0] → { clobTokenIds: [up_id, down_id], ... }
        """
        markets = event.get("markets", [])
        if not markets:
            return None

        market = markets[0]
        clob_ids = market.get("clobTokenIds", [])
        if len(clob_ids) < 2:
            return None

        condition_id = market.get("conditionId", event.get("conditionId", ""))
        if not condition_id:
            return None

        # 推断结束时间
        end_date = event.get("endDate", "")
        end_ts = self._parse_end_time(end_date, event)

        return FastMarket(
            event_id=event.get("id", ""),
            condition_id=condition_id,
            up_token_id=clob_ids[0],
            down_token_id=clob_ids[1],
            end_timestamp=end_ts,
            slug=event.get("slug", ""),
        )

    def _parse_end_time(self, end_date: str, event: dict) -> float:
        """解析结束时间"""
        # 尝试从 endDate 字段解析
        if end_date:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                return dt.timestamp()
            except (ValueError, TypeError):
                pass

        # 尝试从 markets[0].endDate 或 closedTime 获取
        markets = event.get("markets", [])
        if markets:
            market_end = markets[0].get("endDate", "")
            if market_end:
                try:
                    from datetime import datetime, timezone
                    dt = datetime.fromisoformat(market_end.replace("Z", "+00:00"))
                    return dt.timestamp()
                except (ValueError, TypeError):
                    pass

        # 兜底：当前时间 + 5 分钟
        return time.time() + 300

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()
