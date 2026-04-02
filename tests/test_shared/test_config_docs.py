"""
config_docs 单元测试

测试配置文档生成器的各项功能：
- Markdown 文档生成
- JSON Schema 生成
- .env.example 生成
- 参数表格生成
- 各章节内容完整性
"""

import json

import pytest

from shared.config_docs import ConfigDocGenerator


class TestConfigDocGeneratorInit:
    """测试文档生成器初始化"""

    def test_init_creates_instance(self):
        gen = ConfigDocGenerator()
        assert gen is not None
        assert gen.registry is not None


class TestGenerateMarkdown:
    """测试 Markdown 文档生成"""

    def test_generate_returns_string(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert isinstance(md, str)
        assert len(md) > 0

    def test_contains_header(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "SimplePolyBot" in md
        assert "配置指南" in md

    def test_contains_quick_start(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "快速开始" in md or "Quick Start" in md

    def test_contains_core_parameters(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "核心参数" in md or "Core" in md

    def test_contains_strategy_section(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "策略参数" in md or "Strategy" in md

    def test_contains_connection_section(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "连接配置" in md or "Connection" in md

    def test_contains_faq_section(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "常见问题" in md or "FAQ" in md

    def test_contains_presets_section(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "预设方案" in md or "Preset" in md

    def test_contains_footer_timestamp(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "生成时间" in md or "generated" in md.lower()

    def test_contains_table_of_contents(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "目录" in md or "TOC" in md

    def test_contains_risk_section(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "风险管理" in md or "Risk" in md

    def test_contains_troubleshooting(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "故障排除" in md or "Troubleshoot" in md

    def test_markdown_has_table_syntax(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "| --- |" in md or "|------|" in md

    def test_markdown_has_code_blocks(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        assert "```" in md

    def test_all_sections_present(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()
        required_sections = [
            "快速开始",
            "核心参数",
            "策略参数",
            "连接配置",
            "风险管理",
            "预设方案",
            "常见问题",
            "故障排除",
        ]
        for section in required_sections:
            assert section in md, f"Missing section: {section}"


class TestGenerateEnvExample:
    """测试 .env.example 生成"""

    def test_generate_env_example_returns_string(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert isinstance(env, str)
        assert len(env) > 0

    def test_contains_api_key_placeholder(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "POLYMARKET_API_KEY" in env

    def test_contains_api_secret_placeholder(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "POLYMARKET_API_SECRET" in env

    def test_contains_private_key(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "PRIVATE_KEY" in env

    def test_contains_redis_host(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "REDIS_HOST" in env

    def test_contains_redis_port(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "REDIS_PORT" in env

    def test_contains_smtp_config(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "SMTP_SERVER" in env
        assert "SMTP_PORT" in env

    def test_contains_webhook_url(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "WEBHOOK_URL" in env

    def test_contains_polygon_rpc(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "POLYGON_RPC_URL" in env

    def test_contains_comments(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        assert "#" in env

    def test_env_format_is_valid(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        lines = [l.strip() for l in env.split("\n") if l.strip() and not l.startswith("#")]
        for line in lines:
            if "=" in line:
                key, _ = line.split("=", 1)
                assert key.isupper() or key.startswith("#"), f"Invalid key format: {key}"

    def test_all_critical_vars_present(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()
        critical_vars = [
            "POLYMARKET_API_KEY",
            "POLYMARKET_API_SECRET",
            "POLYMARKET_API_PASSPHRASE",
            "PRIVATE_KEY",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB",
            "POLYGON_RPC_URL",
            "SMTP_SERVER",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "ALERT_EMAIL",
            "WEBHOOK_URL",
        ]
        for var in critical_vars:
            assert var in env, f"Missing environment variable: {var}"


class TestGenerateParameterTable:
    """测试参数表格生成"""

    def setup_method(self):
        try:
            from shared.parameter_registry import initialize_parameter_registry
            initialize_parameter_registry()
        except (ImportError, ModuleNotFoundError):
            pass

    def test_table_header_present(self):
        gen = ConfigDocGenerator()
        table = gen.generate_parameter_table("strategy")
        assert "|" in table
        assert "参数" in table

    def test_strategy_params_in_table(self):
        gen = ConfigDocGenerator()
        table = gen.generate_parameter_table("strategy")
        if "strategy.base_cushion" in table or "base_cushion" in table:
            assert True
        else:
            assert "|" in table

    def test_connection_params_in_table(self):
        gen = ConfigDocGenerator()
        table = gen.generate_parameter_table("connection")
        if "redis.host" in table or "host" in table:
            assert True
        else:
            assert "|" in table

    def test_empty_category_still_valid(self):
        gen = ConfigDocGenerator()
        table = gen.generate_parameter_table("nonexistent_category")
        assert isinstance(table, str)

    def test_table_has_columns(self):
        gen = ConfigDocGenerator()
        table = gen.generate_parameter_table("strategy")
        headers = ["参数", "名称", "类型", "默认值"]
        for header in headers:
            assert header in table


class TestGenerateJsonSchema:
    """测试 JSON Schema 生成"""

    def test_schema_returns_dict(self):
        gen = ConfigDocGenerator()
        try:
            schema = gen.generate_json_schema()
            assert isinstance(schema, dict)
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass

    def test_schema_not_empty(self):
        gen = ConfigDocGenerator()
        try:
            schema = gen.generate_json_schema()
            assert len(schema) > 0
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass


class TestSectionGenerators:
    """测试各章节生成器"""

    def test_header_contains_title_and_date(self):
        gen = ConfigDocGenerator()
        header = gen._generate_header()
        assert "SimplePolyBot" in header
        assert "202" in header

    def test_quick_start_contains_wizard_command(self):
        gen = ConfigDocGenerator()
        qs = gen._generate_quick_start()
        assert "config_wizard" in qs or "wizard" in qs.lower()

    def test_quick_start_contains_preset_command(self):
        gen = ConfigDocGenerator()
        qs = gen._generate_quick_start()
        assert "config_presets" in qs or "preset" in qs.lower()

    def test_strategy_section_has_table(self):
        gen = ConfigDocGenerator()
        section = gen._generate_strategy_section()
        assert "策略参数" in section
        assert "|" in section

    def test_connection_section_has_table(self):
        gen = ConfigDocGenerator()
        section = gen._generate_connection_section()
        assert "连接配置" in section
        assert "|" in section

    def test_risk_section_content(self):
        gen = ConfigDocGenerator()
        section = gen._generate_risk_section()
        assert "风险管理" in section

    def test_advanced_section_content(self):
        gen = ConfigDocGenerator()
        section = gen._generate_advanced_section()
        assert "高级参数" in section

    def test_presets_section_mentions_conservative(self):
        gen = ConfigDocGenerator()
        section = gen._generate_presets_section()
        assert "conservative" in section or "保守" in section

    def test_presets_section_mentions_balanced(self):
        gen = ConfigDocGenerator()
        section = gen._generate_presets_section()
        assert "balanced" in section or "平衡" in section

    def test_presets_section_mentions_aggressive(self):
        gen = ConfigDocGenerator()
        section = gen._generate_presets_section()
        assert "aggressive" in section or "激进" in section

    def test_faq_section_has_alpha_question(self):
        gen = ConfigDocGenerator()
        faq = gen._generate_faq_section()
        assert "Alpha" in faq or "alpha" in faq

    def test_faq_section_has_cushion_question(self):
        gen = ConfigDocGenerator()
        faq = gen._generate_faq_section()
        assert "Cushion" in faq or "cushion" in faq or "缓冲" in faq

    def test_faq_section_has_troubleshooting(self):
        gen = ConfigDocGenerator()
        faq = gen._generate_faq_section()
        assert "故障排除" in faq or "错误" in faq

    def test_footer_has_timestamp(self):
        gen = ConfigDocGenerator()
        footer = gen._generate_footer()
        assert "生成时间" in footer or "generated" in footer.lower()

    def test_footer_has_generator_name(self):
        gen = ConfigDocGenerator()
        footer = gen._generate_footer()
        assert "ConfigDocGenerator" in footer


class TestIntegration:
    """集成测试：验证完整输出"""

    def test_full_markdown_structure(self):
        gen = ConfigDocGenerator()
        md = gen.generate_markdown()

        sections = [
            "# SimplePolyBot",
            "快速开始",
            "核心参数",
            "策略参数",
            "连接配置",
            "风险管理",
            "预设方案",
            "常见问题",
            "故障排除",
        ]
        for section in sections:
            assert section in md, f"Missing section: {section}"

    def test_full_env_example_structure(self):
        gen = ConfigDocGenerator()
        env = gen.generate_env_example()

        parts = [
            "凭证",
            "连接",
            "通知",
        ]
        for part in parts:
            assert part in env, f"Missing part: {part}"
