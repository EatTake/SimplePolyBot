# Polymarket 五分钟比特币二元期权自动化交易系统 V1.0 Spec

## Why

基于 `Polymarket 交易研究报告.md` 中的深度研究成果，针对 `Polymarket 交易策略.md` 中描述的"基于时间衰减与动量斜率的动态阈值突破策略"，构建一个轻量化、模块化且具备毫秒级执行能力的自动化交易程序。V1.0 版本优先实现核心交易功能跑通与策略 100% 实现，为后续功能扩展预留架构空间。

## What Changes

### 核心功能模块（独立进程架构）

**架构设计原则**：每个模块作为独立进程运行，通过 Redis Pub/Sub 进行进程间通信，实现解耦、独立部署、独立扩展。

#### 模块 1：市场数据获取模块（独立进程）
- **运行模式**：24 小时不间断执行
- **数据源**：
  - Binance WebSocket（高频动量源）：wss://stream.binance.com:9443/ws/btcusdt@trade
  - Polymarket RTDS（Chainlink 结算基准源）：wss://ws-live-data.polymarket.com
- **输出格式**：`{"timestamp": 1234567890123, "binance_price": 67234.50, "chainlink_price": 67235.20}`
- **发布频道**：Redis `market_data` 频道
- **发布频率**：每秒 1 次（合并 Binance 高频数据与 Chainlink 数据）

#### 模块 2：策略分析引擎（独立进程）
- **运行模式**：持续运行，订阅市场数据
- **输入**：Redis `market_data` 频道
- **核心逻辑**：
  1. 维护 180 秒滚动价格队列
  2. 计算当前 5 分钟周期内的相对时间（如当前时间为 10:25，则相对时间为 25 秒）
  3. 每秒执行 OLS 线性回归计算波动子因子 K
  4. 计算动态安全垫：`Base Cushion + (α × |K| × √Time Remaining)`
  5. 判断是否触发买入信号
- **输出格式**：`{"action": "BUY", "direction": "DOWN", "max_price": 0.85, "timestamp": 1234567890123}` 或 `{"action": "WAIT", "timestamp": 1234567890123}`
- **发布频道**：Redis `trading_signal` 频道
- **发布频率**：每秒 1 次（仅在 T-100s 至 T-10s 区间输出买入信号）

#### 模块 3：订单执行模块（独立进程）
- **运行模式**：持续运行，订阅交易信号
- **输入**：Redis `trading_signal` 频道
- **核心逻辑**：
  1. 接收买入信号
  2. 通过 CLOB API 获取当前最优买入价格
  3. 判断：当前买入价 < 最高可买入价格
  4. 通过时执行 FAK 市场订单买入
  5. 记录交易结果
- **输出**：交易执行日志（成功/失败）
- **发布频道**：Redis `trade_result` 频道（可选）

#### 模块 4：资金结算模块（独立进程）
- **运行模式**：每 10 分钟运行一次（定时任务）
- **核心逻辑**：
  1. 查询已完结且获胜的市场 Condition IDs
  2. 检查获胜份额余额
  3. 调用 CTF 合约 redeemPositions 函数赎回 USDC.e
  4. 记录赎回结果
- **输出**：赎回执行日志

#### 模块 5：状态机管理（内嵌于策略分析引擎）
- **运行模式**：内嵌于策略分析引擎进程
- **核心逻辑**：
  1. 根据当前时间戳计算当前 5 分钟周期的 Start Price
  2. 管理 5 分钟周期切换（每 5 分钟重置价格队列）
  3. 记录每个周期的交易结果

### 技术架构选型

#### 核心技术栈
- **编程语言**：Python 3.10+
- **核心 SDK**：`py-clob-client`（官方 Python SDK）
- **进程间通信**：Redis（Pub/Sub 机制）
- **数据连接**：WebSocket（Binance + Polymarket RTDS）
- **区块链交互**：`web3.py`（CTF 合约赎回）
- **数据存储**：
  - 内存队列（180 秒滚动价格窗口）
  - Redis（进程间通信与状态共享）
