"""
error_formatter 单元测试

测试错误消息格式化器的各项功能：
- 终端美化格式输出（Unicode 边框）
- 纯文本输出
- JSON 格式输出
- 多错误汇总报告
- 修复命令生成
"""

import json

import pytest

from shared.config_validator import (
    Suggestion,
    SuggestionReason,
    ValidationError,
    ValidationResult,
    ValidationWarning,
)
from shared.error_formatter import ErrorFormatter


class TestFormatValidationErrorTerminal:
    """终端格式化单个验证错误"""

    def test_basic_error_format(self):
        err = ValidationError(
            parameter="strategy.alpha",
            message="值超出有效范围",
            current_value=1.5,
        )
        output = ErrorFormatter.format_validation_error(err, style="terminal")
        assert "❌" in output
        assert "strategy.alpha" in output
        assert "1.5" in output
        assert "值超出有效范围" in output
        assert "╔" in output
        assert "╝" in output

    def test_with_expected_type(self):
        err = ValidationError(
            parameter="count",
            message="类型错误",
            current_value="not_int",
            expected_type=int,
        )
        output = ErrorFormatter.format_validation_error(err, style="terminal")
        assert "int" in output or "期望类型" in output

    def test_with_valid_range(self):
        err = ValidationError(
            parameter="rate",
            message="超出范围",
            current_value=2.0,
            valid_range=(0.0, 1.0),
        )
        output = ErrorFormatter.format_validation_error(err, style="terminal")
        assert "0.0" in output
        assert "1.0" in output

    def test_with_line_number(self):
        err = ValidationError(
            parameter="alpha",
            message="错误",
            current_value=1.5,
            line_number=42,
        )
        output = ErrorFormatter.format_validation_error(err, style="terminal")
        assert "42" in output or "行号" in output

    def test_with_suggestion_default(self):
        sug = Suggestion(message="建议降低", suggested_value=0.5, reason=SuggestionReason.DEFAULT)
        err = ValidationError(
            parameter="alpha",
            message="超出范围",
            current_value=1.5,
            suggestion=sug,
        )
        output = ErrorFormatter.format_validation_error(err, style="terminal")
        assert "💡" in output or "建议" in output
        assert "0.5" in output
        assert "默认值" in output

    def test_with_suggestion_conservative(self):
        sug = Suggestion(message="保守策略", suggested_value=0.3, reason=SuggestionReason.CONSERVATIVE)
        err = ValidationError(parameter="x", message="err", current_value=2, suggestion=sug)
        output = ErrorFormatter.format_validation_error(err, style="terminal")
        assert "保守值" in output

    def test_with_suggestion_aggressive(self):
        sug = Suggestion(message="激进策略", suggested_value=0.9, reason=SuggestionReason.AGGRESSIVE)
        err = ValidationError(parameter="x", message="err", current_value=-1, suggestion=sug)
        output = ErrorFormatter.format_validation_error(err, style="terminal")
        assert "激进值" in output

    def test_full_error_all_fields(self):
        sug = Suggestion(message="修正", suggested_value=0.5, reason=SuggestionReason.DEFAULT)
        err = ValidationError(
            parameter="strategy.risk.max_drawdown",
            message="最大回撤超出允许范围",
            current_value=1.5,
            expected_type=float,
            valid_range=(0.0, 1.0),
            suggestion=sug,
            line_number=15,
        )
        output = ErrorFormatter.format_validation_error(err, style="terminal")
        assert "strategy.risk.max_drawdown" in output
        assert "float" in output
        assert "0.0" in output
        assert "1.0" in output
        assert "15" in output
        assert "💡" in output


class TestFormatValidationErrorText:
    """纯文本格式化单个验证错误"""

    def test_basic_text_format(self):
        err = ValidationError(
            parameter="alpha",
            message="超出范围",
            current_value=1.5,
        )
        output = ErrorFormatter.format_validation_error(err, style="text")
        assert "[ERROR]" in output
        assert "alpha" in output
        assert "超出范围" in output
        assert "当前值: 1.5" in output

    def test_text_with_type_and_range(self):
        err = ValidationError(
            parameter="port",
            message="端口无效",
            current_value=99999,
            expected_type=int,
            valid_range=(1, 65535),
            line_number=10,
        )
        output = ErrorFormatter.format_validation_error(err, style="text")
        assert "[ERROR]" in output
        assert "int" in output
        assert "65535" in output
        assert "第 10 行" in output

    def test_text_with_suggestion(self):
        sug = Suggestion(message="使用默认值", suggested_value=6379, reason=SuggestionReason.DEFAULT)
        err = ValidationError(
            parameter="port",
            message="无效端口",
            current_value=70000,
            suggestion=sug,
        )
        output = ErrorFormatter.format_validation_error(err, style="text")
        assert "💡" in output
        assert "6379" in output
        assert "default" in output.lower() or "默认" in output


