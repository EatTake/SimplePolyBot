# Checklist - 深度审计诊断报告改善计划

本文档用于验证每个改善任务的完成情况。**等待实施**

---

## Phase 0: 基础设施层

### Task 0.1: shared/models.py — 统一 TradingSignal
- [ ] 文件已创建
- [ ] TradingSignal dataclass 包含策略字段（action, direction, confidence, price_analysis）
- [ ] TradingSignal dataclass 包含执行字段（signal_id, token_id, market_id, side, size, price）
- [ ] to_dict() 序列化方法正确
- [ ] from_dict() 反序列化方法正确
- [ ] validate() 基本校验通过（token_id 非空等）
- [ ] 单元测试 ≥ 20 个且全部通过

### Task 0.2: shared/market_discovery.py — 市场发现服务
- [ ] 文件已创建
- [ ] MarketDiscovery 类实现完整
- [ ] 支持 CLOB API / Gamma API 查询活跃市场
- [ ] Slug 预计算逻辑正确
- [ ] UP/DOWN → token_id 映射正确
- [ ] Redis 缓存 TTL=300s 正常工作
- [ ] get_active_market() 返回完整市场信息
- [ ] API 不可用时有降级策略
- [ ] 单元测试 ≥ 25 个且全部通过

### Task 0.3: shared/risk_manager.py — 风控管理器
- [ ] 文件已创建
- [ ] RiskManager.check_before_order() 实现 4 项检查
- [ ] 单仓位超限检查正常工作
- [ ] 总敞口超限检查正常工作
- [ ] 日亏损限额检查正常工作
- [ ] 余额保留检查正常工作
- [ ] 返回正确的 RiskCheckResult
- [ ] 单元测试 ≥ 30 个且全部通过

### Task 0.4: shared/position_tracker.py — 持仓追踪器
- [ ] 文件已创建
- [ ] PositionTracker 记录持仓数量/成本/盈亏
- [ ] get_open_positions() 正确返回所有持仓
- [ ] get_position(token_id) 正确查询单个持仓
- [ ] get_total_exposure() 正确计算总敞口
- [ ] get_daily_pnl() 正确计算日内盈亏
- [ ] update_from_trade_result() 正确更新
- [ ] TRADE_RESULT_CHANNEL 订阅自动更新
- [ ] 单元测试 ≥ 25 个且全部通过

### Task 0.5: shared/signal_adapter.py — 信号转换层
- [ ] 文件已创建
- [ ] SignalAdapter.adapt() 方法实现
- [ ] direction→side 映射正确（UP→BUY Yes, DOWN→BUY No）
- [ ] token_id 从 market_info 正确获取
- [ ] confidence→size 映射可配置
- [ ] signal_id 全局唯一
- [ ] 单元测试 ≥ 20 个且全部通过

### Task 0.6: stop_loss_monitor.py — 止损止盈监控
- [ ] 文件已创建
- [ ] StopLossMonitor 定期轮询逻辑正确
- [ ] 止损触发条件正确：price < cost × (1 - stop_loss%)
- [ ] 止盈触发条件正确：price > cost × (1 + take_profit%)
- [ ] 触发时通过 OrderManager 创建 FAK 卖单
- [ ] check_interval 和 enabled 可配置
- [ ] 单元测试 ≥ 20 个且全部通过

---

## Phase 1: 核心逻辑修复

### Task 1.1: #8 周期切换清空 PriceQueue
- [ ] _execute_strategy_cycle() 检测 cycle_id 变化
- [ ] 变化时调用 price_queue.clear()
- [ ] 日志记录旧/新 cycle_id 和清空前大小
- [ ] 单元测试验证周期切换后队列确实被清空

### Task 1.2: #10 移除 ThreadPoolExecutor
- [ ] _process_messages_batch() 改为纯顺序处理
- [ ] ThreadPoolExecutor 已移除
- [ ] 消息按 timestamp 排序后逐条执行
- [ ] 单元测试验证大量消息时序正确

### Task 1.3: #9 _message_buffer 线程安全
- [ ] 改为 queue.Queue(maxsize=1000)
- [ ] Redis 回调使用 .put()
- [ ] 主循环使用 .get_nowait()
- [ ] 单元测试验证并发安全

### Task 1.4: #1+#2+#3 重构 max_buy_price ⭐
- [ ] 安全垫量纲明确标注为概率空间
- [ ] calculate_max_buy_price() 接收 market_best_ask 参数
- [ ] time_decay_factor(time_remaining) 方法已实现
- [ ] 新公式正确：max_buy = best_ask × (1 - cushion) × decay
- [ ] clamp 到 [0.01, 0.99]
- [ ] SafetyCushionCalculator 同名方法同步更新或删除
- [ ] generate_signal() 调用链传入正确参数
- [ ] 单元测试 ≥ 30 个，覆盖各种价格/时间组合

