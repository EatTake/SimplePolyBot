# SimplePolyBot API 文档

## 目录

- [模块概览](#模块概览)
- [共享模块](#共享模块)
- [策略引擎模块](#策略引擎模块)
- [订单执行模块](#订单执行模块)
- [资金结算模块](#资金结算模块)
- [市场数据收集模块](#市场数据收集模块)

---

## 模块概览

SimplePolyBot 采用模块化架构，各模块通过 Redis Pub/Sub 进行通信。

### 模块依赖关系

```
市场数据收集模块 -> Redis (market_data) -> 策略引擎模块
策略引擎模块 -> Redis (trading_signal) -> 订单执行模块
订单执行模块 -> Redis (trade_result) -> 外部系统
资金结算模块 -> Polygon Network -> CTF Contract
```

---

## 共享模块

### 配置管理 (shared.config)

#### Config 类

单例模式的配置管理器。

```python
from shared.config import Config, load_config

# 加载配置
config = load_config(
    env_file=".env",
    config_file="config/settings.yaml",
    validate=True
)

# 获取 Redis 配置
redis_config = config.get_redis_config()
# 返回: RedisConfig(host, port, password, db, ...)

# 获取策略配置
strategy_config = config.get_strategy_config()
# 返回: StrategyConfig(base_cushion, alpha, ...)

# 获取模块配置
module_config = config.get_module_config("strategy_engine")
```

#### RedisConfig

```python
@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    max_connections: int = 50
    min_idle_connections: int = 5
    connection_timeout: int = 5
    socket_timeout: int = 5
    max_attempts: int = 3
    retry_delay: int = 1
```

#### StrategyConfig

```python
@dataclass
class StrategyConfig:
    base_cushion: float = 15.0
    alpha: float = 1.0
    max_buy_prices: Dict[str, float] = field(default_factory=dict)
    order_sizes: Dict[str, float] = field(default_factory=dict)
    risk_management: Dict[str, float] = field(default_factory=dict)
```

### Redis 客户端 (shared.redis_client)

#### RedisClient 类

```python
from shared.redis_client import RedisClient, RedisConnectionConfig

# 创建客户端
config = RedisConnectionConfig(
    host="localhost",
    port=6379,
    password=None,
    db=0,
    max_connections=50
)
client = RedisClient(config)

# 连接
client.connect()

# 发布消息
client.publish_message("market_data", {"price": 67000.0})

# 订阅频道
def message_handler(message):
    print(message)

client.subscribe_channel("trading_signal", message_handler)

# 断开连接
client.disconnect()
```

#### 主要方法

| 方法 | 说明 | 参数 | 返回值 |
|------|------|------|--------|
| `connect()` | 连接 Redis | - | bool |
| `disconnect()` | 断开连接 | - | None |
| `publish_message(channel, message)` | 发布消息 | channel: str, message: Dict | bool |
| `subscribe_channel(channel, callback)` | 订阅频道 | channel: str, callback: Callable | bool |
| `set_value(key, value, expire)` | 设置值 | key: str, value: Any, expire: int | bool |
| `get_value(key)` | 获取值 | key: str | Any |
| `delete_key(key)` | 删除键 | key: str | bool |

### 日志系统 (shared.logger)

```python
from shared.logger import get_logger, setup_logging

# 设置日志
setup_logging(log_level="INFO")

# 获取 logger
logger = get_logger(__name__)

# 记录日志
logger.info("消息", key="value")
logger.error("错误", error=str(e))
```

---

## 策略引擎模块

### 价格队列 (modules.strategy_engine.price_queue)

#### PriceQueue 类

```python
from modules.strategy_engine.price_queue import PriceQueue

queue = PriceQueue(window_seconds=180, max_size=10000)

# 推入价格
queue.push(price=67000.0, timestamp=time.time())

# 获取最新价格
latest = queue.get_latest_price()

# 获取最早价格
earliest = queue.get_earliest_price()

# 获取时间戳和价格数组
timestamps, prices = queue.get_timestamps_and_prices()

# 获取队列大小
size = queue.size()

# 清空队列
queue.clear_queue()
```

#### PricePoint 数据类

```python
@dataclass
class PricePoint:
    price: float
    timestamp: float
```

### OLS 回归 (modules.strategy_engine.ols_regression)

#### OLSRegression 类

```python
from modules.strategy_engine.ols_regression import OLSRegression

regression = OLSRegression(min_samples=10)

# 执行回归
result = regression.fit(timestamps, prices)

# 结果包含
result.slope      # 斜率 K
result.intercept  # 截距
result.r_squared  # R² 值
result.n_samples  # 样本数
```

#### OLSResult 数据类

```python
@dataclass
class OLSResult:
    slope: float
    intercept: float
    r_squared: float
    n_samples: int
```

### 安全垫计算 (modules.strategy_engine.safety_cushion)

#### SafetyCushionCalculator 类

```python
from modules.strategy_engine.safety_cushion import SafetyCushionCalculator

calculator = SafetyCushionCalculator(
    base_cushion=15.0,
    alpha=1.0
)

# 计算安全垫
result = calculator.calculate(
    slope_k=0.5,
    time_remaining_seconds=120.0
)

# 结果包含
result.base_cushion    # 基础安全垫
result.buffer_cushion  # 缓冲安全垫
result.total_cushion   # 总安全垫
```

#### SafetyCushionResult 数据类

```python
@dataclass
class SafetyCushionResult:
    base_cushion: float
    buffer_cushion: float
    total_cushion: float
    slope_k: float
    time_remaining: float
    alpha: float
```

### 信号生成器 (modules.strategy_engine.signal_generator)

#### SignalGenerator 类

```python
from modules.strategy_engine.signal_generator import SignalGenerator

generator = SignalGenerator()

# 生成信号
signal = generator.generate_signal(
    current_price=67500.0,
    start_price=67000.0,
    slope_k=0.5,
    r_squared=0.85,
    time_remaining=120.0
)

# 信号包含
signal.action       # BUY 或 WAIT
signal.direction    # UP 或 DOWN
signal.max_price    # 最大买入价格
signal.confidence   # 置信度
```

#### Signal 数据类

```python
@dataclass
class Signal:
    action: SignalAction          # BUY 或 WAIT
    direction: Optional[SignalDirection]  # UP 或 DOWN
    max_price: Optional[float]
    confidence: float
    timestamp: float
```

### 市场生命周期管理 (modules.strategy_engine.market_lifecycle)

#### MarketLifecycleManager 类

```python
from modules.strategy_engine.market_lifecycle import MarketLifecycleManager

manager = MarketLifecycleManager(cycle_duration=300)

# 获取当前周期
cycle = manager.get_current_cycle()

# 周期包含
cycle.cycle_id          # 周期 ID
cycle.start_time        # 开始时间
cycle.end_time          # 结束时间
cycle.time_remaining    # 剩余时间
cycle.start_price       # 起始价格

# 设置起始价格
manager.set_start_price(67000.0)
```

---

## 订单执行模块

### CLOB 客户端 (modules.order_executor.clob_client)

#### ClobClientWrapper 类

```python
from modules.order_executor.clob_client import ClobClientWrapper

client = ClobClientWrapper()
client.initialize()

# 获取余额
balance = client.get_usdc_balance()

# 获取订单簿
order_book = client.get_order_book(token_id="token_123")

# 创建订单
result = client.create_and_submit_order(
    token_id="token_123",
    price=0.50,
    size=100,
    side="BUY",
    order_type="GTC"
)

# 取消订单
client.cancel_order(order_id="order_123")
```

### 订单管理器 (modules.order_executor.order_manager)

#### OrderManager 类

```python
from modules.order_executor.order_manager import OrderManager

manager = OrderManager(
    clob_client=client,
    fee_calculator=calculator,
    config=config
)

# 执行买入订单
result = manager.execute_buy_order(
    token_id="token_123",
    size=100,
    max_price=0.85,
    category="crypto"
)

# 执行卖出订单
result = manager.execute_sell_order(
    token_id="token_123",
    size=100,
    min_price=0.15,
    category="crypto"
)

# 获取统计信息
stats = manager.get_statistics()
```

#### OrderResult 数据类

```python
@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str]
    status: str
    filled_size: float
    avg_price: float
    fee: float
    error: Optional[str] = None
```

### 费用计算器 (modules.order_executor.fee_calculator)

#### FeeCalculator 类

```python
from modules.order_executor.fee_calculator import FeeCalculator

calculator = FeeCalculator()

# 计算交易费用
fee = calculator.calculate_fee(
    price=0.50,
    size=100,
    side="BUY",
    category="crypto"
)

# 获取费率
rate = calculator.get_fee_rate(category="crypto")
```

---

## 资金结算模块

### CTF 合约交互 (modules.settlement_worker.ctf_contract)

#### CTFContract 类

```python
from modules.settlement_worker.ctf_contract import CTFContract

contract = CTFContract(
    rpc_url="https://polygon-rpc.com",
    private_key="0x..."
)

# 获取账户地址
address = contract.account_address

# 获取余额
balance = contract.get_balance()

# 赎回获胜份额
result = contract.redeem_positions(
    condition_id="condition_123",
    index_sets=[1, 2]
)
```

### 赎回管理器 (modules.settlement_worker.redemption_manager)

#### RedemptionManager 类

```python
from modules.settlement_worker.redemption_manager import RedemptionManager

manager = RedemptionManager(
    ctf_contract=contract,
    config=config
)

# 运行赎回周期
result = await manager.run_redemption_cycle()

# 获取统计信息
stats = manager.get_statistics()
```

---

## 市场数据收集模块

### Binance WebSocket (modules.market_data_collector.binance_ws)

#### BinanceWebSocketClient 类

```python
from modules.market_data_collector.binance_ws import BinanceWebSocketClient

client = BinanceWebSocketClient(
    symbol="btcusdt",
    on_message=message_handler
)

# 启动
client.start()

# 停止
client.stop()
```

---

## Redis 频道消息格式

### market_data 频道

```json
{
  "timestamp": 1234567890123,
  "price": 67234.50,
  "source": "binance"
}
```

### trading_signal 频道

```json
{
  "action": "BUY",
  "direction": "UP",
  "max_price": 0.85,
  "confidence": 0.92,
  "timestamp": 1234567890123,
  "strategy": "ols_momentum"
}
```

### trade_result 频道

```json
{
  "signal_id": "signal_123",
  "token_id": "token_456",
  "market_id": "market_789",
  "order_result": {
    "success": true,
    "order_id": "order_abc",
    "status": "matched",
    "filled_size": 100,
    "avg_price": 0.50,
    "fee": 0.90
  },
  "timestamp": 1234567890123
}
```

---

## 错误处理

### 自定义异常

```python
from shared.redis_client import RedisClientError
from modules.order_executor.clob_client import ClobClientError
from modules.settlement_worker.ctf_contract import CTFContractError
```

### 错误处理示例

```python
try:
    result = client.create_and_submit_order(...)
except ClobClientError as e:
    logger.error("订单创建失败", error=str(e))
except Exception as e:
    logger.error("未知错误", error=str(e))
```

---

## 性能指标

### 目标性能

| 指标 | 目标值 | 实际值 |
|------|--------|--------|
| OLS 回归（小数据集） | < 10ms | < 1ms |
| OLS 回归（中等数据集） | < 50ms | < 5ms |
| 信号生成 | < 5ms | < 1ms |
| 完整策略周期 | < 100ms | < 1ms |
| Redis Pub/Sub 延迟 | < 5ms | < 1ms |

---

## 最佳实践

### 1. 配置管理

- 使用环境变量存储敏感信息
- 定期轮换 API 凭证
- 使用配置验证确保参数正确

### 2. 错误处理

- 捕获并记录所有异常
- 实现重试机制
- 使用断路器模式防止级联失败

### 3. 性能优化

- 使用连接池减少连接开销
- 批量处理消息
- 异步 I/O 操作

### 4. 监控

- 记录关键指标
- 设置告警阈值
- 定期检查日志

---

## 更新日志

### v1.0.0 (2026-04-01)

- ✅ 完成所有核心模块开发
- ✅ 完成单元测试（296+ 测试用例）
- ✅ 完成集成测试（14 测试用例）
- ✅ 完成性能测试（11 测试用例）
- ✅ 完成文档编写
