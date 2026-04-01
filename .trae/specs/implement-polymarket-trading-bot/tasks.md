# Tasks

本文档按照独立进程架构，将 V1.0 版本开发任务分解为可验证的小任务。每个模块独立开发、独立测试、独立部署。

---

## 阶段一：基础设施搭建（Day 1-3）

### Task 1: 项目初始化与依赖管理
- [x] 创建 Python 虚拟环境
- [x] 创建项目目录结构（modules/, shared/, config/, tests/, scripts/, logs/）
- [x] 创建 requirements.txt 并安装核心依赖：
  - py-clob-client >= 0.5.0
  - web3 >= 6.0.0
  - websockets >= 12.0
  - redis >= 5.0.0
  - numpy >= 1.24.0
  - pandas >= 2.0.0
  - python-dotenv >= 1.0.0
  - PyYAML >= 6.0
  - structlog >= 23.0
- [x] 创建 .env.example 环境变量模板文件
- [x] 创建 .gitignore 文件

### Task 2: Redis 安装与配置
- [x] 编写 scripts/setup_redis.sh Redis 安装脚本
- [x] 配置 Redis 服务器（默认端口 6379）
- [x] 测试 Redis 连接与 Pub/Sub 功能
- [x] 编写 shared/redis_client.py Redis 客户端封装

### Task 3: 配置管理系统
- [x] 创建 config/settings.yaml 配置文件，包含：
  - 策略参数（Base Cushion、α、最大买入价格表）
  - Redis 连接配置
  - 模块启动参数
- [x] 创建 config/logging.yaml 日志配置文件
- [x] 实现 shared/config.py 配置加载模块
- [x] 实现配置验证逻辑
- [x] 编写单元测试验证配置加载

### Task 4: 日志系统
- [x] 实现 shared/logger.py 结构化日志模块（基于 structlog）
- [x] 配置日志输出至控制台与文件
- [x] 实现日志轮转机制
- [x] 编写测试验证日志记录功能

### Task 5: 共享常量与工具
- [x] 创建 shared/constants.py 常量定义（Redis 频道名称、合约地址等）
- [x] 创建 shared/__init__.py 导出共享模块

---

## 阶段二：模块 1 - 市场数据获取模块（Day 4-6）

### Task 6: Binance WebSocket 客户端
- [ ] 实现 modules/market_data_collector/binance_ws.py
- [ ] 连接 wss://stream.binance.com:9443/ws/btcusdt@trade
- [ ] 解析价格与时间戳数据
- [ ] 实现断线重连机制（指数退避）
- [ ] 实现心跳机制（每 10 秒发送 PING）
- [ ] 编写单元测试模拟 WebSocket 消息处理

### Task 7: Polymarket RTDS 客户端
- [ ] 实现 modules/market_data_collector/polymarket_rtds.py
- [ ] 连接 wss://ws-live-data.polymarket.com
- [ ] 订阅 crypto_prices_chainlink 主题的 btc/usd 数据流
- [ ] 解析 Chainlink 预言机价格
- [ ] 实现断线重连与心跳机制
- [ ] 编写单元测试验证 RTDS 连接与数据解析

### Task 8: Redis 发布者
- [ ] 实现 modules/market_data_collector/redis_publisher.py
- [ ] 合并 Binance 与 Chainlink 价格数据
- [ ] 每秒发布一次消息至 Redis `market_data` 频道
- [ ] 消息格式：`{"timestamp": 1234567890123, "binance_price": 67234.50, "chainlink_price": 67235.20}`
- [ ] 编写单元测试验证发布功能

### Task 9: 模块入口与集成
- [ ] 实现 modules/market_data_collector/main.py 模块入口
- [ ] 集成 Binance WS、Polymarket RTDS、Redis 发布者
- [ ] 实现优雅关闭逻辑（处理 SIGINT/SIGTERM）
- [ ] 编写集成测试验证完整流程
- [ ] 创建 modules/market_data_collector/__init__.py

---

## 阶段三：模块 2 - 策略分析引擎（Day 7-10）

