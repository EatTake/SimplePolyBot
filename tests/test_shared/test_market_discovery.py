from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from shared.market_discovery import (
    ActiveMarketInfo,
    CACHE_KEY,
    FAST_MARKET_SLUG_PREFIX,
    MarketDiscovery,
    MarketDiscoveryConfig,
    TokenInfo,
)


SAMPLE_GAMMA_EVENT = {
    "id": "event-123",
    "slug": "btc-updown-5m-1740000000",
    "title": "Bitcoin Up or Down - 5 Minutes",
    "conditionId": "0xcondition123",
    "endDate": "2025-02-20T12:05:00Z",
    "clobTokenIds": ["0xup-token-id", "0xdown-token-id"],
    "outcomes": ["UP", "DOWN"],
    "outcomePrices": ["0.55", "0.47"],
    "markets": [],
}

SAMPLE_CLOB_MARKET = {
    "condition_id": "0xcondition456",
    "slug": "btc-updown-5m-1740000300",
    "endDate": "2025-02-20T12:10:00Z",
    "clobTokenIds": ["0xclob-up-token", "0xclob-down-token"],
    "outcomes": ["UP", "DOWN"],
    "outcomePrices": ["0.60", "0.42"],
    "markets": [],
}


class TestMarketDiscoveryConfig:
    def test_default_values(self):
        config = MarketDiscoveryConfig()
        assert config.gamma_api_url == "https://gamma-api.polymarket.com"
        assert config.clob_api_url == "https://clob.polymarket.com"
        assert config.cache_ttl == 300

    def test_custom_values(self):
        config = MarketDiscoveryConfig(
            gamma_api_url="https://custom-gamma.com",
            clob_api_url="https://custom-clob.com",
            cache_ttl=600,
        )
        assert config.gamma_api_url == "https://custom-gamma.com"
        assert config.clob_api_url == "https://custom-clob.com"
        assert config.cache_ttl == 600


class TestTokenInfo:
    def test_default_values(self):
        info = TokenInfo()
        assert info.token_id == ""
        assert info.outcome == ""
        assert info.best_ask == 0.0

    def test_custom_values(self):
        info = TokenInfo(token_id="0xtoken1", outcome="UP", best_ask=0.55)
        assert info.token_id == "0xtoken1"
        assert info.outcome == "UP"
        assert info.best_ask == 0.55


class TestActiveMarketInfo:
    def test_default_values(self):
        info = ActiveMarketInfo()
        assert info.condition_id == ""
        assert info.market_slug == ""
        assert info.tokens == {}
        assert info.end_date == ""
        assert info.active is False

    def test_to_dict_structure(self):
        tokens = {
            "UP": TokenInfo(token_id="0xup", outcome="UP", best_ask=0.55),
            "DOWN": TokenInfo(token_id="0xdown", outcome="DOWN", best_ask=0.47),
        }
        info = ActiveMarketInfo(
            condition_id="0xcond1",
            market_slug="btc-updown-5m-123",
            tokens=tokens,
            end_date="2025-01-01T00:00:00Z",
            active=True,
        )

        result = info.to_dict()

        assert result["condition_id"] == "0xcond1"
        assert result["market_slug"] == "btc-updown-5m-123"
        assert result["end_date"] == "2025-01-01T00:00:00Z"
        assert result["active"] is True
        assert "UP" in result["tokens"]
        assert "DOWN" in result["tokens"]
        assert result["tokens"]["UP"]["token_id"] == "0xup"
        assert result["tokens"]["DOWN"]["best_ask"] == 0.47