- **配置管理**：环境变量 + YAML 配置文件

#### 进程架构图
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

### **BREAKING** 架构决策

* **放弃 Gnosis Safe 多签钱包**：V1.0 采用 EOA（外部拥有账户）模式，简化认证流程

* **放弃高频延迟套利**：接受 Vultr 墨西哥城 50-60ms 延迟，专注于 T-100 至 T-10 的动量突破策略

* **放弃中心化交易所价格基准**：排他性使用 Chainlink 预言机作为结算裁判价格

## Impact

### Affected Specs

* 新增：Polymarket 自动化交易系统能力

* 新增：实时数据流处理能力

* 新增：量化策略执行能力

* 新增：智能合约交互能力

### Affected Code

* 新增目录：`src/`（核心源代码）

* 新增目录：`config/`（配置文件）

* 新增目录：`tests/`（测试代码）

* 新增目录：`scripts/`（部署脚本）

* 新增文件：`requirements.txt`（Python 依赖）

* 新增文件：`.env.example`（环境变量模板）

***

## ADDED Requirements

### Requirement: 市场数据获取模块（独立进程）

系统 SHALL 提供 24 小时不间断的市场数据获取能力，通过 Redis Pub/Sub 发布实时价格数据。

#### Scenario: 模块启动与 WebSocket 连接
- **WHEN** 市场数据获取模块启动
- **THEN** 系统应同时连接 Binance WebSocket 与 Polymarket RTDS WebSocket
- **AND** 系统应订阅 Binance 的 btcusdt 现货深度流
- **AND** 系统应订阅 Polymarket RTDS 的 crypto_prices_chainlink 主题 btc/usd 数据流
- **AND** 系统应连接 Redis 服务器并准备发布消息

#### Scenario: 实时数据发布
- **WHEN** WebSocket 接收到价格更新（Binance 或 Chainlink）
- **THEN** 系统应合并两个数据源的价格
- **AND** 系统应每秒发布一次消息至 Redis `market_data` 频道
- **AND** 消息格式应为：`{"timestamp": 1234567890123, "binance_price": 67234.50, "chainlink_price": 67235.20}`
- **AND** 时间戳应为毫秒级 Unix 时间戳

#### Scenario: WebSocket 断线重连
- **WHEN** 任一 WebSocket 连接意外断开
- **THEN** 系统应采用指数退避策略（1s → 2s → 4s → 8s → 16s）自动重连
- **AND** 重连成功后应重新订阅数据流
- **AND** 系统应记录断线事件与重连时间戳至日志
- **AND** 断线期间应继续发布最近一次有效价格（标记为 stale）

#### Scenario: 模块独立运行
- **WHEN** 市场数据获取模块运行时
- **THEN** 模块应独立于其他模块运行
- **AND** 模块崩溃后应能自动重启（通过进程管理器如 systemd）
- **AND** 模块应不依赖其他模块的状态

***

### Requirement: 策略分析引擎（独立进程）

系统 SHALL 提供基于时间衰减与动量斜率的动态阈值突破策略分析能力，通过 Redis Pub/Sub 接收市场数据并发布交易信号。

#### Scenario: 模块启动与 Redis 订阅
- **WHEN** 策略分析引擎模块启动
- **THEN** 系统应连接 Redis 服务器并订阅 `market_data` 频道
- **AND** 系统应初始化 180 秒滚动价格队列
- **AND** 系统应加载策略参数配置（Base Cushion、α、最大买入价格表）

#### Scenario: 接收市场数据并更新队列
- **WHEN** 从 Redis `market_data` 频道接收到价格数据
- **THEN** 系统应提取 Binance 价格并推入 180 秒滚动队列
- **AND** 系统应提取 Chainlink 价格作为结算基准价格
- **AND** 系统应记录当前时间戳

