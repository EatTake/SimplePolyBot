"""
错误消息格式化模块

提供验证错误的多种格式化输出：
- terminal: Unicode 边框美化终端输出
- text: 纯文本输出（用于日志）
- json: JSON 格式（用于程序处理）
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from shared.config_validator import (
    Suggestion,
    SuggestionReason,
    ValidationError,
    ValidationResult,
    ValidationWarning,
)


class ErrorFormatter:
    """格式化验证错误消息"""

    TERMINAL_WIDTH = 60

    @staticmethod
    def format_validation_error(error: ValidationError, style: str = "terminal") -> str:
        if style == "terminal":
            return ErrorFormatter._format_terminal_error(error)
        elif style == "text":
            return ErrorFormatter._format_text_error(error)
        elif style == "json":
            return json.dumps(ErrorFormatter._error_to_dict(error), ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的样式: {style}")

    @staticmethod
    def format_validation_report(result: ValidationResult, style: str = "terminal") -> str:
        if style == "terminal":
            return ErrorFormatter._format_terminal_report(result)
        elif style == "text":
            return ErrorFormatter._format_text_report(result)
        elif style == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的样式: {style}")

    @staticmethod
    def _format_terminal_error(error: ValidationError) -> str:
        w = ErrorFormatter.TERMINAL_WIDTH
        lines: List[str] = []

        lines.append("╔" + "═" * (w - 2) + "╗")
        lines.append("║  ❌ 配置错误" + " " * (w - 13) + "║")
        lines.append("╠" + "═" * (w - 2) + "╣")

        param_str = f"参数: {error.parameter}"
        lines.append("║  " + param_str.ljust(w - 5) + "║")

        msg_str = f"问题: {error.message}"
        lines.append("║  " + msg_str.ljust(w - 5) + "║")

        val_str = f"当前值: {error.current_value}"
        lines.append("║  " + val_str.ljust(w - 5) + "║")

        if error.expected_type is not None:
            type_str = f"期望类型: {error.expected_type.__name__}"
            lines.append("║  " + type_str.ljust(w - 5) + "║")

        if error.valid_range is not None:
            lo, hi = error.valid_range
            range_str = f"有效范围: {lo} - {hi}"
            lines.append("║  " + range_str.ljust(w - 5) + "║")

        if error.line_number is not None:
            line_str = f"行号: 第 {error.line_number} 行"
            lines.append("║  " + line_str.ljust(w - 5) + "║")

        if error.suggestion is not None:
            lines.append("║                                      ║")
            lines.append("║  💡 建议:                            ║")
            sug_val = error.suggestion.suggested_value
            reason_map = {
                SuggestionReason.CONSERVATIVE: "保守值",
                SuggestionReason.DEFAULT: "默认值",
                SuggestionReason.AGGRESSIVE: "激进值",
            }
            reason_label = reason_map.get(error.suggestion.reason, "建议值")
            sug_line = f"  • {reason_label}: {sug_val}"
            lines.append("║" + sug_line.ljust(w - 1) + "║")
            msg_line = f"  → {error.suggestion.message}"
            lines.append("║" + msg_line.ljust(w - 1) + "║")

        lines.append("╚" + "═" * (w - 2) + "╝")
        return "\n".join(lines)

    @staticmethod
    def _format_text_error(error: ValidationError) -> str:
        parts = [
            f"[ERROR] 参数 '{error.parameter}': {error.message}",
            f"  当前值: {error.current_value}",
        ]
        if error.expected_type is not None:
            parts.append(f"  期望类型: {error.expected_type.__name__}")
        if error.valid_range is not None:
            parts.append(f"  有效范围: {error.valid_range[0]} - {error.valid_range[1]}")
        if error.line_number is not None:
            parts.append(f"  行号: 第 {error.line_number} 行")
        if error.suggestion is not None:
            parts.append(
                f"  💡 建议修改为: {error.suggestion.suggested_value} "
                f"({error.suggestion.reason.value}) - {error.suggestion.message}"
            )
        return "\n".join(parts)

    @staticmethod
    def _format_terminal_report(result: ValidationResult) -> str:
        w = ErrorFormatter.TERMINAL_WIDTH
        sections: List[str] = []

        header = "╔" + "═" * (w - 2) + "╗"
        footer = "╚" + "═" * (w - 2) + "╝"

        status_icon = "✅" if result.is_valid else "❌"
        status_text = "配置验证通过" if result.is_valid else f"发现 {len(result.errors)} 个错误"
        title = f"{status_icon} {status_text}"

        sections.append(header)
        sections.append("║  " + title.ljust(w - 5) + "║")
        sections.append("╠" + "─" * (w - 2) + "╣")

        if result.errors:
            sections.append("║  📋 错误详情:" + " " * max(0, w - 17) + "║")
            for i, err in enumerate(result.errors, 1):
                err_preview = f"  [{i}] {err.parameter}: {err.message[:40]}"
                if len(err.message) > 40:
                    err_preview += "..."
                sections.append("║" + err_preview.ljust(w - 1) + "║")
            for err in result.errors:
                sections.append("")
                sections.append(ErrorFormatter._format_terminal_error(err))

        if result.warnings:
            sections.append("╠" + "─" * (w - 2) + "╣")
            sections.append("║  ⚠️ 警告:" + " " * max(0, w - 14) + "║")
            for warn in result.warnings:
                warn_line = f"  • {warn.parameter}: {warn.message[:45]}"
                if len(warn.message) > 45:
                    warn_line += "..."
                sections.append("║" + warn_line.ljust(w - 1) + "║")

        if result.suggestions and result.is_valid:
            sections.append("╠" + "─" * (w - 2) + "╣")
            sections.append("║  💡 优化建议:" + " " * max(0, w - 16) + "║")
            for sug in result.suggestions:
                sug_line = f"  • {sug.reason.value}: {sug.suggested_value} - {sug.message[:35]}"
                if len(sug.message) > 35:
                    sug_line += "..."
                sections.append("║" + sug_line.ljust(w - 1) + "║")

        sections.append(footer)
        return "\n".join(sections)

    @staticmethod
    def _format_text_report(result: ValidationResult) -> str:
        lines: List[str] = []
        lines.append("=" * 50)
        if result.is_valid:
            lines.append("[PASS] ✅ 配置验证通过")
        else:
            lines.append(f"[FAIL] ❌ 发现 {len(result.errors)} 个错误")
        lines.append("=" * 50)

        if result.errors:
            lines.append("\n--- 错误详情 ---")
            for i, err in enumerate(result.errors, 1):
                lines.append(f"\n[{i}] {ErrorFormatter._format_text_error(err)}")

        if result.warnings:
            lines.append("\n--- 警告 ---")
            for warn in result.warnings:
                lines.append(f"[WARN] {warn.parameter}: {warn.message} (当前值: {warn.current_value})")

        if result.suggestions and result.is_valid:
            lines.append("\n--- 优化建议 ---")
            for sug in result.suggestions:
                lines.append(f"[SUGGESTION] {sug.reason.value}: {sug.suggested_value} - {sug.message}")

        summary = f"\n总计: {len(result.errors)} 个错误, {len(result.warnings)} 个警告"
        lines.append(summary)
        return "\n".join(lines)

    @staticmethod
    def _error_to_dict(error: ValidationError) -> dict:
        d: Dict[str, Any] = {
            "parameter": error.parameter,
            "message": error.message,
            "current_value": error.current_value,
        }
        if error.expected_type is not None:
            d["expected_type"] = error.expected_type.__name__
        if error.valid_range is not None:
            d["valid_range"] = list(error.valid_range)
        if error.line_number is not None:
            d["line_number"] = error.line_number
        if error.suggestion is not None:
            d["suggestion"] = {
                "message": error.suggestion.message,
                "suggested_value": error.suggestion.suggested_value,
                "reason": error.suggestion.reason.value,
            }
        return d

    @staticmethod
    def generate_fix_command(error: ValidationError) -> str:
        lines: List[str] = []
        lines.append("修复建议:")
        if error.line_number is not None:
            lines.append(f"  编辑配置文件第 {error.line_number} 行")
        else:
            lines.append("  编辑配置文件，找到以下参数:")
        lines.append(f"  参数名: {error.parameter}")
        if error.suggestion is not None:
            lines.append(f"  将值设置为: {error.suggestion.suggested_value}")
            lines.append(f"  原因: {error.suggestion.message}")
        elif error.expected_type is not None:
            lines.append(f"  将类型改为: {error.expected_type.__name__}")
        elif error.valid_range is not None:
            lo, hi = error.valid_range
            lines.append(f"  将值调整到范围 [{lo}, {hi}] 内")
        else:
            lines.append(f"  参考错误信息修正: {error.message}")
        return "\n".join(lines)
