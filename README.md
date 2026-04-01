# SimplePolyBot - Polymarket 五分钟比特币二元期权自动化交易系统

## 项目简介

SimplePolyBot 是一个针对 Polymarket 平台上"Bitcoin Up or Down - 5 Minutes"市场的自动化量化交易系统。该系统采用独立进程架构，通过 Redis Pub/Sub 进行模块间通信，实现轻量化、模块化且具备毫秒级执行能力的自动化交易。

### 核心特性

- ✅ **独立进程架构**：每个模块独立运行、独立部署、独立扩展
- ✅ **Redis Pub/Sub 通信**：模块间通过 Redis 进行松耦合通信
- ✅ **双轨制数据源**：Binance 高频动量计算 + Chainlink 结算基准
- ✅ **OLS 线性回归**：计算波动子因子 K，捕捉价格趋势
- ✅ **动态安全垫**：根据波动率和剩余时间动态调整风险控制
- ✅ **时间衰减价格限制**：根据剩余时间动态调整最大买入价格
- ✅ **FAK 订单类型**：部分成交并取消剩余，防止逆向选择
- ✅ **异步资金结算**：独立进程定时赎回已获胜份额

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Redis (Pub/Sub)                          │
│  Channels: market_data, trading_signal, trade_result        │
└─────────────────────────────────────────────────────────────┘
         ↑              ↑              ↑              ↓
         │              │              │              │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │ 模块 1  │    │ 模块 2  │    │ 模块 3  │    │ 模块 4  │
    │ 市场数据 │───→│ 策略分析 │───→│ 订单执行 │    │ 资金结算 │
    │ 获取模块 │    │ 引擎    │    │ 模块    │    │ 模块    │
    └─────────┘    └─────────┘    └─────────┘    └─────────┘
         ↑                                            ↑
         │                                            │
    Binance WS                                   CTF Contract
    Polymarket RTDS                              (Polygon)
```

### 模块说明

#### 模块 1：市场数据获取模块
- **运行模式**：24 小时不间断执行
- **数据源**：Binance WebSocket + Polymarket RTDS
- **输出**：Redis `market_data` 频道（每秒 1 次）

#### 模块 2：策略分析引擎
- **运行模式**：持续运行，订阅市场数据
- **核心逻辑**：OLS 回归、动态安全垫、信号生成
- **输出**：Redis `trading_signal` 频道（每秒 1 次）

#### 模块 3：订单执行模块
- **运行模式**：持续运行，订阅交易信号
- **核心逻辑**：价格验证、FAK 订单执行
- **输出**：交易执行日志

#### 模块 4：资金结算模块
- **运行模式**：每 10 分钟运行一次
- **核心逻辑**：CTF 合约赎回
- **输出**：赎回执行日志

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository_url>
cd SimplePolyBot

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux
# 或
.\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入真实配置
# 必需配置：
# - POLYMARKET_API_KEY
# - POLYMARKET_API_SECRET
# - POLYMARKET_API_PASSPHRASE
# - PRIVATE_KEY
# - WALLET_ADDRESS
```

### 3. 启动 Redis

```bash
# Linux
sudo bash scripts/setup_redis.sh

# 或使用 Docker
docker run -d -p 6379:6379 redis:alpine
```

### 4. 启动系统

```bash
# 启动所有模块
bash scripts/start_all.sh

# 或单独启动模块
bash scripts/start_module.sh market_data_collector
bash scripts/start_module.sh strategy_engine
bash scripts/start_module.sh order_executor
bash scripts/start_module.sh settlement_worker
```

### 5. 监控

```bash
# 查看日志
tail -f logs/market_data_collector.log
tail -f logs/strategy_engine.log
tail -f logs/order_executor.log
tail -f logs/settlement_worker.log

# 运行监控脚本
bash scripts/monitor.sh
```

### 6. 停止系统

```bash
bash scripts/stop_all.sh
```

## 策略参数说明

