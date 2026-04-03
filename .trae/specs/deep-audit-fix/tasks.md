# 深度审计诊断报告改善计划 - 任务列表

本文档定义基于 `deep_audit_report.md` 的全部改善任务。**等待实施**

---

## Phase 0: 基础设施层（6 个新模块）

### Task 0.1: 创建 shared/models.py — 统一 TradingSignal 数据结构
- [ ] 定义唯一的 TradingSignal dataclass（合并策略字段 + 执行字段）
- [ ] 包含策略字段：action, direction, confidence, price_analysis, time_remaining
- [ ] 包含执行字段：signal_id, token_id, market_id, side, size, price
- [ ] 实现 to_dict() / from_dict() 序列化方法
- [ ] 实现 validate() 方法（token_id 非空等基本校验）
- [ ] 编写单元测试（20+ tests）

### Task 0.2: 创建 shared/market_discovery.py — 市场发现服务
- [ ] 实现 MarketDiscovery 类
- [ ] 通过 CLOB API / Gamma API 查询活跃的 Fast Market 列表
- [ ] 预计算 Slug 匹配：`btc-updown-5m-{timestamp}`
- [ ] 构建 UP/DOWN → token_id 映射表
- [ ] 缓存到 Redis（TTL=300s）+ 定期刷新
- [ ] 提供 get_active_market() API 返回完整市场信息
- [ ] 处理 API 不可用时的降级策略
- [ ] 编写单元测试（mock API，25+ tests）

### Task 0.3: 创建 shared/risk_manager.py — 风控管理器
- [ ] 实现 RiskManager 类
- [ ] check_before_order(): 4 项检查（单仓位/总敞口/日亏损/余额保留）
- [ ] 返回 RiskCheckResult(pass, reason)
- [ ] 从 Config 加载 max_position_size, max_total_exposure, max_daily_loss, min_balance
- [ ] 编写单元测试（30+ tests）：各种超限/正常场景

### Task 0.4: 创建 shared/position_tracker.py — 持仓追踪器
- [ ] 实现 PositionTracker 类
- [ ] 记录每个 token_id 的持仓数量、成本、盈亏
- [ ] get_open_positions() / get_position(token_id) / get_total_exposure()
- [ ] get_daily_pnl() 日内盈亏计算
- [ ] update_from_trade_result() 从交易结果更新
- [ ] 订阅 TRADE_RESULT_CHANNEL 自动更新
- [ ] 编写单元测试（25+ tests）

### Task 0.5: 创建 shared/signal_adapter.py — 信号转换层
- [ ] 实现 SignalAdapter 类
- [ ] adapt(strategy_signal, market_info) → 执行型 TradingSignal
- [ ] direction → side + token_id 映射
- [ ] confidence → size 计算（可配置的映射函数）
- [ ] 生成唯一 signal_id
- [ ] 编写单元测试（20+ tests）：各种方向/置信度组合

### Task 0.6: 创建 modules/order_executor/stop_loss_monitor.py — 止损止盈监控
- [ ] 实现 StopLossMonitor 类
- [ ] 定期轮询所有持仓的市场价格
- [ ] 止损触发条件：current_price < cost × (1 - stop_loss%)
- [ ] 止盈触发条件：current_price > cost × (1 + take_profit%)
- [ ] 触发时通过 OrderManager 创建 FAK 卖单
- [ ] 可配置 check_interval 和 enabled 开关
- [ ] 编写单元测试（20+ tests）

---

## Phase 1: 核心逻辑修复（11 个修复任务）

### Task 1.1: 修复 #8 — 周期切换时清空 PriceQueue
- [ ] 在 _execute_strategy_cycle() 中检测 cycle_id 变化
- [ ] 变化时调用 price_queue.clear()
- [ ] 记录日志（旧 cycle_id → 新 cycle_id, 清空前 queue 大小）
- [ ] 编写单元测试验证周期切换后队列确实被清空

