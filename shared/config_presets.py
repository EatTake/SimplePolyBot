"""
预设配置方案管理器

提供配置预设方案的 CRUD 操作：
- 列出/获取/应用/保存/删除预设方案
- 方案对比和差异分析
- 方案验证
- 敏感信息过滤
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class PresetInfo:
    name: str
    description: str
    path: Path
    is_builtin: bool


@dataclass
class PresetDiff:
    only_in_first: dict
    only_in_second: dict
    different: dict


PRESETS_DIR = Path(__file__).parent.parent / "config" / "presets"


class ConfigPresets:
    """预设配置方案管理器"""

    BUILTIN_PRESETS = {
        "conservative": {
            "name": "保守型",
            "description": "低风险低收益，适合新手或稳健型投资者"
        },
        "balanced": {
            "name": "平衡型",
            "description": "中等风险收益，适合大多数用户 [推荐]"
        },
        "aggressive": {
            "name": "激进型",
            "description": "高风险高收益，适合经验丰富的交易者"
        }
    }

    def __init__(self, presets_dir: Path = PRESETS_DIR):
        self.presets_dir = presets_dir
        self.custom_presets_dir = presets_dir / "custom"
        self.custom_presets_dir.mkdir(parents=True, exist_ok=True)

    def list_presets(self) -> list[PresetInfo]:
        """列出所有可用方案"""
        presets = []

        for name, info in self.BUILTIN_PRESETS.items():
            preset_file = self.presets_dir / f"{name}.yaml"
            if preset_file.exists():
                presets.append(PresetInfo(
                    name=name,
                    description=info["description"],
                    path=preset_file,
                    is_builtin=True
                ))

        if self.custom_presets_dir.exists():
            for preset_file in self.custom_presets_dir.glob("*.yaml"):
                name = preset_file.stem
                presets.append(PresetInfo(
                    name=name,
                    description=f"自定义方案: {name}",
                    path=preset_file,
                    is_builtin=False
                ))

        return sorted(presets, key=lambda x: (not x.is_builtin, x.name))

    def get_preset(self, name: str) -> dict:
        """获取方案内容"""
        preset_file = self._find_preset_file(name)
        if not preset_file or not preset_file.exists():
            raise FileNotFoundError(f"预设方案不存在: {name}")

        with open(preset_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def apply_preset(self, name: str, config=None) -> None:
        """应用预设方案到 settings.yaml"""
        preset_data = self.get_preset(name)

        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"

        if not settings_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {settings_path}")

        with open(settings_path, 'r', encoding='utf-8') as f:
            current_config = yaml.safe_load(f) or {}

        merged = self._deep_merge(current_config, preset_data)

        with open(settings_path, 'w', encoding='utf-8') as f:
            yaml.dump(merged, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def save_preset(self, name: str, config=None) -> None:
        """保存当前配置为自定义方案"""
        if config is None:
            from .config import Config
            config = Config.get_instance()
            config_data = config.get_all() if config._config_loaded else {}
        else:
            config_data = config

        safe_data = self._filter_sensitive_data(config_data)

        output_path = self.custom_presets_dir / f"{name}.yaml"
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(safe_data, f, default_flow_style=False, allow_unicode=True)

    def delete_preset(self, name: str) -> None:
        """删除自定义方案"""
        if name in self.BUILTIN_PRESETS:
            raise ValueError(f"不能删除内置方案: {name}")

        preset_file = self.custom_presets_dir / f"{name}.yaml"
        if not preset_file.exists():
            raise FileNotFoundError(f"自定义方案不存在: {name}")

        preset_file.unlink()

    def diff_presets(self, name1: str, name2: str) -> PresetDiff:
        """对比两个方案的差异"""
        data1 = self.get_preset(name1)
        data2 = self.get_preset(name2)

        only_in_first, only_in_second, different = self._dict_diff(data1, data2)

        return PresetDiff(
            only_in_first=only_in_first,
            only_in_second=only_in_second,
            different=different
        )

    def validate_preset(self, name: str):
        """验证方案有效性"""
        from .config_validator import ConfigValidator, ValidationResult

        try:
            preset_data = self.get_preset(name)
            validator = ConfigValidator()
            return validator.validate_with_suggestions(preset_data)
        except Exception as e:
            result = ValidationResult(is_valid=False)
            result.errors.append(
                type('obj', (object,), {
                    'parameter': name,
                    'message': f'加载错误: {e}',
                    'current_value': None,
                    'expected_type': None,
                    'valid_range': None,
                    'suggestion': None,
                    'line_number': None
                })()
            )
            return result

    def _find_preset_file(self, name: str) -> Optional[Path]:
        """查找方案文件"""
        builtin_path = self.presets_dir / f"{name}.yaml"
        if builtin_path.exists():
            return builtin_path

        custom_path = self.custom_presets_dir / f"{name}.yaml"
        if custom_path.exists():
            return custom_path

        return None

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """深度合并两个字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigPresets._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _filter_sensitive_data(data: dict) -> dict:
        """过滤敏感信息"""
        sensitive_keys = ["password", "secret", "key", "private_key"]

        def filter_dict(d):
            result = {}
            for k, v in d.items():
                if any(sens in k.lower() for sens in sensitive_keys):
                    result[k] = "***FILTERED***"
                elif isinstance(v, dict):
                    result[k] = filter_dict(v)
                else:
                    result[k] = v
            return result

        return filter_dict(data)

    @staticmethod
    def _dict_diff(dict1: dict, dict2: dict) -> tuple:
        """比较两个字典的差异"""
        all_keys = set(dict1.keys()) | set(dict2.keys())

        only_in_first = {k: dict1[k] for k in all_keys - set(dict2.keys()) if k in dict1}
        only_in_second = {k: dict2[k] for k in all_keys - set(dict1.keys()) if k in dict2}
        different = {}

        for k in all_keys & set(dict1.keys()) & set(dict2.keys()):
            if dict1[k] != dict2[k]:
                different[k] = {"preset1": dict1[k], "preset2": dict2[k]}

        return only_in_first, only_in_second, different


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="预设方案管理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("list", help="列出所有方案")

    apply_parser = subparsers.add_parser("apply", help="应用方案")
    apply_parser.add_argument("name", help="方案名称")

    save_parser = subparsers.add_parser("save", help="保存自定义方案")
    save_parser.add_argument("name", help="方案名称")

    del_parser = subparsers.add_parser("delete", help="删除自定义方案")
    del_parser.add_argument("name", help="方案名称")

    diff_parser = subparsers.add_parser("diff", help="对比方案")
    diff_parser.add_argument("name1", help="方案1名称")
    diff_parser.add_argument("name2", help="方案2名称")

    val_parser = subparsers.add_parser("validate", help="验证方案")
    val_parser.add_argument("name", help="方案名称")

    args = parser.parse_args()
    presets = ConfigPresets()

    if args.command == "list":
        for p in presets.list_presets():
            icon = "[BUILTIN]" if p.is_builtin else "[CUSTOM]"
            print(f"  {icon} {p.name:<15} - {p.description}")

    elif args.command == "apply":
        try:
            presets.apply_preset(args.name)
            print(f"[OK] 已应用方案: {args.name}")
        except Exception as e:
            print(f"[ERROR] 错误: {e}")

    elif args.command == "save":
        try:
            presets.save_preset(args.name)
            print(f"[OK] 方案已保存: {args.name}")
        except Exception as e:
            print(f"[ERROR] 错误: {e}")

    elif args.command == "delete":
        try:
            presets.delete_preset(args.name)
            print(f"[OK] 方案已删除: {args.name}")
        except Exception as e:
            print(f"[ERROR] 错误: {e}")

    elif args.command == "diff":
        try:
            diff = presets.diff_presets(args.name1, args.name2)
            print(f"\n对比: {args.name1} vs {args.name2}\n")
            if diff.only_in_first:
                print(f"仅在 {args.name1} 中:")
                for k, v in diff.only_in_first.items():
                    print(f"  + {k}: {v}")
            if diff.only_in_second:
                print(f"仅在 {args.name2} 中:")
                for k, v in diff.only_in_second.items():
                    print(f"  + {k}: {v}")
            if diff.different:
                print(f"不同的参数:")
                for k, v in diff.different.items():
                    print(f"  ~ {k}: {v['preset1']} -> {v['preset2']}")
        except Exception as e:
            print(f"[ERROR] 错误: {e}")

    elif args.command == "validate":
        result = presets.validate_preset(args.name)
        if result.is_valid:
            print(f"[OK] 方案 {args.name} 验证通过")
        else:
            print(f"[FAIL] 方案 {args.name} 验证失败: {len(result.errors)} 个错误")

    else:
        parser.print_help()
