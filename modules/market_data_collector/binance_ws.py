"""
Binance WebSocket 客户端

连接 Binance WebSocket 获取 BTC/USDT 实时交易数据
"""

import asyncio
import json
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import websockets
from websockets.client import WebSocketClientProtocol

from shared.logger import get_logger
from shared.constants import BINANCE_WS_URL

logger = get_logger(__name__)


@dataclass
class BinanceTradeData:
    """Binance 交易数据"""
    event_type: str
    event_time: int
    symbol: str
    trade_id: int
    price: float
    quantity: float
    buyer_order_id: int
    seller_order_id: int
    trade_time: int
    is_buyer_maker: bool


class BinanceWebSocketClient:
    """Binance WebSocket 客户端"""
    
    def __init__(
        self,
        symbol: str = "btcusdt",
        stream: str = "trade",
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 16.0,
        ping_interval: float = 10.0,
    ):
        """
        初始化 Binance WebSocket 客户端
        
        Args:
            symbol: 交易对符号（默认 btcusdt）
            stream: 数据流类型（默认 trade）
            on_message: 消息处理回调函数
            reconnect_delay: 初始重连延迟（秒）
            max_reconnect_delay: 最大重连延迟（秒）
            ping_interval: 心跳间隔（秒）
        """
        self.symbol = symbol.lower()
        self.stream = stream
        self.on_message = on_message
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.ping_interval = ping_interval
        
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@{self.stream}"
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.running = False
        self._reconnect_attempts = 0
        self._last_ping_time = 0.0
        self._last_price: Optional[float] = None
        self._last_timestamp: Optional[int] = None
        
        logger.info(
            "初始化 Binance WebSocket 客户端",
            symbol=self.symbol,
            stream=self.stream,
            url=self.ws_url,
        )
    
    async def connect(self) -> bool:
        """
        连接到 Binance WebSocket
        
        Returns:
            是否连接成功
        """
        try:
            logger.info("正在连接 Binance WebSocket", url=self.ws_url)
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=self.ping_interval,
                ping_timeout=10,
                close_timeout=5,
            )
            self.running = True
            self._reconnect_attempts = 0
            logger.info("成功连接 Binance WebSocket")
            return True
        except Exception as e:
            logger.error("连接 Binance WebSocket 失败", error=str(e))
            return False
    
    async def disconnect(self) -> None:
        """断开与 Binance WebSocket 的连接"""
        self.running = False
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("已断开 Binance WebSocket 连接")
            except Exception as e:
                logger.error("断开连接时出错", error=str(e))
            finally:
                self.websocket = None
    
    async def _reconnect(self) -> bool:
        """
        断线重连（指数退避）
        
        Returns:
            是否重连成功
        """
        self._reconnect_attempts += 1
        delay = min(
            self.reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
            self.max_reconnect_delay,
        )
        
        logger.warning(
            "尝试重连 Binance WebSocket",
            attempt=self._reconnect_attempts,
            delay=delay,
        )
        
        await asyncio.sleep(delay)
        return await self.connect()
    
    async def _send_ping(self) -> None:
        """发送心跳包"""
        if self.websocket and self.running:
            try:
                await self.websocket.ping()
                self._last_ping_time = time.time()
                logger.debug("发送心跳包")
            except Exception as e:
                logger.error("发送心跳包失败", error=str(e))
    
    def _parse_message(self, data: Dict[str, Any]) -> Optional[BinanceTradeData]:
        """
        解析 Binance WebSocket 消息
        
        Args:
            data: 原始消息数据
            
        Returns:
            解析后的交易数据
        """
        try:
            return BinanceTradeData(
                event_type=data.get("e", ""),
                event_time=data.get("E", 0),
                symbol=data.get("s", ""),
                trade_id=data.get("t", 0),
                price=float(data.get("p", 0)),
                quantity=float(data.get("q", 0)),
                buyer_order_id=data.get("b", 0),
                seller_order_id=data.get("a", 0),
                trade_time=data.get("T", 0),
                is_buyer_maker=data.get("m", False),
            )
        except Exception as e:
            logger.error("解析消息失败", error=str(e), data=data)
            return None
    
    async def listen(self) -> None:
        """
        监听 WebSocket 消息
        """
        if not self.websocket:
            logger.error("WebSocket 未连接")
            return
        
        logger.info("开始监听 Binance WebSocket 消息")
        
        while self.running:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                trade_data = self._parse_message(data)
                if trade_data:
                    self._last_price = trade_data.price
                    self._last_timestamp = trade_data.trade_time
                    
                    logger.debug(
                        "收到交易数据",
                        price=trade_data.price,
                        quantity=trade_data.quantity,
                        timestamp=trade_data.trade_time,
                    )
                    
                    if self.on_message:
                        try:
                            self.on_message({
                                "price": trade_data.price,
                                "quantity": trade_data.quantity,
                                "timestamp": trade_data.trade_time,
                                "symbol": trade_data.symbol,
                            })
                        except Exception as e:
                            logger.error("消息处理回调失败", error=str(e))
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket 连接已关闭")
                if self.running:
                    logger.info("尝试重新连接...")
                    if not await self._reconnect():
                        logger.error("重连失败，停止监听")
                        break
            except json.JSONDecodeError as e:
                logger.error("JSON 解析失败", error=str(e))
            except Exception as e:
                logger.error("监听消息时出错", error=str(e))
                if self.running:
                    await asyncio.sleep(1)
    
    def get_last_price(self) -> Optional[float]:
        """获取最后接收到的价格"""
        return self._last_price
    
    def get_last_timestamp(self) -> Optional[int]:
        """获取最后接收到的时间戳"""
        return self._last_timestamp
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.websocket is not None and self.websocket.open
    
    async def run(self) -> None:
        """
        运行客户端（连接 + 监听）
        """
        if await self.connect():
            await self.listen()


async def create_binance_client(
    symbol: str = "btcusdt",
    stream: str = "trade",
    on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> BinanceWebSocketClient:
    """
    创建 Binance WebSocket 客户端
    
    Args:
        symbol: 交易对符号
        stream: 数据流类型
        on_message: 消息处理回调函数
        
    Returns:
        Binance WebSocket 客户端实例
    """
    return BinanceWebSocketClient(
        symbol=symbol,
        stream=stream,
        on_message=on_message,
    )