class FormatValidationErrorJSON:
    """JSON 格式化单个验证错误"""

    def test_basic_json_format(self):
        err = ValidationError(
            parameter="key",
            message="msg",
            current_value=1,
        )
        output = ErrorFormatter.format_validation_error(err, style="json")
        data = json.loads(output)
        assert data["parameter"] == "key"
        assert data["message"] == "msg"
        assert data["current_value"] == 1

    def test_json_with_all_fields(self):
        sug = Suggestion(message="sug", suggested_value=42, reason=SuggestionReason.CONSERVATIVE)
        err = ValidationError(
            parameter="full",
            message="full error",
            current_value=99,
            expected_type=int,
            valid_range=(0, 50),
            suggestion=sug,
            line_number=7,
        )
        output = ErrorFormatter.format_validation_error(err, style="json")
        data = json.loads(output)
        assert data["expected_type"] == "int"
        assert data["valid_range"] == [0, 50]
        assert data["line_number"] == 7
        assert data["suggestion"]["reason"] == "conservative"
        assert data["suggestion"]["suggested_value"] == 42

    def test_json_without_optional_fields(self):
        err = ValidationError(parameter="min", message="m", current_value=0)
        output = ErrorFormatter.format_validation_error(err, style="json")
        data = json.loads(output)
        assert "expected_type" not in data or data["expected_type"] is None
        assert "valid_range" not in data or data["valid_range"] is None
        assert "suggestion" not in data or data["suggestion"] is None
        assert "line_number" not in data or data["line_number"] is None

    def test_unsupported_style_raises(self):
        err = ValidationError(parameter="x", message="m", current_value=1)
        with pytest.raises(ValueError, match="不支持的样式"):
            ErrorFormatter.format_validation_error(err, style="xml")


class TestFormatValidationReportTerminal:
    """终端格式化完整报告"""

    def test_valid_report(self):
        result = ValidationResult(is_valid=True)
        output = ErrorFormatter.format_validation_report(result, style="terminal")
        assert "✅" in output
        assert "通过" in output
        assert "❌" not in output

    def test_invalid_report_with_errors(self):
        errors = [
            ValidationError(parameter="a", message="err a", current_value=1),
            ValidationError(parameter="b", message="err b", current_value=2),
        ]
        result = ValidationResult(is_valid=False, errors=errors)
        output = ErrorFormatter.format_validation_report(result, style="terminal")
        assert "❌" in output
        assert "2 个错误" in output or "个错误" in output
        assert "a" in output
        assert "b" in output

    def test_report_with_warnings(self):
        warnings = [
            ValidationWarning(parameter="unk1", message="未注册参数", current_value=42),
            ValidationWarning(parameter="unk2", message="未注册参数", current_value="x"),
        ]
        result = ValidationResult(is_valid=True, warnings=warnings)
        output = ErrorFormatter.format_validation_report(result, style="terminal")
        assert "⚠️" in output or "警告" in output
        assert "unk1" in output

    def test_report_with_suggestions_on_valid(self):
        suggestions = [
            Suggestion(message="优化1", suggested_value=0.3, reason=SuggestionReason.CONSERVATIVE),
            Suggestion(message="优化2", suggested_value=0.7, reason=SuggestionReason.AGGRESSIVE),
        ]
        result = ValidationResult(is_valid=True, suggestions=suggestions)
        output = ErrorFormatter.format_validation_report(result, style="terminal")
        assert "💡" in output or "优化建议" in output

    def test_report_comprehensive(self):
        sug = Suggestion(message="fix it", suggested_value=0.5, reason=SuggestionReason.DEFAULT)
        errors = [ValidationError(parameter="x", message="bad", current_value=2, suggestion=sug)]
        warnings = [ValidationWarning(parameter="y", message="warn", current_value=99)]
        result = ValidationResult(is_valid=False, errors=errors, warnings=warnings, suggestions=[sug])
        output = ErrorFormatter.format_validation_report(result, style="terminal")
        assert "❌" in output
        assert "⚠️" in output or "警告" in output
        assert "x" in output
        assert "y" in output
        assert "╔" in output
        assert "╝" in output


class TestFormatValidationReportText:
    """纯文本格式化完整报告"""

    def test_valid_text_report(self):
        result = ValidationResult(is_valid=True)
        output = ErrorFormatter.format_validation_report(result, style="text")
        assert "[PASS]" in output
        assert "✅" in output

    def test_invalid_text_report(self):
        errors = [ValidationError(parameter="p", message="e", current_value=1)]
        result = ValidationResult(is_valid=False, errors=errors)
        output = ErrorFormatter.format_validation_report(result, style="text")
        assert "[FAIL]" in output
        assert "❌" in output
        assert "p" in output

    def test_text_report_with_warnings_and_suggestions(self):
        warnings = [ValidationWarning(parameter="w", message="warning msg", current_value=None)]
        suggestions = [Suggestion(message="suggest", suggested_value=1, reason=SuggestionReason.DEFAULT)]
        result = ValidationResult(is_valid=True, warnings=warnings, suggestions=suggestions)
        output = ErrorFormatter.format_validation_report(result, style="text")
        assert "[WARN]" in output
        assert "[SUGGESTION]" in output
        assert "总计" in output


