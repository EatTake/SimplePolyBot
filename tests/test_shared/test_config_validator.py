"""
config_validator 单元测试

测试配置验证器的各项功能：
- 各验证器（Type/Range/Choice/Required/Dependency）的正确性
- ValidationResult 多错误收集
- 智能建议生成逻辑
- ParameterRegistry 注册与查询
- 边界条件处理
"""

import pytest

from shared.config_validator import (
    ChoiceValidator,
    ConfigValidator,
    DependencyValidator,
    ParameterInfo,
    ParameterRegistry,
    RangeValidator,
    RequiredValidator,
    Suggestion,
    SuggestionReason,
    TypeValidator,
    ValidationError,
    ValidationWarning,
    ValidationResult,
)


class TestSuggestionAndDataClasses:
    """测试数据类和枚举"""

    def test_suggestion_creation(self):
        sug = Suggestion(message="test", suggested_value=0.5, reason=SuggestionReason.DEFAULT)
        assert sug.message == "test"
        assert sug.suggested_value == 0.5
        assert sug.reason == SuggestionReason.DEFAULT

    def test_validation_error_creation(self):
        err = ValidationError(
            parameter="strategy.alpha",
            message="值超出范围",
            current_value=1.5,
            expected_type=float,
            valid_range=(0.0, 1.0),
        )
        assert err.parameter == "strategy.alpha"
        assert err.current_value == 1.5
        assert err.suggestion is None

    def test_validation_error_with_suggestion(self):
        sug = Suggestion(message="建议", suggested_value=0.5, reason=SuggestionReason.DEFAULT)
        err = ValidationError(
            parameter="x",
            message="err",
            current_value=2,
            suggestion=sug,
        )
        assert err.suggestion is not None
        assert err.suggestion.suggested_value == 0.5

    def test_validation_warning_creation(self):
        warn = ValidationWarning(parameter="unknown_key", message="未注册参数", current_value=42)
        assert warn.parameter == "unknown_key"

    def test_validation_result_valid(self):
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validation_result_invalid_with_errors(self):
        err = ValidationError(parameter="a", message="error a", current_value=1)
        result = ValidationResult(is_valid=False, errors=[err])
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_result_to_dict_empty(self):
        result = ValidationResult(is_valid=True)
        d = result.to_dict()
        assert d["is_valid"] is True
        assert d["errors"] == []
        assert d["warnings"] == []
        assert d["suggestions"] == []

    def test_result_to_dict_with_error_and_suggestion(self):
        sug = Suggestion(message="降低值", suggested_value=0.3, reason=SuggestionReason.CONSERVATIVE)
        err = ValidationError(
            parameter="alpha",
            message="超出范围",
            current_value=1.5,
            expected_type=float,
            valid_range=(0.0, 1.0),
            suggestion=sug,
            line_number=12,
        )
        result = ValidationResult(is_valid=False, errors=[err], suggestions=[sug])
        d = result.to_dict()
        assert len(d["errors"]) == 1
        assert d["errors"][0]["parameter"] == "alpha"
        assert d["errors"][0]["line_number"] == 12
        assert d["errors"][0]["suggestion"]["reason"] == "conservative"
        assert len(d["suggestions"]) == 1


class TestTypeValidator:
    """类型验证器测试"""

    def test_type_match_int(self):
        error = TypeValidator.validate("count", 10, int)
        assert error is None

    def test_type_match_float(self):
        error = TypeValidator.validate("rate", 0.5, float)
        assert error is None

    def test_type_match_str(self):
        error = TypeValidator.validate("name", "test", str)
        assert error is None

    def test_type_mismatch_int_vs_str(self):
        error = TypeValidator.validate("count", "not_a_number", int)
        assert error is not None
        assert "str" in error.message or "期望" in error.message
        assert error.expected_type == int

    def test_type_none_skips(self):
        error = TypeValidator.validate("optional", None, int)
        assert error is None

    def test_type_int_accepted_as_float(self):
        error = TypeValidator.validate("rate", 42, float)
        assert error is None

    def test_type_bool_not_int(self):
        error = TypeValidator.validate("flag", True, int)
        assert error is not None

    def test_type_list_vs_str(self):
        error = TypeValidator.validate("tags", ["a", "b"], str)
        assert error is not None