### Task 1.5: #4 置信度归一化重写
- [ ] 使用 Sigmoid 替代硬编码系数
- [ ] normalize_slope() 使用 Sigmoid(50×(|K|-0.02))
- [ ] normalize_difference() 使用 Sigmoid(0.02×(diff-15))
- [ ] 典型值落在 [0.3, 0.7] 区间内
- [ ] 单元测试验证归一化区分度明显提升

### Task 1.6: #7 时间驱动的价格限制
- [ ] get_max_buy_price_limit(time_remaining, confidence) 新签名
- [ ] 时间阶梯：>80s→0.75, >40s→0.85, >15s→0.90, else→0.93
- [ ] 置信度微调 ±0.02
- [ ] 最终 clamp 到 [0.60, 0.98]

### Task 1.7: #5 统一 TradingSignal
- [ ] signal_generator.py 使用 shared.models.TradingSignal
- [ ] redis_subscriber.py 使用 shared.models.TradingSignal
- [ ] 两处旧定义已删除
- [ ] to_dict() 输出包含执行所需字段
- [ ] from_dict() 兼容新格式
- [ ] validate() 通过率 100%
- [ ] 集成测试验证信号格式兼容性

### Task 1.8: #6 集成 MarketDiscovery ⭐
- [ ] strategy_engine/main.py 初始化 MarketDiscovery
- [ ] generate_signal() 后经 SignalAdapter 转换
- [ ] 发布的信号含完整 token_id/market_id/side/size
- [ ] order_executor 接收并 validate 通过
- [ ] 端到端集成测试通过（mock MarketDiscovery）

### Task 1.9: #11 集成 RiskManager
- [ ] OrderManager 初始化 RiskManager
- [ ] create_order()/place_order() 前调用 check_before_order()
- [ ] 风控不通过时拒绝下单并记录日志
- [ ] OrderResult 包含风险检查结果
- [ ] 单元测试 ≥ 25 个覆盖各种风控场景

### Task 1.10: #12+#13 StopLossMonitor + 反馈闭环
- [ ] StopLossMonitor 已集成启动
- [ ] 使用 PositionTracker 获取持仓
- [ ] strategy_engine 订阅 TRADE_RESULT_CHANNEL
- [ ] 收到结果后更新 PositionTracker
- [ ] generate_signal() 检查 pending 信号避免重复
- [ ] 集成测试验证反馈闭环

### Task 1.11: 配置与参数注册表更新
- [ ] settings.yaml 含 market_discovery 配置段
- [ ] settings.yaml risk_management 有详细注释
- [ ] parameter_registry.py 注册 ~15 个新参数
- [ ] config_validator.py 含新参数规则
- [ ] config_wizard.py 支持新参数交互收集

---

## Phase 2: 测试验证

- [ ] T2.1: MarketDiscovery 单元测试 ≥ 25 个全通过
- [ ] T2.2: SignalAdapter 单元测试 ≥ 20 个全通过
- [ ] T2.3: RiskManager 单元测试 ≥ 30 个全通过
- [ ] T2.4: StopLossMonitor 单元测试 ≥ 20 个全通过
- [ ] T2.5: PositionTracker 单元测试 ≥ 25 个全通过
- [ ] T2.6: 端到端信号流集成测试通过
- [ ] T2.7: 周期切换数据隔离集成测试通过
- [ ] T2.8: 现有 335+ 测试无回归

---

## Phase 3: 文档更新

- [ ] T3.1: USER_GUIDE.md 第 3 章反映修复后策略逻辑
- [ ] T3.2: USER_GUIDE.md 第 5 章含新模块参数说明
- [ ] T3.3: parameter_registry.py 元数据完整

---

## 综合验收标准

### 功能验收
- [ ] 策略引擎发出的信号能成功到达订单执行器并被正确处理
- [ ] 信号包含正确的 token_id（来自 MarketDiscovery）
- [ ] max_buy_price 在合理范围内（非恒定 0.99）
- [ ] determine_action() 包含安全垫比较逻辑
- [ ] 周期切换时 PriceQueue 被清空
- [ ] 风控检查在下单前执行
- [ ] 止损/止盈在阈值触发时自动执行
- [ ] 策略引擎能感知已执行信号避免重复下单
- [ ] 置信度在不同输入下有明显区分

### 性能验收
- [ ] OLS 回归延迟 < 15ms
- [ ] 信号端到端延迟 < 50ms
- [ ] MarketDiscovery 缓存命中 < 5ms
- [ ] 风控检查开销 < 2ms

### 测试验收
- [ ] 新增测试 ≥ 150 个
- [ ] 现有测试无回归
- [ ] 集成测试覆盖完整信号链路

**最终结论**: 全部 Check 完成后 → **生产就绪度从 2/10 提升至 8+/10**