#### Scenario: 计算 5 分钟周期内的相对时间
- **WHEN** 系统每秒执行一次策略判断
- **THEN** 系统应计算当前时间戳对应的 5 分钟周期起始时间
- **AND** 系统应计算当前时间在周期内的相对时间（如当前为 10:25，则相对时间为 25 秒）
- **AND** 系统应计算距离周期结束的剩余时间

#### Scenario: OLS 线性回归计算波动子因子 K
- **WHEN** 系统每秒执行一次策略判断循环
- **THEN** 系统应对过去 180 秒的价格队列进行 OLS 线性回归拟合
- **AND** 系统应计算斜率 K（波动子因子）与决定系数 R²
- **AND** 系统应根据 K 值符号判断趋势方向（K > 0 为上涨，K < 0 为下跌）

#### Scenario: 动态安全垫计算
- **WHEN** 系统计算安全垫总厚度
- **THEN** 系统应使用公式：`安全垫总厚度 = Base Cushion + (α × |K| × √Time Remaining)`
- **AND** Base Cushion 应可配置（默认 $15）
- **AND** α（风险敏感度参数）应可配置（默认 1.0）
- **AND** Time Remaining 应为距离市场结束的剩余秒数

#### Scenario: 买入信号生成与发布
- **WHEN** 当前 Chainlink 价格 < Start Price（DOWN 方向）
- **AND** `|Start Price - Current Price| > 安全垫总厚度`
- **AND** 当前时间处于 T-100s 至 T-10s 区间
- **THEN** 系统应生成买入信号：`{"action": "BUY", "direction": "DOWN", "max_price": 0.85, "timestamp": 1234567890123}`
- **AND** 系统应根据剩余时间查表获取最大买入价格（T-90s: $0.75, T-10s: $0.90）
- **AND** 系统应发布信号至 Redis `trading_signal` 频道

#### Scenario: 等待信号发布
- **WHEN** 当前不满足买入条件
- **THEN** 系统应发布等待信号：`{"action": "WAIT", "timestamp": 1234567890123}`
- **AND** 系统应继续监控下一秒的市场数据

#### Scenario: 5 分钟周期切换
- **WHEN** 当前 5 分钟周期结束（Time Remaining = 0）
- **THEN** 系统应清空 180 秒滚动价格队列
- **AND** 系统应根据新的周期起始时间获取新的 Start Price
- **AND** 系统应记录上一周期的交易结果（是否买入、买入价格）

#### Scenario: 模块独立运行
- **WHEN** 策略分析引擎模块运行时
- **THEN** 模块应独立于其他模块运行
- **AND** 模块崩溃后应能自动重启
- **AND** 模块应通过 Redis 与其他模块通信，无直接依赖

***

### Requirement: 订单执行模块（独立进程）

系统 SHALL 提供基于 EOA + CLOB Off-Chain API 的订单创建、签名与提交能力，通过 Redis Pub/Sub 接收交易信号。

#### Scenario: 模块启动与 Redis 订阅
- **WHEN** 订单执行模块启动
- **THEN** 系统应连接 Redis 服务器并订阅 `trading_signal` 频道
- **AND** 系统应加载环境变量中的私钥与 API 凭证
- **AND** 系统应使用 `signature_type=0`（EOA 模式）初始化 ClobClient
- **AND** 系统应设置 `funder` 参数为钱包公开地址
- **AND** 系统应验证 USDC.e 余额充足（≥ 最小交易金额）

#### Scenario: 接收买入信号并验证价格
- **WHEN** 从 Redis `trading_signal` 频道接收到买入信号
- **THEN** 系统应提取买入方向（UP 或 DOWN）与最高可买入价格
- **AND** 系统应通过 CLOB API 获取当前最优买入价格
- **AND** 系统应判断：当前买入价 < 最高可买入价格
- **AND** 判断通过时进入订单提交流程

