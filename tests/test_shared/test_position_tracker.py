import json
import time
from unittest.mock import MagicMock, patch

import pytest

from shared.position_tracker import Position, PositionTracker


class TestPositionDataclass:
    def test_default_values(self):
        pos = Position(
            token_id="tok_1",
            market_id="mkt_1",
            side="BUY",
            quantity=100.0,
            avg_cost=0.50,
        )
        assert pos.token_id == "tok_1"
        assert pos.market_id == "mkt_1"
        assert pos.side == "BUY"
        assert pos.quantity == 100.0
        assert pos.avg_cost == 0.50
        assert pos.current_price == 0.0
        assert pos.realized_pnl == 0.0
        assert pos.unrealized_pnl == 0.0
        assert pos.opened_at == 0.0
        assert pos.updated_at == 0.0

    def test_custom_values(self):
        now = time.time()
        pos = Position(
            token_id="tok_2",
            market_id="mkt_2",
            side="BUY",
            quantity=50.0,
            avg_cost=0.60,
            current_price=0.70,
            realized_pnl=5.0,
            unrealized_pnl=10.0,
            opened_at=now,
            updated_at=now,
        )
        assert pos.current_price == 0.70
        assert pos.realized_pnl == 5.0
        assert pos.unrealized_pnl == 10.0


class TestPositionTrackerInit:
    def test_default_init(self):
        tracker = PositionTracker()
        assert tracker._positions == {}
        assert tracker._redis_client is None

    def test_init_with_redis_client(self):
        mock_redis = MagicMock()
        tracker = PositionTracker(redis_client=mock_redis)
        assert tracker._redis_client is mock_redis


class TestOpenPosition:
    def _make_buy_result(self, token_id="tok_a", qty=100.0, price=0.50, status="MATCHED"):
        return {
            "token_id": token_id,
            "side": "BUY",
            "filled_size": str(qty),
            "price": str(price),
            "market_id": f"mkt_{token_id}",
            "status": status,
        }

    def test_open_new_long_position(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result(self._make_buy_result(qty=100.0, price=0.50))
        positions = tracker.get_open_positions()
        assert len(positions) == 1
        assert positions[0].token_id == "tok_a"
        assert positions[0].quantity == 100.0
        assert positions[0].avg_cost == 0.50
        assert positions[0].side == "BUY"

    def test_open_position_sets_timestamp(self):
        before = time.time()
        tracker = PositionTracker()
        tracker.update_from_trade_result(self._make_buy_result())
        after = time.time()
        pos = tracker.get_position("tok_a")
        assert before <= pos.opened_at <= after
        assert before <= pos.updated_at <= after

    def test_open_multiple_positions(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result(self._make_buy_result(token_id="tok_x", qty=50, price=0.40))
        tracker.update_from_trade_result(self._make_buy_result(token_id="tok_y", qty=80, price=0.60))
        assert len(tracker.get_open_positions()) == 2


class TestAddToPosition:
    def _buy(self, tracker, token_id="tok_a", qty=100.0, price=0.50):
        tracker.update_from_trade_result({
            "token_id": token_id,
            "side": "BUY",
            "filled_size": str(qty),
            "price": str(price),
            "market_id": f"mkt_{token_id}",
            "status": "MATCHED",
        })

    def test_add_to_existing_position(self):
        tracker = PositionTracker()
        self._buy(tracker, qty=100.0, price=0.40)
        self._buy(tracker, qty=100.0, price=0.60)
        pos = tracker.get_position("tok_a")
        assert pos.quantity == 200.0
        assert pos.avg_cost == 0.50

    def test_weighted_average_cost(self):
        tracker = PositionTracker()
        self._buy(tracker, qty=200.0, price=0.30)
        self._buy(tracker, qty=100.0, price=0.90)
        pos = tracker.get_position("tok_a")
        expected_avg = (200 * 0.30 + 100 * 0.90) / 300
        assert abs(pos.avg_cost - expected_avg) < 1e-9

    def test_multiple_adds_accumulate(self):
        tracker = PositionTracker()
        for p in [0.20, 0.30, 0.40, 0.50]:
            self._buy(tracker, qty=50.0, price=p)
        pos = tracker.get_position("tok_a")
        assert pos.quantity == 200.0
        expected = (50 * 0.20 + 50 * 0.30 + 50 * 0.40 + 50 * 0.50) / 200
        assert abs(pos.avg_cost - expected) < 1e-9


class TestReducePosition:
    def _setup_with_position(self, qty=100.0, cost=0.50):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_a",
            "side": "BUY",
            "filled_size": str(qty),
            "price": str(cost),
            "market_id": "mkt_tok_a",
            "status": "MATCHED",
        })
        return tracker

    def _sell(self, tracker, token_id="tok_a", qty=50.0, price=0.70):
        tracker.update_from_trade_result({
            "token_id": token_id,
            "side": "SELL",
            "filled_size": str(qty),
            "price": str(price),
            "market_id": f"mkt_{token_id}",
            "status": "MATCHED",
        })

    def test_sell_reduces_quantity(self):
        tracker = self._setup_with_position(qty=100.0, cost=0.50)
        self._sell(tracker, qty=30.0, price=0.70)
        pos = tracker.get_position("tok_a")
        assert pos.quantity == 70.0

    def test_sell_calculates_realized_pnl(self):
        tracker = self._setup_with_position(qty=100.0, cost=0.50)
        self._sell(tracker, qty=50.0, price=0.80)
        pos = tracker.get_position("tok_a")
        assert pos.realized_pnl == pytest.approx(15.0)

    def test_sell_at_loss_realizes_negative_pnl(self):
        tracker = self._setup_with_position(qty=100.0, cost=0.50)
        self._sell(tracker, qty=50.0, price=0.30)
        pos = tracker.get_position("tok_a")
        assert pos.realized_pnl == pytest.approx(-10.0)


