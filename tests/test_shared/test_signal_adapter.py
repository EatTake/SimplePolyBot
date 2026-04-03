"""
信号适配层单元测试

覆盖 SignalAdapter 的全部公开方法和边界条件。
"""

from __future__ import annotations

import uuid

import pytest

from shared.models import SignalAction, SignalDirection, TradingSignal
from shared.signal_adapter import (
    DEFAULT_SIZE_MAP,
    SignalAdapter,
)


def _make_market_info(
    market_id: str = "market-001",
    up_token_id: str = "token-up-abc",
    down_token_id: str = "token-down-xyz",
    up_best_ask: float = 0.55,
    down_best_ask: float = 0.48,
) -> dict:
    """构建标准市场信息"""
    return {
        "market_id": market_id,
        "tokens": {
            "UP": {"token_id": up_token_id, "best_ask": up_best_ask},
            "DOWN": {"token_id": down_token_id, "best_ask": down_best_ask},
        },
    }


def _make_strategy_signal(
    action: str = "BUY",
    direction: str = "UP",
    confidence: float = 0.75,
    max_buy_price: float = 0.60,
) -> dict:
    """构建标准策略信号"""
    return {
        "action": action,
        "direction": direction,
        "confidence": confidence,
        "max_buy_price": max_buy_price,
    }


class TestSignalAdapterInit:

    def test_default_config(self):
        adapter = SignalAdapter()
        assert adapter.size_map == DEFAULT_SIZE_MAP
        assert adapter.default_size == 100.0
        assert adapter.min_size == 10.0
        assert adapter.max_size == 500.0

    def test_custom_config(self):
        config = {
            "size_map": {0.9: 300, 0.6: 80},
            "default_size": 50,
            "min_size": 5,
            "max_size": 1000,
        }
        adapter = SignalAdapter(config)
        assert adapter.size_map == {0.9: 300, 0.6: 80}
        assert adapter.default_size == 50
        assert adapter.min_size == 5
        assert adapter.max_size == 1000

    def test_empty_config_uses_defaults(self):
        adapter = SignalAdapter({})
        assert adapter.size_map == DEFAULT_SIZE_MAP
        assert adapter.default_size == 100.0

    def test_partial_config_merges_defaults(self):
        config = {"max_size": 200}
        adapter = SignalAdapter(config)
        assert adapter.max_size == 200
        assert adapter.min_size == 10.0