class TestMatchFastMarketSlug:
    def _create_discovery(self) -> MarketDiscovery:
        redis_mock = MagicMock()
        return MarketDiscovery(redis_mock)

    def test_match_valid_fast_market_slug(self):
        discovery = self._create_discovery()
        events = [SAMPLE_GAMMA_EVENT]
        result = discovery._match_fast_market_slug(events)

        assert result is not None
        assert result["slug"] == "btc-updown-5m-1740000000"

    def test_match_multiple_markets_returns_latest(self):
        discovery = self._create_discovery()
        events = [
            {**SAMPLE_GAMMA_EVENT, "slug": "btc-updown-5m-1740000000", "endDate": "2025-02-20T12:05:00Z"},
            {**SAMPLE_GAMMA_EVENT, "slug": "btc-updown-5m-1740000300", "endDate": "2025-02-20T12:10:00Z"},
            {**SAMPLE_GAMMA_EVENT, "slug": "btc-updown-5m-1739999700", "endDate": "2025-02-20T12:00:00Z"},
        ]
        result = discovery._match_fast_market_slug(events)

        assert result is not None
        assert result["slug"] == "btc-updown-5m-1740000300"

    def test_no_matching_slug_returns_none(self):
        discovery = self._create_discovery()
        events = [
            {"slug": "will-btc-reach-100k", "endDate": "2025-12-31T00:00:00Z"},
            {"slug": "eth-price-prediction", "endDate": "2025-06-30T00:00:00Z"},
        ]
        result = discovery._match_fast_market_slug(events)

        assert result is None

    def test_empty_events_list_returns_none(self):
        discovery = self._create_discovery()
        result = discovery._match_fast_market_slug([])

        assert result is None

    def test_slug_contains_prefix_anywhere(self):
        discovery = self._create_discovery()
        events = [
            {"slug": "some-prefix-btc-updown-5m-1740000000-suffix", "endDate": "2025-02-20T12:05:00Z"},
        ]
        result = discovery._match_fast_market_slug(events)

        assert result is not None

    def test_event_without_end_date_skipped(self):
        discovery = self._create_discovery()
        events = [
            {**SAMPLE_GAMMA_EVENT, "endDate": ""},
            {**SAMPLE_GAMMA_EVENT, "slug": "other-market", "endDate": "2025-02-20T12:05:00Z"},
        ]
        result = discovery._match_fast_market_slug(events)

        assert result is None


class TestBuildTokenMapping:
    def _create_discovery(self) -> MarketDiscovery:
        redis_mock = MagicMock()
        return MarketDiscovery(redis_mock)

    def test_build_from_clobTokenIds_format(self):
        discovery = self._create_discovery()
        data = SAMPLE_GAMMA_EVENT

        result = discovery._build_token_mapping(data)

        assert "UP" in result
        assert "DOWN" in result
        assert isinstance(result["UP"], TokenInfo)
        assert result["UP"].token_id == "0xup-token-id"
        assert result["DOWN"].token_id == "0xdown-token-id"
        assert result["UP"].best_ask == 0.55
        assert result["DOWN"].best_ask == 0.47

    def test_build_from_markets_array_format(self):
        discovery = self._create_discovery()
        data = {
            "markets": [
                {
                    "outcome": "UP",
                    "clobTokenIds": ["0xmkt-up-token"],
                    "outcomePrices": ["0.58"],
                },
                {
                    "outcome": "DOWN",
                    "clobTokenIds": ["0xmkt-down-token"],
                    "outcomePrices": ["0.44"],
                },
            ],
        }

        result = discovery._build_token_mapping(data)

        assert "UP" in result
        assert "DOWN" in result
        assert result["UP"].token_id == "0xmkt-up-token"
        assert result["DOWN"].token_id == "0xmkt-down-token"

    def test_empty_market_data_returns_empty_dict(self):
        discovery = self._create_discovery()
        data = {}

        result = discovery._build_token_mapping(data)

        assert result == {}

    def test_up_down_mapping_correct_order(self):
        discovery = self._create_discovery()
        data = SAMPLE_GAMMA_EVENT

        result = discovery._build_token_mapping(data)

        assert list(result.keys()) == ["UP", "DOWN"]

    def test_invalid_price_defaults_to_zero(self):
        discovery = self._create_discovery()
        data = {
            "clobTokenIds": ["0xtoken1", "0xtoken2"],
            "outcomes": ["UP", "DOWN"],
            "outcomePrices": ["invalid", "not-a-number"],
        }

        result = discovery._build_token_mapping(data)

        assert result["UP"].best_ask == 0.0
        assert result["DOWN"].best_ask == 0.0

    def test_missing_outcome_field_in_markets_skipped(self):
        discovery = self._create_discovery()
        data = {
            "markets": [
                {"outcome": "", "clobTokenIds": ["0xtoken1"], "outcomePrices": ["0.5"]},
                {"outcome": "DOWN", "clobTokenIds": ["0xtoken2"], "outcomePrices": ["0.45"]},
            ],
        }

        result = discovery._build_token_mapping(data)

        assert "UP" not in result
        assert "DOWN" in result