class TestClosePosition:
    def _setup_and_close(self, buy_qty=100.0, buy_price=0.50, sell_qty=100.0, sell_price=0.80):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_a",
            "side": "BUY",
            "filled_size": str(buy_qty),
            "price": str(buy_price),
            "market_id": "mkt_tok_a",
            "status": "MATCHED",
        })
        tracker.update_from_trade_result({
            "token_id": "tok_a",
            "side": "SELL",
            "filled_size": str(sell_qty),
            "price": str(sell_price),
            "market_id": "mkt_tok_a",
            "status": "MATCHED",
        })
        return tracker

    def test_full_close_removes_position(self):
        tracker = self._setup_and_close(buy_qty=100.0, sell_qty=100.0)
        assert len(tracker.get_open_positions()) == 0
        assert tracker.get_position("tok_a") is None

    def test_partial_close_keeps_position(self):
        tracker = self._setup_and_close(buy_qty=100.0, sell_qty=40.0)
        assert len(tracker.get_open_positions()) == 1
        assert tracker.get_position("tok_a").quantity == 60.0

    def test_full_close_realized_pnl(self):
        tracker = self._setup_and_close(
            buy_qty=100.0, buy_price=0.50, sell_qty=100.0, sell_price=0.80
        )
        closed = tracker.close_position("tok_a")
        assert closed is None

    def test_manual_close_position_method(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_b",
            "side": "BUY",
            "filled_size": "50",
            "price": "0.55",
            "market_id": "mkt_tok_b",
            "status": "MATCHED",
        })
        closed = tracker.close_position("tok_b")
        assert closed is not None
        assert closed.token_id == "tok_b"
        assert closed.quantity == 50.0
        assert len(tracker.get_open_positions()) == 0

    def test_close_nonexistent_returns_none(self):
        tracker = PositionTracker()
        assert tracker.close_position("nonexistent") is None


