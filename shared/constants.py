"""
共享常量定义模块

定义系统中使用的所有常量，包括：
- Redis 频道名称
- 合约地址
- WebSocket 端点
- 其他系统常量
"""

from typing import Final


# ==============================================================================
# Redis 频道名称
# ==============================================================================

MARKET_DATA_CHANNEL: Final[str] = "market_data"
"""Redis 频道：市场数据流，用于发布实时市场数据更新"""

TRADING_SIGNAL_CHANNEL: Final[str] = "trading_signal"
"""Redis 频道：交易信号流，用于发布策略引擎生成的交易信号"""

TRADE_RESULT_CHANNEL: Final[str] = "trade_result"
"""Redis 频道：交易结果流，用于发布订单执行结果"""

ORDER_BOOK_CHANNEL: Final[str] = "order_book"
"""Redis 频道：订单簿更新流，用于发布订单簿变化"""

PRICE_UPDATE_CHANNEL: Final[str] = "price_update"
"""Redis 频道：价格更新流，用于发布 BTC 价格变化"""


# ==============================================================================
# Polymarket 合约地址 (Polygon Mainnet - Chain ID: 137)
# ==============================================================================

CTF_EXCHANGE_ADDRESS: Final[str] = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
"""CTF Exchange 合约地址：标准市场订单匹配和结算"""

NEG_RISK_CTF_EXCHANGE_ADDRESS: Final[str] = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
"""Neg Risk CTF Exchange 合约地址：多结果市场订单匹配"""

CTF_CONTRACT_ADDRESS: Final[str] = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
"""Conditional Tokens Framework 合约地址：ERC1155 代币存储，用于 split/merge/redeem 操作"""

USDC_E_ADDRESS: Final[str] = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
"""USDC.e (Bridged USDC) 合约地址：Polymarket 交易抵押代币（6 decimals）"""

NEG_RISK_ADAPTER_ADDRESS: Final[str] = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
"""Neg Risk Adapter 合约地址：在多结果市场之间转换 No 代币"""

UMA_ADAPTER_ADDRESS: Final[str] = "0x6A9D222616C90FcA5754cd1333cFD9b7fb6a4F74"
"""UMA Adapter 合约地址：连接 Polymarket 和 UMA Optimistic Oracle"""

UMA_OPTIMISTIC_ORACLE_ADDRESS: Final[str] = "0xCB1822859cEF82Cd2Eb4E6276C7916e692995130"
"""UMA Optimistic Oracle 合约地址：处理市场解析提案和争议"""


# ==============================================================================
# WebSocket 端点
# ==============================================================================

POLYMARKET_RTDS_URL: Final[str] = "wss://ws-live-data.polymarket.com"
"""Polymarket Real-Time Data Socket 端点：实时评论、加密货币价格、股票价格"""

POLYMARKET_MARKET_WS_URL: Final[str] = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
"""Polymarket Market Channel WebSocket 端点：订单簿、价格变化、交易执行"""

POLYMARKET_USER_WS_URL: Final[str] = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
"""Polymarket User Channel WebSocket 端点：用户订单、持仓、交易更新"""

BINANCE_WS_URL: Final[str] = "wss://stream.binance.com/ws"
"""Binance WebSocket 端点：实时 BTC/USDT 价格数据（用于 Fast Markets）"""

BINANCE_BTCUSDT_STREAM: Final[str] = "btcusdt@ticker"
"""Binance BTC/USDT 行情流：实时价格和交易量数据"""


# ==============================================================================
# API 端点
# ==============================================================================

POLYMARKET_CLOB_API_URL: Final[str] = "https://clob.polymarket.com"
"""Polymarket CLOB API 端点：订单提交、取消、查询"""

POLYMARKET_GAMMA_API_URL: Final[str] = "https://gamma-api.polymarket.com"
"""Polymarket Gamma API 端点：市场数据、事件查询、标签过滤"""

POLYMARKET_DATA_API_URL: Final[str] = "https://data-api.polymarket.com"
"""Polymarket Data API 端点：用户持仓、交易历史、排行榜"""

POLYGON_RPC_URL: Final[str] = "https://polygon-rpc.com"
"""Polygon RPC 端点：区块链交互（可配置为其他 RPC 提供商）"""


# ==============================================================================
# 区块链常量
# ==============================================================================

POLYGON_CHAIN_ID: Final[int] = 137
"""Polygon Mainnet Chain ID"""

POLYGON_BLOCK_TIME_SECONDS: Final[float] = 2.0
"""Polygon 平均出块时间（秒）"""

USDC_E_DECIMALS: Final[int] = 6
"""USDC.e 代币精度"""

CTF_DECIMALS: Final[int] = 18
"""Conditional Tokens 代币精度"""


# ==============================================================================
# 订单相关常量
# ==============================================================================

DEFAULT_TICK_SIZE: Final[str] = "0.01"
"""默认价格最小变动单位"""

MIN_ORDER_SIZE: Final[float] = 1.0
"""最小订单大小（USDC.e）"""

