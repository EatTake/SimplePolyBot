"""
配置向导模块单元测试

测试 ConfigWizard、SensitiveInputHandler 的核心功能：
- 初始化与基本流程
- 敏感信息掩码与确认
- 输入验证与类型转换
- 不同模式下的参数收集（mock 用户交互）
"""

import sys
from unittest.mock import patch, MagicMock

import pytest

from shared.parameter_registry import ParameterInfo, ParameterRegistry, initialize_parameter_registry
from shared.config_wizard import (
    SensitiveInputHandler,
    ConfigWizard,
    ConfigWizardCLI,
)


class TestSensitiveInputHandler:
    """敏感信息输入处理器测试"""

    def test_mask_short_value(self):
        """测试短值掩码 - 长度不超过 visible_chars"""
        result = SensitiveInputHandler.mask("abc", visible_chars=6)
        assert result == "***"

    def test_mask_exact_length(self):
        """测试恰好等于 visible_chars 长度的值"""
        result = SensitiveInputHandler.mask("abcdef", visible_chars=6)
        assert result == "******"

    def test_mask_long_value(self):
        """测试长值掩码 - 显示前半部分 + 星号"""
        result = SensitiveInputHandler.mask("my_secret_api_key_12345", visible_chars=6)
        assert "my" in result
        assert "*" in result
        assert "12345" not in result

    def test_mask_default_visible_chars(self):
        """测试默认可见字符数"""
        result = SensitiveInputHandler.mask("polymarket_secret_key")
        assert "poly" in result or "pol" in result
        assert result.count("*") > 0
        assert "secret" not in result
        assert "key" not in result

    def test_mask_empty_string(self):
        """测试空字符串掩码"""
        result = SensitiveInputHandler.mask("")
        assert result == ""

    def test_prompt_calls_getpass(self):
        """测试 prompt 调用 getpass.getpass"""
        with patch("shared.config_wizard.getpass") as mock_getpass:
            mock_getpass.getpass.return_value = "secret_value"
            result = SensitiveInputHandler.prompt("密码")
            mock_getpass.getpass.assert_called_once_with("  密码: ")
            assert result == "secret_value"

    def test_confirm_match(self):
        """测试确认匹配"""
        with patch("shared.config_wizard.getpass") as mock_getpass:
            mock_getpass.getpass.return_value = "same_password"
            result = SensitiveInputHandler.confirm("密码", "same_password")
            assert result is True

    def test_confirm_mismatch(self):
        """测试确认不匹配"""
        with patch("shared.config_wizard.getpass") as mock_getpass:
            mock_getpass.getpass.return_value = "different_password"
            result = SensitiveInputHandler.confirm("密码", "original_password")
            assert result is False


class TestConfigWizardInit:
    """ConfigWizard 初始化测试"""

    def setup_method(self):
        ParameterRegistry._instance = None
        self.registry = initialize_parameter_registry()

    def test_init_default_mode(self):
        """测试默认模式为 standard"""
        wizard = ConfigWizard()
        assert wizard.mode == "standard"

    def test_init_custom_mode(self):
        """测试自定义模式"""
        for mode in ["quick", "standard", "expert"]:
            wizard = ConfigWizard(mode=mode)
            assert wizard.mode == mode

    def test_init_collected_values_empty(self):
        """测试初始化时收集值为空字典"""
        wizard = ConfigWizard()
        assert wizard.collected_values == {}

    def test_init_registry_loaded(self):
        """测试初始化时注册表已加载"""
        wizard = ConfigWizard()
        assert wizard.registry is not None
        all_params = wizard.registry.get_all()
        assert len(all_params) >= 30

    def test_init_validator_created(self):
        """测试验证器已创建"""
        wizard = ConfigWizard()
        assert wizard.validator is not None

    def test_init_formatter_created(self):
        """测试格式化器已创建"""
        wizard = ConfigWizard()
        assert wizard.formatter is not None

    def test_modes_constant(self):
        """测试 MODES 常量"""
        assert ConfigWizard.MODES == ["quick", "standard", "expert"]


