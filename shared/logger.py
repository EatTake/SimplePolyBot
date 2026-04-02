from __future__ import annotations

"""
结构化日志模块

基于 structlog 实现的结构化日志系统，支持：
- JSON 格式输出
- 控制台和文件输出
- 日志轮转（按日期或大小）
- 多种日志级别
- 模块名称标识
- 敏感信息过滤
"""

import logging
import logging.handlers
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from typing import Any

import structlog
from structlog.types import Processor


SENSITIVE_PATTERNS = [
    re.compile(r'private[_-]?key', re.IGNORECASE),
    re.compile(r'api[_-]?secret', re.IGNORECASE),
    re.compile(r'api[_-]?key', re.IGNORECASE),
    re.compile(r'api[_-]?passphrase', re.IGNORECASE),
    re.compile(r'password', re.IGNORECASE),
    re.compile(r'token', re.IGNORECASE),
    re.compile(r'secret', re.IGNORECASE),
    re.compile(r'0x[a-fA-F0-9]{64}'),
    re.compile(r'[a-fA-F0-9]{64,}', re.IGNORECASE),
    re.compile(r'cred[_-]?key', re.IGNORECASE),
    re.compile(r'auth[_-]?key', re.IGNORECASE),
    re.compile(r'access[_-]?key', re.IGNORECASE),
]


def filter_sensitive_data(data: Any, max_depth: int = 10) -> Any:
    """
    过滤敏感数据
    
    递归检查数据结构，将敏感字段的值替换为 '***REDACTED***'
    
    参数:
        data: 要过滤的数据
        max_depth: 最大递归深度，防止循环引用
    
    返回:
        过滤后的数据
    """
    if max_depth <= 0:
        return data
    
    if isinstance(data, dict):
        filtered = {}
        for key, value in data.items():
            if isinstance(key, str):
                for pattern in SENSITIVE_PATTERNS:
                    if pattern.search(key):
                        filtered[key] = '***REDACTED***'
                        break
                else:
                    filtered[key] = filter_sensitive_data(value, max_depth - 1)
            else:
                filtered[key] = filter_sensitive_data(value, max_depth - 1)
        return filtered
    elif isinstance(data, (list, tuple)):
        return type(data)(filter_sensitive_data(item, max_depth - 1) for item in data)
    elif isinstance(data, str):
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(data):
                return '***REDACTED***'
        return data
    else:
        return data


def add_timestamp(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    添加时间戳处理器
    
    参数:
        logger: 日志记录器实例
        method_name: 日志方法名称
        event_dict: 事件字典
    
    返回:
        添加时间戳后的事件字典
    """
    event_dict['timestamp'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    return event_dict


def filter_sensitive_processor(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    敏感信息过滤处理器
    
    参数:
        logger: 日志记录器实例
        method_name: 日志方法名称
        event_dict: 事件字典
    
    返回:
        过滤敏感信息后的事件字典
    """
    return filter_sensitive_data(event_dict)


def get_log_level(level: str) -> int:
    """
    将日志级别字符串转换为日志级别常量
    
    参数:
        level: 日志级别字符串（DEBUG、INFO、WARNING、ERROR）
    
    返回:
        日志级别常量
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return level_map.get(level.upper(), logging.INFO)


def setup_logging(
    log_level: str = 'INFO',
    log_dir: str | None = None,
    log_file: str = 'app.log',
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True,
    json_format: bool = True,
) -> None:
    """
    配置结构化日志系统
    
    参数:
        log_level: 日志级别（DEBUG、INFO、WARNING、ERROR）
        log_dir: 日志文件目录，默认为项目根目录下的 logs 文件夹
        log_file: 日志文件名
        max_bytes: 单个日志文件最大字节数，默认 10MB
        backup_count: 保留的日志文件数量，默认 5 个
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
        json_format: 是否使用 JSON 格式输出
    """
    if log_dir is None:
        project_root = Path(__file__).parent.parent
        log_dir = project_root / 'logs'
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    level = get_log_level(log_level)
    
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_timestamp,
        filter_sensitive_processor,
    ]
    
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    root_logger.handlers.clear()
    
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        root_logger.addHandler(console_handler)
    
    if enable_file:
        file_path = log_dir / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        root_logger.addHandler(file_handler)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    获取日志记录器实例
    
    参数:
        name: 模块名称，如果不提供则自动获取调用者模块名
    
    返回:
        结构化日志记录器实例
    """
    if name is None:
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get('__name__', 'unknown')
        else:
            name = 'unknown'
    
    return structlog.get_logger(name)


class LoggerMixin:
    """
    日志记录器混入类
    
    为类提供便捷的日志记录功能
    """
    
    _logger: structlog.stdlib.BoundLogger | None = None
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """
        获取日志记录器实例
        
        返回:
            结构化日志记录器实例
        """
        if self._logger is None:
            self._logger = get_logger(self.__class__.__module__)
        return self._logger


def log_function_call(func):
    """
    函数调用日志装饰器
    
    自动记录函数调用信息和执行时间
    
    参数:
        func: 要装饰的函数
    
    返回:
        装饰后的函数
    """
    import asyncio
    import functools
    import inspect
    import time
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        func_name = func.__name__
        
        logger.debug(
            "函数调用开始",
            function=func_name,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys()),
        )
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            logger.debug(
                "函数调用成功",
                function=func_name,
                elapsed_seconds=round(elapsed_time, 4),
            )
            
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            
            logger.error(
                "函数调用失败",
                function=func_name,
                error_type=type(e).__name__,
                error_message=str(e),
                elapsed_seconds=round(elapsed_time, 4),
            )
            raise
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        func_name = func.__name__
        
        logger.debug(
            "异步函数调用开始",
            function=func_name,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys()),
        )
        
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            logger.debug(
                "异步函数调用成功",
                function=func_name,
                elapsed_seconds=round(elapsed_time, 4),
            )
            
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            
            logger.error(
                "异步函数调用失败",
                function=func_name,
                error_type=type(e).__name__,
                error_message=str(e),
                elapsed_seconds=round(elapsed_time, 4),
            )
            raise
    
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


setup_logging()