### Task 10: Redis 订阅者
- [ ] 实现 modules/strategy_engine/redis_subscriber.py
- [ ] 订阅 Redis `market_data` 频道
- [ ] 解析价格数据并传递给处理逻辑
- [ ] 编写单元测试验证订阅功能

### Task 11: 价格队列管理
- [ ] 实现 modules/strategy_engine/price_queue.py
- [ ] 使用 collections.deque 实现 180 秒滚动队列
- [ ] 实现线程安全的 push 与 get 操作
- [ ] 编写单元测试验证队列操作

### Task 12: OLS 线性回归
- [ ] 实现 modules/strategy_engine/ols_regression.py
- [ ] 使用 NumPy 实现线性回归拟合
- [ ] 计算斜率 K（波动子因子）与决定系数 R²
- [ ] 优化计算性能（目标 < 10ms）
- [ ] 编写单元测试验证回归计算正确性

### Task 13: 动态安全垫计算
- [ ] 实现 modules/strategy_engine/safety_cushion.py
- [ ] 实现 Base Cushion 计算（可配置）
- [ ] 实现 Buffer Cushion 计算：`α × |K| × √Time Remaining`
- [ ] 实现安全垫总厚度计算
- [ ] 编写单元测试验证不同参数下的计算

### Task 14: 买入信号生成器
- [ ] 实现 modules/strategy_engine/signal_generator.py
- [ ] 实现差额计算：`|Current Price - Start Price|`
- [ ] 实现方向判断（UP 或 DOWN）
- [ ] 实现信号触发条件判断
- [ ] 实现时间窗口判断（T-100s 至 T-10s）
- [ ] 实现最大买入价格查表逻辑
- [ ] 编写单元测试验证信号生成逻辑

### Task 15: 市场生命周期管理（状态机）
- [ ] 实现 modules/strategy_engine/market_lifecycle.py
- [ ] 实现 5 分钟周期起始时间计算
- [ ] 实现周期内相对时间计算
- [ ] 实现周期切换逻辑（清空队列、获取新 Start Price）
- [ ] 编写单元测试验证状态机转换

### Task 16: Redis 发布者（交易信号）
- [ ] 实现 modules/strategy_engine/redis_publisher.py
- [ ] 发布买入信号至 Redis `trading_signal` 频道
- [ ] 消息格式：`{"action": "BUY", "direction": "DOWN", "max_price": 0.85, "timestamp": 1234567890123}`
- [ ] 发布等待信号：`{"action": "WAIT", "timestamp": 1234567890123}`
- [ ] 编写单元测试验证发布功能

### Task 17: 模块入口与集成
- [ ] 实现 modules/strategy_engine/main.py 模块入口
- [ ] 集成所有子模块（订阅者、队列、回归、安全垫、信号生成器、状态机、发布者）
- [ ] 实现每秒执行一次策略判断的主循环
- [ ] 实现优雅关闭逻辑
- [ ] 编写集成测试验证完整流程
- [ ] 创建 modules/strategy_engine/__init__.py

---

## 阶段四：模块 3 - 订单执行模块（Day 11-14）

### Task 18: Redis 订阅者（交易信号）
- [ ] 实现 modules/order_executor/redis_subscriber.py
- [ ] 订阅 Redis `trading_signal` 频道
- [ ] 解析买入信号并传递给订单管理器
- [ ] 编写单元测试验证订阅功能

### Task 19: CLOB 客户端封装
- [ ] 实现 modules/order_executor/clob_client.py
- [ ] 使用 EOA 模式（signature_type=0）初始化 ClobClient
- [ ] 从 .env 加载私钥与 API 凭证
- [ ] 实现余额查询方法
- [ ] 实现 Tick Size 查询方法
- [ ] 实现订单簿查询方法
- [ ] 编写集成测试验证客户端连接

### Task 20: 动态手续费计算
- [ ] 实现 modules/order_executor/fee_calculator.py
- [ ] 实现 Taker Fee 计算公式：`Fee = C × 0.072 × p × (1 - p)`
- [ ] 实现净期望值计算
- [ ] 编写单元测试验证手续费计算