class TestConfigWizardConvertType:
    """类型转换测试"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        self.wizard = ConfigWizard(mode="quick")

    def test_convert_int(self):
        assert self.wizard.convert_type("42", int) == 42

    def test_convert_float(self):
        assert self.wizard.convert_type("3.14", float) == 3.14

    def test_convert_bool_true(self):
        for val in ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]:
            assert self.wizard.convert_type(val, bool) is True

    def test_convert_bool_false(self):
        for val in ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF", "random"]:
            assert self.wizard.convert_type(val, bool) is False

    def test_convert_str(self):
        assert self.wizard.convert_type("hello", str) == "hello"

    def test_convert_list(self):
        result = self.wizard.convert_type("a, b, c", list)
        assert result == ["a", "b", "c"]

    def test_convert_list_single_item(self):
        result = self.wizard.convert_type("alone", list)
        assert result == ["alone"]


class TestConfigWizardValidateInput:
    """输入验证测试"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        self.wizard = ConfigWizard(mode="quick")

    def _make_param(self, **overrides) -> ParameterInfo:
        defaults = dict(
            key="test.param",
            name="测试参数",
            description="测试描述",
            type=float,
            default=0.5,
        )
        defaults.update(overrides)
        return ParameterInfo(**defaults)

    def test_validate_valid_int_in_range(self):
        param = self._make_param(type=int, default=100, range=(10, 1000))
        valid, msg = self.wizard.validate_input(param, "500")
        assert valid is True
        assert msg == ""

    def test_validate_int_out_of_range_high(self):
        param = self._make_param(type=int, default=100, range=(10, 100))
        valid, msg = self.wizard.validate_input(param, "999")
        assert valid is False
        assert "超出范围" in msg

    def test_validate_int_out_of_range_low(self):
        param = self._make_param(type=int, default=100, range=(10, 100))
        valid, msg = self.wizard.validate_input(param, "1")
        assert valid is False
        assert "超出范围" in msg

    def test_validate_valid_choice(self):
        param = self._make_param(
            type=str, default="development",
            choices=["development", "staging", "production"]
        )
        valid, msg = self.wizard.validate_input(param, "production")
        assert valid is True

    def test_validate_invalid_choice(self):
        param = self._make_param(
            type=str, default="development",
            choices=["development", "staging", "production"]
        )
        valid, msg = self.wizard.validate_input(param, "nightly")
        assert valid is False
        assert "必须是" in msg

    def test_validate_invalid_type_float_from_string(self):
        param = self._make_param(type=float, default=0.5)
        valid, msg = self.wizard.validate_input(param, "not_a_number")
        assert valid is False
        assert "类型错误" in msg

    def test_validate_no_range_no_choice_passes(self):
        param = self._make_param(type=str, default="hello")
        valid, msg = self.wizard.validate_input(param, "any_value")
        assert valid is True

    def test_validate_float_at_boundary_min(self):
        param = self._make_param(type=float, default=0.5, range=(0.0, 1.0))
        valid, _ = self.wizard.validate_input(param, "0.0")
        assert valid is True

    def test_validate_float_at_boundary_max(self):
        param = self._make_param(type=float, default=0.5, range=(0.0, 1.0))
        valid, _ = self.wizard.validate_input(param, "1.0")
        assert valid is True


