"""
参数元数据系统单元测试

测试 ParameterInfo、ParameterRegistry 的核心功能以及全量参数注册验证
"""

import pytest

from shared.parameter_registry import (
    ParameterInfo,
    ParameterRegistry,
    initialize_parameter_registry,
)


class TestParameterInfo:
    """ParameterInfo dataclass 测试"""

    def test_creation_with_required_fields(self):
        info = ParameterInfo(
            key="test.param",
            name="测试参数",
            description="这是一个测试参数",
            type=float,
            default=0.5,
        )
        assert info.key == "test.param"
        assert info.name == "测试参数"
        assert info.description == "这是一个测试参数"
        assert info.type is float
        assert info.default == 0.5
        assert info.range is None
        assert info.choices is None
        assert info.required is False
        assert info.sensitive is False
        assert info.category == "general"
        assert info.level == "standard"
        assert info.suggestions == {}
        assert info.depends_on is None
        assert info.validation_hint == ""

    def test_creation_with_all_fields(self):
        info = ParameterInfo(
            key="strategy.alpha",
            name="Alpha 系数",
            description="价格调整系数",
            type=float,
            default=0.5,
            range=(0.0, 1.0),
            required=True,
            sensitive=False,
            category="strategy",
            level="core",
            suggestions={"conservative": 0.3, "default": 0.5},
            depends_on=["strategy.base_cushion"],
            validation_hint="范围 0-1",
        )
        assert info.range == (0.0, 1.0)
        assert info.required is True
        assert info.category == "strategy"
        assert info.level == "core"
        assert info.suggestions == {"conservative": 0.3, "default": 0.5}
        assert info.depends_on == ["strategy.base_cushion"]
        assert info.validation_hint == "范围 0-1"

    def test_choices_field(self):
        info = ParameterInfo(
            key="system.env",
            name="环境",
            description="运行环境",
            type=str,
            default="development",
            choices=["development", "staging", "production"],
        )
        assert info.choices == ["development", "staging", "production"]

    def test_sensitive_flag(self):
        sensitive_info = ParameterInfo(
            key="api.secret",
            name="API 密钥",
            description="敏感信息",
            type=str,
            default="",
            sensitive=True,
        )
        normal_info = ParameterInfo(
            key="api.timeout",
            name="超时",
            description="普通参数",
            type=int,
            default=30,
        )
        assert sensitive_info.sensitive is True
        assert normal_info.sensitive is False

    def test_suggestions_default_factory(self):
        info1 = ParameterInfo(key="a", name="A", description="", type=int, default=1)
        info2 = ParameterInfo(key="b", name="B", description="", type=int, default=2)
        assert info1.suggestions == {}
        assert info2.suggestions == {}


class TestParameterRegistry:
    """ParameterRegistry 注册表测试"""

    def setup_method(self):
        ParameterRegistry._instance = None

    def test_singleton_pattern(self):
        reg1 = ParameterRegistry()
        reg2 = ParameterRegistry()
        assert reg1 is reg2

    def test_get_instance_classmethod(self):
        reg1 = ParameterRegistry.get_instance()
        reg2 = ParameterRegistry.get_instance()
        assert reg1 is reg2

    def test_register_and_get(self):
        registry = ParameterRegistry.get_instance()
        info = ParameterInfo(
            key="test.unique_key",
            name="唯一键测试",
            description="注册和获取测试",
            type=int,
            default=42,
        )
        registry.register(info)
        result = registry.get("test.unique_key")
        assert result is not None
        assert result.key == "test.unique_key"
        assert result.default == 42

    def test_get_nonexistent_key(self):
        registry = ParameterRegistry.get_instance()
        result = registry.get("nonexistent.key.that.does.not.exist")
        assert result is None

    def test_register_overwrite(self):
        registry = ParameterRegistry.get_instance()
        info1 = ParameterInfo(
            key="test.overwrite",
            name="原始值",
            description="第一次注册",
            type=int,
            default=10,
        )
        info2 = ParameterInfo(
            key="test.overwrite",
            name="覆盖值",
            description="第二次注册",
            type=int,
            default=20,
        )
        registry.register(info1)
        registry.register(info2)
        result = registry.get("test.overwrite")
        assert result.default == 20
        assert result.name == "覆盖值"

    def test_get_all_no_filter(self):
        registry = ParameterRegistry.get_instance()
        registry.register(ParameterInfo(key="a", name="A", description="", type=int, default=1, category="cat1"))
        registry.register(ParameterInfo(key="b", name="B", description="", type=int, default=2, category="cat2"))
        registry.register(ParameterInfo(key="c", name="C", description="", type=int, default=3, category="cat1"))
        all_params = registry.get_all()
        assert len(all_params) == 3

    def test_get_all_with_category_filter(self):
        registry = ParameterRegistry.get_instance()
        registry.register(ParameterInfo(key="a", name="A", description="", type=int, default=1, category="strategy"))
        registry.register(ParameterInfo(key="b", name="B", description="", type=int, default=2, category="redis"))
        registry.register(ParameterInfo(key="c", name="C", description="", type=int, default=3, category="strategy"))
        strategy_params = registry.get_all(category="strategy")
        assert len(strategy_params) == 2
        keys = {p.key for p in strategy_params}
        assert keys == {"a", "c"}

    def test_get_required(self):
        registry = ParameterRegistry.get_instance()
        registry.register(ParameterInfo(key="req1", name="R1", description="", type=str, default="", required=True))
        registry.register(ParameterInfo(key="req2", name="R2", description="", type=str, default="", required=True))
        registry.register(ParameterInfo(key="opt1", name="O1", description="", type=str, default="", required=False))
        required = registry.get_required()
        assert len(required) == 2
        keys = {p.key for p in required}
        assert keys == {"req1", "req2"}

    def test_get_sensitive(self):
        registry = ParameterRegistry.get_instance()
        registry.register(ParameterInfo(key="secret1", name="S1", description="", type=str, default="", sensitive=True))
        registry.register(ParameterInfo(key="secret2", name="S2", description="", type=str, default="", sensitive=True))
        registry.register(ParameterInfo(key="public1", name="P1", description="", type=str, default="", sensitive=False))
        sensitive = registry.get_sensitive()
        assert len(sensitive) == 2
        keys = {p.key for p in sensitive}
        assert keys == {"secret1", "secret2"}

    def test_get_by_level(self):
        registry = ParameterRegistry.get_instance()
        registry.register(ParameterInfo(key="core1", name="C1", description="", type=int, default=1, level="core"))
        registry.register(ParameterInfo(key="core2", name="C2", description="", type=int, default=2, level="core"))
        registry.register(ParameterInfo(key="adv1", name="A1", description="", type=int, default=3, level="advanced"))
        core_params = registry.get_by_level("core")
        assert len(core_params) == 2
        adv_params = registry.get_by_level("advanced")
        assert len(adv_params) == 1


