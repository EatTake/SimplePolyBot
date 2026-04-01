"""
日志模块单元测试

测试日志记录功能，包括：
- 日志级别
- JSON 格式输出
- 敏感信息过滤
- 日志轮转
- 模块名称标识
"""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import structlog

from shared.logger import (
    LoggerMixin,
    add_timestamp,
    filter_sensitive_data,
    filter_sensitive_processor,
    get_log_level,
    get_logger,
    log_function_call,
    setup_logging,
)


class TestFilterSensitiveData:
    """测试敏感数据过滤功能"""
    
    def test_filter_private_key(self):
        """测试过滤私钥字段"""
        data = {
            'private_key': '0x1234567890abcdef',
            'public_key': '0xabcdef1234567890',
        }
        
        filtered = filter_sensitive_data(data)
        
        assert filtered['private_key'] == '***REDACTED***'
        assert filtered['public_key'] == '0xabcdef1234567890'
    
    def test_filter_api_secret(self):
        """测试过滤 API Secret 字段"""
        data = {
            'api_secret': 'my-secret-key',
            'api_key': 'my-api-key',
            'user_id': '12345',
        }
        
        filtered = filter_sensitive_data(data)
        
        assert filtered['api_secret'] == '***REDACTED***'
        assert filtered['api_key'] == '***REDACTED***'
        assert filtered['user_id'] == '12345'
    
    def test_filter_password(self):
        """测试过滤密码字段"""
        data = {
            'password': 'my-password',
            'username': 'admin',
        }
        
        filtered = filter_sensitive_data(data)
        
        assert filtered['password'] == '***REDACTED***'
        assert filtered['username'] == 'admin'
    
    def test_filter_token(self):
        """测试过滤令牌字段"""
        data = {
            'token': 'bearer-token-123',
            'session_id': 'session-456',
        }
        
        filtered = filter_sensitive_data(data)
        
        assert filtered['token'] == '***REDACTED***'
        assert filtered['session_id'] == 'session-456'
    
    def test_filter_ethereum_private_key(self):
        """测试过滤以太坊私钥格式"""
        data = {
            'key': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        }
        
        filtered = filter_sensitive_data(data)
        
        assert filtered['key'] == '***REDACTED***'
    
    def test_filter_nested_dict(self):
        """测试过滤嵌套字典"""
        data = {
            'user': {
                'name': 'Alice',
                'credentials': {
                    'api_key': 'secret-key',
                    'password': 'secret-pass',
                },
            },
        }
        
        filtered = filter_sensitive_data(data)
        
        assert filtered['user']['name'] == 'Alice'
        assert filtered['user']['credentials']['api_key'] == '***REDACTED***'
        assert filtered['user']['credentials']['password'] == '***REDACTED***'
    
    def test_filter_list(self):
        """测试过滤列表"""
        data = {
            'keys': [
                {'api_key': 'key1'},
                {'api_key': 'key2'},
            ],
        }
        
        filtered = filter_sensitive_data(data)
        
        assert filtered['keys'][0]['api_key'] == '***REDACTED***'
        assert filtered['keys'][1]['api_key'] == '***REDACTED***'
    
    def test_filter_string_value(self):
        """测试过滤字符串值"""
        data = 'private_key=0x1234567890abcdef'
        
        filtered = filter_sensitive_data(data)
        
        assert filtered == '***REDACTED***'


class TestAddTimestamp:
    """测试时间戳添加功能"""
    
    def test_add_timestamp(self):
        """测试添加时间戳"""
        event_dict = {'message': 'test'}
        
        result = add_timestamp(None, 'info', event_dict)
        
        assert 'timestamp' in result
        assert result['message'] == 'test'
        assert 'T' in result['timestamp']
        assert 'Z' in result['timestamp']


class TestFilterSensitiveProcessor:
    """测试敏感信息过滤处理器"""
    
    def test_processor_filters_sensitive_data(self):
        """测试处理器过滤敏感数据"""
        event_dict = {
            'message': 'login',
            'password': 'secret123',
            'username': 'admin',
        }
        
        result = filter_sensitive_processor(None, 'info', event_dict)
        
        assert result['password'] == '***REDACTED***'
        assert result['username'] == 'admin'


class TestGetLogLevel:
    """测试日志级别转换功能"""
    
    def test_debug_level(self):
        """测试 DEBUG 级别"""
        level = get_log_level('DEBUG')
        assert level == logging.DEBUG
    
    def test_info_level(self):
        """测试 INFO 级别"""
        level = get_log_level('INFO')
        assert level == logging.INFO
    
    def test_warning_level(self):
        """测试 WARNING 级别"""
        level = get_log_level('WARNING')
        assert level == logging.WARNING
    
    def test_error_level(self):
        """测试 ERROR 级别"""
        level = get_log_level('ERROR')
        assert level == logging.ERROR
    
    def test_critical_level(self):
        """测试 CRITICAL 级别"""
        level = get_log_level('CRITICAL')
        assert level == logging.CRITICAL
    
    def test_invalid_level_defaults_to_info(self):
        """测试无效级别默认为 INFO"""
        level = get_log_level('INVALID')
        assert level == logging.INFO
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        level = get_log_level('debug')
        assert level == logging.DEBUG