class TestConfigWizardPromptForValue:
    """用户输入提示测试（使用 mock input）"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        self.wizard = ConfigWizard(mode="quick")

    @patch("builtins.input")
    def test_prompt_returns_user_input(self, mock_input):
        """测试返回用户输入的转换值"""
        param = ParameterInfo(
            key="test.value", name="测试值", description="", type=int, default=10
        )
        mock_input.return_value = "42"
        result = self.wizard.prompt_for_value(param)
        assert result == 42

    @patch("builtins.input")
    def test_prompt_empty_returns_default(self, mock_input):
        """测试空输入返回默认值"""
        param = ParameterInfo(
            key="test.value", name="测试值", description="", type=int, default=99
        )
        mock_input.return_value = ""
        result = self.wizard.prompt_for_value(param)
        assert result == 99

    @patch("builtins.input")
    def test_prompt_invalid_then_retry_default(self, mock_input):
        """测试无效输入后重试并使用默认值"""
        param = ParameterInfo(
            key="test.value", name="测试值", description="",
            type=int, default=50, range=(10, 100),
            suggestions={"default": 50}
        )
        mock_input.side_effect = ["999", "y"]
        result = self.wizard.prompt_for_value(param)
        assert result == 50

    @patch("builtins.input")
    def test_prompt_invalid_then_retry_decline_default(self, mock_input):
        """测试无效输入后拒绝默认值，仍返回默认值（fallback）"""
        param = ParameterInfo(
            key="test.value", name="测试值", description="",
            type=int, default=50, range=(10, 100),
        )
        mock_input.side_effect = ["999", "n"]
        result = self.wizard.prompt_for_value(param)
        assert result == 50

    @patch("builtins.input")
    def test_prompt_bool_true_input(self, mock_input):
        """测试布尔类型 true 输入"""
        param = ParameterInfo(
            key="test.flag", name="开关", description="",
            type=bool, default=False,
        )
        mock_input.return_value = "true"
        result = self.wizard.prompt_for_value(param)
        assert result is True


class TestConfigWizardPromptForSensitiveValue:
    """敏感值输入提示测试"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        self.wizard = ConfigWizard(mode="quick")

    @patch("shared.config_wizard.getpass")
    def test_sensitive_non_required_returns_value(self, mock_getpass):
        """测试非必填敏感参数直接返回值"""
        param = ParameterInfo(
            key="optional.secret", name="可选密钥", description="",
            type=str, default="", sensitive=True, required=False,
        )
        mock_getpass.getpass.side_effect = ["my_secret"]
        result = self.wizard.prompt_for_sensitive_value(param)
        assert result == "my_secret"

    @patch("shared.config_wizard.getpass")
    def test_sensitive_required_confirm_match(self, mock_getpass):
        """测试必填敏感参数确认匹配"""
        param = ParameterInfo(
            key="api.key", name="API Key", description="",
            type=str, default="", sensitive=True, required=True,
        )
        mock_getpass.getpass.side_effect = ["secret123", "secret123"]
        result = self.wizard.prompt_for_sensitive_value(param)
        assert result == "secret123"

    @patch("shared.config_wizard.getpass")
    def test_sensitive_required_confirm_mismatch_recurses(self, mock_getpass):
        """测试必填敏感参数确认不匹配时递归重试"""
        param = ParameterInfo(
            key="api.key", name="API Key", description="",
            type=str, default="", sensitive=True, required=True,
        )
        call_count = [0]
        def side_effect(label):
            call_count[0] += 1
            if call_count[0] % 2 == 1:
                return "first_try"
            return "different_try"
        mock_getpass.getpass.side_effect = side_effect

        with pytest.raises(RecursionError):
            self.wizard.prompt_for_sensitive_value(param)

    @patch("shared.config_wizard.getpass")
    def test_sensitive_empty_value_returns_none(self, mock_getpass):
        """测试空敏感值返回 None"""
        param = ParameterInfo(
            key="api.key", name="API Key", description="",
            type=str, default="", sensitive=True, required=False,
        )
        mock_getpass.getpass.return_value = ""
        result = self.wizard.prompt_for_sensitive_value(param)
        assert result is None


