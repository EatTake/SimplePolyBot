"""
shared.models 统一 TradingSignal 数据结构单元测试
"""

import time
import pytest

from shared.models import (
    TradingSignal,
    SignalAction,
    SignalDirection,
    generate_signal_id,
)


class TestSignalAction:
    """SignalAction 枚举测试"""

    def test_buy_value(self):
        assert SignalAction.BUY.value == "BUY"

    def test_wait_value(self):
        assert SignalAction.WAIT.value == "WAIT"

    def test_hold_value(self):
        assert SignalAction.HOLD.value == "HOLD"

    def test_enum_members_count(self):
        assert len(SignalAction) == 3


class TestSignalDirection:
    """SignalDirection 枚举测试"""

    def test_up_value(self):
        assert SignalDirection.UP.value == "UP"

    def test_down_value(self):
        assert SignalDirection.DOWN.value == "DOWN"

    def test_enum_members_count(self):
        assert len(SignalDirection) == 2


class TestGenerateSignalId:
    """generate_signal_id 辅助函数测试"""

    def test_returns_string(self):
        sid = generate_signal_id()
        assert isinstance(sid, str)

    def test_uuid_format(self):
        sid = generate_signal_id()
        parts = sid.split("-")
        assert len(parts) == 5

    def test_uniqueness(self):
        ids = {generate_signal_id() for _ in range(100)}
        assert len(ids) == 100


class TestTradingSignalFields:
    """TradingSignal dataclass 字段正确性测试"""

    def _make_signal(self, **overrides) -> TradingSignal:
        defaults = dict(
            signal_id="sig-001",
            token_id="token-abc",
            market_id="market-123",
            side="BUY",
            size=50.0,
            price=0.55,
            action=SignalAction.BUY,
            confidence=0.82,
            timestamp=1700000000.0,
        )
        defaults.update(overrides)
        return TradingSignal(**defaults)

    def test_required_fields_set(self):
        s = self._make_signal()
        assert s.signal_id == "sig-001"
        assert s.token_id == "token-abc"
        assert s.market_id == "market-123"
        assert s.side == "BUY"
        assert s.size == 50.0
        assert s.price == 0.55
        assert s.action is SignalAction.BUY
        assert s.confidence == 0.82
        assert s.timestamp == 1700000000.0

    def test_default_strategy(self):
        s = self._make_signal()
        assert s.strategy == "fast_market"

    def test_default_direction_is_none(self):
        s = self._make_signal()
        assert s.direction is None

    def test_default_numeric_fields_zero(self):
        s = self._make_signal()
        assert s.current_price == 0.0
        assert s.start_price == 0.0
        assert s.price_difference == 0.0
        assert s.max_buy_price == 0.0
        assert s.safety_cushion == 0.0
        assert s.slope_k == 0.0
        assert s.r_squared == 0.0
        assert s.time_remaining == 0.0

    def test_default_metadata_empty_dict(self):
        s = self._make_signal()
        assert s.metadata == {}

    def test_strategy_fields_populated(self):
        s = self._make_signal(
            direction=SignalDirection.UP,
            current_price=43000.0,
            start_price=42500.0,
            price_difference=500.0,
            max_buy_price=0.62,
            safety_cushion=0.08,
            slope_k=12.5,
            r_squared=0.92,
            time_remaining=45.0,
        )
        assert s.direction is SignalDirection.UP
        assert s.current_price == 43000.0
        assert s.start_price == 42500.0
        assert s.price_difference == 500.0
        assert s.max_buy_price == 0.62
        assert s.safety_cushion == 0.08
        assert s.slope_k == 12.5
        assert s.r_squared == 0.92
        assert s.time_remaining == 45.0

    def test_sell_side(self):
        s = self._make_signal(side="SELL", size=30.0, price=0.68)
        assert s.side == "SELL"

    def test_repr_contains_key_info(self):
        s = self._make_signal()
        r = repr(s)
        assert "sig-001" in r
        assert "token-abc" in r
        assert "BUY" in r


class TestTradingSignalToDict:
    """to_dict 序列化测试"""

    def _full_signal(self) -> TradingSignal:
        return TradingSignal(
            signal_id="s1",
            token_id="t1",
            market_id="m1",
            side="BUY",
            size=100.0,
            price=0.50,
            action=SignalAction.BUY,
            confidence=0.9,
            timestamp=1700000000.0,
            strategy="fast_market",
            direction=SignalDirection.UP,
            current_price=43100.0,
            start_price=42800.0,
            price_difference=300.0,
            max_buy_price=0.58,
            safety_cushion=0.06,
            slope_k=10.0,
            r_squared=0.88,
            time_remaining=60.0,
            metadata={"source": "test"},
        )

    def test_all_keys_present(self):
        d = self._full_signal().to_dict()
        expected = {
            "signal_id", "token_id", "market_id", "side", "size",
            "price", "action", "confidence", "timestamp", "strategy",
            "direction", "current_price", "start_price", "price_difference",
            "max_buy_price", "safety_cushion", "slope_k", "r_squared",
            "time_remaining", "metadata",
        }
        assert set(d.keys()) == expected

    def test_action_serialized_as_value(self):
        d = self._full_signal().to_dict()
        assert d["action"] == "BUY"

    def test_direction_serialized_as_value(self):
        d = self._full_signal().to_dict()
        assert d["direction"] == "UP"

    def test_none_direction_serialized_as_none(self):
        s = TradingSignal(
            signal_id="s2", token_id="t2", market_id="m2",
            side="SELL", size=1.0, price=0.60,
            action=SignalAction.HOLD, confidence=0.5,
            timestamp=1700000000.0,
        )
        assert s.to_dict()["direction"] is None