### 核心策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Base Cushion | $15 | 基础安全垫，过滤微小波动 |
| α (风险敏感度) | 1.0 | Buffer Cushion 的敏感度系数 |
| 最大买入价格表 | - | 根据剩余时间动态调整 |

### 最大买入价格表

| 剩余时间 | 最大买入价格 | 说明 |
|----------|---------------|------|
| T-90s | $0.75 | 风险尚存，盈亏比健康 |
| T-50s | $0.85 | 确定性增加，适度放宽 |
| T-10s | $0.90 | 确定性极高，收益率约 10.3% |

### 动态安全垫公式

```
安全垫总厚度 = Base Cushion + (α × |K| × √Time Remaining)
```

其中：
- K：OLS 线性回归斜率（波动子因子）
- Time Remaining：距离市场结束的剩余秒数

## Redis 频道消息格式

### market_data 频道

```json
{
  "timestamp": 1234567890123,
  "binance_price": 67234.50,
  "chainlink_price": 67235.20
}
```

### trading_signal 频道

```json
{
  "action": "BUY",
  "direction": "DOWN",
  "max_price": 0.85,
  "timestamp": 1234567890123
}
```

或

```json
{
  "action": "WAIT",
  "timestamp": 1234567890123
}
```

## 常见问题与故障排查

### 问题 1：模块无法启动

**症状**：执行 `start_module.sh` 后模块立即退出

**排查步骤**：
1. 检查日志文件：`cat logs/<module_name>.log`
2. 检查配置文件：确保 `.env` 文件存在且配置正确
3. 检查 Redis 连接：确保 Redis 服务正在运行
4. 检查依赖：确保所有依赖已安装 `pip install -r requirements.txt`

### 问题 2：WebSocket 频繁断线

**症状**：日志中频繁出现"WebSocket 连接断开"

**解决方案**：
1. 检查网络连接稳定性
2. 检查是否被 Cloudflare 拦截（返回 403）
3. 考虑使用住宅代理或 `curl-impersonate`

### 问题 3：订单执行失败

**症状**：订单提交返回错误

**排查步骤**：
1. 检查 USDC.e 余额是否充足
2. 检查 API 凭证是否正确
3. 检查订单簿深度是否充足
4. 检查价格是否符合 Tick Size 要求

### 问题 4：赎回失败

**症状**：CTF 合约赎回交易失败

**排查步骤**：
1. 检查 POL/MATIC 余额是否充足（用于支付 Gas 费）
2. 检查市场是否已结算
3. 检查是否持有获胜份额
4. 检查 Polygon 网络是否拥堵

## 安全注意事项

⚠️ **重要安全提示**

1. **私钥管理**：
   - 绝不将私钥硬编码在代码中
   - 绝不将私钥提交到版本控制系统
   - 使用环境变量或密钥管理服务

2. **API 凭证**：
   - 定期轮换 API Key、Secret、Passphrase
   - 限制 API 权限范围

3. **资金安全**：
   - 使用小额资金进行测试
   - 设置最大持仓限制
   - 设置日最大亏损限制

4. **网络安全**：
   - 使用防火墙限制访问
   - 定期更新依赖库
   - 监控异常交易活动

## 测试

### 测试概览

项目包含完整的测试套件，涵盖单元测试、集成测试和性能测试。

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/test_shared tests/test_strategy_engine tests/test_order_executor tests/test_settlement_worker

# 运行集成测试
pytest tests/test_integration

# 运行性能测试
pytest tests/test_performance -v -s