class TestConfigWizardShowParameterInfo:
    """参数信息展示测试"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        self.wizard = ConfigWizard(mode="quick")

    @patch("builtins.print")
    def test_show_basic_info(self, mock_print):
        """测试显示基本信息"""
        param = ParameterInfo(
            key="test.param", name="测试参数", description="这是一个测试参数",
            type=int, default=10,
        )
        self.wizard.show_parameter_info(param)

        printed_text = str([str(call) for call in mock_print.call_args_list])
        assert "测试参数" in printed_text
        assert "这是一个测试参数" in printed_text

    @patch("builtins.print")
    def test_show_info_with_range(self, mock_print):
        """测试带范围的参数信息"""
        param = ParameterInfo(
            key="test.range", name="范围参数", description="有取值范围",
            type=int, default=50, range=(10, 100),
        )
        self.wizard.show_parameter_info(param)

        printed_text = str([str(call) for call in mock_print.call_args_list])
        assert "10" in printed_text
        assert "100" in printed_text

    @patch("builtins.print")
    def test_show_info_with_choices(self, mock_print):
        """测试带选项的参数信息"""
        param = ParameterInfo(
            key="test.env", name="环境", description="运行环境",
            type=str, default="dev",
            choices=["dev", "staging", "prod"],
        )
        self.wizard.show_parameter_info(param)

        printed_text = str([str(call) for call in mock_print.call_args_list])
        assert "dev" in printed_text
        assert "prod" in printed_text

    @patch("builtins.print")
    def test_show_info_with_suggestions(self, mock_print):
        """测试带建议值的参数信息"""
        param = ParameterInfo(
            key="test.sug", name="建议参数", description="有建议值",
            type=float, default=0.5,
            suggestions={"conservative": 0.3, "aggressive": 0.7},
        )
        self.wizard.show_parameter_info(param)

        printed_text = str([str(call) for call in mock_print.call_args_list])
        assert "conservative" in printed_text
        assert "aggressive" in printed_text


class TestConfigWizardRunModes:
    """不同模式下的配置收集流程测试"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()

    @patch("builtins.input")
    @patch("shared.config_wizard.getpass")
    def test_quick_mode_collects_only_core(self, mock_getpass, mock_input):
        """快速模式仅收集核心参数（前5个）"""
        mock_input.return_value = ""
        mock_getpass.getpass.return_value = ""

        wizard = ConfigWizard(mode="quick")
        result = wizard.run()

        core_params = ParameterRegistry.get_instance().get_by_level("core")
        assert len(result) <= len(core_params[:5])

    @patch("builtins.input")
    @patch("shared.config_wizard.getpass")
    @patch("sys.exit")
    def test_review_and_confirm_yes(self, mock_exit, mock_getpass, mock_input):
        """测试确认保存 - 输入 y"""
        mock_input.side_effect = ["", "", "", "", "", "", "y"]
        mock_getpass.getpass.return_value = ""

        wizard = ConfigWizard(mode="quick")
        result = wizard.run()

        mock_exit.assert_not_called()
        assert isinstance(result, dict)

    @patch("builtins.input")
    @patch("shared.config_wizard.getpass")
    def test_review_and_confirm_no_exits(self, mock_getpass, mock_input):
        """测试取消配置 - 输入 n 触发 sys.exit"""
        mock_input.side_effect = ["", "", "", "", "", "n"]
        mock_getpass.getpass.return_value = ""

        wizard = ConfigWizard(mode="quick")

        with pytest.raises(SystemExit):
            wizard.run()