class TestFullParameterRegistration:
    """全量参数注册验证测试"""

    def setup_method(self):
        ParameterRegistry._instance = None
        self.registry = initialize_parameter_registry()

    def test_total_parameter_count(self):
        all_params = self.registry.get_all()
        assert len(all_params) >= 30, f"期望至少 30 个参数，实际注册了 {len(all_params)} 个"

    def test_strategy_category_count(self):
        strategy_params = self.registry.get_all(category="strategy")
        assert len(strategy_params) >= 16, f"策略类别至少应有 16 个参数，实际: {len(strategy_params)}"

    def test_redis_category_count(self):
        redis_params = self.registry.get_all(category="connection")
        assert len(redis_params) >= 11, f"Redis/连接类别至少应有 11 个参数，实际: {len(redis_params)}"

    def test_module_category_count(self):
        module_params = self.registry.get_all(category="module")
        assert len(module_params) >= 5, f"模块类别至少应有 5 个参数，实际: {len(module_params)}"

    def test_api_category_count(self):
        api_params = self.registry.get_all(category="api")
        assert len(api_params) >= 3, f"API 类别至少应有 3 个参数，实际: {len(api_params)}"

    def test_system_category_count(self):
        system_params = self.registry.get_all(category="system")
        assert len(system_params) >= 2, f"系统类别至少应有 2 个参数，实际: {len(system_params)}"

    def test_required_parameters_exist(self):
        required = self.registry.get_sensitive()
        required_keys = {p.key for p in required}
        expected_sensitive = {
            "redis.password",
            "api.polymarket.api_key",
            "api.polymarket.api_secret",
            "api.polymarket.api_passphrase",
        }
        for key in expected_sensitive:
            assert key in required_keys, f"缺少敏感参数: {key}"

    def test_sensitive_parameters_exist(self):
        sensitive = self.registry.get_sensitive()
        sensitive_keys = {p.key for p in sensitive}
        expected_sensitive = {
            "redis.password",
            "api.polymarket.api_key",
            "api.polymarket.api_secret",
            "api.polymarket.api_passphrase",
        }
        for key in expected_sensitive:
            assert key in sensitive_keys, f"缺少敏感参数: {key}"

    def test_core_strategy_params_registered(self):
        core_strategy_keys = [
            "strategy.base_cushion",
            "strategy.alpha",
            "strategy.max_buy_prices.default",
            "strategy.order_sizes.default",
            "strategy.risk_management.max_position_size",
            "strategy.risk_management.max_total_exposure",
            "strategy.risk_management.max_daily_loss",
            "strategy.risk_management.max_drawdown",
        ]
        for key in core_strategy_keys:
            info = self.registry.get(key)
            assert info is not None, f"缺少核心策略参数: {key}"
            assert info.level == "core", f"{key} 应为 core 级别"
            assert info.category == "strategy", f"{key} 应属于 strategy 类别"

    def test_redis_connection_params_registered(self):
        redis_keys = [
            "redis.host",
            "redis.port",
            "redis.password",
            "redis.db",
            "redis.pool.max_connections",
            "redis.retry.exponential_backoff",
        ]
        for key in redis_keys:
            info = self.registry.get(key)
            assert info is not None, f"缺少 Redis 参数: {key}"
            assert info.category == "connection", f"{key} 应属于 connection 类别"

    def test_module_switch_params_registered(self):
        module_keys = [
            "modules.market_data_collector.enabled",
            "modules.market_data_collector.websocket.url",
            "modules.strategy_engine.enabled",
            "modules.order_executor.enabled",
            "modules.settlement_worker.enabled",
        ]
        for key in module_keys:
            info = self.registry.get(key)
            assert info is not None, f"缺少模块参数: {key}"

    def test_api_credentials_registered(self):
        api_keys = [
            "api.polymarket.api_key",
            "api.polymarket.api_secret",
            "api.polymarket.api_passphrase",
        ]
        for key in api_keys:
            info = self.registry.get(key)
            assert info is not None, f"缺少 API 参数: {key}"
            assert info.sensitive is True, f"{key} 应标记为敏感"
            assert info.required is True, f"{key} 应标记为必填"

    def test_system_env_and_log_level(self):
        env_info = self.registry.get("system.environment")
        assert env_info is not None
        assert env_info.choices is not None
        assert "production" in env_info.choices

        log_info = self.registry.get("system.log_level")
        assert log_info is not None
        assert log_info.choices is not None
        assert "DEBUG" in log_info.choices
        assert "INFO" in log_info.choices

    def test_all_parameters_have_chinese_description(self):
        all_params = self.registry.get_all()
        for param in all_params:
            assert param.description, f"参数 {param.key} 缺少中文描述"
            assert len(param.description) > 5, f"参数 {param.key} 描述过短: '{param.description}'"

    def test_all_parameters_have_name(self):
        all_params = self.registry.get_all()
        for param in all_params:
            assert param.name, f"参数 {param.key} 缺少显示名称"

    def test_max_buy_prices_sub_params(self):
        sub_keys = [
            "strategy.max_buy_prices.high_confidence",
            "strategy.max_buy_prices.low_volatility",
            "strategy.max_buy_prices.fast_market",
        ]
        for key in sub_keys:
            info = self.registry.get(key)
            assert info is not None, f"缺少参数: {key}"
            assert info.type is float, f"{key} 类型应为 float"
            assert info.range is not None, f"{key} 应有取值范围"
            assert info.depends_on is not None, f"{key} 应有依赖声明"

    def test_risk_management_params_have_suggestions(self):
        risk_keys = [
            "strategy.risk_management.max_position_size",
            "strategy.risk_management.max_total_exposure",
            "strategy.risk_management.max_daily_loss",
            "strategy.risk_management.max_drawdown",
        ]
        for key in risk_keys:
            info = self.registry.get(key)
            assert info is not None, f"缺少风控参数: {key}"
            assert "conservative" in info.suggestions, f"{key} 缺少 conservative 建议"
            assert "aggressive" in info.suggestions, f"{key} 缺少 aggressive 建议"

    def test_stop_loss_take_profit_params(self):
        sltp_keys = [
            "strategy.stop_loss_take_profit.enabled",
            "strategy.stop_loss_take_profit.stop_loss_percentage",
            "strategy.stop_loss_take_profit.take_profit_percentage",
        ]
        for key in sltp_keys:
            info = self.registry.get(key)
            assert info is not None, f"缺少止损止盈参数: {key}"