### Task 21: 订单管理器
- [ ] 实现 modules/order_executor/order_manager.py
- [ ] 实现价格验证逻辑（当前买入价 < 最高可买入价格）
- [ ] 实现 FAK 市场订单创建逻辑
- [ ] 实现订单簿深度检查逻辑
- [ ] 实现滑点保护逻辑
- [ ] 实现订单执行结果处理
- [ ] 实现错误处理逻辑
- [ ] 编写单元测试模拟订单提交流程

### Task 22: 模块入口与集成
- [ ] 实现 modules/order_executor/main.py 模块入口
- [ ] 集成订阅者、CLOB 客户端、手续费计算、订单管理器
- [ ] 实现主循环（监听交易信号并执行订单）
- [ ] 实现优雅关闭逻辑
- [ ] 编写集成测试验证完整流程
- [ ] 创建 modules/order_executor/__init__.py

---

## 阶段五：模块 4 - 资金结算模块（Day 15-17）

### Task 23: CTF 合约交互
- [ ] 实现 modules/settlement_worker/ctf_contract.py
- [ ] 使用 web3.py 连接 Polygon 网络
- [ ] 加载 CTF 合约 ABI
- [ ] 实现 redeemPositions 函数调用逻辑
- [ ] 实现交易签名与 Gas 费支付
- [ ] 编写集成测试验证合约交互（使用测试网）

### Task 24: 赎回管理器
- [ ] 实现 modules/settlement_worker/redemption_manager.py
- [ ] 实现查询已完结市场 Condition IDs 的逻辑
- [ ] 实现检查获胜份额余额的逻辑
- [ ] 实现批量赎回逻辑
- [ ] 实现赎回失败重试机制
- [ ] 实现 POL/MATIC 余额监控
- [ ] 编写单元测试验证赎回逻辑

### Task 25: 模块入口与定时任务
- [ ] 实现 modules/settlement_worker/main.py 模块入口
- [ ] 实现定时任务（每 10 分钟执行一次）
- [ ] 集成 CTF 合约交互与赎回管理器
- [ ] 实现优雅关闭逻辑
- [ ] 编写集成测试验证完整流程
- [ ] 创建 modules/settlement_worker/__init__.py

---

## 阶段六：部署脚本与监控（Day 18-20）

### Task 26: 启动与停止脚本
- [ ] 编写 scripts/start_module.sh 启动单个模块脚本
- [ ] 编写 scripts/start_all.sh 启动所有模块脚本
- [ ] 编写 scripts/stop_all.sh 停止所有模块脚本
- [ ] 测试脚本在 Vultr 墨西哥城服务器上的执行

### Task 27: 监控脚本
- [ ] 编写 scripts/monitor.sh 监控脚本
- [ ] 实现日志监控与关键词告警
- [ ] 实现进程健康检查（自动重启崩溃进程）
- [ ] 实现余额监控（USDC.e 与 POL/MATIC）
- [ ] 实现告警通知（邮件或 Webhook）

### Task 28: Systemd 服务配置（可选）
- [ ] 为每个模块创建 systemd 服务文件
- [ ] 配置自动重启与日志记录
- [ ] 测试服务启动、停止、重启

---

## 阶段七：测试与优化（Day 21-23）

### Task 29: 单元测试完善
- [ ] 为所有核心模块编写单元测试（目标覆盖率 > 80%）
- [ ] 使用 pytest 和 pytest-asyncio 编写异步测试
- [ ] 使用 Mock 对象模拟外部依赖
- [ ] 编写测试数据生成器

### Task 30: 集成测试
- [ ] 编写端到端测试：模拟完整数据流（市场数据 → 策略分析 → 订单执行）
- [ ] 测试 Redis Pub/Sub 通信稳定性
- [ ] 测试模块独立运行与崩溃恢复
- [ ] 测试定时任务执行