class TestTradingSignalFromDict:
    """from_dict 反序列化测试"""

    def _base_dict(self) -> dict:
        return {
            "signal_id": "fd-001",
            "token_id": "tok-x",
            "market_id": "mkt-y",
            "side": "BUY",
            "size": 80.0,
            "price": 0.52,
            "action": "BUY",
            "confidence": 0.78,
            "timestamp": 1700000000.0,
        }

    def test_basic_roundtrip(self):
        d = self._base_dict()
        s = TradingSignal.from_dict(d)
        assert s.signal_id == "fd-001"
        assert s.token_id == "tok-x"
        assert s.side == "BUY"
        assert s.size == 80.0
        assert s.price == 0.52
        assert s.action is SignalAction.BUY
        assert s.confidence == 0.78

    def test_missing_optional_fields_use_defaults(self):
        d = self._base_dict()
        s = TradingSignal.from_dict(d)
        assert s.strategy == "fast_market"
        assert s.direction is None
        assert s.metadata == {}

    def test_strategy_field_from_dict(self):
        d = self._base_dict()
        d["strategy"] = "trend_following"
        s = TradingSignal.from_dict(d)
        assert s.strategy == "trend_following"

    def test_direction_parsed_from_dict(self):
        d = self._base_dict()
        d["direction"] = "DOWN"
        s = TradingSignal.from_dict(d)
        assert s.direction is SignalDirection.DOWN

    def test_invalid_action_falls_back_to_wait(self):
        d = self._base_dict()
        d["action"] = "INVALID"
        s = TradingSignal.from_dict(d)
        assert s.action is SignalAction.WAIT

    def test_invalid_direction_falls_back_to_none(self):
        d = self._base_dict()
        d["direction"] = "INVALID"
        s = TradingSignal.from_dict(d)
        assert s.direction is None

    def test_full_roundtrip_preserves_all_fields(self):
        original = TradingSignal(
            signal_id="rt-001",
            token_id="rt-tok",
            market_id="rt-mkt",
            side="SELL",
            size=200.0,
            price=0.71,
            action=SignalAction.BUY,
            confidence=0.95,
            timestamp=1700000000.0,
            strategy="custom",
            direction=SignalDirection.DOWN,
            current_price=42000.0,
            start_price=42500.0,
            price_difference=-500.0,
            max_buy_price=0.65,
            safety_cushion=0.10,
            slope_k=-8.0,
            r_squared=0.85,
            time_remaining=30.0,
            metadata={"k": "v"},
        )
        restored = TradingSignal.from_dict(original.to_dict())
        assert restored.to_dict() == original.to_dict()


class TestTradingSignalValidate:
    """validate() 验证方法测试"""

    def _valid(self, **kw) -> TradingSignal:
        defaults = dict(
            signal_id="v-001",
            token_id="valid-token",
            market_id="m",
            side="BUY",
            size=10.0,
            price=0.55,
            action=SignalAction.BUY,
            confidence=0.7,
            timestamp=time.time(),
        )
        defaults.update(kw)
        return TradingSignal(**defaults)

    def test_valid_signal_passes(self):
        assert self._valid().validate() is True

    def test_valid_sell_signal_passes(self):
        assert self._valid(side="SELL", price=0.60).validate() is True

    def test_confidence_zero_passes(self):
        assert self._valid(confidence=0.0).validate() is True

    def test_confidence_one_passes(self):
        assert self._valid(confidence=1.0).validate() is True

    def test_empty_token_id_fails(self):
        assert self._valid(token_id="").validate() is False

    def test_invalid_side_fails(self):
        assert self._valid(side="LONG").validate() is False

    def test_size_zero_fails(self):
        assert self._valid(size=0).validate() is False

    def test_size_negative_fails(self):
        assert self._valid(size=-1.0).validate() is False

    def test_confidence_above_one_fails(self):
        assert self._valid(confidence=1.1).validate() is False

    def test_confidence_negative_fails(self):
        assert self._valid(confidence=-0.1).validate() is False

    def test_price_zero_fails(self):
        assert self._valid(price=0.0).validate() is False

    def test_price_one_fails(self):
        assert self._valid(price=1.0).validate() is False

    def test_price_negative_fails(self):
        assert self._valid(price=-0.1).validate() is False

    def test_price_above_one_fails(self):
        assert self._valid(price=1.5).validate() is False