MAX_ORDER_SIZE: Final[float] = 10000.0
"""单笔订单最大金额（USDC.e）"""

DEFAULT_ORDER_TYPE: Final[str] = "GTC"
"""默认订单类型：Good-Til-Cancelled"""

ORDER_EXPIRY_BUFFER_SECONDS: Final[int] = 300
"""GTD 订单过期缓冲时间（秒）：订单在市场结束前 5 分钟自动过期"""


# ==============================================================================
# 队列与缓冲区常量
# ==============================================================================

ORDER_BOOK_DEPTH: Final[int] = 20
"""订单簿深度：保留的买卖盘档位数量"""

PRICE_HISTORY_LENGTH: Final[int] = 1000
"""价格历史长度：保留的历史价格数据点数"""

ORDER_QUEUE_MAX_SIZE: Final[int] = 100
"""订单队列最大长度：待处理订单缓冲区大小"""

WEBSOCKET_MESSAGE_QUEUE_SIZE: Final[int] = 1000
"""WebSocket 消息队列大小：消息缓冲区大小"""

REDIS_CONNECTION_POOL_SIZE: Final[int] = 10
"""Redis 连接池大小"""


# ==============================================================================
# 时间窗口常量
# ==============================================================================

FAST_MARKET_DURATION_SECONDS: Final[int] = 300
"""Fast Market 持续时间（秒）：5 分钟市场"""

FAST_MARKET_ROLLING_INTERVAL_SECONDS: Final[int] = 300
"""Fast Market 滚动间隔（秒）：每 5 分钟创建新市场"""

PRICE_UPDATE_INTERVAL_MS: Final[int] = 1000
"""价格更新间隔（毫秒）：BTC 价格刷新频率"""

ORDER_BOOK_UPDATE_INTERVAL_MS: Final[int] = 500
"""订单簿更新间隔（毫秒）：订单簿刷新频率"""

HEARTBEAT_INTERVAL_SECONDS: Final[int] = 10
"""WebSocket 心跳间隔（秒）：Market/User Channel"""

SPORTS_HEARTBEAT_INTERVAL_SECONDS: Final[int] = 5
"""Sports Channel 心跳间隔（秒）：服务器发送 ping"""

SPORTS_HEARTBEAT_TIMEOUT_SECONDS: Final[int] = 10
"""Sports Channel 心跳超时（秒）：客户端必须在 10 秒内响应 pong"""

RECONNECT_DELAY_MIN_SECONDS: Final[int] = 1
"""WebSocket 重连最小延迟（秒）"""

RECONNECT_DELAY_MAX_SECONDS: Final[int] = 16
"""WebSocket 重连最大延迟（秒）"""


# ==============================================================================
# 风险控制常量
# ==============================================================================

MAX_POSITION_SIZE: Final[float] = 5000.0
"""单市场最大持仓（USDC.e）"""

MAX_TOTAL_EXPOSURE: Final[float] = 20000.0
"""总风险敞口上限（USDC.e）"""

MAX_DAILY_LOSS: Final[float] = 1000.0
"""日最大亏损（USDC.e）"""

MAX_DRAWDOWN_PERCENT: Final[float] = 0.10
"""最大回撤比例：10%"""

MIN_BALANCE_RESERVE: Final[float] = 100.0
"""最小保留余额（USDC.e）"""

MIN_PROFIT_THRESHOLD: Final[float] = 0.02
"""最小盈利阈值：2%（用于套利策略）"""

MIN_SPREAD_THRESHOLD: Final[float] = 0.01
"""最小价差阈值：1%（用于做市策略）"""


# ==============================================================================
# 策略相关常量
# ==============================================================================

MOMENTUM_WINDOW_SECONDS: Final[int] = 60
"""动量计算窗口（秒）：用于趋势跟踪策略"""

VOLATILITY_WINDOW_SECONDS: Final[int] = 300
"""波动率计算窗口（秒）：用于风险评估"""

MOVING_AVERAGE_SHORT_PERIOD: Final[int] = 20
"""短期移动平均周期"""

MOVING_AVERAGE_LONG_PERIOD: Final[int] = 50
"""长期移动平均周期"""

EDGE_THRESHOLD: Final[float] = 0.05
"""边际优势阈值：5%（用于 Fast Market 策略）"""

SIGNAL_CONFIDENCE_THRESHOLD: Final[float] = 0.7
"""信号置信度阈值：70%"""


# ==============================================================================
# 日志与监控常量
# ==============================================================================

LOG_MAX_BYTES: Final[int] = 10 * 1024 * 1024
"""单个日志文件最大大小：10 MB"""

LOG_BACKUP_COUNT: Final[int] = 5
"""日志文件备份数量"""

METRICS_EXPORT_INTERVAL_SECONDS: Final[int] = 60
"""指标导出间隔（秒）"""

HEALTH_CHECK_INTERVAL_SECONDS: Final[int] = 30
"""健康检查间隔（秒）"""


# ==============================================================================
# 重试与超时常量
# ==============================================================================

API_REQUEST_TIMEOUT_SECONDS: Final[int] = 30
"""API 请求超时（秒）"""

