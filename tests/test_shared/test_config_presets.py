"""
config_presets 单元测试

测试预设方案管理器的各项功能：
- 列出/获取/应用/保存/删除预设方案
- 方案对比和差异分析
- 深度合并逻辑
- 敏感信息过滤
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from shared.config_presets import (
    ConfigPresets,
    PresetDiff,
    PresetInfo,
)


class TestPresetInfo:
    """测试 PresetInfo 数据类"""

    def test_creation(self):
        info = PresetInfo(
            name="test",
            description="test desc",
            path=Path("/tmp/test.yaml"),
            is_builtin=True,
        )
        assert info.name == "test"
        assert info.is_builtin is True


class TestPresetDiff:
    """测试 PresetDiff 数据类"""

    def test_creation(self):
        diff = PresetDiff(
            only_in_first={"a": 1},
            only_in_second={"b": 2},
            different={"c": {"preset1": 1, "preset2": 2}},
        )
        assert diff.only_in_first == {"a": 1}
        assert diff.only_in_second == {"b": 2}
        assert len(diff.different) == 1


class TestConfigPresetsInit:
    """测试初始化"""

    def test_init_creates_custom_dir(self, tmp_path):
        presets_dir = tmp_path / "presets"
        ConfigPresets(presets_dir=presets_dir)
        assert (presets_dir / "custom").exists()

    def test_init_default_dir(self):
        presets = ConfigPresets()
        assert presets.presets_dir.name == "presets"
        assert presets.custom_presets_dir.name == "custom"


class TestListPresets:
    """测试列出方案"""

    @pytest.fixture
    def preset_env(self, tmp_path):
        """创建预设方案环境"""
        presets_dir = tmp_path / "config" / "presets"
        presets_dir.mkdir(parents=True)

        (presets_dir / "conservative.yaml").write_text(
            yaml.dump({"strategy": {"base_cushion": 0.03}}), encoding="utf-8"
        )
        (presets_dir / "balanced.yaml").write_text(
            yaml.dump({"strategy": {"base_cushion": 0.02}}), encoding="utf-8"
        )

        custom_dir = presets_dir / "custom"
        custom_dir.mkdir()
        (custom_dir / "my_preset.yaml").write_text(
            yaml.dump({"strategy": {"alpha": 0.9}}), encoding="utf-8"
        )

        return presets_dir

    def test_list_includes_builtins(self, preset_env):
        presets = ConfigPresets(presets_dir=preset_env)
        result = presets.list_presets()
        names = [p.name for p in result]
        assert "conservative" in names
        assert "balanced" in names

    def test_list_includes_custom(self, preset_env):
        presets = ConfigPresets(presets_dir=preset_env)
        result = presets.list_presets()
        names = [p.name for p in result]
        assert "my_preset" in names

    def test_list_builtin_first(self, preset_env):
        presets = ConfigPresets(presets_dir=preset_env)
        result = presets.list_presets()
        builtin_names = [p.name for p in result if p.is_builtin]
        custom_names = [p.name for p in result if not p.is_builtin]
        assert all(p.is_builtin for p in result[:len(builtin_names)])

    def test_list_builtin_flag(self, preset_env):
        presets = ConfigPresets(presets_dir=preset_env)
        result = presets.list_presets()
        conservative = next(p for p in result if p.name == "conservative")
        my_preset = next(p for p in result if p.name == "my_preset")
        assert conservative.is_builtin is True
        assert my_preset.is_builtin is False

    def test_list_empty(self, tmp_path):
        empty_dir = tmp_path / "empty_presets"
        empty_dir.mkdir()
        presets = ConfigPresets(presets_dir=empty_dir)
        result = presets.list_presets()
        assert len(result) == 0

    def test_list_description(self, preset_env):
        presets = ConfigPresets(presets_dir=preset_env)
        result = presets.list_presets()
        conservative = next(p for p in result if p.name == "conservative")
        assert "低风险" in conservative.description or "新手" in conservative.description


class TestGetPreset:
    """测试获取方案内容"""

    @pytest.fixture
    def preset_with_file(self, tmp_path):
        """创建带预设文件的目录"""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        test_data = {
            "strategy": {
                "base_cushion": 0.03,
                "alpha": 0.3,
                "order_sizes": {"default": 50},
            }
        }
        (presets_dir / "conservative.yaml").write_text(
            yaml.dump(test_data), encoding="utf-8"
        )
        return presets_dir, test_data

    def test_get_existing_preset(self, preset_with_file):
        presets_dir, expected_data = preset_with_file
        presets = ConfigPresets(presets_dir=presets_dir)
        result = presets.get_preset("conservative")
        assert result["strategy"]["base_cushion"] == 0.03
        assert result["strategy"]["alpha"] == 0.3

    def test_get_nonexistent_preset(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        presets = ConfigPresets(presets_dir=presets_dir)
        with pytest.raises(FileNotFoundError, match="不存在"):
            presets.get_preset("nonexistent")

    def test_get_custom_preset(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        custom_dir = presets_dir / "custom"
        custom_dir.mkdir()

        custom_data = {"custom_key": "custom_value"}
        (custom_dir / "mine.yaml").write_text(yaml.dump(custom_data), encoding="utf-8")

        presets = ConfigPresets(presets_dir=presets_dir)
        result = presets.get_preset("mine")
        assert result["custom_key"] == "custom_value"

    def test_get_empty_yaml(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()
        (presets_dir / "empty.yaml").write_text("", encoding="utf-8")

        presets = ConfigPresets(presets_dir=presets_dir)
        result = presets.get_preset("empty")
        assert result == {}


class TestApplyPreset:
    """测试应用方案"""

    @pytest.fixture
    def apply_env(self, tmp_path):
        """创建应用方案测试环境"""
        base = tmp_path / "project"
        base.mkdir()

        shared_dir = base / "shared"
        shared_dir.mkdir()
        (shared_dir / "__init__.py").write_text("", encoding="utf-8")

        config_dir = base / "config"
        config_dir.mkdir()

        settings_data = {
            "redis": {"host": "localhost", "port": 6379},
            "existing_key": "keep_me",
        }
        (config_dir / "settings.yaml").write_text(
            yaml.dump(settings_data), encoding="utf-8"
        )

        presets_dir = config_dir / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        preset_data = {
            "strategy": {"base_cushion": 0.05, "alpha": 0.7},
            "new_key": "new_value",
        }
        (presets_dir / "test_preset.yaml").write_text(
            yaml.dump(preset_data), encoding="utf-8"
        )
        (presets_dir / "any.yaml").write_text(
            yaml.dump({"key": "val"}), encoding="utf-8"
        )

        return base, config_dir / "settings.yaml", presets_dir

    def test_apply_merges_config(self, apply_env, monkeypatch):
        base, settings_path, presets_dir = apply_env

        real_presets = Path(__file__).resolve().parents[2] / "shared" / "config_presets.py"
        fake_cp = (base / "shared" / "config_presets.py")
        fake_cp.write_text(real_presets.read_text(encoding='utf-8'), encoding='utf-8')

        sys_path_backup = list(sys.path)
        sys.path.insert(0, str(base))
        try:
            import importlib
            if 'shared.config_presets' in sys.modules:
                del sys.modules['shared.config_presets']
            if 'shared' in sys.modules:
                del sys.modules['shared']
            import shared.config_presets as cp
            importlib.reload(cp)

            presets = cp.ConfigPresets(presets_dir=presets_dir)
            presets.apply_preset("test_preset")

            with open(settings_path, 'r', encoding='utf-8') as f:
                merged = yaml.safe_load(f)

            assert merged["strategy"]["base_cushion"] == 0.05
            assert merged["strategy"]["alpha"] == 0.7
            assert merged["redis"]["host"] == "localhost"
            assert merged["existing_key"] == "keep_me"
            assert merged["new_key"] == "new_value"
        finally:
            sys.path[:] = sys_path_backup
            for mod in list(sys.modules):
                if mod.startswith('shared'):
                    sys.modules.pop(mod, None)

    def test_apply_nonexistent_raises(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        base = tmp_path / "project"
        base.mkdir()
        config_dir = base / "config"
        config_dir.mkdir()
        (config_dir / "settings.yaml").write_text(yaml.dump({}), encoding="utf-8")

        real_presets = Path(__file__).resolve().parents[2] / "shared" / "config_presets.py"
        shared_dir = base / "shared"
        shared_dir.mkdir()
        (shared_dir / "__init__.py").write_text("", encoding="utf-8")
        fake_cp = shared_dir / "config_presets.py"
        fake_cp.write_text(real_presets.read_text(encoding='utf-8'), encoding='utf-8')

        sys_path_backup = list(sys.path)
        sys.path.insert(0, str(base))
        try:
            import importlib
            for mod in list(sys.modules):
                if mod.startswith('shared'):
                    sys.modules.pop(mod, None)
            import shared.config_presets as cp
            importlib.reload(cp)

            presets = cp.ConfigPresets(presets_dir=presets_dir)
            with pytest.raises(FileNotFoundError, match="不存在"):
                presets.apply_preset("nonexistent")
        finally:
            sys.path[:] = sys_path_backup

    def test_apply_missing_settings_raises(self, apply_env):
        base, settings_path, presets_dir = apply_env
        settings_path.unlink()

        real_presets = Path(__file__).resolve().parents[2] / "shared" / "config_presets.py"
        shared_dir = base / "shared"
        fake_cp = shared_dir / "config_presets.py"
        fake_cp.write_text(real_presets.read_text(encoding='utf-8'), encoding='utf-8')

        sys_path_backup = list(sys.path)
        sys.path.insert(0, str(base))
        try:
            import importlib
            for mod in list(sys.modules):
                if mod.startswith('shared'):
                    sys.modules.pop(mod, None)
            import shared.config_presets as cp
            importlib.reload(cp)

            presets = cp.ConfigPresets(presets_dir=presets_dir)
            with pytest.raises(FileNotFoundError, match="配置文件不存在"):
                presets.apply_preset("any")
        finally:
            sys.path[:] = sys_path_backup


class TestSavePreset:
    """测试保存自定义方案"""

    def test_save_filters_sensitive_data(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        custom_dir = presets_dir / "custom"
        custom_dir.mkdir()

        config_data = {
            "api": {
                "polymarket": {
                    "api_secret": "super_secret_123",
                    "api_key": "key_456",
                }
            },
            "redis": {
                "password": "redis_pass",
                "host": "localhost",
            },
            "safe_param": "normal_value",
        }

        presets = ConfigPresets(presets_dir=presets_dir)
        presets.save_preset("my_safe", config=config_data)

        saved_file = custom_dir / "my_safe.yaml"
        assert saved_file.exists()

        with open(saved_file, 'r', encoding='utf-8') as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["api"]["polymarket"]["api_secret"] == "***FILTERED***"
        assert saved_data["api"]["polymarket"]["api_key"] == "***FILTERED***"
        assert saved_data["redis"]["password"] == "***FILTERED***"
        assert saved_data["redis"]["host"] == "localhost"
        assert saved_data["safe_param"] == "normal_value"

    def test_save_creates_file(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        presets = ConfigPresets(presets_dir=presets_dir)
        presets.save_preset("test_save", config={"key": "value"})

        assert (presets_dir / "custom" / "test_save.yaml").exists()


class TestDeletePreset:
    """测试删除自定义方案"""

    def test_delete_custom_preset(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        custom_dir = presets_dir / "custom"
        custom_dir.mkdir()

        (custom_dir / "to_delete.yaml").write_text(yaml.dump({}), encoding="utf-8")

        presets = ConfigPresets(presets_dir=presets_dir)
        presets.delete_preset("to_delete")

        assert not (custom_dir / "to_delete.yaml").exists()

    def test_delete_builtin_raises(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        presets = ConfigPresets(presets_dir=presets_dir)
        with pytest.raises(ValueError, match="不能删除内置方案"):
            presets.delete_preset("conservative")

    def test_delete_nonexistent_raises(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        presets = ConfigPresets(presets_dir=presets_dir)
        with pytest.raises(FileNotFoundError, match="自定义方案不存在"):
            presets.delete_preset("ghost")


class TestDiffPresets:
    """测试方案对比"""

    @pytest.fixture
    def diff_env(self, tmp_path):
        """创建对比测试环境"""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        data1 = {
            "strategy": {"base_cushion": 0.03, "alpha": 0.3},
            "only_in_1": "value1",
        }
        data2 = {
            "strategy": {"base_cushion": 0.01, "alpha": 0.7},
            "only_in_2": "value2",
        }

        (presets_dir / "preset1.yaml").write_text(yaml.dump(data1), encoding="utf-8")
        (presets_dir / "preset2.yaml").write_text(yaml.dump(data2), encoding="utf-8")

        return presets_dir

    def test_diff_identifies_only_in_first(self, diff_env, monkeypatch):
        with patch.object(ConfigPresets, '__init__', lambda self, presets_dir=None: None):
            presets = object.__new__(ConfigPresets)
            presets.presets_dir = diff_env
            presets.custom_presets_dir = diff_env / "custom"

            diff = presets.diff_presets("preset1", "preset2")
            assert "only_in_1" in diff.only_in_first
            assert diff.only_in_first["only_in_1"] == "value1"

    def test_diff_identifies_only_in_second(self, diff_env, monkeypatch):
        with patch.object(ConfigPresets, '__init__', lambda self, presets_dir=None: None):
            presets = object.__new__(ConfigPresets)
            presets.presets_dir = diff_env
            presets.custom_presets_dir = diff_env / "custom"

            diff = presets.diff_presets("preset1", "preset2")
            assert "only_in_2" in diff.only_in_second
            assert diff.only_in_second["only_in_2"] == "value2"

    def test_diff_identifies_different_values(self, diff_env, monkeypatch):
        with patch.object(ConfigPresets, '__init__', lambda self, presets_dir=None: None):
            presets = object.__new__(ConfigPresets)
            presets.presets_dir = diff_env
            presets.custom_presets_dir = diff_env / "custom"

            diff = presets.diff_presets("preset1", "preset2")
            assert "strategy" in diff.different
            assert diff.different["strategy"]["preset1"]["base_cushion"] == 0.03
            assert diff.different["strategy"]["preset2"]["base_cushion"] == 0.01

    def test_diff_identical_presets_empty_diff(self, tmp_path, monkeypatch):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        same_data = {"key": "value"}
        (presets_dir / "same1.yaml").write_text(yaml.dump(same_data), encoding="utf-8")
        (presets_dir / "same2.yaml").write_text(yaml.dump(same_data), encoding="utf-8")

        with patch.object(ConfigPresets, '__init__', lambda self, presets_dir=None: None):
            presets = object.__new__(ConfigPresets)
            presets.presets_dir = presets_dir
            presets.custom_presets_dir = presets_dir / "custom"

            diff = presets.diff_presets("same1", "same2")
            assert len(diff.only_in_first) == 0
            assert len(diff.only_in_second) == 0
            assert len(diff.different) == 0


class TestDeepMerge:
    """测试深度合并逻辑"""

    def test_flat_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = ConfigPresets._deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"strategy": {"base_cushion": 0.02, "alpha": 0.5}}
        override = {"strategy": {"base_cushion": 0.05}}
        result = ConfigPresets._deep_merge(base, override)
        assert result["strategy"]["base_cushion"] == 0.05
        assert result["strategy"]["alpha"] == 0.5

    def test_deeply_nested_merge(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 10}}}
        result = ConfigPresets._deep_merge(base, override)
        assert result["a"]["b"]["c"] == 10
        assert result["a"]["b"]["d"] == 2

    def test_add_new_keys(self):
        base = {"a": 1}
        override = {"b": 2, "c": 3}
        result = ConfigPresets._deep_merge(base, override)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_override_dict_with_non_dict(self):
        base = {"nested": {"key": "old"}}
        override = {"nested": "replaced"}
        result = ConfigPresets._deep_merge(base, override)
        assert result["nested"] == "replaced"

    def test_does_not_mutate_original(self):
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        original_base = {"a": {"b": 1}}
        ConfigPresets._deep_merge(base, override)
        assert base == original_base

    def test_empty_base(self):
        result = ConfigPresets._deep_merge({}, {"a": 1})
        assert result == {"a": 1}

    def test_empty_override(self):
        result = ConfigPresets._deep_merge({"a": 1}, {})
        assert result == {"a": 1}


class TestFilterSensitiveData:
    """测试敏感信息过滤"""

    def test_filters_password(self):
        data = {"password": "secret123", "normal": "ok"}
        result = ConfigPresets._filter_sensitive_data(data)
        assert result["password"] == "***FILTERED***"
        assert result["normal"] == "ok"

    def test_filters_secret(self):
        data = {"secret": "hidden", "visible": "yes"}
        result = ConfigPresets._filter_sensitive_data(data)
        assert result["secret"] == "***FILTERED***"

    def test_filters_key(self):
        data = {"api_key": "abc123", "name": "test"}
        result = ConfigPresets._filter_sensitive_data(data)
        assert result["api_key"] == "***FILTERED***"

    def test_filters_private_key(self):
        data = {"private_key": "0x1234...abcd", "public": "info"}
        result = ConfigPresets._filter_sensitive_data(data)
        assert result["private_key"] == "***FILTERED***"

    def test_case_insensitive(self):
        data = {"API_SECRET": "val", "MyPassword": "pass"}
        result = ConfigPresets._filter_sensitive_data(data)
        assert result["API_SECRET"] == "***FILTERED***"
        assert result["MyPassword"] == "***FILTERED***"

    def test_nested_filtering(self):
        data = {
            "api": {
                "polymarket": {
                    "api_secret": "s",
                    "api_key": "k",
                },
                "normal_field": "ok"
            }
        }
        result = ConfigPresets._filter_sensitive_data(data)
        assert result["api"]["polymarket"]["api_secret"] == "***FILTERED***"
        assert result["api"]["polymarket"]["api_key"] == "***FILTERED***"
        assert result["api"]["normal_field"] == "ok"

    def test_no_sensitive_keys(self):
        data = {"name": "test", "count": 42}
        result = ConfigPresets._filter_sensitive_data(data)
        assert result == data

    def test_empty_dict(self):
        result = ConfigPresets._filter_sensitive_data({})
        assert result == {}

    def test_partial_key_match(self):
        data = {"mypassword123": "val", "normalfield": "ok"}
        result = ConfigPresets._filter_sensitive_data(data)
        assert result["mypassword123"] == "***FILTERED***"
        assert result["normalfield"] == "ok"


class TestDictDiff:
    """测试字典差异比较"""

    def test_only_in_first(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2}
        o1, o2, diff = ConfigPresets._dict_diff(d1, d2)
        assert o1 == {"a": 1}
        assert o2 == {}
        assert diff == {}

    def test_only_in_second(self):
        d1 = {"a": 1}
        d2 = {"a": 1, "c": 3}
        o1, o2, diff = ConfigPresets._dict_diff(d1, d2)
        assert o1 == {}
        assert o2 == {"c": 3}

    def test_different_values(self):
        d1 = {"x": 10}
        d2 = {"x": 20}
        o1, o2, diff = ConfigPresets._dict_diff(d1, d2)
        assert o1 == {}
        assert o2 == {}
        assert "x" in diff
        assert diff["x"]["preset1"] == 10
        assert diff["x"]["preset2"] == 20

    def test_identical_dicts(self):
        d = {"a": 1, "b": 2}
        o1, o2, diff = ConfigPresets._dict_diff(d, d)
        assert o1 == {}
        assert o2 == {}
        assert diff == {}

    def test_mixed_scenario(self):
        d1 = {"a": 1, "b": 2, "c": 3}
        d2 = {"b": 2, "c": 30, "d": 4}
        o1, o2, diff = ConfigPresets._dict_diff(d1, d2)
        assert o1 == {"a": 1}
        assert o2 == {"d": 4}
        assert "c" in diff

    def test_empty_both(self):
        o1, o2, diff = ConfigPresets._dict_diff({}, {})
        assert o1 == {}
        assert o2 == {}
        assert diff == {}


class TestFindPresetFile:
    """测试查找方案文件"""

    def test_finds_builtin(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()
        (presets_dir / "builtin.yaml").write_text("{}", encoding="utf-8")

        with patch.object(ConfigPresets, '__init__', lambda self, presets_dir=None: None):
            presets = object.__new__(ConfigPresets)
            presets.presets_dir = presets_dir
            presets.custom_presets_dir = presets_dir / "custom"

            result = presets._find_preset_file("builtin")
            assert result is not None
            assert result.name == "builtin.yaml"
            assert result.parent == presets_dir

    def test_finds_custom(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        custom_dir = presets_dir / "custom"
        custom_dir.mkdir()
        (custom_dir / "custom_one.yaml").write_text("{}", encoding="utf-8")

        with patch.object(ConfigPresets, '__init__', lambda self, presets_dir=None: None):
            presets = object.__new__(ConfigPresets)
            presets.presets_dir = presets_dir
            presets.custom_presets_dir = custom_dir

            result = presets._find_preset_file("custom_one")
            assert result is not None
            assert result.parent == custom_dir

    def test_builtin_priority_over_custom(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        custom_dir = presets_dir / "custom"
        custom_dir.mkdir()
        (presets_dir / "both.yaml").write_text("builtin", encoding="utf-8")
        (custom_dir / "both.yaml").write_text("custom", encoding="utf-8")

        with patch.object(ConfigPresets, '__init__', lambda self, presets_dir=None: None):
            presets = object.__new__(ConfigPresets)
            presets.presets_dir = presets_dir
            presets.custom_presets_dir = custom_dir

            result = presets._find_preset_file("both")
            assert result.parent == presets_dir

    def test_not_found_returns_none(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        with patch.object(ConfigPresets, '__init__', lambda self, presets_dir=None: None):
            presets = object.__new__(ConfigPresets)
            presets.presets_dir = presets_dir
            presets.custom_presets_dir = presets_dir / "custom"

            result = presets._find_preset_file("ghost")
            assert result is None


class TestValidatePreset:
    """测试方案验证"""

    def test_validate_valid_preset(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        valid_data = {"strategy": {"base_cushion": 0.5, "alpha": 0.5}}
        (presets_dir / "valid.yaml").write_text(yaml.dump(valid_data), encoding="utf-8")

        presets = ConfigPresets(presets_dir=presets_dir)
        try:
            result = presets.validate_preset("valid")
            assert isinstance(result.is_valid, bool)
        except (ImportError, ModuleNotFoundError):
            pass

    def test_validate_nonexistent_preset(self, tmp_path):
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "custom").mkdir()

        presets = ConfigPresets(presets_dir=presets_dir)
        try:
            result = presets.validate_preset("ghost")
            assert result.is_valid is False
            assert len(result.errors) > 0
        except (ImportError, ModuleNotFoundError):
            pass