class TestFetchFromGammaApi:
    def _create_discovery(self) -> tuple[MarketDiscovery, MagicMock]:
        redis_mock = MagicMock()
        discovery = MarketDiscovery(redis_mock)
        return discovery, redis_mock

    @patch("shared.market_discovery.requests.get")
    def test_successful_response_parses_correctly(self, mock_get):
        discovery, _ = self._create_discovery()
        mock_response = MagicMock()
        mock_response.json.return_value = [SAMPLE_GAMMA_EVENT]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = discovery._fetch_from_gamma_api()

        assert result is not None
        assert result["market_slug"] == "btc-updown-5m-1740000000"
        assert result["condition_id"] == "0xcondition123"
        assert "tokens" in result
        assert result["active"] is True

    @patch("shared.market_discovery.requests.get")
    def test_empty_events_list_returns_none(self, mock_get):
        discovery, _ = self._create_discovery()
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = discovery._fetch_from_gamma_api()

        assert result is None

    @patch("shared.market_discovery.requests.get")
    def test_no_matching_market_returns_none(self, mock_get):
        discovery, _ = self._create_discovery()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"slug": "other-market", "endDate": "2025-12-31T00:00:00Z"}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = discovery._fetch_from_gamma_api()

        assert result is None

    @patch("shared.market_discovery.requests.get")
    def test_http_error_raises_exception(self, mock_get):
        discovery, _ = self._create_discovery()
        mock_get.side_effect = requests.exceptions.HTTPError("500 Server Error")

        with pytest.raises(requests.exceptions.HTTPError):
            discovery._fetch_from_gamma_api()

    @patch("shared.market_discovery.requests.get")
    def test_timeout_raises_exception(self, mock_get):
        discovery, _ = self._create_discovery()
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            discovery._fetch_from_gamma_api()


class TestFetchFromClobApi:
    def _create_discovery(self) -> tuple[MarketDiscovery, MagicMock]:
        redis_mock = MagicMock()
        discovery = MarketDiscovery(redis_mock)
        return discovery, redis_mock

    @patch("shared.market_discovery.requests.get")
    def test_successful_response_parses_correctly(self, mock_get):
        discovery, _ = self._create_discovery()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [SAMPLE_CLOB_MARKET]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = discovery._fetch_from_clob_api()

        assert result is not None
        assert result["market_slug"] == "btc-updown-5m-1740000300"
        assert result["condition_id"] == "0xcondition456"

    @patch("shared.market_discovery.requests.get")
    def test_empty_data_list_returns_none(self, mock_get):
        discovery, _ = self._create_discovery()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = discovery._fetch_from_clob_api()

        assert result is None

    @patch("shared.market_discovery.requests.get")
    def test_no_matching_slug_returns_none(self, mock_get):
        discovery, _ = self._create_discovery()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"market_slug": "some-other-market"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = discovery._fetch_from_clob_api()

        assert result is None


class TestCacheResult:
    def _create_discovery(self) -> tuple[MarketDiscovery, MagicMock]:
        redis_mock = MagicMock()
        discovery = MarketDiscovery(redis_mock, MarketDiscoveryConfig(cache_ttl=300))
        return discovery, redis_mock

    def test_cache_write_success(self):
        discovery, redis_mock = self._create_discovery()
        data = {"test": "value"}

        result = discovery._cache_result(data)

        assert result is True
        redis_mock.set.assert_called_once_with(CACHE_KEY, json.dumps(data), ex=300)

    def test_cache_write_failure_returns_false(self):
        discovery, redis_mock = self._create_discovery()
        redis_mock.set.side_effect = Exception("Redis error")

        result = discovery._cache_result({"test": "value"})

        assert result is False