#### Scenario: FAK 市场订单创建与提交
- **WHEN** 价格验证通过
- **THEN** 系统应调用 `create_and_post_market_order` 方法
- **AND** 订单类型应设置为 `OrderType.FAK`（部分成交并取消剩余）
- **AND** 订单价格应设置为策略计算的最大买入价格
- **AND** 订单金额应考虑动态 Taker Fee（公式：`Fee = C × 0.072 × p × (1 - p)`）
- **AND** 系统应记录订单执行结果至日志

#### Scenario: 订单簿深度检查
- **WHEN** 系统准备提交订单前
- **THEN** 系统应通过 CLOB API 拉取实时订单簿
- **AND** 系统应计算从最优卖价往下吃单的真实成交均价
- **AND** 系统应验证单次下注金额不超过目标价格层级可用流动性深度的 50%

#### Scenario: 订单执行失败处理
- **WHEN** 订单提交返回错误（如 `FOK_ORDER_NOT_FILLED_ERROR`）
- **THEN** 系统应记录错误日志并放弃当前交易机会
- **AND** 系统应继续监听下一个交易信号
- **AND** 系统不应重试失败的订单（避免逆向选择）

#### Scenario: 模块独立运行
- **WHEN** 订单执行模块运行时
- **THEN** 模块应独立于其他模块运行
- **AND** 模块崩溃后应能自动重启
- **AND** 模块应通过 Redis 与其他模块通信，无直接依赖

***

### Requirement: 资金结算模块（独立进程）

系统 SHALL 提供定时执行的已获胜份额赎回能力，每 10 分钟运行一次。

#### Scenario: 模块启动与定时任务设置
- **WHEN** 资金结算模块启动
- **THEN** 系统应连接 Polygon 网络（使用 web3.py）
- **AND** 系统应加载 CTF 合约 ABI
- **AND** 系统应设置定时任务（每 10 分钟执行一次）

#### Scenario: 查询可赎回市场
- **WHEN** 定时任务触发
- **THEN** 系统应查询已完结且获胜的市场 Condition IDs
- **AND** 系统应检查这些市场中是否持有获胜份额
- **AND** 系统应过滤出余额 > 0 的市场