class TestConfigGetParameterInfo:
    """Config 新增方法测试：get_parameter_info"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        from shared.config import Config
        Config._instance = None

    def test_get_existing_parameter_info(self):
        """获取存在的参数信息"""
        from shared.config import Config
        config = Config.get_instance()

        info = config.get_parameter_info("strategy.alpha")
        assert info is not None
        assert info.key == "strategy.alpha"
        assert info.name == "Alpha 价格调整系数"

    def test_get_nonexistent_parameter_info(self):
        """获取不存在的参数返回 None"""
        from shared.config import Config
        config = Config.get_instance()

        info = config.get_parameter_info("nonexistent.parameter.key")
        assert info is None

    def test_get_redis_host_info(self):
        """获取 Redis 主机参数信息"""
        from shared.config import Config
        config = Config.get_instance()

        info = config.get_parameter_info("redis.host")
        assert info is not None
        assert info.type is str
        assert info.required is True

    def test_get_sensitive_parameter_info(self):
        """获取敏感参数信息"""
        from shared.config import Config
        config = Config.get_instance()

        info = config.get_parameter_info("redis.password")
        assert info is not None
        assert info.sensitive is True


class TestConfigGetAllParameters:
    """Config 新增方法测试：get_all_parameters"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        from shared.config import Config
        Config._instance = None

    def test_get_all_no_filter(self):
        """无过滤获取所有参数"""
        from shared.config import Config
        config = Config.get_instance()

        params = config.get_all_parameters()
        assert len(params) >= 30

    def test_get_all_filter_by_strategy(self):
        """按 strategy 类别过滤"""
        from shared.config import Config
        config = Config.get_instance()

        params = config.get_all_parameters(category="strategy")
        assert len(params) >= 16
        for p in params:
            assert p.category == "strategy"

    def test_get_all_filter_by_connection(self):
        """按 connection 类别过滤"""
        from shared.config import Config
        config = Config.get_instance()

        params = config.get_all_parameters(category="connection")
        assert len(params) >= 11
        for p in params:
            assert p.category == "connection"

    def test_get_all_filter_by_api(self):
        """按 api 类别过滤"""
        from shared.config import Config
        config = Config.get_instance()

        params = config.get_all_parameters(category="api")
        assert len(params) >= 3

    def test_get_all_filter_returns_list(self):
        """返回类型为 list"""
        from shared.config import Config
        config = Config.get_instance()

        params = config.get_all_parameters()
        assert isinstance(params, list)


