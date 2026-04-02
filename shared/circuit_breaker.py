from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone
from typing import Any, Callable


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.total_requests = 0
        self.total_failures = 0

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        self.total_requests += 1

        if self.state == CircuitState.OPEN:
            now = datetime.now(timezone.utc)
            assert self.last_failure_time is not None
            elapsed = (now - self.last_failure_time).total_seconds()
            if elapsed >= self.timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"断路器处于 OPEN 状态，剩余冷却时间: {self.timeout_seconds - elapsed:.2f}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN

    def get_stats(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "success_rate": round(
                (self.total_requests - self.total_failures) / max(self.total_requests, 1), 4
            ),
            "timeout_seconds": self.timeout_seconds,
        }
