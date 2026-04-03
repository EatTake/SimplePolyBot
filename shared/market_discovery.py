from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

import structlog

from shared.constants import (
    POLYMARKET_CLOB_API_URL,
    POLYMARKET_GAMMA_API_URL,
    API_REQUEST_TIMEOUT_SECONDS,
)

logger = structlog.get_logger()

FAST_MARKET_SLUG_PREFIX = "btc-updown-5m"
CACHE_KEY = "market_discovery:active_market"


@dataclass
class MarketDiscoveryConfig:
    gamma_api_url: str = POLYMARKET_GAMMA_API_URL
    clob_api_url: str = POLYMARKET_CLOB_API_URL
    cache_ttl: int = 300


@dataclass
class TokenInfo:
    token_id: str = ""
    outcome: str = ""
    best_ask: float = 0.0


@dataclass
class ActiveMarketInfo:
    condition_id: str = ""
    market_slug: str = ""
    tokens: Dict[str, TokenInfo] = field(default_factory=dict)
    end_date: str = ""
    active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "market_slug": self.market_slug,
            "tokens": {
                key: {
                    "token_id": val.token_id,
                    "outcome": val.outcome,
                    "best_ask": val.best_ask,
                }
                for key, val in self.tokens.items()
            },
            "end_date": self.end_date,
            "active": self.active,
        }


