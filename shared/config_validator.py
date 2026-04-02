"""
配置验证器模块

提供增强的配置验证功能，支持：
- 类型验证、范围验证、枚举值验证
- 必填项检查、依赖关系验证
- 智能建议生成（保守/默认/激进）
- 多错误收集，一次性返回所有问题
- 警告与错误分离
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type


class SuggestionReason(str, Enum):
    CONSERVATIVE = "conservative"
    DEFAULT = "default"
    AGGRESSIVE = "aggressive"


@dataclass
class Suggestion:
    message: str
    suggested_value: Any
    reason: SuggestionReason


@dataclass
class ValidationError:
    parameter: str
    message: str
    current_value: Any
    expected_type: Optional[type] = None
    valid_range: Optional[tuple] = None
    suggestion: Optional[Suggestion] = None
    line_number: Optional[int] = None


@dataclass
class ValidationWarning:
    parameter: str
    message: str
    current_value: Any


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    suggestions: List[Suggestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": [
                {
                    "parameter": e.parameter,
                    "message": e.message,
                    "current_value": e.current_value,
                    "expected_type": e.expected_type.__name__ if e.expected_type else None,
                    "valid_range": list(e.valid_range) if e.valid_range else None,
                    "suggestion": {
                        "message": e.suggestion.message,
                        "suggested_value": e.suggestion.suggested_value,
                        "reason": e.suggestion.reason.value,
                    } if e.suggestion else None,
                    "line_number": e.line_number,
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "parameter": w.parameter,
                    "message": w.message,
                    "current_value": w.current_value,
                }
                for w in self.warnings
            ],
            "suggestions": [
                {
                    "message": s.message,
                    "suggested_value": s.suggested_value,
                    "reason": s.reason.value,
                }
                for s in self.suggestions
            ],
        }

    def format_report(self) -> str:
        from shared.error_formatter import ErrorFormatter

        return ErrorFormatter.format_validation_report(self)


@dataclass
class ParameterInfo:
    key: str
    expected_type: type
    required: bool = True
    valid_range: Optional[Tuple[Any, Any]] = None
    choices: Optional[List[Any]] = None
    depends_on: Optional[List[str]] = None
    default_value: Any = None
    suggestions: Optional[Dict[str, Any]] = None
    description: str = ""


class ParameterRegistry:
    """参数注册表，存储参数元数据用于智能验证和建议生成"""

    _parameters: Dict[str, ParameterInfo] = {}

    @classmethod
    def register(cls, info: ParameterInfo) -> None:
        cls._parameters[info.key] = info

    @classmethod
    def get(cls, key: str) -> Optional[ParameterInfo]:
        return cls._parameters.get(key)

    @classmethod
    def clear(cls) -> None:
        cls._parameters.clear()

    @classmethod
    def all_parameters(cls) -> Dict[str, ParameterInfo]:
        return cls._parameters.copy()


class TypeValidator:
    """类型验证器"""

    @staticmethod
    def validate(key: str, value: Any, expected_type: type) -> Optional[ValidationError]:
        if value is None:
            return None
        if expected_type == int and isinstance(value, bool):
            actual_type_name = type(value).__name__
            return ValidationError(
                parameter=key,
                message=f"类型错误: 期望 int, 实际为 {actual_type_name}",
                current_value=value,
                expected_type=expected_type,
            )
        if not isinstance(value, expected_type):
            actual_type_name = type(value).__name__
            expected_type_name = expected_type.__name__
            if expected_type_name == "float" and isinstance(value, int):
                return None
            return ValidationError(
                parameter=key,
                message=f"类型错误: 期望 {expected_type_name}, 实际为 {actual_type_name}",
                current_value=value,
                expected_type=expected_type,
            )
        return None


class RangeValidator:
    """范围验证器"""

    @staticmethod
    def validate(
        key: str, value: Any, valid_range: tuple, suggestions: Optional[Dict[str, Any]] = None
    ) -> Optional[ValidationError]:
        if not isinstance(value, (int, float)):
            return None

        min_val, max_val = valid_range
        if min_val <= value <= max_val:
            return None

        range_str = f"{min_val} - {max_val}"
        error = ValidationError(
            parameter=key,
            message=f"值超出有效范围 [{range_str}]",
            current_value=value,
            valid_range=valid_range,
        )

        if suggestions:
            default_sug = suggestions.get("default")
            conservative_sug = suggestions.get("conservative")
            aggressive_sug = suggestions.get("aggressive")

            if value > max_val and default_sug is not None:
                error.suggestion = Suggestion(
                    message="值偏大，建议降低到安全范围",
                    suggested_value=default_sug,
                    reason=SuggestionReason.DEFAULT,
                )
            elif value < min_val and default_sug is not None:
                error.suggestion = Suggestion(
                    message="值偏小，建议提高到安全范围",
                    suggested_value=default_sug,
                    reason=SuggestionReason.DEFAULT,
                )

        return error


class ChoiceValidator:
    """枚举值验证器"""

    @staticmethod
    def validate(
        key: str, value: Any, choices: list
    ) -> Optional[ValidationError]:
        if value is None:
            return None
        if value not in choices:
            choices_str = ", ".join(str(c) for c in choices)
            return ValidationError(
                parameter=key,
                message=f"无效的选项值，可选值: [{choices_str}]",
                current_value=value,
                suggestion=Suggestion(
                    message=f"请从以下选项中选择一个: {choices_str}",
                    suggested_value=choices[0] if choices else None,
                    reason=SuggestionReason.DEFAULT,
                ),
            )
        return None


class RequiredValidator:
    """必填项验证器"""

    @staticmethod
    def validate(key: str, value: Any, required: bool) -> Optional[ValidationError]:
        if not required:
            return None
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return ValidationError(
                parameter=key,
                message="此参数为必填项，不能为空或 None",
                current_value=value,
            )
        return None


class DependencyValidator:
    """依赖关系验证器"""

    @staticmethod
    def validate(
        key: str, config: dict, depends_on: list
    ) -> Optional[ValidationError]:
        if not depends_on:
            return None

        errors = []
        for dep_key in depends_on:
            dep_value = config.get(dep_key)
            if dep_value is None:
                continue

            try:
                current_value = config.get(key)
                if current_value is None:
                    continue

                if isinstance(dep_value, (int, float)) and isinstance(current_value, (int, float)):
                    if current_value > dep_value:
                        errors.append(f"{key} ({current_value}) 应小于或等于 {dep_key} ({dep_value})")
                elif isinstance(dep_value, (int, float)) and isinstance(current_value, (int, float)):
                    if current_value <= dep_value:
                        errors.append(f"{key} ({current_value}) 应大于 {dep_key} ({dep_value})")
            except TypeError:
                pass

        if errors:
            return ValidationError(
                parameter=key,
                message="; ".join(errors),
                current_value=config.get(key),
                suggestion=Suggestion(
                    message=f"{key} 与 {depends_on[0]} 的值不满足依赖关系约束",
                    suggested_value=None,
                    reason=SuggestionReason.DEFAULT,
                ),
            )
        return None


class ConfigValidator:
    """主配置验证器"""

    def __init__(self, registry: Optional[ParameterRegistry] = None):
        self.registry = registry or ParameterRegistry()
        self.validators: List[type] = [
            RequiredValidator,
            TypeValidator,
            RangeValidator,
            ChoiceValidator,
            DependencyValidator,
        ]
        self._custom_rules: List[Callable[[str, Any, dict], Optional[ValidationError]]] = []

    def add_custom_rule(self, rule: Callable[[str, Any, dict], Optional[ValidationError]]) -> None:
        self._custom_rules.append(rule)

    def validate_with_suggestions(self, config: dict) -> ValidationResult:
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        all_suggestions: List[Suggestion] = []

        for key, value in config.items():
            info = self.registry.get(key)
            if info is None:
                warnings.append(ValidationWarning(
                    parameter=key,
                    message=f"参数 '{key}' 未在注册表中定义，跳过结构化验证",
                    current_value=value,
                ))
                continue

            for validator_class in self.validators:
                error = self._run_validator(validator_class, key, value, info, config)
                if error:
                    errors.append(error)
                    if error.suggestion:
                        all_suggestions.append(error.suggestion)

            for rule in self._custom_rules:
                custom_error = rule(key, value, config)
                if custom_error:
                    errors.append(custom_error)
                    if custom_error.suggestion:
                        all_suggestions.append(custom_error.suggestion)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=all_suggestions,
        )

    def _run_validator(
        self,
        validator_class: Type,
        key: str,
        value: Any,
        info: ParameterInfo,
        config: dict,
    ) -> Optional[ValidationError]:
        if validator_class == RequiredValidator:
            return RequiredValidator.validate(key, value, info.required)
        elif validator_class == TypeValidator:
            return TypeValidator.validate(key, value, info.expected_type)
        elif validator_class == RangeValidator:
            if info.valid_range:
                return RangeValidator.validate(key, value, info.valid_range, info.suggestions)
        elif validator_class == ChoiceValidator:
            if info.choices:
                return ChoiceValidator.validate(key, value, info.choices)
        elif validator_class == DependencyValidator:
            if info.depends_on:
                return DependencyValidator.validate(key, config, info.depends_on)
        return None

    def validate_single(self, key: str, value: Any) -> Optional[ValidationError]:
        info = self.registry.get(key)
        if info is None:
            return None

        for validator_class in self.validators:
            error = self._run_validator(validator_class, key, value, info, {})
            if error:
                return error
        return None
