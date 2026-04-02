"""
ErrorContext 单元测试

测试 ErrorContext 类和工厂函数的各项功能：
- 基本创建和 to_dict()
- 上下文管理器（with 语句）
- 异常时自动捕获异常信息
- 时间戳自动生成
- 持续时间计算
"""

import time

import pytest

from shared.error_context import ErrorContext, create_error_context


class TestBasicCreationAndToDict:
    """测试基本创建和 to_dict()"""

    def test_create_with_operation_only(self):
        ctx = ErrorContext("test_operation")
        result = ctx.to_dict()

        assert result["operation"] == "test_operation"
        assert result["context"] == {}
        assert "timestamp" in result
        assert "duration" not in result

    def test_create_with_context_kwargs(self):
        ctx = ErrorContext("create_order", token_id="abc123", price=0.5, size=100)
        result = ctx.to_dict()

        assert result["operation"] == "create_order"
        assert result["context"]["token_id"] == "abc123"
        assert result["context"]["price"] == 0.5
        assert result["context"]["size"] == 100

    def test_to_dict_returns_copy(self):
        ctx = ErrorContext("op", key="value")
        result1 = ctx.to_dict()
        result2 = ctx.to_dict()

        assert result1 is not result2
        assert result1 == result2

    def test_context_is_mutable_dict(self):
        ctx = ErrorContext("op")
        ctx.context["dynamic_key"] = "dynamic_value"

        result = ctx.to_dict()
        assert result["context"]["dynamic_key"] == "dynamic_value"


class TestContextManager:
    """测试上下文管理器（with 语句）"""

    def test_enter_returns_self(self):
        with ErrorContext("test") as ctx:
            assert isinstance(ctx, ErrorContext)
            assert ctx.operation == "test"

    def test_exit_returns_false_on_no_exception(self):
        with ErrorContext("test") as ctx:
            pass

        result = ctx.to_dict()
        assert "duration" in result
        assert result["duration"] >= 0
        assert "exception" not in result.get("context", {})

    def test_exit_does_not_swallow_exception(self):
        with pytest.raises(ValueError, match="test error"):
            with ErrorContext("test"):
                raise ValueError("test error")

    def test_duration_calculated_after_with_block(self):
        with ErrorContext("timed_op") as ctx:
            time.sleep(0.05)

        result = ctx.to_dict()
        assert "duration" in result
        assert result["duration"] >= 0.04


class TestExceptionAutoCapture:
    """测试异常时自动捕获异常信息"""

    def test_exception_info_captured_in_context(self):
        try:
            with ErrorContext("failing_op") as ctx:
                raise RuntimeError("something went wrong")
        except RuntimeError:
            pass

        result = ctx.to_dict()
        assert "exception" in result["context"]
        assert result["context"]["exception"]["type"] == "RuntimeError"
        assert result["context"]["exception"]["message"] == "something went wrong"

    def test_value_error_captured(self):
        try:
            with ErrorContext("validate") as ctx:
                raise ValueError("invalid input")
        except ValueError:
            pass

        exc_info = ctx.context.get("exception")
        assert exc_info is not None
        assert exc_info["type"] == "ValueError"
        assert exc_info["message"] == "invalid input"

    def test_no_exception_when_successful(self):
        with ErrorContext("success_op") as ctx:
            result = 42

        assert "exception" not in ctx.context
        assert result == 42

    def test_multiple_exceptions_overwrite(self):
        try:
            with ErrorContext("multi") as ctx:
                raise OSError("first error")
        except OSError:
            pass

        first_exc = ctx.context.get("exception")
        assert first_exc["type"] == "OSError"


class TestTimestampAutoGeneration:
    """测试时间戳自动生成"""

    def test_timestamp_is_iso_format(self):
        before = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        ctx = ErrorContext("ts_test")
        after = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

        ts_str = ctx.timestamp.isoformat()
        parsed_ts = __import__("datetime").datetime.fromisoformat(ts_str)

        assert before <= parsed_ts <= after

    def test_timestamp_is_utc(self):
        ctx = ErrorContext("utc_test")
        assert ctx.timestamp.tzinfo is not None

    def test_timestamp_in_to_dict(self):
        ctx = ErrorContext("op")
        result = ctx.to_dict()
        assert "T" in result["timestamp"]
        assert "+" in result["timestamp"] or result["timestamp"].endswith("Z")


class TestDurationCalculation:
    """测试持续时间计算"""

    def test_duration_not_present_before_with(self):
        ctx = ErrorContext("op")
        result = ctx.to_dict()
        assert "duration" not in result

    def test_duration_present_after_with(self):
        with ErrorContext("op") as ctx:
            time.sleep(0.02)

        result = ctx.to_dict()
        assert "duration" in result
        assert isinstance(result["duration"], float)

    def test_duration_accuracy(self):
        sleep_time = 0.1
        with ErrorContext("op") as ctx:
            time.sleep(sleep_time)

        duration = ctx.to_dict()["duration"]
        assert abs(duration - sleep_time) < 0.05

    def test_duration_rounded(self):
        with ErrorContext("op") as ctx:
            time.sleep(0.001)

        duration = ctx.to_dict()["duration"]
        decimal_places = len(str(duration).split(".")[-1]) if "." in str(duration) else 0
        assert decimal_places <= 6


class TestFactoryFunction:
    """测试工厂函数 create_error_context"""

    def test_factory_creates_instance(self):
        ctx = create_error_context("factory_op")
        assert isinstance(ctx, ErrorContext)
        assert ctx.operation == "factory_op"

    def test_factory_passes_context(self):
        ctx = create_error_context("factory_op", key1="val1", key2=42)
        assert ctx.context["key1"] == "val1"
        assert ctx.context["key2"] == 42

    def test_factory_used_in_with_statement(self):
        with create_error_context("factory_with", x=1) as ctx:
            assert ctx.operation == "factory_with"
            assert ctx.context["x"] == 1
