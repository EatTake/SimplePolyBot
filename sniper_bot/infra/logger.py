"""
结构化日志模块

统一日志格式，自动脱敏敏感信息（私钥、API Key 等）
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Optional


# 需要脱敏的正则模式
_SENSITIVE_PATTERNS = [
    (re.compile(r"(0x[a-fA-F0-9]{64})", re.IGNORECASE), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"(key[_-]?\w*[=:]\s*)([a-zA-Z0-9\-_]{20,})", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(secret[_-]?\w*[=:]\s*)([a-zA-Z0-9\-_+/]{16,})", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(passphrase[=:]\s*)(\S+)", re.IGNORECASE), r"\1[REDACTED]"),
]


class SensitiveFilter(logging.Filter):
    """日志过滤器：自动脱敏敏感信息"""

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        return True


def _redact(text: str) -> str:
    """对文本中的敏感信息进行脱敏"""
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """
    初始化全局日志配置

    Args:
        level: 日志级别
        log_file: 日志文件路径（可选）
    """
    fmt = "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = []

    # 控制台输出
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt, datefmt))
    console.addFilter(SensitiveFilter())
    handlers.append(console)

    # 文件输出
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt, datefmt))
        file_handler.addFilter(SensitiveFilter())
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
        force=True,
    )

    # 降低第三方库日志级别
    for name in ("websockets", "urllib3", "httpx", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)