class TestInitializeFunction:
    """initialize_parameter_registry 函数测试"""

    def setup_method(self):
        ParameterRegistry._instance = None

    def test_initialize_returns_registry(self):
        registry = initialize_parameter_registry()
        assert isinstance(registry, ParameterRegistry)

    def test_initialize_populates_parameters(self):
        registry = initialize_parameter_registry()
        all_params = registry.get_all()
        assert len(all_params) >= 30

    def test_idempotent_initialization(self):
        reg1 = initialize_parameter_registry()
        count1 = len(reg1.get_all())
        reg2 = initialize_parameter_registry()
        count2 = len(reg2.get_all())
        assert reg1 is reg2
        assert count1 == count2


class TestCategoryAndLevelCoverage:
    """分类与级别覆盖完整性测试"""

    def setup_method(self):
        ParameterRegistry._instance = None
        self.registry = initialize_parameter_registry()

    def test_all_categories_present(self):
        all_params = self.registry.get_all()
        categories = {p.category for p in all_params}
        expected_categories = {"strategy", "connection", "module", "api", "system"}
        for cat in expected_categories:
            assert cat in categories, f"缺少类别: {cat}"

    def test_all_levels_present(self):
        all_params = self.registry.get_all()
        levels = {p.level for p in all_params}
        expected_levels = {"core", "standard", "advanced", "expert"}
        for lvl in expected_levels:
            assert lvl in levels, f"缺少级别: {lvl}"

    def test_core_level_has_most_params(self):
        core_params = self.registry.get_by_level("core")
        standard_params = self.registry.get_by_level("standard")
        assert len(core_params) > len(standard_params), \
            f"core 级别({len(core_params)})应多于 standard({len(standard_params)})"