class TestGetCached:
    def _create_discovery(self) -> tuple[MarketDiscovery, MagicMock]:
        redis_mock = MagicMock()
        discovery = MarketDiscovery(redis_mock)
        return discovery, redis_mock

    def test_cache_hit_returns_parsed_data(self):
        discovery, redis_mock = self._create_discovery()
        cached_data = json.dumps({"market_slug": "test-market"})
        redis_mock.get.return_value = cached_data
        redis_mock.ttl.return_value = 250

        result = discovery._get_cached()

        assert result == {"market_slug": "test-market"}

    def test_cache_miss_returns_none(self):
        discovery, redis_mock = self._create_discovery()
        redis_mock.get.return_value = None

        result = discovery._get_cached()

        assert result is None

    def test_expired_cache_returns_none_when_force_refresh(self):
        discovery, redis_mock = self._create_discovery()
        redis_mock.get.return_value = json.dumps({"market_slug": "old"})
        redis_mock.ttl.return_value = -1

        result = discovery._get_cached(force_refresh=True)

        assert result is None

    def test_expired_cache_returns_data_when_not_force_refresh(self):
        discovery, redis_mock = self._create_discovery()
        redis_mock.get.return_value = json.dumps({"market_slug": "stale"})
        redis_mock.ttl.return_value = -2

        result = discovery._get_cached(force_refresh=False)

        assert result == {"market_slug": "stale"}

    def test_redis_error_returns_none(self):
        discovery, redis_mock = self._create_discovery()
        redis_mock.get.side_effect = Exception("Connection lost")

        result = discovery._get_cached()

        assert result is None


class TestGetActiveMarketFullFlow:
    def _create_discovery(self) -> tuple[MarketDiscovery, MagicMock]:
        redis_mock = MagicMock()
        discovery = MarketDiscovery(redis_mock)
        return discovery, redis_mock

    def test_returns_cached_data_when_available(self):
        discovery, redis_mock = self._create_discovery()
        cached = {"market_slug": "cached-market", "active": True}
        redis_mock.get.return_value = json.dumps(cached)
        redis_mock.ttl.return_value = 200

        result = discovery.get_active_market()

        assert result == cached

    @patch("shared.market_discovery.MarketDiscovery._fetch_from_gamma_api")
    @patch("shared.market_discovery.MarketDiscovery._fetch_from_clob_api")
    def test_falls_back_to_clob_on_gamma_failure(self, mock_clob, mock_gamma):
        discovery, redis_mock = self._create_discovery()
        redis_mock.get.return_value = None
        mock_gamma.side_effect = Exception("Gamma down")
        clob_result = {"market_slug": "clob-fallback", "active": True}
        mock_clob.return_value = clob_result

        result = discovery.get_active_market()

        assert result == clob_result
        mock_gamma.assert_called_once()
        mock_clob.assert_called_once()

    @patch("shared.market_discovery.MarketDiscovery._fetch_from_gamma_api")
    @patch("shared.market_discovery.MarketDiscovery._fetch_from_clob_api")
    def test_returns_stale_cache_on_both_api_failures(self, mock_clob, mock_gamma):
        discovery, redis_mock = self._create_discovery()
        stale_data = {"market_slug": "stale-market", "active": True}

        call_count = [0]

        def get_side_effect(key):
            if key == CACHE_KEY:
                call_count[0] += 1
                if call_count[0] == 1:
                    return None
                return json.dumps(stale_data)
            return None

        redis_mock.get.side_effect = get_side_effect
        redis_mock.ttl.return_value = -100
        mock_gamma.side_effect = Exception("Gamma error")
        mock_clob.side_effect = Exception("CLOB error")

        result = discovery.get_active_market()

        assert result == stale_data

    @patch("shared.market_discovery.MarketDiscovery._fetch_from_gamma_api")
    @patch("shared.market_discovery.MarketDiscovery._fetch_from_clob_api")
    def test_returns_none_when_no_cache_and_no_api(self, mock_clob, mock_gamma):
        discovery, redis_mock = self._create_discovery()
        redis_mock.get.return_value = None
        mock_gamma.return_value = None
        mock_clob.return_value = None

        result = discovery.get_active_market()

        assert result is None

    @patch("shared.market_discovery.MarketDiscovery._fetch_from_gamma_api")
    def test_full_happy_path_caches_result(self, mock_gamma):
        discovery, redis_mock = self._create_discovery()
        redis_mock.get.return_value = None
        gamma_result = {"market_slug": "fresh-market", "active": True, "tokens": {}}
        mock_gamma.return_value = gamma_result

        result = discovery.get_active_market()

        assert result == gamma_result
        redis_mock.set.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
