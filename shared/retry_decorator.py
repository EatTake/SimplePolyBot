from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar('T')


class ClobClientError(Exception):
    """CLOB 客户端异常"""
    pass


def with_retry(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    通用重试装饰器

    使用指数退避算法对函数调用进行自动重试。

    Args:
        max_retries: 最大重试次数（默认 3）
        retry_delay: 初始重试延迟，单位秒（默认 1.0）
        backoff_factor: 退避因子，第 n 次重试延迟 = retry_delay * (backoff_factor ** (n-1))（默认 2.0）
        retryable_exceptions: 可重试的异常类型元组，只有这些异常才会触发重试（默认所有 Exception）

    Returns:
        装饰器函数

    示例:
        >>> @with_retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0)
        ... def fetch_data():
        ...     return api_call()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            current_delay = retry_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "API调用失败，准备重试",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=current_delay,
                            error=str(e),
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            "API调用失败，已达到最大重试次数",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e),
                        )

            raise ClobClientError(f"重试{max_retries}次后仍然失败: {last_exception}")

        return wrapper
    return decorator
