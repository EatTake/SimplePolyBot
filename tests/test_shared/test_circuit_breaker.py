import time
from unittest.mock import MagicMock

import pytest

from shared.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestCircuitState:
    def test_enum_values(self):
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerOpenError:
    def test_is_exception(self):
        assert issubclass(CircuitBreakerOpenError, Exception)

    def test_message(self):
        error = CircuitBreakerOpenError("test message")
        assert str(error) == "test message"


class TestCircuitBreakerInit:
    def test_default_values(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.timeout_seconds == 60.0
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert cb.total_requests == 0
        assert cb.total_failures == 0

    def test_custom_values(self):
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=30.0)
        assert cb.failure_threshold == 3
        assert cb.timeout_seconds == 30.0


class TestNormalRequestPasses:
    def test_closed_state_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        func = MagicMock(return_value="success")

        result = cb.call(func)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.total_requests == 1
        assert cb.total_failures == 0


class TestConsecutiveFailuresTriggerOpen:
    def test_failure_count_increments(self):
        cb = CircuitBreaker(failure_threshold=3)
        func = MagicMock(side_effect=ValueError("error"))

        with pytest.raises(ValueError):
            cb.call(func)

        assert cb.failure_count == 1
        assert cb.total_failures == 1
        assert cb.state == CircuitState.CLOSED

    def test_reaches_threshold_opens_circuit(self):
        cb = CircuitBreaker(failure_threshold=3)
        failing_func = MagicMock(side_effect=ValueError("error"))

        for i in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3
        assert cb.total_failures == 3

    def test_partial_failures_do_not_trigger(self):
        cb = CircuitBreaker(failure_threshold=3)
        fail_func = MagicMock(side_effect=ValueError("fail"))
        success_func = MagicMock(return_value="ok")

        with pytest.raises(ValueError):
            cb.call(fail_func)
        assert cb.call(success_func) == "ok"
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

        with pytest.raises(ValueError):
            cb.call(fail_func)
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED


class TestOpenStateRejectsRequests:
    def test_open_state_raises_error(self):
        cb = CircuitBreaker(failure_threshold=2)
        fail_func = MagicMock(side_effect=ValueError("fail"))

        with pytest.raises(ValueError):
            cb.call(fail_func)
        with pytest.raises(ValueError):
            cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        any_func = MagicMock(return_value="ok")
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(any_func)

        assert any_func.call_count == 0


class TestTimeoutTransitionsToHalfOpen:
    def test_timeout_transitions_to_half_open(self):
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0.1)
        fail_func = MagicMock(side_effect=ValueError("fail"))

        with pytest.raises(ValueError):
            cb.call(fail_func)
        with pytest.raises(ValueError):
            cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)

        success_func = MagicMock(return_value="recovered")
        result = cb.call(success_func)

        assert result == "recovered"
        assert cb.state == CircuitState.HALF_OPEN or cb.state == CircuitState.CLOSED


class TestHalfOpenProbeSuccess:
    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0.1)
        fail_func = MagicMock(side_effect=ValueError("fail"))

        with pytest.raises(ValueError):
            cb.call(fail_func)
        with pytest.raises(ValueError):
            cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)

        success_func = MagicMock(return_value="recovered")
        result = cb.call(success_func)

        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


class TestHalfOpenProbeFailure:
    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0.1)
        fail_func = MagicMock(side_effect=ValueError("fail"))

        with pytest.raises(ValueError):
            cb.call(fail_func)
        with pytest.raises(ValueError):
            cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)

        still_failing = MagicMock(side_effect=RuntimeError("still broken"))
        with pytest.raises(RuntimeError):
            cb.call(still_failing)

        assert cb.state == CircuitState.OPEN


class TestStatsAccuracy:
    def test_stats_after_mixed_calls(self):
        cb = CircuitBreaker(failure_threshold=10)
        success = MagicMock(return_value="ok")
        fail = MagicMock(side_effect=Exception("err"))

        for _ in range(7):
            cb.call(success)

        for _ in range(3):
            with pytest.raises(Exception):
                cb.call(fail)

        stats = cb.get_stats()

        assert stats["state"] == "closed"
        assert stats["failure_count"] == 3
        assert stats["total_requests"] == 10
        assert stats["total_failures"] == 3
        assert stats["success_rate"] == 0.7

    def test_stats_keys(self):
        cb = CircuitBreaker()
        stats = cb.get_stats()

        expected_keys = {
            "state",
            "failure_count",
            "failure_threshold",
            "last_failure_time",
            "total_requests",
            "total_failures",
            "success_rate",
            "timeout_seconds",
        }
        assert set(stats.keys()) == expected_keys

    def test_stats_no_failures(self):
        cb = CircuitBreaker()
        ok = MagicMock(return_value="x")
        cb.call(ok)

        stats = cb.get_stats()
        assert stats["success_rate"] == 1.0
        assert stats["last_failure_time"] is None