class TestRangeValidator:
    """范围验证器测试"""

    def test_within_range(self):
        error = RangeValidator.validate("alpha", 0.5, (0.0, 1.0))
        assert error is None

    def test_at_lower_boundary(self):
        error = RangeValidator.validate("alpha", 0.0, (0.0, 1.0))
        assert error is None

    def test_at_upper_boundary(self):
        error = RangeValidator.validate("alpha", 1.0, (0.0, 1.0))
        assert error is None

    def test_above_range(self):
        error = RangeValidator.validate("alpha", 1.5, (0.0, 1.0), {"default": 0.5})
        assert error is not None
        assert "超出" in error.message
        assert error.valid_range == (0.0, 1.0)

    def test_below_range(self):
        error = RangeValidator.validate("alpha", -0.5, (0.0, 1.0), {"default": 0.3})
        assert error is not None
        assert error.suggestion is not None
        assert error.suggestion.suggested_value == 0.3

    def test_suggestion_for_exceeding_max(self):
        suggestions = {"default": 0.5, "conservative": 0.3, "aggressive": 0.7}
        error = RangeValidator.validate("alpha", 2.0, (0.0, 1.0), suggestions)
        assert error is not None
        assert error.suggestion is not None
        assert error.suggestion.reason == SuggestionReason.DEFAULT
        assert error.suggestion.suggested_value == 0.5

    def test_no_suggestion_when_no_suggestions_provided(self):
        error = RangeValidator.validate("alpha", 2.0, (0.0, 1.0))
        assert error is not None
        assert error.suggestion is None

    def test_non_numeric_ignored(self):
        error = RangeValidator.validate("name", "hello", (0.0, 1.0))
        assert error is None

    def test_negative_range(self):
        error = RangeValidator.validate("temp", -50, (-100, 100))
        assert error is None

    def test_integer_range(self):
        error = RangeValidator.validate("port", 8080, (1, 65535))
        assert error is None

    def test_integer_out_of_range(self):
        error = RangeValidator.validate("port", 99999, (1, 65535))
        assert error is not None


class TestChoiceValidator:
    """枚举值验证器测试"""

    def test_valid_choice(self):
        error = ChoiceValidator.validate("mode", "production", ["development", "staging", "production"])
        assert error is None

    def test_invalid_choice(self):
        error = ChoiceValidator.validate("mode", "invalid_mode", ["dev", "prod"])
        assert error is not None
        assert "无效" in error.message
        assert error.suggestion is not None

    def test_none_skips(self):
        error = ChoiceValidator.validate("mode", None, ["a", "b"])
        assert error is None

    def test_single_choice_list(self):
        error = ChoiceValidator.validate("flag", "yes", ["yes"])
        assert error is None

    def test_suggestion_is_first_choice(self):
        error = ChoiceValidator.validate("level", "expert", ["beginner", "intermediate", "advanced"])
        assert error is not None
        assert error.suggestion.suggested_value == "beginner"


class TestRequiredValidator:
    """必填项验证器测试"""

    def test_required_with_value(self):
        error = RequiredValidator.validate("host", "localhost", True)
        assert error is None

    def test_required_with_none(self):
        error = RequiredValidator.validate("host", None, True)
        assert error is not None
        assert "必填" in error.message

    def test_required_with_empty_string(self):
        error = RequiredValidator.validate("host", "", True)
        assert error is not None

    def test_required_with_whitespace_only(self):
        error = RequiredValidator.validate("host", "   ", True)
        assert error is not None

    def test_optional_with_none(self):
        error = RequiredValidator.validate("comment", None, False)
        assert error is None

    def test_optional_with_empty_string(self):
        error = RequiredValidator.validate("comment", "", False)
        assert error is None

    def test_required_with_zero(self):
        error = RequiredValidator.validate("count", 0, True)
        assert error is None

    def test_required_with_false(self):
        error = RequiredValidator.validate("enabled", False, True)
        assert error is None