### Task 1.2: 修复 #10 — 移除 ThreadPoolExecutor 保证时序
- [ ] 将 _process_messages_batch() 改为纯顺序处理
- [ ] 移除 ThreadPoolExecutor(max_workers=4)
- [ ] 保留批量处理框架但保证消息按 timestamp 排序后逐条执行
- [ ] 编写单元测试验证大量消息时序正确

### Task 1.3: 修复 #9 — _message_buffer 改为线程安全
- [ ] import queue; self._message_buffer = queue.Queue(maxsize=1000)
- [ ] Redis 回调中用 .put() 替代 .append()
- [ ] 主循环中用 .get_nowait() 替代直接遍历
- [ ] 编写单元测试验证并发安全

### Task 1.4: 修复 #1+#2+#3 — 重构 max_buy_price 计算逻辑 ⭐ 最复杂
- [ ] 明确安全垫量纲为概率空间（添加注释）
- [ ] calculate_max_buy_price() 接收 market_best_ask 而非 BTC price
- [ ] 新增 time_decay_factor(time_remaining) 方法
- [ ] 新公式：max_buy = best_ask × (1 - cushion) × decay_factor
- [ ] clamp 到 [0.01, 0.99]
- [ ] 同步修改 SafetyCushionCalculator 中的同名方法或删除
- [ ] 修改 generate_signal() 调用链传入正确的市场价格
- [ ] 编写单元测试（30+ tests）：各种价格/时间组合

### Task 1.5: 修复 #4 — 重写置信度归一化
- [ ] 用 Sigmoid 替换硬编码系数
- [ ] normalize_slope(): sigmoid(50 × (|K| - 0.02))
- [ ] normalize_difference(): sigmoid(0.02 × (diff - 15))
- [ ] 参数选择使典型值落在 [0.3, 0.7] 区间
- [ ] 编写单元测试验证归一化区分度

### Task 1.6: 修复 #7 — get_max_buy_price_limit 改为时间驱动
- [ ] 签名改为 (time_remaining, confidence=None)
- [ ] 基础限制按时间阶梯：>80s→0.75, >40s→0.85, >15s→0.90, else→0.93
- [ ] 置信度微调 ±0.02
- [ ] 最终 clamp 到 [0.60, 0.98]

### Task 1.7: 修复 #5 — 统一 TradingSignal 数据结构
- [ ] signal_generator.py 改用 from shared.models import TradingSignal
- [ ] redis_subscriber.py 改用 from shared.models import TradingSignal
- [ ] 删除两处旧定义
- [ ] 更新 signal_generator.to_dict() 输出包含执行所需字段
- [ ] 更新 redis_subscriber.from_dict() 兼容新格式
- [ ] 确保两端 validate() 通过
- [ ] 编写集成测试验证信号格式兼容性

### Task 1.8: 修复 #6 — 集成 MarketDiscovery 到信号链路 ⭐ 复杂
- [ ] strategy_engine/main.py 启动时初始化 MarketDiscovery
- [ ] generate_signal() 后经过 SignalAdapter 转换再发布
- [ ] 发布到 Redis 的信号包含完整的 token_id/market_id/side/size
- [ ] order_executor 能正确接收并 validate 通过
- [ ] 编写端到端集成测试（mock MarketDiscovery）

### Task 1.9: 修复 #11 — OrderManager 集成 RiskManager
- [ ] OrderManager.__init__() 中初始化 RiskManager
- [ ] create_order() / place_order() 前调用 risk_manager.check_before_order()
- [ ] 检查不通过时记录警告日志并拒绝下单
- [ ] 返回包含风险检查结果的 OrderResult
- [ ] 编写单元测试（25+ tests）：各种风控触发场景

### Task 1.10: 修复 #12+#13 — 集成 StopLossMonitor + 反馈闭环
- [ ] settlement_worker 或独立进程启动 StopLossMonitor
- [ ] StopLossMonitor 使用 PositionTracker 获取持仓
- [ ] strategy_engine/main.py 订阅 TRADE_RESULT_CHANNEL
- [ ] 收到结果后更新 PositionTracker
- [ ] generate_signal() 前检查是否已有 pending 的同方向信号
- [ ] 编写集成测试验证反馈闭环