#### Scenario: 执行 CTF 合约赎回
- **WHEN** 检测到可赎回的获胜份额
- **THEN** 系统应构建交易调用 CTF 合约的 `redeemPositions` 函数
- **AND** 交易参数应包括：
  - `collateralToken`: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`（USDC.e 地址）
  - `parentCollectionId`: `0x0000...0000`（32 字节零值）
  - `conditionId`: 市场的 Condition ID
  - `indexSets`: `[1, 2]`（赎回两种结果代币）
- **AND** 系统应使用钱包私钥签名交易并支付 Gas 费（POL/MATIC）
- **AND** 交易成功后，USDC.e 应划拨至钱包可用资金池
- **AND** 系统应记录赎回结果至日志

#### Scenario: 赎回失败重试
- **WHEN** CTF 合约赎回交易失败（如 Gas 不足、网络拥堵）
- **THEN** 系统应记录失败原因并等待下一个 10 分钟周期重试
- **AND** 系统应检查 POL/MATIC 余额是否充足
- **AND** 系统应在余额不足时发送告警通知

#### Scenario: 模块独立运行
- **WHEN** 资金结算模块运行时
- **THEN** 模块应独立于其他模块运行
- **AND** 模块崩溃后应能自动重启
- **AND** 模块应不依赖其他模块的状态
- **AND** 模块应不依赖 Redis 通信（独立定时任务）

---

### Requirement: 状态机管理（内嵌于策略分析引擎）

系统 SHALL 提供事件驱动的 5 分钟周期生命周期管理能力，内嵌于策略分析引擎进程。

#### Scenario: 市场初始化阶段（T-300s）
- **WHEN** 新的 5 分钟周期开始
- **THEN** 系统应根据当前时间戳预计算市场 Slug（格式：`btc-updown-5m-{window_start_timestamp}`）
- **AND** 系统应通过 Gamma API 获取市场元数据（Condition ID、Token IDs、Start Price）
- **AND** 系统应清空 180 秒价格队列并开始积累数据

#### Scenario: 数据积累阶段（T-300s 至 T-101s）
- **WHEN** 系统处于数据积累阶段
- **THEN** 系统应持续将 Binance 价格推入队列
- **AND** 系统应不执行任何交易判断
- **AND** 系统应监控 Chainlink 价格与 Start Price 的差额

#### Scenario: 狙击监控阶段（T-100s 至 T-0s）
- **WHEN** 系统进入狙击监控阶段
- **THEN** 系统应每秒执行一次完整的策略判断循环：
  1. 计算 OLS 线性回归斜率 K
  2. 提取 Chainlink 实时价格并计算差额
  3. 计算动态 Buffer Cushion
  4. 判断是否触发买入信号
  5. 如触发信号，发布交易信号至 Redis
- **AND** 系统应在 T-0s 后立即重置状态，准备进入下一个周期

#### Scenario: 周期切换
- **WHEN** 当前 5 分钟周期结束
- **THEN** 系统应记录本周期交易结果（是否买入、买入价格、最终结果）
- **AND** 系统应立即初始化下一个 5 分钟周期
- **AND** 系统应确保无状态残留影响下一周期决策

---

### Requirement: 配置管理与日志系统

系统 SHALL 提供灵活的配置管理与完善的日志记录能力。

#### Scenario: 配置文件加载
- **WHEN** 任一模块启动
- **THEN** 系统应从 `.env` 文件加载敏感配置（私钥、API 凭证、Redis 连接信息）
- **AND** 系统应从 `config/settings.yaml` 加载策略参数（Base Cushion、α、最大买入价格表）
- **AND** 系统应验证所有必需配置项已设置

#### Scenario: 交易日志记录
- **WHEN** 系统执行任何关键操作（订单提交、赎回、状态切换）
- **THEN** 系统应记录结构化日志（JSON 格式），包含：
  - 时间戳（毫秒级）
  - 模块名称
  - 操作类型
  - 市场 ID
  - 关键参数（价格、数量、K 值、安全垫厚度）
  - 执行结果（成功/失败、错误信息）
- **AND** 日志应同时输出至控制台与文件（`logs/trading.log`）

  * 关键参数（价格、数量、K 值、安全垫厚度）

  - 执行结果（成功/失败、错误信息）
- **AND** 日志应同时输出至控制台与文件（`logs/trading.log`）

#### Scenario: 错误告警
- **WHEN** 系统遇到严重错误（WebSocket 断线超过 5 分钟、余额不足、连续 3 次订单失败）
- **THEN** 系统应发送告警通知（支持邮件/Webhook）
- **AND** 系统应进入安全模式（暂停交易，仅监控数据）

---

### Requirement: 网络防屏蔽策略

系统 SHALL 提供绕过 Cloudflare WAF 拦截的能力。

#### Scenario: 持久化 WebSocket 连接
- **WHEN** 系统连接 Polymarket RTDS 或 Binance WebSocket
- **THEN** 系统应建立持久化长连接
- **AND** 系统应每 10 秒发送 `PING` 消息保持连接活跃
- **AND** 系统应避免高频 REST API 轮询（减少 403 Forbidden 风险）

#### Scenario: Cloudflare 拦截处理
- **WHEN** REST API 请求返回 403 Forbidden 错误
- **THEN** 系统应记录拦截事件并降低请求频率
- **AND** 系统应考虑切换至住宅代理或集成 `curl-impersonate`（后续版本）
- **AND** 系统应优先使用 WebSocket 数据流而非 REST API

---

## MODIFIED Requirements

无修改的需求（V1.0 为全新实现）。

---

## REMOVED Requirements

无移除的需求（V1.0 为全新实现）。

---

## 非功能性需求

### 性能要求
- **订单提交延迟**：从信号生成到订单提交 < 200ms（含网络延迟）
- **WebSocket 消息处理延迟**：< 50ms
- **OLS 回归计算延迟**：< 10ms（180 数据点）
- **Redis Pub/Sub 延迟**：< 10ms
- **系统可用性**：> 99%（允许计划内维护停机）

### 安全要求
- **私钥管理**：私钥仅存储于 `.env` 文件，绝不硬编码或记录日志
- **API 凭证轮换**：支持定期轮换 API Key、Secret、Passphrase
- **审计日志**：所有交易操作记录完整审计日志，保留 30 天
- **进程隔离**：每个模块独立进程，崩溃不影响其他模块

### 可维护性要求
- **模块化设计**：每个模块独立、可测试、可替换
- **配置外部化**：所有参数通过配置文件管理，无需修改代码
- **代码注释**：关键逻辑提供中文注释，复杂算法提供数学公式说明
- **独立部署**：每个模块可独立部署、重启、升级

### 扩展性要求
- **多市场支持**：架构预留支持多个市场同时监控的能力
- **多策略支持**：策略引擎设计为可插拔，支持后续添加新策略
- **多账户支持**：架构预留支持多个 EOA 钱包同时运行的能力
- **水平扩展**：通过 Redis Pub/Sub 支持多实例部署

---

## 技术栈详细选型

### 核心依赖
```
Python >= 3.10
py-clob-client >= 0.5.0      # Polymarket 官方 Python SDK
web3 >= 6.0.0                # 以太坊交互
websockets >= 12.0           # WebSocket 客户端
redis >= 5.0.0               # Redis 客户端（进程间通信）
numpy >= 1.24.0              # 数值计算（OLS 回归）
pandas >= 2.0.0              # 数据处理
python-dotenv >= 1.0.0       # 环境变量管理
PyYAML >= 6.0                # YAML 配置文件
structlog >= 23.0            # 结构化日志
aiohttp >= 3.9.0             # 异步 HTTP 客户端
```

### 开发工具

```
pytest >= 7.4.0              # 单元测试
pytest-asyncio >= 0.21.0     # 异步测试支持
black >= 23.0.0              # 代码格式化
mypy >= 1.5.0                # 类型检查
ruff >= 0.1.0                # 快速 Linter
```

***

## 项目目录结构（独立进程架构）

```
SimplePolyBot/
├── modules/                        # 独立模块目录
│   ├── market_data_collector/      # 模块 1：市场数据获取模块
│   │   ├── __init__.py
│   │   ├── main.py                 # 模块入口（独立运行）
│   │   ├── binance_ws.py           # Binance WebSocket 客户端
│   │   ├── polymarket_rtds.py      # Polymarket RTDS 客户端
│   │   └── redis_publisher.py      # Redis 发布者
│   ├── strategy_engine/            # 模块 2：策略分析引擎
│   │   ├── __init__.py
│   │   ├── main.py                 # 模块入口（独立运行）
│   │   ├── redis_subscriber.py     # Redis 订阅者
│   │   ├── price_queue.py          # 180 秒滚动价格队列
│   │   ├── ols_regression.py       # OLS 线性回归
│   │   ├── safety_cushion.py       # 动态安全垫计算
│   │   ├── signal_generator.py     # 买入信号生成器
│   │   ├── market_lifecycle.py     # 市场生命周期管理（状态机）
│   │   └── redis_publisher.py      # Redis 发布者
│   ├── order_executor/             # 模块 3：订单执行模块
│   │   ├── __init__.py
│   │   ├── main.py                 # 模块入口（独立运行）
│   │   ├── redis_subscriber.py     # Redis 订阅者
│   │   ├── clob_client.py          # CLOB 客户端封装
│   │   ├── order_manager.py        # 订单管理器
│   │   └── fee_calculator.py       # 动态手续费计算
│   └── settlement_worker/          # 模块 4：资金结算模块
│       ├── __init__.py
│       ├── main.py                 # 模块入口（定时任务）
│       ├── ctf_contract.py         # CTF 合约交互
│       └── redemption_manager.py   # 赎回管理器
├── shared/                         # 共享代码目录
│   ├── __init__.py
│   ├── config.py                   # 配置管理（所有模块共用）
│   ├── logger.py                   # 日志工具（所有模块共用）
│   ├── redis_client.py             # Redis 客户端封装
│   └── constants.py                # 常量定义
├── config/                         # 配置文件目录
│   ├── settings.yaml               # 策略参数配置
│   └── logging.yaml                # 日志配置
├── tests/                          # 测试代码目录
│   ├── __init__.py
│   ├── test_market_data_collector/
│   ├── test_strategy_engine/
│   ├── test_order_executor/
│   └── test_settlement_worker/
├── scripts/                        # 部署与运维脚本
│   ├── start_all.sh                # 启动所有模块
│   ├── stop_all.sh                 # 停止所有模块
│   ├── start_module.sh             # 启动单个模块
│   ├── monitor.sh                  # 监控脚本
│   └── setup_redis.sh              # Redis 安装与配置
├── logs/                           # 日志目录
│   ├── market_data_collector.log
│   ├── strategy_engine.log
│   ├── order_executor.log
│   └── settlement_worker.log
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python 依赖
├── README.md                       # 项目说明
└── .gitignore
```

**架构说明**：
- 每个模块位于 `modules/` 目录下，可独立运行
- `shared/` 目录包含所有模块共用的工具代码
- 每个模块有独立的日志文件
- 通过 Redis Pub/Sub 进行模块间通信
- 可通过脚本单独启动/停止任一模块

***

## 风险与应对措施

### 技术风险

| 风险             | 影响          | 应对措施                                   |
| -------------- | ----------- | -------------------------------------- |
| WebSocket 频繁断线 | 数据丢失、错过交易机会 | 指数退避重连 + 断线告警 + 数据完整性检查                |
| Cloudflare 拦截  | 无法访问 API    | 优先使用 WebSocket + 降低 REST 调用频率 + 预留代理支持 |
| Polygon 网络拥堵   | 赎回交易延迟      | 异步清算 + Gas 价格监控 + 交易加速                 |
| OLS 计算性能瓶颈     | 策略判断延迟      | 使用 NumPy 向量化计算 + 限制队列长度                |

### 业务风险

| 风险      | 影响   | 应对措施                    |
| ------- | ---- | ----------------------- |
| 策略失效    | 持续亏损 | 回测验证 + 实盘小资金测试 + 策略参数可调 |
| 市场流动性不足 | 订单滑点 | 订单簿深度检查 + 流动性熔断机制       |
| 预言机价格异常 | 错误结算 | Chainlink 价格监控 + 异常值过滤  |
| 私钥泄露    | 资金损失 | 环境变量存储 + 权限分离 + 冷热钱包分离  |

### 运维风险

| 风险      | 影响     | 应对措施                          |
| ------- | ------ | ----------------------------- |
| 服务器宕机   | 系统停机   | 健康检查 + 自动重启 + 监控告警            |
| 磁盘空间不足  | 日志写入失败 | 日志轮转 + 磁盘空间监控                 |
| 依赖库版本冲突 | 运行错误   | 虚拟环境 + 依赖锁定（requirements.txt） |

***

## 成功标准

V1.0 版本成功标准：

1. ✅ 系统能够稳定连接 Binance 与 Polymarket RTDS 数据流，断线重连成功率 > 95%
2. ✅ 策略引擎能够准确计算 OLS 斜率 K 与动态安全垫，计算延迟 < 10ms
3. ✅ 订单执行模块能够成功提交 FAK 订单至 Polymarket CLOB，订单成功率 > 90%
4. ✅ 资金结算模块能够成功赎回已获胜份额，赎回成功率 > 95%
5. ✅ 系统能够连续运行 24 小时无崩溃，日志记录完整
6. ✅ 核心策略逻辑 100% 实现（动态安全垫、时间衰减价格限制、OLS 回归）