class TestDependencyValidator:
    """依赖关系验证器测试"""

    def test_dependency_satisfied(self):
        config = {"min_price": 0.1, "max_price": 0.9}
        error = DependencyValidator.validate("min_price", config, ["max_price"])
        assert error is None

    def test_dependency_violated_min_ge_max(self):
        config = {"min_price": 0.8, "max_price": 0.5}
        error = DependencyValidator.validate("min_price", config, ["max_price"])
        assert error is not None
        assert "应小于" in error.message

    def test_dependency_missing_dep_key(self):
        config = {"min_price": 0.8}
        error = DependencyValidator.validate("min_price", config, ["max_price"])
        assert error is None

    def test_dependency_missing_current_key(self):
        config = {"max_price": 0.9}
        error = DependencyValidator.validate("min_price", config, ["max_price"])
        assert error is None

    def test_empty_depends_on(self):
        config = {"a": 1}
        error = DependencyValidator.validate("a", config, [])
        assert error is None

    def test_equal_values_allowed(self):
        config = {"min_size": 100, "max_size": 100}
        error = DependencyValidator.validate("min_size", config, ["max_size"])
        assert error is None


class TestParameterRegistry:
    """参数注册表测试"""

    def setup_method(self):
        ParameterRegistry.clear()

    def teardown_method(self):
        ParameterRegistry.clear()

    def test_register_and_get(self):
        info = ParameterInfo(
            key="strategy.alpha",
            expected_type=float,
            valid_range=(0.0, 1.0),
            default_value=0.5,
        )
        ParameterRegistry.register(info)
        retrieved = ParameterRegistry.get("strategy.alpha")
        assert retrieved is info

    def test_get_nonexistent(self):
        assert ParameterRegistry.get("nonexistent") is None

    def test_clear(self):
        ParameterRegistry.register(ParameterInfo(key="a", expected_type=int))
        ParameterRegistry.clear()
        assert ParameterRegistry.get("a") is None

    def test_all_parameters(self):
        ParameterRegistry.register(ParameterInfo(key="x", expected_type=str))
        ParameterRegistry.register(ParameterInfo(key="y", expected_type=float))
        all_params = ParameterRegistry.all_parameters()
        assert len(all_params) == 2
        assert "x" in all_params
        assert "y" in all_params

    def test_parameter_info_defaults(self):
        info = ParameterInfo(key="test", expected_type=int)
        assert info.required is True
        assert info.valid_range is None
        assert info.choices is None
        assert info.default_value is None
        assert info.description == ""

    def test_parameter_info_full(self):
        info = ParameterInfo(
            key="full_param",
            expected_type=str,
            required=False,
            choices=["a", "b"],
            depends_on=["other"],
            default_value="a",
            suggestions={"conservative": "a", "default": "b"},
            description="完整参数定义",
        )
        assert info.required is False
        assert len(info.choices) == 2
        assert info.depends_on == ["other"]
        assert info.default_value == "a"