class TestSetupLogging:
    """测试日志配置功能"""
    
    def test_setup_with_default_config(self):
        """测试默认配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                enable_console=True,
                enable_file=True,
            )
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO
            assert len(root_logger.handlers) == 2
    
    def test_setup_with_custom_log_level(self):
        """测试自定义日志级别"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='DEBUG',
                log_dir=tmpdir,
                enable_console=True,
                enable_file=True,
            )
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG
    
    def test_setup_console_only(self):
        """测试仅控制台输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                enable_console=True,
                enable_file=False,
            )
            
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 1
            assert isinstance(root_logger.handlers[0], logging.StreamHandler)
    
    def test_setup_file_only(self):
        """测试仅文件输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
            )
            
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 1
            assert isinstance(root_logger.handlers[0], logging.handlers.RotatingFileHandler)
    
    def test_log_file_created(self):
        """测试日志文件创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                log_file='test.log',
                enable_console=False,
                enable_file=True,
            )
            
            logger = get_logger('test')
            logger.info("测试消息")
            
            log_file = Path(tmpdir) / 'test.log'
            assert log_file.exists()


class TestGetLogger:
    """测试获取日志记录器功能"""
    
    def test_get_logger_with_name(self):
        """测试使用名称获取日志记录器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                enable_console=False,
                enable_file=False,
            )
            
            logger = get_logger('test_module')
            
            assert logger is not None
            assert isinstance(logger, structlog.stdlib.BoundLogger)
    
    def test_get_logger_without_name(self):
        """测试自动获取模块名"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                enable_console=False,
                enable_file=False,
            )
            
            logger = get_logger()
            
            assert logger is not None
            assert isinstance(logger, structlog.stdlib.BoundLogger)


class TestLoggerMixin:
    """测试日志混入类"""
    
    def test_logger_mixin(self):
        """测试混入类功能"""
        class TestClass(LoggerMixin):
            def do_something(self):
                self.logger.info("执行操作")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
            )
            
            obj = TestClass()
            obj.do_something()
            
            assert obj._logger is not None


class TestLogFunctionCall:
    """测试函数调用日志装饰器"""
    
    def test_sync_function_success(self):
        """测试同步函数成功调用"""
        @log_function_call
        def add(a, b):
            return a + b
        
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='DEBUG',
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
            )
            
            result = add(2, 3)
            
            assert result == 5
    
    def test_sync_function_failure(self):
        """测试同步函数失败调用"""
        @log_function_call
        def divide(a, b):
            return a / b
        
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='DEBUG',
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
            )
            
            with pytest.raises(ZeroDivisionError):
                divide(1, 0)
    
    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """测试异步函数成功调用"""
        @log_function_call
        async def async_add(a, b):
            return a + b
        
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='DEBUG',
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
            )
            
            result = await async_add(2, 3)
            
            assert result == 5
    
    @pytest.mark.asyncio
    async def test_async_function_failure(self):
        """测试异步函数失败调用"""
        @log_function_call
        async def async_divide(a, b):
            return a / b
        
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='DEBUG',
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
            )
            
            with pytest.raises(ZeroDivisionError):
                await async_divide(1, 0)


class TestJSONFormat:
    """测试 JSON 格式输出"""
    
    def test_json_output(self):
        """测试 JSON 格式日志输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                log_file='json_test.log',
                enable_console=False,
                enable_file=True,
                json_format=True,
            )
            
            logger = get_logger('json_test')
            logger.info("测试消息", user_id="123", action="login")
            
            log_file = Path(tmpdir) / 'json_test.log'
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                log_entry = json.loads(content.strip())
                
                assert 'timestamp' in log_entry
                assert 'level' in log_entry
                assert 'event' in log_entry
                assert log_entry['event'] == '测试消息'
                assert log_entry['user_id'] == '123'
                assert log_entry['action'] == 'login'


class TestLogRotation:
    """测试日志轮转功能"""
    
    def test_log_rotation_by_size(self):
        """测试按大小轮转日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                log_file='rotation_test.log',
                max_bytes=100,
                backup_count=3,
                enable_console=False,
                enable_file=True,
            )
            
            logger = get_logger('rotation_test')
            
            for i in range(20):
                logger.info("测试消息" * 10, iteration=i)
            
            log_dir = Path(tmpdir)
            log_files = list(log_dir.glob('rotation_test.log*'))
            
            assert len(log_files) > 1


class TestModuleIdentification:
    """测试模块名称标识"""
    
    def test_module_name_in_log(self):
        """测试日志中包含模块名称"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level='INFO',
                log_dir=tmpdir,
                log_file='module_test.log',
                enable_console=False,
                enable_file=True,
                json_format=True,
            )
            
            logger = get_logger('my_module.submodule')
            logger.info("模块测试")
            
            log_file = Path(tmpdir) / 'module_test.log'
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                log_entry = json.loads(content.strip())
                
                assert 'logger' in log_entry
                assert log_entry['logger'] == 'my_module.submodule'