### Task 1.11: 补充 — 更新配置与参数注册表
- [ ] settings.yaml 添加 market_discovery 配置段
- [ ] settings.yaml 添加 risk_manager 详细注释
- [ ] parameter_registry.py 注册新模块的所有参数（约 15 个新参数）
- [ ] config_validator.py 添加新参数的验证规则
- [ ] config_wizard.py 添加新参数的交互收集

---

## Phase 2: 测试验证（8 个测试任务）

### Task 2.1-T2.8: 全面测试覆盖
- [ ] T2.1: MarketDiscovery 单元测试（mock API, 25+ tests）
- [ ] T2.2: SignalAdapter 单元测试（20+ tests）
- [ ] T2.3: RiskManager 单元测试（30+ tests）
- [ ] T2.4: StopLossMonitor 单元测试（20+ tests）
- [ ] T2.5: PositionTracker 单元测试（25+ tests）
- [ ] T2.6: 端到端信号流集成测试（策略→adapter→Redis→执行器）
- [ ] T2.7: 周期切换数据隔离集成测试
- [ ] T2.8: 回归现有 335+ 测试确保无破坏

---

## Phase 3: 文档更新（3 个文档任务）

### Task 3.1-T3.3: 文档同步
- [ ] T3.1: 更新 USER_GUIDE.md 第 3 章（修复后的策略逻辑说明）
- [ ] T3.2: 更新 USER_GUIDE.md 第 5 章（新增 6 个模块参数）
- [ ] T3.3: 更新 parameter_registry.py 元数据

---

## Task Dependencies

```
Phase 0（基础设施）— 全部可并行:
  T0.1 ─┬─ T1.7 (统一TradingSignal)
  T0.2 ─┼─ T1.8 (集成MarketDiscovery)
  T0.3 ─┼─ T1.9 (集成RiskManager)
  T0.4 ─┼─ T1.10 (集成StopLoss+PositionTracker)
  T0.5 ─┘─ T1.8 (SignalAdapter依赖MarketDiscovery)
  T0.6 ── T1.10 (StopLossMonitor依赖PositionTracker)

Phase 1（核心修复）— 有依赖关系:
  T1.1, T1.2, T1.3 ── 无依赖，可最先做
  T1.4 ─────────────── 依赖 T0.2, T0.5（最复杂，核心路径）
  T1.5 ─────────────── 无依赖
  T1.6 ─────────────── 依赖 T1.4
  T1.7 ─────────────── 依赖 T0.1
  T1.8 ─────────────── 依赖 T0.2, T0.5, T1.7
  T1.9 ─────────────── 依赖 T0.3, T0.4
  T1.10 ────────────── 依赖 T0.4, T0.6
  T1.11 ────────────── 依赖 T1.1~T1.10

Phase 2（测试）─── 依赖 Phase 1 全部完成
Phase 3（文档）─── 可与 Phase 2 并行
```

---

## 预估工作量

| Phase | 任务数 | 新增代码(估) | 新增测试(估) | 复杂度 |
|-------|--------|-------------|-------------|--------|
| Phase 0 | 6 | ~1200 行 | ~140 tests | 中 |
| Phase 1 | 11 | ~800 行 | ~80 tests | 高 |
| Phase 2 | 8 | ~500 行 | 全部 | 中 |
| Phase 3 | 3 | 仅文档 | 无 | 低 |
| **合计** | **28** | **~2500 行** | **~250+ tests** | |

---

## 交付物

| 类型 | 文件 |
|------|------|
| **新增核心模块** | shared/models.py, market_discovery.py, risk_manager.py, position_tracker.py, signal_adapter.py |
| **新增监控模块** | modules/order_executor/stop_loss_monitor.py |
| **修改核心逻辑** | signal_generator.py, safety_cushion.py, main.py(策略), main.py(订单), order_manager.py, redis_subscriber.py |
| **修改配置** | settings.yaml, parameter_registry.py, config_validator.py, config_wizard.py |
| **修改文档** | docs/USER_GUIDE.md |