# 查看测试覆盖率
pytest --cov=modules --cov=shared --cov-report=html
```

### 测试统计

- **总测试用例**: 310+
- **单元测试**: 296 个测试用例
- **集成测试**: 14 个测试用例
- **性能测试**: 11 个测试用例

### 性能测试结果

#### OLS 回归性能

| 数据集大小 | 平均延迟 | 中位数延迟 | P95 延迟 | 最大延迟 |
|-----------|---------|-----------|---------|---------|
| 10-50 点 | < 1ms | < 1ms | < 2ms | < 10ms |
| 100-500 点 | < 5ms | < 5ms | < 10ms | < 50ms |
| 1000-5000 点 | < 20ms | < 20ms | < 50ms | < 100ms |

#### 价格队列性能

| 操作 | 平均延迟 | 中位数延迟 | P95 延迟 |
|------|---------|-----------|---------|
| 推入操作 | 0.04ms | 0.03ms | 0.05ms |
| 范围查询 | < 1ms | < 1ms | < 2ms |

#### 信号生成性能

| 操作 | 平均延迟 | 中位数延迟 | P95 延迟 |
|------|---------|-----------|---------|
| 信号生成 | < 1ms | < 1ms | < 2ms |
| 完整策略周期 | < 1ms | < 1ms | < 2ms |

#### 高频交易模拟

| 指标 | 数值 |
|------|------|
| 平均迭代延迟 | 0.69ms |
| 中位数延迟 | 0.63ms |
| P95 延迟 | 1.14ms |
| 最大延迟 | 1.60ms |

### 集成测试覆盖

集成测试验证了完整的模块间通信流程：

- ✅ 市场数据到信号生成的完整流程
- ✅ 信号到订单执行的完整流程
- ✅ Redis Pub/Sub 通信
- ✅ 错误处理和恢复
- ✅ 并发消息处理
- ✅ 模块初始化
- ✅ 高频数据处理
- ✅ 完整数据管道

## 性能优化建议

1. **OLS 回归优化**：使用 NumPy 向量化计算，确保 < 10ms
2. **Redis 连接池**：配置连接池减少连接开销
3. **日志轮转**：配置日志轮转避免磁盘占满
4. **进程监控**：使用 systemd 或 supervisor 自动重启崩溃进程

### 已实现的性能优化

- ✅ NumPy 向量化 OLS 回归计算
- ✅ Redis 连接池管理
- ✅ 价格队列时间窗口清理
- ✅ 异步日志记录
- ✅ 结构化日志输出

## 技术栈

- **Python**: 3.10+
- **py-clob-client**: Polymarket 官方 Python SDK
- **web3.py**: 以太坊交互
- **websockets**: WebSocket 客户端
- **redis**: 进程间通信
- **numpy**: 数值计算
- **structlog**: 结构化日志
- **pytest**: 测试框架
- **pytest-asyncio**: 异步测试支持

## 项目状态

### 开发进度

- ✅ **阶段一**: 项目初始化与基础设施（已完成）
- ✅ **阶段二**: 核心模块开发（已完成）
  - ✅ 模块 1: 市场数据获取模块
  - ✅ 模块 2: 策略分析引擎
  - ✅ 模块 3: 订单执行模块
  - ✅ 模块 4: 资金结算模块
- ✅ **阶段三**: 部署与监控（已完成）
- ✅ **阶段四**: 测试与质量保证（已完成）
  - ✅ 单元测试（296+ 测试用例）
  - ✅ 集成测试（14 测试用例）
  - ✅ 性能测试（11 测试用例）
- ✅ **阶段五**: 文档完善（已完成）

### 完成率

**总任务数**: 33  
**已完成**: 33  
**完成率**: 100%

## 文档

- [API 文档](docs/api.md) - 模块接口文档
- [架构设计](docs/architecture.md) - 系统架构说明
- [部署指南](docs/deployment.md) - 生产环境部署
- [策略说明](docs/strategy.md) - 交易策略详解

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 使用 Black 格式化代码
- 使用 Ruff 进行代码检查
- 使用 MyPy 进行类型检查
- 确保所有测试通过

## 联系方式

- 项目主页：https://github.com/<username>/SimplePolyBot
- 问题反馈：https://github.com/<username>/SimplePolyBot/issues

## 免责声明

⚠️ **重要提示**

本项目仅供学习和研究使用，不构成任何投资建议。使用本系统进行实盘交易存在资金损失风险，请谨慎评估自身风险承受能力。作者不对使用本系统造成的任何损失负责。
