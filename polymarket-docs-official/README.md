# Polymarket 官方文档（完整版）

> 下载时间：2026-03-30
> 来源：https://docs.polymarket.com/llms.txt + changelog.md

---

## ✅ 完整性验证

| 部分 | 状态 | 数量 |
|------|------|------|
| **Documentation** | ✅ 完整 | 50+ 文档 |
| **API Reference** | ✅ 完整 | 101 端点 |
| **OpenAPI Specs** | ✅ 完整 | 8 yaml + 16 json |
| **Changelog** | ✅ 已补充 | 1 文档 |

---

## 统计

| 类型 | 数量 |
|------|------|
| **总文件数** | 179 |
| **.md 文件** | 156 |
| **.yaml 文件** | 8 |
| **.json 文件** | 16 |
| **总大小** | 2.3 MB |

---

## 目录结构

```
polymarket-docs-official/
├── llms.txt                    # 官方文档索引
├── index.md                    # 首页
├── quickstart.md               # 快速开始
├── polymarket-101.md           # Polymarket 入门
│
├── api-reference/              # API 参考 (101 个端点)
│   ├── introduction.md
│   ├── authentication.md
│   ├── rate-limits.md
│   ├── clients-sdks.md
│   ├── geoblock.md
│   ├── events/                 # 4 个端点
│   ├── markets/                # 8 个端点
│   ├── market-data/            # 17 个端点
│   ├── core/                   # 10 个端点
│   ├── data/                   # 2 个端点
│   ├── trade/                  # 12 个端点
│   ├── rewards/                # 7 个端点
│   ├── bridge/                 # 5 个端点
│   ├── relayer/                # 6 个端点
│   ├── relayer-api-keys/       # 1 个端点
│   ├── profiles/               # 1 个端点
│   ├── search/                 # 1 个端点
│   ├── tags/                   # 7 个端点
│   ├── series/                 # 2 个端点
│   ├── comments/               # 3 个端点
│   ├── sports/                 # 3 个端点
│   ├── builders/               # 2 个端点
│   ├── rebates/                # 1 个端点
│   ├── misc/                   # 4 个端点
│   └── wss/                    # 3 个 WebSocket 频道
│
├── api-spec/                   # OpenAPI 规范
│   ├── gamma-openapi.yaml
│   ├── clob-openapi.yaml
│   ├── data-openapi.yaml
│   ├── bridge-openapi.yaml
│   └── relayer-openapi.yaml
│
├── concepts/                   # 核心概念
│   ├── markets-events.md
│   ├── positions-tokens.md
│   ├── prices-orderbook.md
│   ├── order-lifecycle.md
│   └── resolution.md
│
├── trading/                    # 交易指南
│   ├── overview.md
│   ├── quickstart.md
│   ├── fees.md
│   ├── gasless.md
│   ├── matching-engine.md
│   ├── orderbook.md
│   ├── bridge/                 # 存取款
│   ├── clients/                # 客户端配置
│   ├── ctf/                    # CTF 操作
│   └── orders/                 # 订单操作
│
├── market-data/                # 市场数据
│   ├── overview.md
│   ├── subgraph.md
│   ├── fetching-markets.md
│   └── websocket/              # WebSocket
│
├── builders/                   # Builder 程序
│   ├── overview.md
│   ├── api-keys.md
│   └── tiers.md
│
├── market-makers/              # 做市商
│   ├── overview.md
│   ├── getting-started.md
│   ├── trading.md
│   ├── inventory.md
│   ├── maker-rebates.md
│   └── liquidity-rewards.md
│
├── advanced/                   # 高级主题
│   └── neg-risk.md
│
├── resources/                  # 资源
│   ├── blockchain-data.md
│   ├── contract-addresses.md
│   ├── error-codes.md
│   └── referral-program.md
│
├── developers/                 # 开发者资源
│   └── open-api/               # OpenAPI JSON
│
└── asyncapi.json               # AsyncAPI 规范
```

---

## API 端点索引

### Gamma API (`https://gamma-api.polymarket.com`)

公开数据 API，无需认证。

| 分类 | 端点数 | 说明 |
|------|--------|------|
| events | 4 | 事件查询 |
| markets | 8 | 市场查询 |
| tags | 7 | 标签查询 |
| series | 2 | 系列查询 |
| comments | 3 | 评论查询 |
| sports | 3 | 体育数据 |
| profiles | 1 | 用户档案 |
| search | 1 | 搜索 |
| misc | 4 | 杂项 |

### CLOB API (`https://clob.polymarket.com`)

交易 API，部分端点需认证。

| 分类 | 端点数 | 说明 |
|------|--------|------|
| market-data | 17 | 市场数据 |
| trade | 12 | 交易操作 |
| data | 2 | 数据查询 |

### Data API (`https://data-api.polymarket.com`)

用户数据 API。

| 分类 | 端点数 | 说明 |
|------|--------|------|
| core | 10 | 核心数据 |
| rewards | 7 | 奖励数据 |
| builders | 2 | Builder 数据 |
| rebates | 1 | 返佣数据 |
| relayer | 6 | Relayer 操作 |
| bridge | 5 | 存取款 |

### WebSocket

| 频道 | 说明 |
|------|------|
| market | 市场实时数据 |
| user | 用户实时数据 |
| sports | 体育实时数据 |

---

## 快速开始

```bash
# 查看 API 简介
cat api-reference/introduction.md

# 查看认证说明
cat api-reference/authentication.md

# 查看 SDK 使用
cat api-reference/clients-sdks.md

# 查看快速开始
cat quickstart.md
```

---

## OpenAPI 规范

| 文件 | API |
|------|-----|
| `api-spec/gamma-openapi.yaml` | Gamma API |
| `api-spec/clob-openapi.yaml` | CLOB API |
| `api-spec/data-openapi.yaml` | Data API |
| `api-spec/bridge-openapi.yaml` | Bridge API |
| `api-spec/relayer-openapi.yaml` | Relayer API |

---

## 相关链接

- 官方文档：https://docs.polymarket.com
- 文档索引：https://docs.polymarket.com/llms.txt
- Builder 程序：https://builders.polymarket.com
- 帮助中心：https://help.polymarket.com
- 状态页面：https://status.polymarket.com