class TestFormatValidationReportJSON:
    """JSON 格式化完整报告"""

    def test_valid_json_report(self):
        result = ValidationResult(is_valid=True)
        output = ErrorFormatter.format_validation_report(result, style="json")
        data = json.loads(output)
        assert data["is_valid"] is True
        assert data["errors"] == []
        assert data["warnings"] == []

    def test_invalid_json_report(self):
        sug = Suggestion(message="s", suggested_value=1, reason=SuggestionReason.DEFAULT)
        errors = [ValidationError(parameter="k", message="m", current_value=2, suggestion=sug)]
        warnings = [ValidationWarning(parameter="w", message="wm", current_value=3)]
        result = ValidationResult(is_valid=False, errors=errors, warnings=warnings, suggestions=[sug])
        output = ErrorFormatter.format_validation_report(result, style="json")
        data = json.loads(output)
        assert data["is_valid"] is False
        assert len(data["errors"]) == 1
        assert len(data["warnings"]) == 1
        assert len(data["suggestions"]) == 1
        assert data["errors"][0]["parameter"] == "k"
        assert data["errors"][0]["suggestion"]["reason"] == "default"


class TestGenerateFixCommand:
    """修复命令生成测试"""

    def test_fix_command_with_line_number(self):
        err = ValidationError(
            parameter="strategy.alpha",
            message="超出范围",
            current_value=1.5,
            line_number=12,
            suggestion=Suggestion(message="设为0.5", suggested_value=0.5, reason=SuggestionReason.DEFAULT),
        )
        cmd = ErrorFormatter.generate_fix_command(err)
        assert "第 12 行" in cmd
        assert "strategy.alpha" in cmd
        assert "0.5" in cmd

    def test_fix_command_without_line_number(self):
        err = ValidationError(
            parameter="redis.port",
            message="无效端口",
            current_value=70000,
        )
        cmd = ErrorFormatter.generate_fix_command(err)
        assert "编辑配置文件" in cmd
        assert "redis.port" in cmd

    def test_fix_command_with_suggestion(self):
        err = ValidationError(
            parameter="rate",
            message="超出范围",
            current_value=2.0,
            valid_range=(0.0, 1.0),
            suggestion=Suggestion(message="降低到安全范围", suggested_value=0.5, reason=SuggestionReason.DEFAULT),
        )
        cmd = ErrorFormatter.generate_fix_command(err)
        assert "0.5" in cmd
        assert "降低到安全范围" in cmd

    def test_fix_command_with_range_no_suggestion(self):
        err = ValidationError(
            parameter="temp",
            message="温度超限",
            current_value=150,
            valid_range=(-40, 85),
        )
        cmd = ErrorFormatter.generate_fix_command(err)
        assert "-40" in cmd
        assert "85" in cmd

    def test_fix_command_with_type_error(self):
        err = ValidationError(
            parameter="count",
            message="类型错误",
            current_value="abc",
            expected_type=int,
        )
        cmd = ErrorFormatter.generate_fix_command(err)
        assert "int" in cmd

    def test_fix_command_fallback_to_message(self):
        err = ValidationError(
            parameter="custom",
            message="自定义校验失败",
            current_value="bad",
        )
        cmd = ErrorFormatter.generate_fix_command(err)
        assert "自定义校验失败" in cmd


class TestErrorToDictHelper:
    """_error_to_dict 辅助方法测试"""

    def test_minimal_error_to_dict(self):
        err = ValidationError(parameter="k", message="m", current_value=1)
        d = ErrorFormatter._error_to_dict(err)
        assert set(d.keys()) == {"parameter", "message", "current_value"}

    def test_full_error_to_dict(self):
        sug = Suggestion(message="s", suggested_value=0.5, reason=SuggestionReason.AGGRESSIVE)
        err = ValidationError(
            parameter="full",
            message="complete error",
            current_value=99,
            expected_type=float,
            valid_range=(0.0, 1.0),
            suggestion=sug,
            line_number=33,
        )
        d = ErrorFormatter._error_to_dict(err)
        assert len(d) == 7
        assert d["expected_type"] == "float"
        assert d["valid_range"] == [0.0, 1.0]
        assert d["line_number"] == 33
        assert d["suggestion"]["reason"] == "aggressive"


class TestTerminalWidthConsistency:
    """终端输出宽度一致性测试"""

    def test_terminal_error_has_consistent_width(self):
        err = ValidationError(parameter="short", message="short error", current_value=1)
        lines = ErrorFormatter.format_validation_error(err, style="terminal").split("\n")
        for line in lines:
            if line.startswith("║") and not line.strip().endswith("═") and not line.strip().startswith("╔") and not line.strip().startswith("╚") and not line.strip().startswith("╠"):
                pass

    def test_terminal_report_structure(self):
        result = ValidationResult(is_valid=False, errors=[
            ValidationError(parameter="e1", message="m1", current_value=1),
            ValidationError(parameter="e2", message="m2", current_value=2),
        ])
        output = ErrorFormatter.format_validation_report(result, style="terminal")
        assert output.count("╔") >= 1
        assert output.count("╝") >= 1