ORDER_SUBMISSION_TIMEOUT_SECONDS: Final[int] = 10
"""订单提交超时（秒）"""

MAX_RETRY_ATTEMPTS: Final[int] = 3
"""最大重试次数"""

RETRY_DELAY_BASE_SECONDS: Final[float] = 1.0
"""重试延迟基数（秒）：指数退避基础延迟"""


# ==============================================================================
# 市场类型常量
# ==============================================================================

MARKET_TYPE_BINARY: Final[str] = "binary"
"""市场类型：二元市场（Yes/No）"""

MARKET_TYPE_MULTI_OUTCOME: Final[str] = "multi_outcome"
"""市场类型：多结果市场"""

MARKET_TYPE_SPORTS: Final[str] = "sports"
"""市场类型：体育市场"""

MARKET_TYPE_FAST: Final[str] = "fast"
"""市场类型：快速结算市场（如 5 分钟 BTC 市场）"""


# ==============================================================================
# 订单状态常量
# ==============================================================================

ORDER_STATUS_LIVE: Final[str] = "live"
"""订单状态：订单在订单簿上"""

ORDER_STATUS_MATCHED: Final[str] = "matched"
"""订单状态：订单立即匹配"""

ORDER_STATUS_DELAYED: Final[str] = "delayed"
"""订单状态：可匹配订单被延迟（体育市场）"""

ORDER_STATUS_UNMATCHED: Final[str] = "unmatched"
"""订单状态：延迟后仍未匹配"""


# ==============================================================================
# 交易状态常量
# ==============================================================================

TRADE_STATUS_MATCHED: Final[str] = "MATCHED"
"""交易状态：交易匹配，等待链上提交"""

TRADE_STATUS_MINED: Final[str] = "MINED"
"""交易状态：交易已打包进区块"""

TRADE_STATUS_CONFIRMED: Final[str] = "CONFIRMED"
"""交易状态：交易已确认（终态）"""

TRADE_STATUS_RETRYING: Final[str] = "RETRYING"
"""交易状态：交易失败，重试中"""

TRADE_STATUS_FAILED: Final[str] = "FAILED"
"""交易状态：交易永久失败（终态）"""


# ==============================================================================
# 订单类型常量
# ==============================================================================

ORDER_TYPE_GTC: Final[str] = "GTC"
"""订单类型：Good-Til-Cancelled，一直挂单直到成交或取消"""

ORDER_TYPE_GTD: Final[str] = "GTD"
"""订单类型：Good-Til-Date，指定时间自动过期"""

ORDER_TYPE_FOK: Final[str] = "FOK"
"""订单类型：Fill-Or-Kill，全部成交或全部取消"""

ORDER_TYPE_FAK: Final[str] = "FAK"
"""订单类型：Fill-And-Kill，部分成交后取消剩余"""


# ==============================================================================
# 订单方向常量
# ==============================================================================

ORDER_SIDE_BUY: Final[str] = "BUY"
"""订单方向：买入"""

ORDER_SIDE_SELL: Final[str] = "SELL"
"""订单方向：卖出"""


# ==============================================================================
# 签名类型常量
# ==============================================================================

SIGNER_TYPE_EOA: Final[int] = 0
"""签名类型：EOA (Type 0) - 标准以太坊钱包，用户支付 Gas"""

SIGNER_TYPE_POLY_PROXY: Final[int] = 1
"""签名类型：POLY_PROXY (Type 1) - Polymarket Magic Link 用户"""

SIGNER_TYPE_GNOSIS_SAFE: Final[int] = 2
"""签名类型：GNOSIS_SAFE (Type 2) - Gnosis Safe 多签钱包"""


# ==============================================================================
# 环境变量名称常量
# ==============================================================================

ENV_POLYMARKET_API_KEY: Final[str] = "POLYMARKET_API_KEY"
"""环境变量：Polymarket API Key"""

ENV_POLYMARKET_API_SECRET: Final[str] = "POLYMARKET_API_SECRET"
"""环境变量：Polymarket API Secret"""

ENV_POLYMARKET_API_PASSPHRASE: Final[str] = "POLYMARKET_API_PASSPHRASE"
"""环境变量：Polymarket API Passphrase"""

ENV_PRIVATE_KEY: Final[str] = "PRIVATE_KEY"
"""环境变量：钱包私钥"""

ENV_WALLET_ADDRESS: Final[str] = "WALLET_ADDRESS"
"""环境变量：钱包地址"""

ENV_REDIS_HOST: Final[str] = "REDIS_HOST"
"""环境变量：Redis 主机地址"""

ENV_REDIS_PORT: Final[str] = "REDIS_PORT"
"""环境变量：Redis 端口"""

ENV_REDIS_PASSWORD: Final[str] = "REDIS_PASSWORD"
"""环境变量：Redis 密码"""

ENV_REDIS_DB: Final[str] = "REDIS_DB"
"""环境变量：Redis 数据库编号"""

ENV_POLYGON_RPC_URL: Final[str] = "POLYGON_RPC_URL"
"""环境变量：Polygon RPC URL"""