class TestConfigValidator:
    """主验证器集成测试"""

    def setup_method(self):
        ParameterRegistry.clear()
        self.registry = ParameterRegistry()
        self.registry.register(ParameterInfo(
            key="strategy.alpha",
            expected_type=float,
            required=True,
            valid_range=(0.0, 1.0),
            default_value=0.5,
            suggestions={"conservative": 0.3, "default": 0.5, "aggressive": 0.7},
            description="策略 alpha 系数",
        ))
        self.registry.register(ParameterInfo(
            key="strategy.mode",
            expected_type=str,
            required=True,
            choices=["live", "paper", "backtest"],
            default_value="paper",
            description="运行模式",
        ))
        self.registry.register(ParameterInfo(
            key="redis.port",
            expected_type=int,
            required=True,
            valid_range=(1, 65535),
            default_value=6379,
            description="Redis 端口",
        ))
        self.registry.register(ParameterInfo(
            key="order.min_size",
            expected_type=int,
            required=False,
            valid_range=(1, 10000),
            default_value=10,
            depends_on=["order.max_size"],
            description="最小订单大小",
        ))
        self.registry.register(ParameterInfo(
            key="order.max_size",
            expected_type=int,
            required=True,
            valid_range=(1, 100000),
            default_value=1000,
            description="最大订单大小",
        ))

    def teardown_method(self):
        ParameterRegistry.clear()

    def test_valid_config(self):
        validator = ConfigValidator(registry=self.registry)
        config = {
            "strategy.alpha": 0.5,
            "strategy.mode": "live",
            "redis.port": 6380,
            "order.max_size": 500,
            "order.min_size": 10,
        }
        result = validator.validate_with_suggestions(config)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_single_error_alpha_out_of_range(self):
        validator = ConfigValidator(registry=self.registry)
        config = {
            "strategy.alpha": 1.5,
            "strategy.mode": "live",
            "redis.port": 6379,
            "order.max_size": 1000,
        }
        result = validator.validate_with_suggestions(config)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].parameter == "strategy.alpha"
        assert result.errors[0].suggestion is not None

    def test_multiple_errors_collected(self):
        validator = ConfigValidator(registry=self.registry)
        config = {
            "strategy.alpha": -0.5,
            "strategy.mode": "invalid_mode",
            "redis.port": 70000,
            "order.max_size": 1000,
            "order.min_size": 2000,
        }
        result = validator.validate_with_suggestions(config)
        assert result.is_valid is False
        assert len(result.errors) >= 3
        error_params = {e.parameter for e in result.errors}
        assert "strategy.alpha" in error_params
        assert "strategy.mode" in error_params
        assert "redis.port" in error_params

    def test_warning_for_unregistered_key(self):
        validator = ConfigValidator(registry=self.registry)
        config = {
            "strategy.alpha": 0.5,
            "unknown.param": 42,
        }
        result = validator.validate_with_suggestions(config)
        assert len(result.warnings) == 1
        assert result.warnings[0].parameter == "unknown.param"

    def test_required_field_missing_treated_as_none(self):
        validator = ConfigValidator(registry=self.registry)
        config = {
            "strategy.alpha": None,
            "strategy.mode": "live",
        }
        result = validator.validate_with_suggestions(config)
        assert result.is_valid is False
        required_errors = [e for e in result.errors if e.parameter == "strategy.alpha"]
        assert any("必填" in e.message for e in required_errors)

    def test_dependency_violation_detected(self):
        validator = ConfigValidator(registry=self.registry)
        config = {
            "strategy.alpha": 0.5,
            "strategy.mode": "live",
            "redis.port": 6379,
            "order.max_size": 100,
            "order.min_size": 200,
        }
        result = validator.validate_with_suggestions(config)
        dep_errors = [e for e in result.errors if "应小于" in e.message]
        assert len(dep_errors) > 0

    def test_suggestions_collected_in_result(self):
        validator = ConfigValidator(registry=self.registry)
        config = {
            "strategy.alpha": 2.0,
            "strategy.mode": "live",
            "redis.port": 6379,
            "order.max_size": 1000,
        }
        result = validator.validate_with_suggestions(config)
        assert len(result.suggestions) > 0
        assert any(s.reason == SuggestionReason.DEFAULT for s in result.suggestions)

    def test_validate_single(self):
        validator = ConfigValidator(registry=self.registry)
        error = validator.validate_single("strategy.alpha", 1.5)
        assert error is not None
        assert "超出" in error.message

    def test_validate_single_valid(self):
        validator = ConfigValidator(registry=self.registry)
        error = validator.validate_single("strategy.alpha", 0.5)
        assert error is None

    def test_validate_single_unregistered(self):
        validator = ConfigValidator(registry=self.registry)
        error = validator.validate_single("nonexistent.key", 42)
        assert error is None

    def test_custom_rule(self):
        validator = ConfigValidator(registry=self.registry)

        def even_check(key: str, value: Any, config: dict):
            if key == "redis.port" and isinstance(value, int) and value % 2 != 0:
                return ValidationError(
                    parameter=key,
                    message="端口号建议为偶数",
                    current_value=value,
                )
            return None

        validator.add_custom_rule(even_check)
        config = {
            "strategy.alpha": 0.5,
            "strategy.mode": "live",
            "redis.port": 6379,
            "order.max_size": 1000,
        }
        result = validator.validate_with_suggestions(config)
        custom_errors = [e for e in result.errors if "偶数" in e.message]
        assert len(custom_errors) == 1

    def test_empty_config(self):
        validator = ConfigValidator(registry=self.registry)
        result = validator.validate_with_suggestions({})
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_all_optional_fields_ok(self):
        self.registry.register(ParameterInfo(
            key="optional.field",
            expected_type=str,
            required=False,
        ))
        validator = ConfigValidator(registry=self.registry)
        result = validator.validate_with_suggestions({})
        opt_errors = [e for e in result.errors if e.parameter == "optional.field"]
        assert len(opt_errors) == 0

    def test_format_report_integration(self):
        validator = ConfigValidator(registry=self.registry)
        config = {
            "strategy.alpha": 1.5,
            "strategy.mode": "bad_mode",
            "redis.port": 99999,
        }
        result = validator.validate_with_suggestions(config)
        report = result.format_report()
        assert isinstance(report, str)
        assert len(report) > 0
        if result.errors:
            assert "strategy.alpha" in report or "错误" in report

    def test_to_dict_round_trip(self):
        validator = ConfigValidator(registry=self.registry)
        config = {"strategy.alpha": 2.0, "strategy.mode": "live"}
        result = validator.validate_with_suggestions(config)
        d = result.to_dict()
        assert d["is_valid"] is False
        assert isinstance(d["errors"], list)