class TestConfigGetParameterSchema:
    """Config 新增方法测试：get_parameter_schema"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        from shared.config import Config
        Config._instance = None

    def test_schema_has_required_fields(self):
        """Schema 包含必需字段"""
        from shared.config import Config
        config = Config.get_instance()

        schema = config.get_parameter_schema()

        assert "$schema" in schema
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert schema["title"] == "SimplePolyBot Configuration"

    def test_schema_has_nested_properties(self):
        """Schema 包含嵌套属性结构"""
        from shared.config import Config
        config = Config.get_instance()

        schema = config.get_parameter_schema()

        assert "strategy" in schema["properties"]
        assert "redis" in schema["properties"]

    def test_schema_strategy_has_alpha(self):
        """Schema 中 strategy 下包含 alpha 属性"""
        from shared.config import Config
        config = Config.get_instance()

        schema = config.get_parameter_schema()

        strategy_props = schema["properties"]["strategy"]["properties"]
        assert "alpha" in strategy_props
        alpha_prop = strategy_props["alpha"]
        assert alpha_prop["type"] == "number"
        assert "description" in alpha_prop
        assert "default" in alpha_prop

    def test_schema_range_becomes_minimum_maximum(self):
        """Schema 中 range 转换为 minimum/maximum"""
        from shared.config import Config
        config = Config.get_instance()

        schema = config.get_parameter_schema()

        strategy_props = schema["properties"]["strategy"]["properties"]
        if "base_cushion" in strategy_props:
            bc = strategy_props["base_cushion"]
            assert "minimum" in bc
            assert "maximum" in bc

    def test_schema_choices_become_enum(self):
        """Schema 中 choices 转换为 enum"""
        from shared.config import Config
        config = Config.get_instance()

        schema = config.get_parameter_schema()

        system_props = schema["properties"].get("system", {}).get("properties", {})
        if "environment" in system_props:
            env = system_props["environment"]
            assert "enum" in env
            assert "production" in env["enum"]

    def test_schema_required_contains_required_params(self):
        """Schema required 列表包含必填参数"""
        from shared.config import Config
        config = Config.get_instance()

        schema = config.get_parameter_schema()

        assert len(schema["required"]) > 0
        assert "redis.host" in schema["required"]
        assert "redis.port" in schema["required"]


class TestPythonTypeToJson:
    """Python 类型到 JSON 类型映射测试"""

    def test_int_to_integer(self):
        from shared.config import Config
        assert Config._python_type_to_json(int) == "integer"

    def test_float_to_number(self):
        from shared.config import Config
        assert Config._python_type_to_json(float) == "number"

    def test_bool_to_boolean(self):
        from shared.config import Config
        assert Config._python_type_to_json(bool) == "boolean"

    def test_str_to_string(self):
        from shared.config import Config
        assert Config._python_type_to_json(str) == "string"

    def test_list_to_array(self):
        from shared.config import Config
        assert Config._python_type_to_json(list) == "array"

    def test_dict_to_object(self):
        from shared.config import Config
        assert Config._python_type_to_json(dict) == "object"

    def test_unknown_type_fallback(self):
        from shared.config import Config
        assert Config._python_type_to_json(object) == "string"


class TestConfigWizardCLI:
    """命令行入口测试"""

    def test_create_parser(self):
        """测试解析器创建成功"""
        cli = ConfigWizardCLI()
        assert cli.parser is not None

    def test_parser_has_mode_argument(self):
        """测试 --mode 参数存在"""
        cli = ConfigWizardCLI()
        args = cli.parser.parse_args(["--mode", "quick"])
        assert args.mode == "quick"

    def test_parser_mode_default_standard(self):
        """测试 mode 默认值为 standard"""
        cli = ConfigWizardCLI()
        args = cli.parser.parse_args([])
        assert args.mode == "standard"

    def test_parser_has_preset_argument(self):
        """测试 --preset 参数存在"""
        cli = ConfigWizardCLI()
        args = cli.parser.parse_args(["--preset", "balanced"])
        assert args.preset == "balanced"

    def test_parser_has_output_argument(self):
        """测试 --output 参数存在"""
        cli = ConfigWizardCLI()
        args = cli.parser.parse_args(["--output", "/tmp/config.yaml"])
        assert args.output == "/tmp/config.yaml"

    def test_parser_has_validate_only_flag(self):
        """测试 --validate-only 标志存在"""
        cli = ConfigWizardCLI()
        args_normal = cli.parser.parse_args([])
        args_flag = cli.parser.parse_args(["--validate-only"])
        assert args_normal.validate_only is False
        assert args_flag.validate_only is True

    def test_parser_has_generate_docs_flag(self):
        """测试 --generate-docs 标志存在"""
        cli = ConfigWizardCLI()
        args = cli.parser.parse_args(["--generate-docs"])
        assert args.generate_docs is True

    def test_parser_short_flags(self):
        """测试短标志别名"""
        cli = ConfigWizardCLI()
        args = cli.parser.parse_args(["-m", "expert", "-p", "aggressive"])
        assert args.mode == "expert"
        assert args.preset == "aggressive"


class TestConfigWizardIntegration:
    """集成风格测试：完整流程模拟"""

    def setup_method(self):
        ParameterRegistry._instance = None
        initialize_parameter_registry()
        from shared.config import Config
        Config._instance = None

    @patch("builtins.input")
    @patch("shared.config_wizard.getpass")
    @patch("sys.exit")
    def test_full_quick_mode_flow(self, mock_exit, mock_getpass, mock_input):
        """完整快速模式流程"""
        inputs = []
        getpass_inputs = []

        core_params = ParameterRegistry.get_instance().get_by_level("core")
        for _ in core_params[:5]:
            inputs.append("")
        for _ in ParameterRegistry.get_instance().get_sensitive():
            getpass_inputs.append("")
            getpass_inputs.append("")
        inputs.append("y")

        mock_input.side_effect = inputs
        mock_getpass.getpass.side_effect = getpass_inputs

        wizard = ConfigWizard(mode="quick")
        result = wizard.run()

        assert isinstance(result, dict)
        mock_exit.assert_not_called()

    @patch("builtins.input")
    @patch("shared.config_wizard.getpass")
    def test_collected_values_contain_defaults(self, mock_getpass, mock_input):
        """收集的值包含默认值"""
        mock_input.return_value = ""
        mock_getpass.getpass.return_value = ""

        wizard = ConfigWizard(mode="quick")
        result = wizard.run()

        for key, value in result.items():
            param = ParameterRegistry.get_instance().get(key)
            if param:
                assert value == param.default, \
                    f"{key}: 期望 {param.default}, 实际 {value}"