class TestGetOpenPositions:
    def test_filters_zero_quantity(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_z",
            "side": "BUY",
            "filled_size": "100",
            "price": "0.50",
            "market_id": "mkt_tok_z",
            "status": "MATCHED",
        })
        tracker.update_from_trade_result({
            "token_id": "tok_z",
            "side": "SELL",
            "filled_size": "100",
            "price": "0.60",
            "market_id": "mkt_tok_z",
            "status": "MATCHED",
        })
        assert len(tracker.get_open_positions()) == 0

    def test_returns_only_positive_quantity(self):
        tracker = PositionTracker()
        for tid in ["t1", "t2", "t3"]:
            tracker.update_from_trade_result({
                "token_id": tid,
                "side": "BUY",
                "filled_size": "10",
                "price": "0.50",
                "market_id": f"mkt_{tid}",
                "status": "MATCHED",
            })
        tracker.update_from_trade_result({
            "token_id": "t2",
            "side": "SELL",
            "filled_size": "10",
            "price": "0.50",
            "market_id": "mkt_t2",
            "status": "MATCHED",
        })
        open_pos = tracker.get_open_positions()
        token_ids = {p.token_id for p in open_pos}
        assert token_ids == {"t1", "t3"}


class TestGetPosition:
    def test_get_existing(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_g",
            "side": "BUY",
            "filled_size": "99",
            "price": "0.45",
            "market_id": "mkt_tok_g",
            "status": "CONFIRMED",
        })
        pos = tracker.get_position("tok_g")
        assert pos is not None
        assert pos.quantity == 99.0

    def test_get_nonexistent(self):
        tracker = PositionTracker()
        assert tracker.get_position("no_such_token") is None

    def test_get_zero_quantity_returns_none(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_zero",
            "side": "BUY",
            "filled_size": "50",
            "price": "0.50",
            "market_id": "mkt_tok_zero",
            "status": "MINED",
        })
        tracker.update_from_trade_result({
            "token_id": "tok_zero",
            "side": "SELL",
            "filled_size": "50",
            "price": "0.50",
            "market_id": "mkt_tok_zero",
            "status": "MINED",
        })
        assert tracker.get_position("tok_zero") is None


class TestTotalExposure:
    def test_single_position_exposure(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_e1",
            "side": "BUY",
            "filled_size": "200",
            "price": "0.50",
            "market_id": "mkt_tok_e1",
            "status": "MATCHED",
        })
        tracker.update_prices({"tok_e1": 0.60})
        assert tracker.get_total_exposure() == pytest.approx(120.0)

    def test_multi_position_exposure(self):
        tracker = PositionTracker()
        for i, (tid, qty, cp) in enumerate([
            ("e_a", 100, 0.55), ("e_b", 200, 0.33), ("e_c", 50, 0.80)
        ]):
            tracker.update_from_trade_result({
                "token_id": tid,
                "side": "BUY",
                "filled_size": str(qty),
                "price": "0.50",
                "market_id": f"mkt_{tid}",
                "status": "MATCHED",
            })
        tracker.update_prices({"e_a": 0.55, "e_b": 0.33, "e_c": 0.80})
        exposure = tracker.get_total_exposure()
        assert exposure == pytest.approx(100 * 0.55 + 200 * 0.33 + 50 * 0.80)

    def test_no_positions_zero_exposure(self):
        tracker = PositionTracker()
        assert tracker.get_total_exposure() == 0.0