class MarketDiscovery:
    def __init__(self, redis_client: Any, config: Optional[MarketDiscoveryConfig] = None):
        self.redis_client = redis_client
        self.config = config or MarketDiscoveryConfig()

        logger.info(
            "初始化市场发现服务",
            gamma_api_url=self.config.gamma_api_url,
            clob_api_url=self.config.clob_api_url,
            cache_ttl=self.config.cache_ttl,
        )

    def get_active_market(self) -> Optional[Dict[str, Any]]:
        cached = self._get_cached()
        if cached is not None:
            logger.debug("返回缓存的活跃市场数据")
            return cached

        try:
            result = self._fetch_from_gamma_api()
            if result is not None:
                self._cache_result(result)
                return result
        except Exception as e:
            logger.warning("Gamma API 查询失败，尝试备用 API", error=str(e))

        try:
            result = self._fetch_from_clob_api()
            if result is not None:
                self._cache_result(result)
                return result
        except Exception as e:
            logger.warning("CLOB API 备用查询失败", error=str(e))

        fallback_cached = self._get_cached(force_refresh=False)
        if fallback_cached is not None:
            logger.info("API 均不可用，返回过期缓存")
            return fallback_cached

        logger.warning("无法获取活跃市场数据，缓存也为空")
        return None

    def _fetch_from_gamma_api(self) -> Optional[Dict[str, Any]]:
        url = f"{self.config.gamma_api_url}/events"
        params = {
            "tag": "bitcoin price",
            "closed": "false",
            "limit": 5,
            "order": "endDate",
            "ascending": "false",
        }

        logger.debug("查询 Gamma API", url=url, params=params)

        response = requests.get(
            url,
            params=params,
            timeout=API_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        events: List[Dict] = response.json()
        if not events:
            logger.debug("Gamma API 返回空事件列表")
            return None

        matched = self._match_fast_market_slug(events)
        if matched is None:
            logger.debug("未匹配到 Fast Market slug")
            return None

        token_mapping = self._build_token_mapping(matched)

        info = ActiveMarketInfo(
            condition_id=matched.get("conditionId", ""),
            market_slug=matched.get("slug", ""),
            tokens=token_mapping,
            end_date=matched.get("endDate", ""),
            active=True,
        )

        logger.info(
            "从 Gamma API 获取到活跃市场",
            slug=info.market_slug,
            condition_id=info.condition_id,
        )

        return info.to_dict()

    def _fetch_from_clob_api(self) -> Optional[Dict[str, Any]]:
        url = f"{self.config.clob_api_url}/markets"
        params = {"next_cursor": "", "limit": 10}

        logger.debug("查询 CLOB API", url=url, params=params)

        response = requests.get(
            url,
            params=params,
            timeout=API_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data: Dict = response.json()
        markets: List[Dict] = data.get("data", [])
        if not markets:
            logger.debug("CLOB API 返回空市场列表")
            return None

        matched = self._match_fast_market_slug(markets)
        if matched is None:
            logger.debug("CLOB API 未匹配到 Fast Market slug")
            return None

        token_mapping = self._build_token_mapping(matched)

        info = ActiveMarketInfo(
            condition_id=matched.get("condition_id", matched.get("conditionId", "")),
            market_slug=matched.get("market_slug", matched.get("slug", "")),
            tokens=token_mapping,
            end_date=matched.get("end_date", matched.get("endDate", "")),
            active=True,
        )

        logger.info(
            "从 CLOB API 获取到活跃市场（备用）",
            slug=info.market_slug,
            condition_id=info.condition_id,
        )

        return info.to_dict()

    def _match_fast_market_slug(self, events: List[Dict]) -> Optional[Dict]:
        best_match: Optional[Dict] = None
        best_end_date: Optional[str] = None

        for event in events:
            slug = event.get("slug", "")
            if FAST_MARKET_SLUG_PREFIX not in slug:
                continue

            end_date = event.get("endDate", event.get("end_date", ""))
            if not end_date:
                continue

            if best_end_date is None or end_date > best_end_date:
                best_match = event
                best_end_date = end_date

        if best_match is not None:
            logger.debug(
                "匹配到 Fast Market",
                slug=best_match.get("slug"),
                end_date=best_end_date,
            )

        return best_match

    def _build_token_mapping(self, market_data: Dict) -> Dict[str, TokenInfo]:
        tokens: Dict[str, TokenInfo] = {}

        markets = market_data.get("markets", [])
        if not markets:
            clob_token_ids = market_data.get("clobTokenIds", [])
            outcomes = market_data.get("outcomes", ["UP", "DOWN"])
            outcome_prices = market_data.get("outcomePrices", ["0.5", "0.5"])

            for i, (outcome, token_id) in enumerate(zip(outcomes, clob_token_ids)):
                try:
                    best_ask = float(outcome_prices[i]) if i < len(outcome_prices) else 0.0
                except (ValueError, TypeError):
                    best_ask = 0.0

                tokens[outcome.upper()] = TokenInfo(
                    token_id=str(token_id),
                    outcome=outcome,
                    best_ask=best_ask,
                )
        else:
            for mkt in markets:
                outcome = mkt.get("outcome", "").upper()
                token_id = mkt.get("clobTokenIds", [""])[0] if isinstance(mkt.get("clobTokenIds"), list) else mkt.get("clobTokenIds", "")
                try:
                    best_ask = float(mkt.get("outcomePrices", [0.5])[0]) if isinstance(mkt.get("outcomePrices"), list) else float(mkt.get("outcomePrices", 0.5))
                except (ValueError, TypeError):
                    best_ask = 0.0

                if outcome and token_id:
                    tokens[outcome] = TokenInfo(
                        token_id=str(token_id),
                        outcome=outcome,
                        best_ask=best_ask,
                    )

        logger.debug(
            "构建 Token 映射",
            up_token=tokens.get("UP", {}).token_id if isinstance(tokens.get("UP"), TokenInfo) else tokens.get("UP", {}).get("token_id"),
            down_token=tokens.get("DOWN", {}).token_id if isinstance(tokens.get("DOWN"), TokenInfo) else tokens.get("DOWN", {}).get("token_id"),
        )

        return tokens

    def _cache_result(self, data: Dict[str, Any]) -> bool:
        try:
            serialized = json.dumps(data)
            self.redis_client.set(CACHE_KEY, serialized, ex=self.config.cache_ttl)
            logger.debug("缓存活跃市场结果", ttl=self.config.cache_ttl)
            return True
        except Exception as e:
            logger.error("缓存写入失败", error=str(e))
            return False

    def _get_cached(self, force_refresh: bool = True) -> Optional[Dict[str, Any]]:
        try:
            value = self.redis_client.get(CACHE_KEY)
            if value is None:
                return None

            if isinstance(value, (bytes, str)):
                parsed = json.loads(value)
            else:
                parsed = value

            ttl = self.redis_client.ttl(CACHE_KEY)
            if force_refresh and ttl is not None and ttl <= 0:
                return None

            logger.debug("读取缓存成功", remaining_ttl=ttl)
            return parsed
        except Exception as e:
            logger.error("缓存读取失败", error=str(e))
            return None
