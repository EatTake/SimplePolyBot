"""
参数元数据系统

提供参数的完整元数据描述，包括类型、范围、默认值、建议值等，
用于配置验证、文档生成、UI 表单渲染等场景。
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParameterInfo:
    key: str
    name: str
    description: str
    type: type
    default: Any
    range: Optional[tuple] = None
    choices: Optional[list] = None
    required: bool = False
    sensitive: bool = False
    category: str = "general"
    level: str = "standard"
    suggestions: dict = field(default_factory=dict)
    depends_on: Optional[list] = None
    validation_hint: str = ""


class ParameterRegistry:
    _instance = None
    _parameters: dict[str, ParameterInfo] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._parameters = {}
        self._initialized = True

    def register(self, info: ParameterInfo) -> None:
        self._parameters[info.key] = info

    def get(self, key: str) -> Optional[ParameterInfo]:
        return self._parameters.get(key)

    def get_all(self, category: str = None) -> list[ParameterInfo]:
        if category:
            return [p for p in self._parameters.values() if p.category == category]
        return list(self._parameters.values())

    def get_required(self) -> list[ParameterInfo]:
        return [p for p in self._parameters.values() if p.required]

    def get_sensitive(self) -> list[ParameterInfo]:
        return [p for p in self._parameters.values() if p.sensitive]

    def get_by_level(self, level: str) -> list[ParameterInfo]:
        return [p for p in self._parameters.values() if p.level == level]

    @classmethod
    def get_instance(cls) -> 'ParameterRegistry':
        return cls()


def _register_strategy_params(registry: ParameterRegistry) -> None:
    registry.register(ParameterInfo(
        key="strategy.base_cushion",
        name="基础缓冲值 (Base Cushion)",
        description="用于计算买入价格的安全缓冲，公式：买入价格 = 当前价格 - Base Cushion。值越大，买入价格越保守。",
        type=float,
        default=0.02,
        range=(0.0, 1.0),
        category="strategy",
        level="core",
        suggestions={"conservative": 0.05, "default": 0.02, "aggressive": 0.01},
        validation_hint="建议范围 0.01-0.10，过大会导致错失交易机会",
    ))
    registry.register(ParameterInfo(
        key="strategy.alpha",
        name="Alpha 价格调整系数",
        description="动态调整买入价格的系数，与市场波动性相关。高波动市场应使用较低的 alpha 值以降低风险敞口。",
        type=float,
        default=0.5,
        range=(0.0, 1.0),
        category="strategy",
        level="core",
        suggestions={"conservative": 0.3, "default": 0.5, "aggressive": 0.7},
        validation_hint="范围 0.0-1.0，建议根据市场波动率调整",
    ))
    registry.register(ParameterInfo(
        key="strategy.max_buy_prices.default",
        name="默认最大买入价格",
        description="所有市场的通用最大买入价格上限（占代币面值的比例），超过此价格将不会执行买单。",
        type=float,
        default=0.95,
        range=(0.0, 1.0),
        category="strategy",
        level="core",
        suggestions={"conservative": 0.85, "default": 0.95, "aggressive": 0.98},
        validation_hint="不应设置为 1.0，需留有利润空间",
    ))
    registry.register(ParameterInfo(
        key="strategy.max_buy_prices.high_confidence",
        name="高置信度最大买入价格",
        description="当策略信号置信度较高时允许的最大买入价格。适用于信号来源可靠、历史准确率高的场景。",
        type=float,
        default=0.98,
        range=(0.0, 1.0),
        category="strategy",
        level="advanced",
        suggestions={"conservative": 0.92, "default": 0.98, "aggressive": 0.99},
        depends_on=["strategy.max_buy_prices.default"],
        validation_hint="应大于等于默认最大买入价格",
    ))
    registry.register(ParameterInfo(
        key="strategy.max_buy_prices.low_volatility",
        name="低波动市场最大买入价格",
        description="在低波动市场中允许的最大买入价格。低波动市场风险较低，可适当放宽价格限制。",
        type=float,
        default=0.92,
        range=(0.0, 1.0),
        category="strategy",
        level="advanced",
        suggestions={"conservative": 0.88, "default": 0.92, "aggressive": 0.96},
        depends_on=["strategy.max_buy_prices.default"],
        validation_hint="低波动市场仍需保持谨慎，避免追高",
    ))
    registry.register(ParameterInfo(
        key="strategy.max_buy_prices.fast_market",
        name="快速市场最大买入价格",
        description="针对 Fast Market（如 5 分钟 BTC 涨跌）的最大买入价格限制。快速市场结算周期短，风险更高。",
        type=float,
        default=0.90,
        range=(0.0, 1.0),
        category="strategy",
        level="expert",
        suggestions={"conservative": 0.80, "default": 0.90, "aggressive": 0.94},
        depends_on=["strategy.max_buy_prices.default"],
        validation_hint="快速市场流动性差、滑点大，应设置更严格的限制",
    ))
    registry.register(ParameterInfo(
        key="strategy.order_sizes.default",
        name="默认订单大小",
        description="每笔交易的默认下单金额（USDC），直接影响单笔交易的风险敞口和资金利用率。",
        type=int,
        default=100,
        range=(10, 10000),
        category="strategy",
        level="core",
        suggestions={"conservative": 50, "default": 100, "aggressive": 500},
        validation_hint="应根据账户总资金按比例设定，通常不超过资金的 5%",
    ))
    registry.register(ParameterInfo(
        key="strategy.order_sizes.min",
        name="最小订单大小",
        description="允许的最小下单金额（USDC）。低于此值的订单将被拒绝，避免无效的小额交易消耗手续费。",
        type=int,
        default=10,
        range=(1, 10000),
        category="strategy",
        level="standard",
        suggestions={"conservative": 20, "default": 10, "aggressive": 5},
        depends_on=["strategy.order_sizes.default", "strategy.order_sizes.max"],
        validation_hint="必须小于等于默认订单大小和最大订单大小",
    ))
    registry.register(ParameterInfo(
        key="strategy.order_sizes.max",
        name="最大订单大小",
        description="允许的最大下单金额（USDC）。超过此值的订单将被拆分或拒绝，防止单笔交易过度集中风险。",
        type=int,
        default=1000,
        range=(10, 100000),
        category="strategy",
        level="standard",
        suggestions={"conservative": 500, "default": 1000, "aggressive": 5000},
        depends_on=["strategy.order_sizes.default", "strategy.order_sizes.min"],
        validation_hint="必须大于等于默认订单大小和最小订单大小",
    ))
    registry.register(ParameterInfo(
        key="strategy.risk_management.max_position_size",
        name="单市场最大持仓",
        description="单个预测市场中允许持有的最大仓位金额（USDC），防止过度集中于单一市场。",
        type=int,
        default=5000,
        range=(100, 100000),
        category="strategy",
        level="core",
        suggestions={"conservative": 2000, "default": 5000, "aggressive": 10000},
        validation_hint="建议不超过总资金的 20-30%",
    ))
    registry.register(ParameterInfo(
        key="strategy.risk_management.max_total_exposure",
        name="总风险敞口上限",
        description="所有持仓的总金额上限（USDC）。达到此限制后不再开新仓，是资金安全的第一道防线。",
        type=int,
        default=20000,
        range=(1000, 500000),
        category="strategy",
        level="core",
        suggestions={"conservative": 10000, "default": 20000, "aggressive": 50000},
        validation_hint="应始终低于账户可用余额",
    ))
    registry.register(ParameterInfo(
        key="strategy.risk_management.max_daily_loss",
        name="日最大亏损限额",
        description="每日允许的最大亏损金额（USDC）。触发后当日停止所有交易操作，防止连续亏损扩大损失。",
        type=int,
        default=500,
        range=(50, 50000),
        category="strategy",
        level="core",
        suggestions={"conservative": 200, "default": 500, "aggressive": 2000},
        validation_hint="建议设为总资金的 1-5%",
    ))
    registry.register(ParameterInfo(
        key="strategy.risk_management.max_drawdown",
        name="最大回撤比例",
        description="从账户峰值允许的最大回撤比例。超出此阈值将触发风控熔断，暂停所有交易直至人工确认。",
        type=float,
        default=0.15,
        range=(0.05, 0.5),
        category="strategy",
        level="core",
        suggestions={"conservative": 0.08, "default": 0.15, "aggressive": 0.25},
        validation_hint="专业量化团队通常控制在 10-20%",
    ))
    registry.register(ParameterInfo(
        key="strategy.risk_management.min_balance",
        name="最小保留余额",
        description="账户中必须保留的最小 USDC 余额，不参与交易。作为应急储备金应对极端行情。",
        type=int,
        default=100,
        range=(10, 10000),
        category="strategy",
        level="standard",
        suggestions={"conservative": 500, "default": 100, "aggressive": 50},
        validation_hint="至少覆盖可能的 Gas 费用和手续费",
    ))
    registry.register(ParameterInfo(
        key="strategy.stop_loss_take_profit.enabled",
        name="止损止盈功能开关",
        description="是否启用自动止损止盈机制。开启后系统会根据预设比例自动平仓，无需人工干预。",
        type=bool,
        default=True,
        category="strategy",
        level="standard",
        suggestions={},
        validation_hint="生产环境强烈建议开启",
    ))
    registry.register(ParameterInfo(
        key="strategy.stop_loss_take_profit.stop_loss_percentage",
        name="止损比例",
        description="触发自动止损的价格下跌百分比。当持仓浮亏达到此比例时，系统自动卖出止损离场。",
        type=float,
        default=0.10,
        range=(0.02, 0.5),
        category="strategy",
        level="standard",
        suggestions={"conservative": 0.05, "default": 0.10, "aggressive": 0.20},
        depends_on=["strategy.stop_loss_take_profit.enabled"],
        validation_hint="需配合止盈比例综合考虑风险收益比",
    ))
    registry.register(ParameterInfo(
        key="strategy.stop_loss_take_profit.take_profit_percentage",
        name="止盈比例",
        description="触发自动止盈的价格上涨百分比。当持仓盈利达到此比例时，系统自动卖出锁定利润。",
        type=float,
        default=0.20,
        range=(0.05, 0.8),
        category="strategy",
        level="standard",
        suggestions={"conservative": 0.10, "default": 0.20, "aggressive": 0.40},
        depends_on=["strategy.stop_loss_take_profit.enabled"],
        validation_hint="建议止盈/止损比不低于 2:1 以保证正期望收益",
    ))


def _register_market_discovery_params(registry: ParameterRegistry) -> None:
    registry.register(ParameterInfo(
        key="strategy.market_discovery.enabled",
        name="市场发现模块开关",
        description="控制市场发现模块是否启用。启用后自动扫描并发现符合条件的 Fast Market 市场。",
        type=bool,
        default=True,
        category="market_discovery",
        level="core",
        validation_hint="Fast Market 策略必须开启此模块",
    ))
    registry.register(ParameterInfo(
        key="strategy.market_discovery.gamma_api_url",
        name="Gamma API 地址",
        description="Polymarket Gamma API 的基础 URL，用于查询市场列表、事件信息、标签过滤等。",
        type=str,
        default="https://gamma-api.polymarket.com",
        required=True,
        category="market_discovery",
        level="core",
        validation_hint="使用官方 API 地址，生产环境可通过环境变量覆盖",
    ))
    registry.register(ParameterInfo(
        key="strategy.market_discovery.clob_api_url",
        name="CLOB API 地址",
        description="Polymarket CLOB API 的基础 URL，用于获取订单簿深度、交易量等实时数据。",
        type=str,
        default="https://clob.polymarket.com",
        required=True,
        category="market_discovery",
        level="core",
        validation_hint="使用官方 CLOB 地址，生产环境可通过环境变量覆盖",
    ))
    registry.register(ParameterInfo(
        key="strategy.market_discovery.cache_ttl",
        name="缓存生存时间 (TTL)",
        description="市场发现结果的缓存时间（秒）。在此时间内重复查询将返回缓存结果，减少 API 调用频率。",
        type=int,
        default=300,
        range=(60, 3600),
        category="market_discovery",
        level="standard",
        suggestions={"low_frequency": 600, "default": 300, "high_frequency": 120},
        validation_hint="建议范围 60-3600 秒，过短会增加 API 压力，过长会导致数据滞后",
    ))
    registry.register(ParameterInfo(
        key="strategy.market_discovery.slug_prefix",
        name="市场 Slug 前缀过滤",
        description="用于筛选目标市场的 slug 前缀模式。只有 slug 匹配此前缀的市场才会被策略引擎处理。",
        type=str,
        default="btc-updown-5m",
        required=False,
        category="market_discovery",
        level="standard",
        choices=["btc-updown-5m", "btc-updown-15m", "btc-updown-1h"],
        validation_hint="确保前缀与 Gamma API 中实际的市场 slug 格式一致",
    ))
    registry.register(ParameterInfo(
        key="strategy.market_discovery.refresh_interval",
        name="市场刷新间隔",
        description="定时刷新活跃市场列表的间隔时间（秒）。控制市场发现模块扫描新市场的频率。",
        type=int,
        default=60,
        range=(30, 300),
        category="market_discovery",
        level="standard",
        suggestions={"slow": 120, "default": 60, "fast": 30},
        validation_hint="建议范围 30-300 秒，Fast Market 每 5 分钟滚动一次，60 秒较合理",
    ))


def _register_signal_adapter_params(registry: ParameterRegistry) -> None:
    registry.register(ParameterInfo(
        key="signal_adapter.default_size",
        name="信号适配器默认订单大小",
        description="信号适配器将策略信号转换为订单时的默认下单金额（USDC），当无法从 size_map 匹配时使用此值。",
        type=int,
        default=100,
        range=(10, 10000),
        category="signal_adapter",
        level="core",
        suggestions={"conservative": 50, "default": 100, "aggressive": 500},
        validation_hint="应与 strategy.order_sizes.default 保持一致或略小",
    ))
    registry.register(ParameterInfo(
        key="signal_adapter.min_size",
        name="信号适配器最小订单大小",
        description="信号适配器允许的最小下单金额（USDC）。低于此值的信号将被忽略或合并。",
        type=int,
        default=10,
        range=(1, 5000),
        category="signal_adapter",
        level="standard",
        suggestions={"conservative": 25, "default": 10, "aggressive": 5},
        depends_on=["signal_adapter.default_size", "signal_adapter.max_size"],
        validation_hint="必须小于等于 default_size 和 max_size",
    ))
    registry.register(ParameterInfo(
        key="signal_adapter.max_size",
        name="信号适配器最大订单大小",
        description="信号适配器允许的最大下单金额（USDC）。超过此值的信号将被拆分或截断。",
        type=int,
        default=1000,
        range=(100, 50000),
        category="signal_adapter",
        level="standard",
        suggestions={"conservative": 500, "default": 1000, "aggressive": 5000},
        depends_on=["signal_adapter.default_size", "signal_adapter.min_size"],
        validation_hint="必须大于等于 default_size 和 min_size",
    ))
    registry.register(ParameterInfo(
        key="signal_adapter.size_map",
        name="信号强度到订单大小映射表",
        description="根据策略信号置信度/强度映射到不同订单大小的配置字典。格式: {\"high\": 500, \"medium\": 200, \"low\": 50}",
        type=dict,
        default={"high": 500, "medium": 200, "low": 50},
        category="signal_adapter",
        level="advanced",
        validation_hint="复杂类型，键为信号等级字符串，值为正整数 USDC 金额",
    ))


def _register_stop_loss_monitor_params(registry: ParameterRegistry) -> None:
    registry.register(ParameterInfo(
        key="stop_loss_monitor.enabled",
        name="止损监控器独立开关",
        description="止损监控器模块的独立启用开关。即使全局 stop_loss_take_profit.enabled 为 true，也可单独关闭此监控器。",
        type=bool,
        default=True,
        category="risk_control",
        level="standard",
        depends_on=["strategy.stop_loss_take_profit.enabled"],
        validation_hint="依赖全局止损止盈开关，两者都为 true 时才生效",
    ))
    registry.register(ParameterInfo(
        key="stop_loss_monitor.check_interval",
        name="止损检查间隔",
        description="止损监控器扫描持仓并评估止损/止盈条件的间隔时间（秒）。越频繁则响应越快但资源消耗越大。",
        type=int,
        default=30,
        range=(5, 300),
        category="risk_control",
        level="standard",
        suggestions={"realtime": 10, "default": 30, "relaxed": 60},
        validation_hint="Fast Market 建议 10-30 秒，普通市场可放宽至 60 秒",
    ))
    registry.register(ParameterInfo(
        key="stop_loss_monitor.notification_threshold",
        name="止损通知阈值",
        description="触发通知的最低亏损金额（USDC）。仅当单次止损平仓亏损超过此值时发送告警通知。",
        type=int,
        default=50,
        range=(10, 10000),
        category="risk_control",
        level="advanced",
        suggestions={"sensitive": 20, "default": 50, "tolerant": 200},
        validation_hint="避免过多无效告警，建议设置为 min_order_size 的 2-5 倍",
    ))


def _register_redis_params(registry: ParameterRegistry) -> None:
    registry.register(ParameterInfo(
        key="redis.host",
        name="Redis 主机地址",
        description="Redis 服务器的主机名或 IP 地址。支持 localhost、内网 IP 或域名解析。",
        type=str,
        default="localhost",
        required=True,
        category="connection",
        level="core",
        validation_hint="确保网络可达，生产环境建议使用内网地址",
    ))
    registry.register(ParameterInfo(
        key="redis.port",
        name="Redis 端口号",
        description="Redis 服务监听的 TCP 端口。标准端口为 6379，如使用集群模式可能不同。",
        type=int,
        default=6379,
        range=(1, 65535),
        required=True,
        category="connection",
        level="core",
        validation_hint="确保防火墙已开放该端口",
    ))
    registry.register(ParameterInfo(
        key="redis.password",
        name="Redis 认证密码",
        description="Redis 服务器的认证密码（AUTH 命令使用的密码）。空字符串表示无密码认证。",
        type=str,
        default="",
        sensitive=True,
        category="connection",
        level="core",
        validation_hint="生产环境务必设置强密码并通过环境变量传入",
    ))
    registry.register(ParameterInfo(
        key="redis.db",
        name="Redis 数据库编号",
        description="使用的 Redis 数据库编号（0-15）。不同模块可使用不同数据库隔离数据。",
        type=int,
        default=0,
        range=(0, 15),
        category="connection",
        level="standard",
        validation_hint="开发环境可用默认 0，多租户场景分配不同 db",
    ))
    registry.register(ParameterInfo(
        key="redis.pool.max_connections",
        name="连接池最大连接数",
        description="Redis 连接池中允许创建的最大连接数量。过小会导致请求排队等待，过大则浪费资源。",
        type=int,
        default=50,
        range=(1, 500),
        category="connection",
        level="advanced",
        suggestions={"low_traffic": 10, "default": 50, "high_traffic": 200},
        validation_hint="根据并发量和 QPS 调整，建议通过压测确定最优值",
    ))
    registry.register(ParameterInfo(
        key="redis.pool.min_idle_connections",
        name="连接池最小空闲连接",
        description="连接池中始终保持的最小空闲连接数。预热后可直接使用，减少首次连接延迟。",
        type=int,
        default=5,
        range=(0, 100),
        category="connection",
        level="advanced",
        suggestions={"low_traffic": 2, "default": 5, "high_traffic": 20},
        depends_on=["redis.pool.max_connections"],
        validation_hint="不应超过 max_connections 的 50%",
    ))
    registry.register(ParameterInfo(
        key="redis.pool.connection_timeout",
        name="连接超时时间",
        description="从连接池获取连接的超时时间（秒）。超时后抛出连接获取失败异常。",
        type=int,
        default=5,
        range=(1, 60),
        category="connection",
        level="advanced",
        suggestions={"fast": 3, "default": 5, "slow": 10},
        validation_hint="高并发场景可适当增大，但过长会影响错误反馈速度",
    ))
    registry.register(ParameterInfo(
        key="redis.pool.socket_timeout",
        name="Socket 读写超时",
        description="单个 Redis 操作的 Socket 超时时间（秒）。涵盖发送请求到接收响应的全过程。",
        type=int,
        default=5,
        range=(1, 60),
        category="connection",
        level="advanced",
        suggestions={"fast": 3, "default": 5, "slow": 10},
        validation_hint="批量操作（如 MGET/MSET）应适当增加此值",
    ))
    registry.register(ParameterInfo(
        key="redis.retry.max_attempts",
        name="最大重试次数",
        description="Redis 操作失败后的最大重试次数。超过此次数后将抛出最终异常。",
        type=int,
        default=3,
        range=(0, 10),
        category="connection",
        level="standard",
        suggestions={"critical": 5, "default": 3, "non_critical": 1},
        validation_hint="写操作建议较多重试，读操作可适当减少",
    ))
    registry.register(ParameterInfo(
        key="redis.retry.retry_delay",
        name="重试间隔时间",
        description="每次重试之间的基础等待时间（秒）。配合指数退避使用时为初始延迟。",
        type=int,
        default=1,
        range=(0, 30),
        category="connection",
        level="standard",
        suggestions={"fast": 0.5, "default": 1, "slow": 3},
        depends_on=["redis.retry.exponential_backoff"],
        validation_hint="启用指数退避时此值为首次重试延迟",
    ))
    registry.register(ParameterInfo(
        key="redis.retry.exponential_backoff",
        name="指数退避开关",
        description="是否启用指数退避策略。启用后每次重试延迟翻倍（1s → 2s → 4s...），避免雪崩效应。",
        type=bool,
        default=True,
        category="connection",
        level="standard",
        suggestions={},
        validation_hint="生产环境强烈建议开启",
    ))


def _register_module_params(registry: ParameterRegistry) -> None:
    registry.register(ParameterInfo(
        key="modules.market_data_collector.enabled",
        name="市场数据收集器开关",
        description="控制市场数据收集器模块是否启动。关闭后将无法接收实时市场数据和 WebSocket 推送。",
        type=bool,
        default=True,
        category="module",
        level="core",
        validation_hint="核心模块，除非调试否则不应关闭",
    ))
    registry.register(ParameterInfo(
        key="modules.market_data_collector.websocket.url",
        name="WebSocket 连接地址",
        description="Polymarket CLOB WebSocket Market Channel 的端点 URL，用于订阅实时订单簿和价格更新。",
        type=str,
        default="wss://ws-subscriptions-clob.polymarket.com/ws/market",
        required=True,
        category="module",
        level="core",
        validation_hint="请勿修改，使用官方提供的端点地址",
    ))
    registry.register(ParameterInfo(
        key="modules.strategy_engine.enabled",
        name="策略引擎开关",
        description="控制策略引擎模块是否启动。关闭后不会生成任何交易信号，订单执行器也将无单可下。",
        type=bool,
        default=True,
        category="module",
        level="core",
        validation_hint="核心模块，关闭则整个交易系统停摆",
    ))
    registry.register(ParameterInfo(
        key="modules.order_executor.enabled",
        name="订单执行器开关",
        description="控制订单执行器模块是否启动。关闭后无法向 CLOB 提交订单，已有订单也不会被管理。",
        type=bool,
        default=True,
        category="module",
        level="core",
        validation_hint="核心模块，关闭后无法进行任何交易操作",
    ))
    registry.register(ParameterInfo(
        key="modules.settlement_worker.enabled",
        name="结算工作器开关",
        description="控制结算工作器模块是否启动。关闭后将无法自动检测已结算市场并进行代币赎回操作。",
        type=bool,
        default=True,
        category="module",
        level="standard",
        validation_hint="关闭可能导致已赢取的代币无法及时赎回",
    ))


def _register_api_params(registry: ParameterRegistry) -> None:
    registry.register(ParameterInfo(
        key="api.polymarket.api_key",
        name="Polymarket API Key",
        description="Polymarket CLOB API 密钥标识符，用于 API 请求的身份认证。从 Polymarket 后台生成。",
        type=str,
        default="",
        sensitive=True,
        required=True,
        category="api",
        level="core",
        validation_hint="通过环境变量 POLYMARKET_API_KEY 注入，切勿硬编码",
    ))
    registry.register(ParameterInfo(
        key="api.polymarket.api_secret",
        name="Polymarket API Secret",
        description="Polymarket CLOB API 签名密钥，用于对请求进行 HMAC-SHA256 签名验证。具有最高安全级别。",
        type=str,
        default="",
        sensitive=True,
        required=True,
        category="api",
        level="core",
        validation_hint="通过环境变量 POLYMARKET_API_SECRET 注入，泄露将导致资金风险",
    ))
    registry.register(ParameterInfo(
        key="api.polymarket.api_passphrase",
        name="Polymarket API Passphrase",
        description="Polymarket CLOB API 口令短语，配合密钥一起完成完整的 API 认证流程。",
        type=str,
        default="",
        sensitive=True,
        required=True,
        category="api",
        level="core",
        validation_hint="通过环境变量 POLYMARKET_API_PASSPHRASE 注入",
    ))


def _register_system_params(registry: ParameterRegistry) -> None:
    registry.register(ParameterInfo(
        key="system.environment",
        name="运行环境",
        description="当前系统的运行环境模式。不同环境下日志级别、监控频率、安全检查等行为会有差异。",
        type=str,
        default="development",
        choices=["development", "staging", "production"],
        category="system",
        level="core",
        suggestions={},
        validation_hint="生产环境部署前务必切换为 production",
    ))
    registry.register(ParameterInfo(
        key="system.log_level",
        name="日志级别",
        description="全局日志输出级别。DEBUG 输出最详细信息，CRITICAL 仅输出致命错误。影响日志体积和排查效率。",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        category="system",
        level="core",
        suggestions={},
        validation_hint="生产环境建议 INFO 或 WARNING，排查问题时临时切换 DEBUG",
    ))


def initialize_parameter_registry() -> ParameterRegistry:
    """初始化参数注册表并注册所有参数元数据"""
    registry = ParameterRegistry.get_instance()
    _register_strategy_params(registry)
    _register_market_discovery_params(registry)
    _register_signal_adapter_params(registry)
    _register_stop_loss_monitor_params(registry)
    _register_redis_params(registry)
    _register_module_params(registry)
    _register_api_params(registry)
    _register_system_params(registry)
    return registry