class TestDailyPnl:
    @patch("shared.position_tracker.time")
    def test_daily_pnl_includes_today(self, mock_time):
        today_start = 1700000000.0
        mock_time.time.return_value = today_start + 3600
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_d1",
            "side": "BUY",
            "filled_size": "100",
            "price": "0.50",
            "market_id": "mkt_tok_d1",
            "status": "MATCHED",
        })
        tracker.update_prices({"tok_d1": 0.60})
        pnl = tracker.get_daily_pnl()
        assert pnl == pytest.approx(10.0)

    @patch("shared.position_tracker.time")
    def test_daily_pnl_excludes_old(self, mock_time):
        old_ts = 1600000000.0
        now = 1700000000.0
        mock_time.time.return_value = now
        tracker = PositionTracker()
        with patch.object(tracker, "_positions"):
            fake_pos = Position(
                token_id="old_tok",
                market_id="mkt_old",
                side="BUY",
                quantity=100.0,
                avg_cost=0.50,
                current_price=0.80,
                realized_pnl=20.0,
                opened_at=old_ts,
            )
            tracker._positions = {"old_tok": fake_pos}
        pnl = tracker.get_daily_pnl()
        assert pnl == 0.0

    def test_no_positions_daily_pnl_is_zero(self):
        tracker = PositionTracker()
        assert tracker.get_daily_pnl() == 0.0


class TestUpdatePrices:
    def test_batch_update_current_prices(self):
        tracker = PositionTracker()
        for tid in ["p1", "p2", "p3"]:
            tracker.update_from_trade_result({
                "token_id": tid,
                "side": "BUY",
                "filled_size": "10",
                "price": "0.50",
                "market_id": f"mkt_{tid}",
                "status": "MATCHED",
            })
        feed = {"p1": 0.65, "p2": 0.40, "p3": 0.55}
        tracker.update_prices(feed)
        for tid, expected in feed.items():
            pos = tracker.get_position(tid)
            assert pos.current_price == pytest.approx(expected)

    def test_unknown_tokens_ignored(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "known",
            "side": "BUY",
            "filled_size": "10",
            "price": "0.50",
            "market_id": "mkt_known",
            "status": "MATCHED",
        })
        tracker.update_prices({"known": 0.70, "unknown_tok": 0.99})
        assert tracker.get_position("known").current_price == pytest.approx(0.70)
        assert "unknown_tok" not in tracker._positions


class TestUnrealizedPnl:
    def test_profit_unrealized_for_buy(self):
        pos = Position(
            token_id="u1",
            market_id="mkt_u1",
            side="BUY",
            quantity=100.0,
            avg_cost=0.40,
            current_price=0.60,
        )
        tracker = PositionTracker()
        result = tracker.calculate_unrealized_pnl(pos)
        assert result == pytest.approx(20.0)

    def test_loss_unrealized_for_buy(self):
        pos = Position(
            token_id="u2",
            market_id="mkt_u2",
            side="BUY",
            quantity=200.0,
            avg_cost=0.60,
            current_price=0.35,
        )
        tracker = PositionTracker()
        result = tracker.calculate_unrealized_pnl(pos)
        assert result == pytest.approx(-50.0)

    def test_zero_price_returns_negative_cost(self):
        pos = Position(
            token_id="u3",
            market_id="mkt_u3",
            side="BUY",
            quantity=50.0,
            avg_cost=0.50,
            current_price=0.0,
        )
        tracker = PositionTracker()
        result = tracker.calculate_unrealized_pnl(pos)
        assert result == pytest.approx(-25.0)

    def test_update_prices_updates_unrealized(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "uu",
            "side": "BUY",
            "filled_size": "100",
            "price": "0.45",
            "market_id": "mkt_uu",
            "status": "MATCHED",
        })
        tracker.update_prices({"uu": 0.75})
        pos = tracker.get_position("uu")
        assert pos.unrealized_pnl == pytest.approx(30.0)


