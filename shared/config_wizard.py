"""
交互式配置向导模块

提供引导式配置收集流程，支持：
- quick / standard / expert 三种模式
- 敏感信息安全输入（密码掩码）
- 输入验证与类型转换
- 配置预览与确认
- 命令行接口（CLI）
"""

from __future__ import annotations

import sys
import getpass
from typing import Any, Optional
from pathlib import Path

from .parameter_registry import ParameterRegistry, ParameterInfo
from .config_validator import ConfigValidator, ValidationResult
from .error_formatter import ErrorFormatter
from .config import Config


class SensitiveInputHandler:
    """敏感信息输入处理器"""

    @staticmethod
    def prompt(label: str) -> str:
        """输入时不回显（使用 getpass）"""
        return getpass.getpass(f"  {label}: ")

    @staticmethod
    def confirm(label: str, value: str) -> bool:
        """确认时要求重新输入"""
        confirm_value = getpass.getpass(f"  确认 {label}: ")
        return value == confirm_value

    @staticmethod
    def mask(value: str, visible_chars: int = 6) -> str:
        """返回掩码版本"""
        if len(value) <= visible_chars:
            return "*" * len(value)
        return value[:visible_chars // 2] + "*" * (len(value) - visible_chars)


class ConfigWizard:
    """交互式配置向导"""

    MODES = ["quick", "standard", "expert"]

    def __init__(self, config: Config | None = None, mode: str = "standard"):
        self.config = config or Config.get_instance()
        self.registry = ParameterRegistry.get_instance()
        self.validator = ConfigValidator(self.registry)
        self.formatter = ErrorFormatter()
        self.mode = mode
        self.collected_values: dict[str, Any] = {}

    def run(self) -> dict:
        """运行配置向导流程"""
        self._show_welcome()
        self._collect_basic_settings()

        if self.mode != "quick":
            self._collect_connection_settings()
            self._collect_credentials()

        if self.mode in ["standard", "expert"]:
            self._collect_strategy_params()
            self._collect_risk_params()

        if self.mode == "expert":
            self._collect_advanced_params()

        self._review_and_confirm()
        return self.collected_values

    def _show_welcome(self):
        """显示欢迎界面"""
        print("\n" + "=" * 60)
        print("  🤖 SimplePolyBot 配置向导")
        print("=" * 60)
        print(f"  模式: {self.mode}")
        print("  本向导将引导您完成交易策略的配置")
        print("=" * 60 + "\n")

    def _collect_basic_settings(self):
        """收集基本设置"""
        print("📋 第一步：基本设置\n")

        core_params = self.registry.get_by_level("core")
        for param in core_params[:5]:
            value = self.prompt_for_value(param)
            if value is not None:
                self.collected_values[param.key] = value

    def _collect_connection_settings(self):
        """收集连接配置"""
        print("\n🔗 第二步：连接配置\n")
        connection_params = [p for p in self.registry.get_all("connection")
                           if p.level != "expert"]
        for param in connection_params:
            value = self.prompt_for_value(param)
            if value is not None:
                self.collected_values[param.key] = value

    def _collect_credentials(self):
        """收集凭证配置（敏感信息）"""
        print("\n🔐 第三步：凭证配置\n")
        sensitive_params = self.registry.get_sensitive()
        for param in sensitive_params:
            value = self.prompt_for_sensitive_value(param)
            if value is not None:
                self.collected_values[param.key] = value

    def _collect_strategy_params(self):
        """收集策略参数"""
        print("\n📊 第四步：策略参数\n")
        strategy_params = [p for p in self.registry.get_all("strategy")
                         if p.level in ["core", "standard"]]
        for param in strategy_params:
            value = self.prompt_for_value(param)
            if value is not None:
                self.collected_values[param.key] = value

    def _collect_risk_params(self):
        """收集风险管理参数"""
        print("\n⚠️ 第五步：风险管理\n")
        risk_params = [p for p in self.registry.get_all("strategy")
                      if "risk" in p.key or "stop" in p.key]
        for param in risk_params:
            value = self.prompt_for_value(param)
            if value is not None:
                self.collected_values[param.key] = value

    def _collect_advanced_params(self):
        """收集高级参数"""
        print("\n🔧 第六步：高级参数\n")
        advanced_params = self.registry.get_by_level("advanced") + \
                        self.registry.get_by_level("expert")
        for param in advanced_params:
            value = self.prompt_for_value(param)
            if value is not None:
                self.collected_values[param.key] = value

    def prompt_for_value(self, param: ParameterInfo) -> Any:
        """提示用户输入值"""
        self.show_parameter_info(param)

        default_str = f" [默认: {param.default}]" if param.default else ""
        prompt_text = f"{param.name}{default_str}: "

        user_input = input(f"  {prompt_text}").strip()

        if not user_input:
            return param.default

        valid, error_msg = self.validate_input(param, user_input)
        if not valid:
            print(f"  ⚠️ {error_msg}")
            return self._retry_input(param)

        return self.convert_type(user_input, param.type)

    def prompt_for_sensitive_value(self, param: ParameterInfo) -> Any:
        """提示输入敏感值"""
        print(f"\n  🔒 {param.name}")
        print(f"     {param.description}")

        value = SensitiveInputHandler.prompt(param.name)

        if value and param.required:
            if not SensitiveInputHandler.confirm(param.name, value):
                print("  ❌ 确认不匹配，请重新输入")
                return self.prompt_for_sensitive_value(param)

        masked = SensitiveInputHandler.mask(value) if value else "(未设置)"
        print(f"  ✅ 已设置: {masked}\n")

        return value or None

    def show_parameter_info(self, param: ParameterInfo):
        """显示参数信息"""
        print(f"\n  📌 {param.name}")
        print(f"     说明: {param.description}")

        if param.range:
            print(f"     范围: {param.range[0]} - {param.range[1]}")

        if param.choices:
            print(f"     可选值: {', '.join(str(c) for c in param.choices)}")

        if param.suggestions:
            suggestions_str = ", ".join(
                f"{k}={v}" for k, v in list(param.suggestions.items())[:3]
            )
            print(f"     建议: ({suggestions_str})")

    def validate_input(self, param: ParameterInfo, value: str) -> tuple[bool, str]:
        """验证用户输入"""
        try:
            converted = self.convert_type(value, param.type)

            if param.range and isinstance(converted, (int, float)):
                if not (param.range[0] <= converted <= param.range[1]):
                    return False, f"超出范围 {param.range}"

            if param.choices and converted not in param.choices:
                return False, f"必须是: {', '.join(str(c) for c in param.choices)}"

            return True, ""

        except ValueError as e:
            return False, f"类型错误: {e}"

    def convert_type(self, value: str, target_type: type) -> Any:
        """转换字符串为目标类型"""
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == list:
            return [item.strip() for item in value.split(",")]
        return value

    def _retry_input(self, param: ParameterInfo) -> Any:
        """重试输入"""
        if param.suggestions:
            print(f"  💡 建议使用默认值: {param.default}")
            use_default = input("  使用默认值? (y/n): ").strip().lower()
            if use_default in ("y", "yes", ""):
                return param.default
        return param.default

    def _review_and_confirm(self):
        """显示确认界面"""
        print("\n" + "=" * 60)
        print("  📋 配置摘要")
        print("=" * 60)

        for key, value in self.collected_values.items():
            param = self.registry.get(key)
            display_key = param.name if param else key
            if param and param.sensitive and value:
                value_display = SensitiveInputHandler.mask(str(value))
            else:
                value_display = str(value)
            print(f"  • {display_key}: {value_display}")

        print("=" * 60)

        confirm = input("\n  确认保存此配置? (y/n): ").strip().lower()
        if confirm not in ("y", "yes", ""):
            print("  ❌ 配置已取消")
            sys.exit(0)

        print("  ✅ 配置已确认")


class ConfigWizardCLI:
    """命令行入口"""

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self):
        """创建参数解析器"""
        import argparse
        parser = argparse.ArgumentParser(
            description="SimplePyBot 配置向导",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  python -m shared.config_wizard                  # 标准模式
  python -m shared.config_wizard --mode quick      # 快速模式
  python -m shared.config_wizard --preset balanced # 应用预设方案
  python -m shared.config_wizard --validate-only   # 仅验证当前配置
            """
        )
        parser.add_argument(
            "--mode", "-m",
            choices=["quick", "standard", "expert"],
            default="standard",
            help="配置模式"
        )
        parser.add_argument(
            "--preset", "-p",
            choices=["conservative", "balanced", "aggressive"],
            help="应用预设方案"
        )
        parser.add_argument(
            "--output", "-o",
            help="输出配置文件路径"
        )
        parser.add_argument(
            "--validate-only",
            action="store_true",
            help="仅验证不修改配置"
        )
        parser.add_argument(
            "--generate-docs",
            action="store_true",
            help="生成配置文档"
        )
        return parser

    def main(self):
        """主函数"""
        args = self.parser.parse_args()

        if args.generate_docs:
            self._generate_docs()
            return

        if args.validate_only:
            self._validate_config()
            return

        if args.preset:
            self._apply_preset(args.preset)
            return

        wizard = ConfigWizard(mode=args.mode)
        try:
            collected = wizard.run()

            if args.output:
                self._save_config(collected, args.output)
            else:
                print("\n✅ 配置完成！请查看 config/settings.yaml")

        except KeyboardInterrupt:
            print("\n\n❌ 用户取消配置")
            sys.exit(1)

    def _generate_docs(self):
        """生成文档"""
        from .config_docs import ConfigDocGenerator
        generator = ConfigDocGenerator()
        md = generator.generate_markdown()

        docs_path = Path("docs/configuration_guide.md")
        docs_path.write_text(md, encoding="utf-8")
        print(f"✅ 文档已生成: {docs_path}")

    def _validate_config(self):
        """验证当前配置"""
        config = Config.get_instance()
        try:
            config.load_env()
            config.load_yaml()
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            return

        validator = ConfigValidator(ParameterRegistry.get_instance())
        result = validator.validate_with_suggestions(config.get_all())

        formatter = ErrorFormatter()
        report = formatter.format_validation_report(result)
        print(report)

        if result.is_valid:
            print("\n✅ 配置验证通过！")
        else:
            print(f"\n❌ 发现 {len(result.errors)} 个错误")

    def _apply_preset(self, preset_name: str):
        """应用预设方案"""
        from .config_presets import ConfigPresets
        presets = ConfigPresets()

        try:
            presets.apply_preset(preset_name)
            print(f"✅ 已应用预设方案: {preset_name}")
        except Exception as e:
            print(f"❌ 应用预设失败: {e}")

    def _save_config(self, config_data: dict, output_path: str):
        """保存配置到文件"""
        import yaml
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        print(f"✅ 配置已保存到: {output}")


if __name__ == "__main__":
    cli = ConfigWizardCLI()
    cli.main()