### Task 31: 性能优化
- [ ] 性能基准测试：测量关键路径延迟
- [ ] 优化 OLS 回归计算（确保 < 10ms）
- [ ] 优化 Redis Pub/Sub 延迟（确保 < 10ms）
- [ ] 优化订单提交流程（确保 < 200ms）
- [ ] 使用 Python Profiler 识别性能瓶颈

---

## 阶段八：文档编写（Day 24-25）

### Task 32: 项目文档
- [ ] 编写 README.md 项目说明文档
- [ ] 编写快速开始指南（环境准备、配置、启动）
- [ ] 编写架构说明文档（独立进程架构、Redis Pub/Sub）
- [ ] 编写策略参数说明文档
- [ ] 编写常见问题与故障排查文档

### Task 33: API 文档
- [ ] 编写模块接口文档（每个模块的输入输出）
- [ ] 编写 Redis 频道消息格式文档
- [ ] 编写配置文件说明文档

---

## 阶段九：验收测试（Day 26-28）

### Task 34: 实盘小资金测试
- [ ] 在 Polygon 主网部署程序（Vultr 墨西哥城服务器）
- [ ] 启动 Redis 服务器
- [ ] 依次启动 4 个独立模块
- [ ] 使用小额资金（如 $50 USDC.e）进行实盘测试
- [ ] 监控至少 10 个完整 5 分钟周期
- [ ] 记录所有交易结果与系统行为

### Task 35: 问题修复与优化
- [ ] 分析实盘测试日志，识别问题
- [ ] 修复发现的 Bug
- [ ] 优化策略参数
- [ ] 优化系统性能
- [ ] 更新文档与配置

### Task 36: 最终验收
- [ ] 验证所有成功标准是否达成
- [ ] 验证系统稳定性（24 小时连续运行）
- [ ] 验证日志记录完整性
- [ ] 验证错误处理与恢复机制
- [ ] 确认 V1.0 版本可发布

---

## Task Dependencies

```
阶段一（基础设施）
  Task 1 → Task 2, Task 3, Task 4, Task 5（可并行）
  
阶段二（模块 1）
  Task 6, Task 7（可并行）→ Task 8 → Task 9
  
阶段三（模块 2）
  Task 10 → Task 11 → Task 12, Task 13, Task 14, Task 15（可并行）→ Task 16 → Task 17
  
阶段四（模块 3）
  Task 18 → Task 19 → Task 20, Task 21（可并行）→ Task 22
  
阶段五（模块 4）
  Task 23 → Task 24 → Task 25
  
阶段六（部署与监控）
  Task 26, Task 27, Task 28（可并行，依赖阶段二至五完成）
  
阶段七（测试与优化）
  Task 29, Task 30, Task 31（可并行，依赖阶段二至五完成）
  
阶段八（文档）
  Task 32, Task 33（可并行）
  
阶段九（验收）
  Task 34 → Task 35 → Task 36
```

**并行开发建议**：
- 阶段二、三、四、五可由不同开发者并行开发（模块独立）
- 每个模块开发完成后可独立测试
- 阶段六、七、八可并行执行

---

## 时间估算

| 阶段 | 工作日 | 日历天 |
|------|--------|--------|
| 阶段一：基础设施搭建 | 3 天 | 3 天 |
| 阶段二：模块 1 - 市场数据获取 | 3 天 | 3 天 |
| 阶段三：模块 2 - 策略分析引擎 | 4 天 | 4 天 |
| 阶段四：模块 3 - 订单执行 | 4 天 | 4 天 |
| 阶段五：模块 4 - 资金结算 | 3 天 | 3 天 |
| 阶段六：部署脚本与监控 | 3 天 | 3 天 |
| 阶段七：测试与优化 | 3 天 | 3 天 |
| 阶段八：文档编写 | 2 天 | 2 天 |
| 阶段九：验收测试 | 3 天 | 3 天 |
| **总计** | **28 天** | **28 天** |

**注**：以上时间估算基于单人全职开发，实际时间可能因经验、环境准备、问题复杂度等因素有所调整。如多人并行开发，可缩短总工期至约 15-20 天。
