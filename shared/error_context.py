from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal


class ErrorContext:
    """
    错误上下文管理器

    用于在操作执行过程中收集结构化的错误上下文信息，
    支持作为上下文管理器使用，自动记录时间戳和持续时间。

    示例:
        >>> with ErrorContext("create_order", token_id="abc", price=0.5) as ctx:
        ...     result = submit_order(...)
        >>> print(ctx.to_dict())
    """

    def __init__(self, operation: str, **context: Any) -> None:
        self.operation = operation
        self.context: dict[str, Any] = dict(context)
        self.timestamp = datetime.now(timezone.utc)
        self._start_time: datetime | None = None
        self._duration: float | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "operation": self.operation,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }
        if self._duration is not None:
            result["duration"] = round(self._duration, 6)
        return result

    def __enter__(self: ErrorContext) -> ErrorContext:
        self._start_time = datetime.now(timezone.utc)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> Literal[False]:
        if self._start_time is not None:
            end_time = datetime.now(timezone.utc)
            self._duration = (end_time - self._start_time).total_seconds()
        if exc_type is not None:
            self.context["exception"] = {
                "type": exc_type.__name__,
                "message": str(exc_val),
            }
        return False


def create_error_context(operation: str, **context: Any) -> ErrorContext:
    """工厂函数，快速创建 ErrorContext 实例"""
    return ErrorContext(operation, **context)
