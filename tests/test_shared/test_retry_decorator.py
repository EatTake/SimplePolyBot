"""
重试装饰器单元测试

测试 with_retry 装饰器的各项功能：
- 可重试异常触发重试
- 不可重试异常立即抛出
- 最大重试次数限制
- 指数退避延迟计算
- 日志记录完整性
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from shared.retry_decorator import with_retry, ClobClientError


class CustomRetryableError(Exception):
    """可重试的自定义异常"""
    pass


class CustomNonRetryableError(Exception):
    """不可重试的自定义异常"""
    pass


class TestRetryableExceptionTriggersRetry:
    """测试可重试异常触发重试"""

    def test_retry_on_matching_exception(self):
        """测试匹配的异常类型触发重试"""
        call_count = 0

        @with_retry(max_retries=2, retry_delay=0.01)
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("连接失败")

        with pytest.raises(ClobClientError):
            failing_func()

        assert call_count == 3

    def test_succeeds_after_retries(self):
        """测试重试后成功"""
        call_count = 0

        @with_retry(max_retries=3, retry_delay=0.01)
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("暂时失败")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_custom_retryable_exception(self):
        """测试自定义可重试异常类型"""
        call_count = 0

        @with_retry(
            max_retries=2,
            retry_delay=0.01,
            retryable_exceptions=(CustomRetryableError,),
        )
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise CustomRetryableError("自定义错误")

        with pytest.raises(ClobClientError):
            failing_func()

        assert call_count == 3


class TestNonRetryableExceptionImmediateRaise:
    """测试不可重试异常立即抛出"""

    def test_non_retryable_exception_not_retried(self):
        """测试不在 retryable_exceptions 中的异常不触发重试"""
        call_count = 0

        @with_retry(
            max_retries=3,
            retry_delay=0.01,
            retryable_exceptions=(ConnectionError,),
        )
        def raising_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("参数错误")

        with pytest.raises(ValueError):
            raising_value_error()

        assert call_count == 1

    def test_non_retryable_with_multiple_retryable_types(self):
        """测试多种可重试异常类型时，非匹配异常立即抛出"""
        call_count = 0

        @with_retry(
            max_retries=3,
            retry_delay=0.01,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        )
        def raising_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("类型错误")

        with pytest.raises(TypeError):
            raising_type_error()

        assert call_count == 1

    def test_default_catches_all_exceptions(self):
        """测试默认配置下所有 Exception 都会重试"""
        call_count = 0

        @with_retry(max_retries=2, retry_delay=0.01)
        def raising_runtime_error():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("运行时错误")

        with pytest.raises(ClobClientError):
            raising_runtime_error()

        assert call_count == 3


class TestMaxRetriesLimit:
    """测试最大重试次数限制"""

    def test_exact_max_retries(self):
        """测试精确执行 max_retries 次重试"""
        call_count = 0

        @with_retry(max_retries=5, retry_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("总是失败")

        with pytest.raises(ClobClientError):
            always_fail()

        assert call_count == 6

    def test_zero_max_retries(self):
        """测试 max_retries=0 时不重试，只尝试一次"""
        call_count = 0

        @with_retry(max_retries=0, retry_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("失败")

        with pytest.raises(ClobClientError) as exc_info:
            always_fail()

        assert call_count == 1
        assert "重试0次后仍然失败" in str(exc_info.value)

    def test_one_max_retry(self):
        """测试 max_retries=1 时总共尝试 2 次"""
        call_count = 0

        @with_retry(max_retries=1, retry_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("失败")

        with pytest.raises(ClobClientError):
            always_fail()

        assert call_count == 2


class TestExponentialBackoff:
    """测试指数退避延迟计算"""

    def test_backoff_delays(self):
        """测试延迟按指数增长: delay * (backoff_factor ** (n-1))"""
        sleep_times = []

        with patch('shared.retry_decorator.time.sleep') as mock_sleep:
            mock_sleep.side_effect = lambda t: sleep_times.append(t)

            @with_retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0)
            def always_fail():
                raise Exception("失败")

            try:
                always_fail()
            except ClobClientError:
                pass

        assert len(sleep_times) == 3
        assert sleep_times[0] == 1.0
        assert sleep_times[1] == 2.0
        assert sleep_times[2] == 4.0

    def test_custom_backoff_factor(self):
        """测试自定义退避因子"""
        sleep_times = []

        with patch('shared.retry_decorator.time.sleep') as mock_sleep:
            mock_sleep.side_effect = lambda t: sleep_times.append(t)

            @with_retry(max_retries=2, retry_delay=0.5, backoff_factor=3.0)
            def always_fail():
                raise Exception("失败")

            try:
                always_fail()
            except ClobClientError:
                pass

        assert len(sleep_times) == 2
        assert sleep_times[0] == 0.5
        assert sleep_times[1] == 1.5

    def test_no_delay_when_zero_retry_delay(self):
        """测试 retry_delay=0 时无等待"""
        sleep_times = []

        with patch('shared.retry_decorator.time.sleep') as mock_sleep:
            mock_sleep.side_effect = lambda t: sleep_times.append(t)

            @with_retry(max_retries=2, retry_delay=0.0, backoff_factor=2.0)
            def always_fail():
                raise Exception("失败")

            try:
                always_fail()
            except ClobClientError:
                pass

        assert all(t == 0.0 for t in sleep_times)


class TestLoggingCompleteness:
    """测试日志记录完整性"""

    def test_warning_logged_on_each_retry(self):
        """测试每次重试都记录 warning 日志"""
        warning_calls = []
        error_calls = []

        with patch('shared.retry_decorator.logger') as mock_logger:
            mock_logger.warning.side_effect = lambda *args, **kw: warning_calls.append(kw)
            mock_logger.error.side_effect = lambda *args, **kw: error_calls.append(kw)

            @with_retry(max_retries=2, retry_delay=0.01)
            def always_fail():
                raise ConnectionError("连接超时")

            try:
                always_fail()
            except ClobClientError:
                pass

        assert len(warning_calls) == 2
        for i, log_entry in enumerate(warning_calls):
            assert log_entry['function'] == 'always_fail'
            assert log_entry['attempt'] == i + 1
            assert log_entry['max_retries'] == 2
            assert 'delay' in log_entry
            assert log_entry['error'] == '连接超时'

    def test_error_logged_on_final_failure(self):
        """测试最终失败时记录 error 日志"""
        error_calls = []

        with patch('shared.retry_decorator.logger') as mock_logger:
            mock_logger.error.side_effect = lambda *args, **kw: error_calls.append(kw)

            @with_retry(max_retries=2, retry_delay=0.01)
            def always_fail():
                raise ValueError("值错误")

            try:
                always_fail()
            except ClobClientError:
                pass

        assert len(error_calls) == 1
        assert error_calls[0]['function'] == 'always_fail'
        assert error_calls[0]['attempts'] == 3
        assert error_calls[0]['error'] == '值错误'

    def test_log_contains_function_name(self):
        """测试日志包含正确的函数名称"""
        warning_calls = []

        with patch('shared.retry_decorator.logger') as mock_logger:
            mock_logger.warning.side_effect = lambda *args, **kw: warning_calls.append(kw)

            @with_retry(max_retries=1, retry_delay=0.01)
            def my_custom_function_name():
                raise RuntimeError("错误")

            try:
                my_custom_function_name()
            except ClobClientError:
                pass

        assert len(warning_calls) == 1
        assert warning_calls[0]['function'] == 'my_custom_function_name'

    def test_log_contains_attempt_and_max_retries(self):
        """测试日志包含尝试次数和最大重试次数"""
        warning_calls = []

        with patch('shared.retry_decorator.logger') as mock_logger:
            mock_logger.warning.side_effect = lambda *args, **kw: warning_calls.append(kw)

            @with_retry(max_retries=3, retry_delay=0.01)
            def flaky_func():
                raise IOError("IO 错误")

            try:
                flaky_func()
            except ClobClientError:
                pass

        for i, entry in enumerate(warning_calls):
            assert entry['attempt'] == i + 1
            assert entry['max_retries'] == 3

    def test_log_contains_current_delay(self):
        """测试日志包含当前延迟时间"""
        warning_calls = []

        with patch('shared.retry_decorator.time.sleep'):
            with patch('shared.retry_decorator.logger') as mock_logger:
                mock_logger.warning.side_effect = lambda *args, **kw: warning_calls.append(kw)

                @with_retry(max_retries=2, retry_delay=1.0, backoff_factor=2.0)
                def fail_func():
                    raise Exception("失败")

                try:
                    fail_func()
                except ClobClientError:
                    pass

        assert warning_calls[0]['delay'] == 1.0
        assert warning_calls[1]['delay'] == 2.0

    def test_log_contains_error_message(self):
        """测试日志包含错误信息"""
        warning_calls = []

        with patch('shared.retry_decorator.logger') as mock_logger:
            mock_logger.warning.side_effect = lambda *args, **kw: warning_calls.append(kw)

            @with_retry(max_retries=1, retry_delay=0.01)
            def specific_error():
                raise KeyError("找不到键: token_12345")

            try:
                specific_error()
            except ClobClientError:
                pass

        assert warning_calls[0]['error'] == "'找不到键: token_12345'"


class TestClobClientErrorMessage:
    """测试 ClobClientError 异常消息格式"""

    def test_error_message_format(self):
        """测试异常消息格式正确"""
        with pytest.raises(ClobClientError) as exc_info:
            @with_retry(max_retries=2, retry_delay=0.01)
            def fail():
                raise ConnectionError("网络断开")

            fail()

        assert "重试2次后仍然失败" in str(exc_info.value)
        assert "网络断开" in str(exc_info.value)

    def test_error_message_preserves_original_exception(self):
        """测试原始异常信息被保留在消息中"""
        original_error = TimeoutError("请求超时: 30s")

        with pytest.raises(ClobClientError) as exc_info:
            @with_retry(max_retries=1, retry_delay=0.01)
            def fail():
                raise original_error

            fail()

        error_msg = str(exc_info.value)
        assert "重试1次后仍然失败" in error_msg
        assert "请求超时: 30s" in error_msg


class TestPreserveFunctionMetadata:
    """测试函数元数据保留"""

    def test_preserves_function_name(self):
        """测试装饰器保留函数名"""
        @with_retry()
        def my_function():
            pass

        assert my_function.__name__ == 'my_function'

    def test_preserves_docstring(self):
        """测试装饰器保留文档字符串"""
        @with_retry()
        def documented_function():
            """这是函数的文档字符串"""
            pass

        assert documented_function.__doc__ == '这是函数的文档字符串'

    def test_preserves_module(self):
        """测试装饰器保留模块名"""
        @with_retry()
        def module_function():
            pass

        assert module_function.__module__ == __name__