class TestAdaptUpDirection:

    def test_up_maps_to_yes_token_and_buy(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="BUY", direction="UP", confidence=0.75)
        market = _make_market_info(up_token_id="yes-token-up")

        result = adapter.adapt(signal, market)

        assert isinstance(result, TradingSignal)
        assert result.side == "BUY"
        assert result.token_id == "yes-token-up"
        assert result.direction == SignalDirection.UP

    def test_up_with_high_confidence(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="BUY", direction="UP", confidence=0.85)
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.side == "BUY"
        assert result.size == 200.0

    def test_up_preserves_market_id(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(direction="UP")
        market = _make_market_info(market_id="mkt-up-999")

        result = adapter.adapt(signal, market)

        assert result.market_id == "mkt-up-999"

    def test_up_action_is_buy_enum(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="BUY", direction="UP")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.BUY


class TestAdaptDownDirection:

    def test_down_maps_to_no_token_and_buy(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="BUY", direction="DOWN", confidence=0.70)
        market = _make_market_info(down_token_id="no-token-down")

        result = adapter.adapt(signal, market)

        assert isinstance(result, TradingSignal)
        assert result.side == "BUY"
        assert result.token_id == "no-token-down"
        assert result.direction == SignalDirection.DOWN

    def test_down_with_medium_confidence(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="BUY", direction="DOWN", confidence=0.65)
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.side == "BUY"
        assert result.size == 100.0

    def test_down_direction_is_enum(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="BUY", direction="DOWN")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.direction == SignalDirection.DOWN


class TestAdaptWaitAction:

    def test_wait_action_returns_hold(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="WAIT")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD
        assert result.side == "HOLD"
        assert result.size == 0.0

    def test_hold_action_returns_hold(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="HOLD")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD
        assert result.side == "HOLD"
        assert result.size == 0.0

    def test_wait_signal_has_zero_price(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="WAIT")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.price == 0.0

    def test_wait_signal_token_id_is_empty_string(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="WAIT")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.token_id == ""

    def test_unknown_action_treated_as_non_buy(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(action="SELL")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD


class TestConfidenceToSizeMapping:

    def test_confidence_0_8_maps_to_200(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(0.8)
        assert size == 200.0

    def test_confidence_0_85_maps_to_200(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(0.85)
        assert size == 200.0

    def test_confidence_0_7_maps_to_150(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(0.7)
        assert size == 150.0

    def test_confidence_0_75_maps_to_150(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(0.75)
        assert size == 150.0

    def test_confidence_0_6_maps_to_100(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(0.6)
        assert size == 100.0

    def test_confidence_0_55_maps_to_50(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(0.55)
        assert size == 50.0

    def test_confidence_0_5_maps_to_50(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(0.5)
        assert size == 50.0

    def test_low_confidence_falls_back_to_default(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(0.3)
        assert size == adapter.default_size

    def test_confidence_1_0_maps_to_max_threshold(self):
        adapter = SignalAdapter()
        size = adapter._map_confidence_to_size(1.0)
        assert size == 200.0

    def test_size_clamped_to_min(self):
        adapter = SignalAdapter(config={"min_size": 25, "default_size": 10})
        size = adapter._map_confidence_to_size(0.3)
        assert size == 25

    def test_size_clamped_to_max(self):
        adapter = SignalAdapter(config={"size_map": {0.5: 600}, "max_size": 400})
        size = adapter._map_confidence_to_size(0.8)
        assert size == 400


class TestPriceCalculation:

    def test_price_is_min_of_max_buy_and_best_ask_when_max_lower(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(max_buy_price=0.50)
        market = _make_market_info(up_best_ask=0.60)

        result = adapter.adapt(signal, market)

        assert result.price == 0.50

    def test_price_is_min_of_max_buy_and_best_ask_when_ask_lower(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(max_buy_price=0.70)
        market = _make_market_info(up_best_ask=0.55)

        result = adapter.adapt(signal, market)

        assert result.price == 0.55

    def test_price_equal_when_both_same(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(max_buy_price=0.52)
        market = _make_market_info(up_best_ask=0.52)

        result = adapter.adapt(signal, market)

        assert result.price == 0.52

    def test_price_rounded_to_4_decimal_places(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(max_buy_price=0.512345)
        market = _make_market_info(up_best_ask=0.60)

        result = adapter.adapt(signal, market)

        assert result.price == round(0.512345, 4)


class TestSignalIdGeneration:

    def test_signal_id_is_uuid_format(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal()
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        uuid.UUID(result.signal_id)

    def test_signal_ids_are_unique_across_calls(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal()
        market = _make_market_info()

        ids = {adapter.adapt(signal, market).signal_id for _ in range(20)}

        assert len(ids) == 20

    def test_wait_signal_also_has_unique_id(self):
        adapter = SignalAdapter()
        wait_signal = _make_strategy_signal(action="WAIT")
        market = _make_market_info()

        id1 = adapter.adapt(wait_signal, market).signal_id
        id2 = adapter.adapt(wait_signal, market).signal_id

        assert id1 != id2


class TestMissingTokenDegradation:

    def test_missing_tokens_dict_returns_hold(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal()
        market = {"market_id": "m-no-tokens"}

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD
        assert result.size == 0.0

    def test_empty_tokens_dict_returns_hold(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal()
        market = {"market_id": "m-empty", "tokens": {}}

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD

    def test_tokens_missing_direction_key_returns_hold(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(direction="UP")
        market = {"market_id": "m-partial", "tokens": {"DOWN": {"token_id": "t-d"}}}

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD

    def test_token_entry_without_token_id_returns_hold(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(direction="UP")
        market = {
            "market_id": "m-bad-entry",
            "tokens": {"UP": {"best_ask": 0.50}},
        }

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD


class TestNoneDirectionHandling:

    def test_none_direction_returns_hold(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(direction=None)
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD
        assert result.size == 0.0

    def test_missing_direction_key_returns_hold(self):
        adapter = SignalAdapter()
        signal = {"action": "BUY", "confidence": 0.7}
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.action == SignalAction.HOLD

    def test_none_direction_still_generates_signal_id(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(direction=None)
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.signal_id is not None
        uuid.UUID(result.signal_id)


class TestRawSignalPreservation:

    def test_raw_signal_attached_on_buy(self):
        adapter = SignalAdapter()
        raw = _make_strategy_signal(confidence=0.88)
        market = _make_market_info()

        result = adapter.adapt(raw, market)

        assert "raw_signal" in result.metadata
        assert result.metadata["raw_signal"]["confidence"] == 0.88

    def test_raw_signal_attached_on_wait(self):
        adapter = SignalAdapter()
        raw = _make_strategy_signal(action="WAIT", confidence=0.3)
        market = _make_market_info()

        result = adapter.adapt(raw, market)

        assert "raw_signal" in result.metadata
        assert result.metadata["raw_signal"]["action"] == "WAIT"


class TestToDict:

    def test_buy_signal_to_dict_keys(self):
        adapter = SignalAdapter()
        result = adapter.adapt(_make_strategy_signal(), _make_market_info())

        d = result.to_dict()

        expected_keys = {
            "signal_id",
            "token_id",
            "market_id",
            "side",
            "size",
            "price",
            "action",
            "confidence",
            "timestamp",
            "strategy",
            "direction",
            "metadata",
        }
        assert set(d.keys()) >= expected_keys - {"current_price", "start_price"}

    def test_hold_signal_to_dict_values(self):
        adapter = SignalAdapter()
        result = adapter.adapt(
            _make_strategy_signal(action="WAIT"),
            _make_market_info(),
        )

        d = result.to_dict()

        assert d["action"] == "HOLD"
        assert d["size"] == 0.0
        assert d["price"] == 0.0


class TestCaseInsensitiveDirection:

    def test_lowercase_up_resolved(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(direction="up")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.token_id == "token-up-abc"

    def test_mixed_case_down_resolved(self):
        adapter = SignalAdapter()
        signal = _make_strategy_signal(direction="Down")
        market = _make_market_info()

        result = adapter.adapt(signal, market)

        assert result.token_id == "token-down-xyz"


class TestTimestampPresent:

    def test_buy_signal_has_timestamp(self):
        adapter = SignalAdapter()
        result = adapter.adapt(_make_strategy_signal(), _make_market_info())

        assert result.timestamp > 0
        assert isinstance(result.timestamp, float)

    def test_hold_signal_has_timestamp(self):
        adapter = SignalAdapter()
        result = adapter.adapt(
            _make_strategy_signal(action="WAIT"),
            _make_market_info(),
        )

        assert result.timestamp > 0