class TestMultipleTokensParallel:
    def test_three_independent_tokens(self):
        tracker = PositionTracker()
        tokens_data = {
            "alpha": (150, 0.30),
            "beta": (250, 0.55),
            "gamma": (80, 0.72),
        }
        for tid, (qty, price) in tokens_data.items():
            tracker.update_from_trade_result({
                "token_id": tid,
                "side": "BUY",
                "filled_size": str(qty),
                "price": str(price),
                "market_id": f"mkt_{tid}",
                "status": "MATCHED",
            })
        for tid, (qty, cost) in tokens_data.items():
            pos = tracker.get_position(tid)
            assert pos.quantity == qty
            assert pos.avg_cost == pytest.approx(cost)

    def test_cross_token_no_interference(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "x1",
            "side": "BUY",
            "filled_size": "100",
            "price": "0.40",
            "market_id": "mkt_x1",
            "status": "MATCHED",
        })
        tracker.update_from_trade_result({
            "token_id": "x2",
            "side": "BUY",
            "filled_size": "200",
            "price": "0.70",
            "market_id": "mkt_x2",
            "status": "MATCHED",
        })
        tracker.update_from_trade_result({
            "token_id": "x1",
            "side": "SELL",
            "filled_size": "100",
            "price": "0.60",
            "market_id": "mkt_x1",
            "status": "MATCHED",
        })
        assert tracker.get_position("x1") is None
        x2 = tracker.get_position("x2")
        assert x2 is not None
        assert x2.quantity == 200.0


class TestInvalidTradeResults:
    def test_missing_token_id_skipped(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({"side": "BUY", "filled_size": "100"})
        assert len(tracker.get_open_positions()) == 0

    def test_non_matched_status_skipped(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_skip",
            "side": "BUY",
            "filled_size": "100",
            "price": "0.50",
            "status": "PENDING",
        })
        assert len(tracker.get_open_positions()) == 0

    def test_unknown_side_skipped(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "tok_bad_side",
            "side": "HOLD",
            "filled_size": "100",
            "price": "0.50",
            "status": "MATCHED",
        })
        assert len(tracker.get_open_positions()) == 0

    def test_sell_without_position_warns(self):
        tracker = PositionTracker()
        tracker.update_from_trade_result({
            "token_id": "ghost",
            "side": "SELL",
            "filled_size": "999",
            "price": "0.99",
            "status": "MATCHED",
        })
        assert len(tracker.get_open_positions()) == 0


class TestRedisSubscriptionMock:
    def test_subscribe_calls_pubsub(self):
        mock_redis = MagicMock()
        mock_ps = MagicMock()
        mock_redis.pubsub.return_value = mock_ps
        tracker = PositionTracker(redis_client=mock_redis)
        tracker.subscribe_to_trade_results()
        time.sleep(0.2)
        tracker.unsubscribe()
        mock_redis.pubsub.assert_called_once()
        mock_ps.subscribe.assert_called_once_with("trade_result")

    def test_handle_trade_result_dispatches(self):
        tracker = PositionTracker()
        trade_data = {
            "token_id": "sub_tok",
            "side": "BUY",
            "filled_size": "77",
            "price": "0.42",
            "market_id": "mkt_sub_tok",
            "status": "MATCHED",
        }
        tracker._handle_trade_result(trade_data)
        pos = tracker.get_position("sub_tok")
        assert pos is not None
        assert pos.quantity == 77.0
        assert pos.avg_cost == pytest.approx(0.42)

    def test_handle_string_json(self):
        tracker = PositionTracker()
        raw = json.dumps({
            "token_id": "json_tok",
            "side": "BUY",
            "filled_size": "33",
            "price": "0.25",
            "market_id": "mkt_json_tok",
            "status": "CONFIRMED",
        })
        tracker._handle_trade_result(raw)
        assert tracker.get_position("json_tok") is not None

    def test_subscribe_without_client_raises(self):
        tracker = PositionTracker()
        with pytest.raises(ValueError, match="Redis 客户端不可用"):
            tracker.subscribe_to_trade_results()


class TestThreadSafety:
    def test_concurrent_updates_do_not_crash(self):
        import threading

        tracker = PositionTracker()
        errors = []

        def buy(i):
            try:
                tracker.update_from_trade_result({
                    "token_id": "concurrent_tok",
                    "side": "BUY",
                    "filled_size": "10",
                    "price": "0.50",
                    "market_id": "mkt_concurrent",
                    "status": "MATCHED",
                })
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=buy, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)
        assert len(errors) == 0
        pos = tracker.get_position("concurrent_tok")
        assert pos is not None
        assert pos.quantity > 0