class TestEdgeCases:
    """边界条件测试"""

    def setup_method(self):
        ParameterRegistry.clear()

    def teardown_method(self):
        ParameterRegistry.clear()

    def test_float_precision_at_boundary(self):
        registry = ParameterRegistry()
        registry.register(ParameterInfo(
            key="precise",
            expected_type=float,
            valid_range=(0.0, 1.0),
        ))
        validator = ConfigValidator(registry=registry)
        error = validator.validate_single("precise", 0.99999999)
        assert error is None

    def test_very_large_integer_in_range(self):
        registry = ParameterRegistry()
        registry.register(ParameterInfo(
            key="big_num",
            expected_type=int,
            valid_range=(1, 10**18),
        ))
        validator = ConfigValidator(registry=registry)
        error = validator.validate_single("big_num", 10**17)
        assert error is None

    def test_unicode_in_choice_values(self):
        error = ChoiceValidator.validate("lang", "中文", ["中文", "English", "日本語"])
        assert error is None

    def test_unicode_in_choice_invalid(self):
        error = ChoiceValidator.validate("lang", "Français", ["中文", "English"])
        assert error is not None

    def test_boolean_choice_validation(self):
        error = ChoiceValidator.validate("flag", True, [True, False])
        assert error is None

    def test_nested_dict_value_type_check(self):
        error = TypeValidator.validate("config", {"key": "value"}, dict)
        assert error is None

    def test_list_value_type_check(self):
        error = TypeValidator.validate("items", [1, 2, 3], list)
        assert error is None

    def test_zero_float_at_boundary(self):
        error = RangeValidator.validate("val", 0.0, (0.0, 1.0))
        assert error is None

    def test_negative_range_validation(self):
        error = RangeValidator.validate("offset", -10, (-20, -5))
        assert error is None

    def test_negative_range_violation(self):
        error = RangeValidator.validate("offset", 0, (-20, -5))
        assert error is not None

    def test_empty_choices_list(self):
        error = ChoiceValidator.validate("x", "any", [])
        assert error is not None

    def test_config_validator_without_registry(self):
        validator = ConfigValidator()
        result = validator.validate_with_suggestions({"any": "value"})
        assert len(result.warnings) == 1
