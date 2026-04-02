"""
配置文档生成器

自动生成多种格式的配置文档：
- Markdown 配置指南
- JSON Schema
- .env.example 模板
"""

from datetime import datetime
from typing import Optional
from .parameter_registry import ParameterRegistry, ParameterInfo


class ConfigDocGenerator:
    """配置文档生成器"""

    def __init__(self):
        self.registry = ParameterRegistry.get_instance()

    def generate_markdown(self) -> str:
        """生成 Markdown 格式的配置指南"""
        sections = [
            self._generate_header(),
            self._generate_quick_start(),
            self._generate_table_of_contents(),
            self._generate_core_parameters(),
            self._generate_strategy_section(),
            self._generate_connection_section(),
            self._generate_risk_section(),
            self._generate_advanced_section(),
            self._generate_presets_section(),
            self._generate_faq_section(),
            self._generate_footer(),
        ]
        return "\n\n".join(sections)

    def generate_json_schema(self) -> dict:
        """生成 JSON Schema"""
        from .config import Config
        config = Config()
        return config.get_parameter_schema()

    def generate_env_example(self) -> str:
        """生成 .env.example 内容"""
        lines = [
            "# SimplePolyBot 环境变量配置",
            "# 复制此文件为 .env 并填写实际值",
            "",
            "# ==================== 凭证配置 ====================",
            "",
            "# Polymarket API 凭证（必填）",
            "POLYMARKET_API_KEY=your_api_key_here",
            "POLYMARKET_API_SECRET=your_api_secret_here",
            "POLYMARKET_API_PASSPHRASE=your_passphrase_here",
            "",
            "# 以太坊私钥（必填）- 0x 开头的 64 位十六进制字符串",
            "PRIVATE_KEY=0x...",
            "",
            "# ==================== 连接配置 ====================",
            "",
            "# Redis 配置",
            "REDIS_HOST=localhost",
            "REDIS_PORT=6379",
            "REDIS_PASSWORD=",
            "REDIS_DB=0",
            "",
            "# Polygon RPC URL",
            "POLYGON_RPC_URL=https://polygon-rpc.com",
            "",
            "# ==================== 通知配置（可选）====================",
            "",
            "# SMTP 邮件服务器",
            "SMTP_SERVER=smtp.gmail.com",
            "SMTP_PORT=587",
            "SMTP_USERNAME=your_email@gmail.com",
            "SMTP_PASSWORD=your_app_password",
            "ALERT_EMAIL=alert@example.com",
            "",
            "# Webhook 通知 URL",
            "WEBHOOK_URL=",
        ]
        return "\n".join(lines)

    def generate_parameter_table(self, category: str) -> str:
        """生成指定类别的参数表格"""
        params = self.registry.get_all(category)

        lines = [f"| 参数 | 名称 | 类型 | 默认值 | 必填 |"]
        lines.append("|------|------|------|--------|------|")

        for p in params:
            sens = " [SENSITIVE]" if p.sensitive else ""
            req = " Y" if p.required else ""
            type_name = p.type.__name__
            default = str(p.default) if p.default else "-"
            lines.append(f"| `{p.key}` | {p.name}{sens} | {type_name} | {default} | {req} |")

        return "\n".join(lines)

    def _generate_header(self) -> str:
        """生成文档头部"""
        return f"""# SimplePolyBot 配置指南

> **最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **适用版本**: v1.0+

本文档详细说明 SimplePolyBot 的所有配置参数、取值范围和使用建议。

---

## 目录

- [快速开始](#快速开始)
- [核心参数](#核心参数必填)
- [策略参数](#策略参数)
- [连接配置](#连接配置)
- [风险管理](#风险管理)
- [高级参数](#高级参数)
- [预设方案](#预设方案)
- [常见问题](#常见问题)
- [故障排除](#故障排除)

---

## 快速开始"""

    def _generate_quick_start(self) -> str:
        return """### 三分钟快速配置

#### 方式一：使用配置向导（推荐）

```bash
python -m shared.config_wizard

# 或使用快速模式（仅需填写核心参数）
python -m shared.config_wizard --mode quick
```

#### 方式二：使用预设方案

```bash
# 查看可用方案
python -m shared.config_presets list

# 应用平衡型方案
python -m shared.config_presets apply balanced
```

#### 方式三：手动编辑

1. 复制 `.env.example` 为 `.env`
2. 填写凭证信息
3. 编辑 `config/settings.yaml` 调整策略参数
4. 运行 `python -m shared.config_wizard --validate-only` 验证配置

---

## 核心参数（必填）

以下参数**必须配置**才能正常运行：

| 参数 | 说明 | 示例 |
|------|------|------|
| `PRIVATE_KEY` | 以太坊私钥 | `0x1234...abcd` |
| `POLYMARKET_API_KEY` | Polymarket API 密钥 | `abc...xyz` |
| `POLYMARKET_API_SECRET` | API 密钥 | `secret...` |
| `redis.host` | Redis 地址 | `localhost` |
| `redis.port` | Redis 端口 | `6379` |"""

    def _generate_table_of_contents(self) -> str:
        return ""

    def _generate_core_parameters(self) -> str:
        return ""

    def _generate_strategy_section(self) -> str:
        params = self.registry.get_all("strategy")
        content = "## 策略参数\n\n"
        content += "策略参数控制交易行为和风险偏好。\n\n"
        content += self.generate_parameter_table("strategy")
        return content

    def _generate_connection_section(self) -> str:
        params = self.registry.get_all("connection")
        content = "## 连接配置\n\n"
        content += "Redis 和 API 连接相关配置。\n\n"
        content += self.generate_parameter_table("connection")
        return content

    def _generate_risk_section(self) -> str:
        content = "## 风险管理\n\n"
        content += "风险控制相关参数，保护账户资金安全。\n\n"
        risk_params = [p for p in self.registry.get_all("strategy") if "risk" in p.key or "stop" in p.key]
        if risk_params:
            lines = ["| 参数 | 名称 | 类型 | 默认值 | 必填 |"]
            lines.append("|------|------|------|--------|------|")
            for p in risk_params:
                sens = " [SENSITIVE]" if p.sensitive else ""
                req = " Y" if p.required else ""
                type_name = p.type.__name__
                default = str(p.default) if p.default else "-"
                lines.append(f"| `{p.key}` | {p.name}{sens} | {type_name} | {default} | {req} |")
            content += "\n".join(lines)
        return content

    def _generate_advanced_section(self) -> str:
        advanced_params = self.registry.get_by_level("advanced")
        content = "## 高级参数\n\n"
        content += "高级配置项，通常不需要修改。\n\n"
        if advanced_params:
            lines = ["| 参数 | 名称 | 类型 | 默认值 |"]
            lines.append("|------|------|------|--------|")
            for p in advanced_params:
                type_name = p.type.__name__
                default = str(p.default) if p.default else "-"
                lines.append(f"| `{p.key}` | {p.name} | {type_name} | {default} |")
            content += "\n".join(lines)
        return content

    def _generate_presets_section(self) -> str:
        return """## 预设方案

SimplePolyBot 提供三种预设方案，满足不同风险偏好：

### 保守型 (conservative)
- 低仓位、高缓冲、严格风控
- 适合新手或高波动市场

### 平衡型 (balanced) [推荐]
- 中等仓位、适中缓冲
- 适合大多数用户

### 激进型 (aggressive)
- 大仓位、低缓冲、激进风控
- 适合经验丰富的交易者

```bash
# 应用预设方案
python -m shared.config_presets apply conservative
python -m shared.config_presets apply balanced
python -m shared.config_presets apply aggressive
```
"""

    def _generate_faq_section(self) -> str:
        return """## 常见问题

### Q1: 如何选择合适的 Alpha 值？

**Alpha** 控制价格调整系数：

| 值 | 适用场景 |
|-----|----------|
| **0.3 (保守)** | 新手、高波动市场 |
| **0.5 (平衡)** | 一般情况（推荐）|
| **0.7 (激进)** | 低波动、高确信度 |

### Q2: Base Cushion 设置多大合适？

- **高波动市场**: 0.03 - 0.05
- **一般市场**: 0.02（默认）
- **低波动市场**: 0.01 - 0.015

### Q3: 如何修改配置后生效？

修改 `config/settings.yaml` 后重启所有模块即可。如需热加载，可在模块中使用 `Config.reload()`。

---

## 故障排除

### 配置验证失败

```bash
# 运行诊断
python -m shared.config_wizard --validate-only

# 查看详细错误报告
python -c "from shared.config import Config; c = Config(); c.load_yaml(); c.validate()"
```

### 常见错误及解决方案

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `环境变量 xxx 未设置` | 缺少必填环境变量 | 在 `.env` 中添加 |
| `值超出有效范围` | 参数值不在允许范围内 | 参考建议值调整 |
| `私钥格式无效` | 私钥不符合以太坊格式 | 使用 0x + 64位十六进制 |

---

*本文档由 ConfigDocGenerator 自动生成*
"""

    def _generate_footer(self) -> str:
        return f"""---
*文档生成时间: {datetime.now().isoformat()}*
*生成工具: SimplePolyBot ConfigDocGenerator*
"""


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="配置文档生成器")
    parser.add_argument("command", choices=["generate", "schema", "env"], help="命令")
    parser.add_argument("-o", "--output", help="输出文件路径")
    args = parser.parse_args()

    generator = ConfigDocGenerator()

    if args.command == "generate":
        md = generator.generate_markdown()
        output = args.output or "docs/configuration_guide.md"
        from pathlib import Path
        Path(output).write_text(md, encoding="utf-8")
        print(f"[OK] Markdown 文档已生成: {output}")

    elif args.command == "schema":
        schema = generator.generate_json_schema()
        import json
        output = args.output or "config/settings.schema.json"
        Path(output).write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] JSON Schema 已生成: {output}")

    elif args.command == "env":
        env_content = generator.generate_env_example()
        output = args.output or ".env.example"
        Path(output).write_text(env_content, encoding="utf-8")
        print(f"[OK] .env.example 已生成: {output}")
