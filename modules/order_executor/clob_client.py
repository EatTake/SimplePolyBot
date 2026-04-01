"""
CLOB 客户端封装模块

封装 py-clob-client，提供简化的接口用于：
- 客户端初始化（EOA 模式）
- 余额查询
- Tick Size 查询
- 订单簿查询
- 订单创建和提交
"""

import os
import time
import functools
from typing import Any, Dict, List, Optional, Callable, TypeVar
from decimal import Decimal

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType, TradeParams
from py_clob_client.order_builder.constants import BUY, SELL
import structlog

from shared.constants import (
    POLYMARKET_CLOB_API_URL,
    POLYGON_CHAIN_ID,
    SIGNER_TYPE_EOA,
)

logger = structlog.get_logger()

T = TypeVar('T')

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_RETRY_BACKOFF = 2.0


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    backoff_factor: float = DEFAULT_RETRY_BACKOFF,
    retryable_exceptions: tuple = (Exception,),
) -> Callable:
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 初始重试延迟（秒）
        backoff_factor: 退避因子
        retryable_exceptions: 可重试的异常类型
    
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = retry_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "API调用失败，准备重试",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e)
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            "API调用失败，已达到最大重试次数",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e)
                        )
            
            raise ClobClientError(f"重试{max_retries}次后仍然失败: {last_exception}")
        
        return wrapper
    return decorator


class ClobClientError(Exception):
    """CLOB 客户端异常"""
    pass


class ClobClientWrapper:
    """
    CLOB 客户端封装类
    
    使用 EOA 模式（signature_type=0）初始化 ClobClient
    提供余额查询、Tick Size 查询、订单簿查询等功能
    """
    
    def __init__(
        self,
        host: str = POLYMARKET_CLOB_API_URL,
        chain_id: int = POLYGON_CHAIN_ID,
        private_key: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_passphrase: Optional[str] = None,
    ):
        """
        初始化 CLOB 客户端
        
        Args:
            host: CLOB API 主机地址
            chain_id: 链 ID（Polygon Mainnet = 137）
            private_key: 钱包私钥
            api_key: API Key
            api_secret: API Secret
            api_passphrase: API Passphrase
        """
        self.host = host
        self.chain_id = chain_id
        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        
        if not self.private_key:
            raise ClobClientError("缺少私钥配置，请设置 PRIVATE_KEY 环境变量")
        
        self.api_key = api_key or os.getenv("POLYMARKET_API_KEY")
        self.api_secret = api_secret or os.getenv("POLYMARKET_API_SECRET")
        self.api_passphrase = api_passphrase or os.getenv("POLYMARKET_API_PASSPHRASE")
        
        self._client: Optional[ClobClient] = None
        self._funder_address: Optional[str] = None
        
        logger.info(
            "初始化 CLOB 客户端封装",
            host=host,
            chain_id=chain_id
        )
    
    def initialize(self) -> None:
        """
        初始化客户端连接
        
        使用 EOA 模式（signature_type=0）初始化
        如果没有 API 凭证，则自动派生
        """
        try:
            if self.api_key and self.api_secret and self.api_passphrase:
                api_creds = ApiCreds(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    api_passphrase=self.api_passphrase
                )
                
                temp_client = ClobClient(
                    host=self.host,
                    key=self.private_key,
                    chain_id=self.chain_id
                )
                self._funder_address = temp_client.get_address()
                
                self._client = ClobClient(
                    host=self.host,
                    key=self.private_key,
                    chain_id=self.chain_id,
                    creds=api_creds,
                    signature_type=SIGNER_TYPE_EOA,
                    funder=self._funder_address
                )
                
                logger.info(
                    "使用现有 API 凭证初始化客户端",
                    funder_address=self._funder_address
                )
            else:
                temp_client = ClobClient(
                    host=self.host,
                    key=self.private_key,
                    chain_id=self.chain_id
                )
                
                api_creds = temp_client.create_or_derive_api_creds()
                self._funder_address = temp_client.get_address()
                
                self._client = ClobClient(
                    host=self.host,
                    key=self.private_key,
                    chain_id=self.chain_id,
                    creds=api_creds,
                    signature_type=SIGNER_TYPE_EOA,
                    funder=self._funder_address
                )
                
                logger.info(
                    "自动派生 API 凭证并初始化客户端",
                    funder_address=self._funder_address
                )
            
            self._verify_connection()
            
        except Exception as e:
            logger.error("初始化 CLOB 客户端失败", error=str(e))
            raise ClobClientError(f"初始化客户端失败: {e}")
    
    def _verify_connection(self) -> None:
        """验证客户端连接"""
        try:
            server_time = self._client.get_server_time()
            logger.info("CLOB 客户端连接验证成功", server_time=server_time)
        except Exception as e:
            raise ClobClientError(f"客户端连接验证失败: {e}")
    
    @property
    def client(self) -> ClobClient:
        """获取底层 ClobClient 实例"""
        if self._client is None:
            raise ClobClientError("客户端未初始化，请先调用 initialize()")
        return self._client
    
    @property
    def funder_address(self) -> str:
        """获取 Funder 地址"""
        if self._funder_address is None:
            raise ClobClientError("客户端未初始化，请先调用 initialize()")
        return self._funder_address
    
    @with_retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0)
    def get_usdc_balance(self) -> float:
        """
        查询 USDC.e 余额
        
        Returns:
            USDC.e 余额
        """
        try:
            balance_info = self.client.get_balance_allowance(
                asset_type="COLLATERAL"
            )
            
            balance = float(balance_info.get("balance", 0))
            
            logger.debug("查询 USDC.e 余额", balance=balance)
            
            return balance
            
        except Exception as e:
            logger.error("查询 USDC.e 余额失败", error=str(e))
            raise ClobClientError(f"查询余额失败: {e}")
    
    @with_retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0)
    def get_token_balance(self, token_id: str) -> float:
        """
        查询指定代币余额
        
        Args:
            token_id: 代币 ID
        
        Returns:
            代币余额
        """
        try:
            balance_info = self.client.get_balance_allowance(
                asset_type="CONDITIONAL",
                token_id=token_id
            )
            
            balance = float(balance_info.get("balance", 0))
            
            logger.debug("查询代币余额", token_id=token_id, balance=balance)
            
            return balance
            
        except Exception as e:
            logger.error("查询代币余额失败", token_id=token_id, error=str(e))
            raise ClobClientError(f"查询代币余额失败: {e}")
    
    @with_retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0)
    def get_tick_size(self, token_id: str) -> str:
        """
        查询 Tick Size（最小价格变动单位）
        
        Args:
            token_id: 代币 ID
        
        Returns:
            Tick Size 字符串（如 "0.01"）
        """
        try:
            tick_size = self.client.get_tick_size(token_id)
            
            logger.debug("查询 Tick Size", token_id=token_id, tick_size=tick_size)
            
            return tick_size
            
        except Exception as e:
            logger.error("查询 Tick Size 失败", token_id=token_id, error=str(e))
            raise ClobClientError(f"查询 Tick Size 失败: {e}")
    
    def get_neg_risk(self, token_id: str) -> bool:
        """
        查询是否为 Neg Risk 市场
        
        Args:
            token_id: 代币 ID
        
        Returns:
            是否为 Neg Risk 市场
        """
        try:
            neg_risk = self.client.get_neg_risk(token_id)
            
            logger.debug("查询 Neg Risk", token_id=token_id, neg_risk=neg_risk)
            
            return neg_risk
            
        except Exception as e:
            logger.error("查询 Neg Risk 失败", token_id=token_id, error=str(e))
            raise ClobClientError(f"查询 Neg Risk 失败: {e}")
    
    @with_retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0)
    def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """
        查询订单簿
        
        Args:
            token_id: 代币 ID
        
        Returns:
            订单簿数据（包含 bids, asks 等）
        """
        try:
            order_book = self.client.get_order_book(token_id)
            
            logger.debug(
                "查询订单簿",
                token_id=token_id,
                bids_count=len(order_book.get("bids", [])),
                asks_count=len(order_book.get("asks", []))
            )
            
            return order_book
            
        except Exception as e:
            logger.error("查询订单簿失败", token_id=token_id, error=str(e))
            raise ClobClientError(f"查询订单簿失败: {e}")
    
    def get_midpoint_price(self, token_id: str) -> Optional[float]:
        """
        查询中间价
        
        Args:
            token_id: 代币 ID
        
        Returns:
            中间价（买卖价差的中点）
        """
        try:
            midpoint = self.client.get_midpoint(token_id)
            
            if midpoint:
                price = float(midpoint)
                logger.debug("查询中间价", token_id=token_id, midpoint=price)
                return price
            
            return None
            
        except Exception as e:
            logger.error("查询中间价失败", token_id=token_id, error=str(e))
            return None
    
    def get_price_history(
        self,
        token_id: str,
        interval: str = "1h",
        fudge: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        查询价格历史
        
        Args:
            token_id: 代币 ID
            interval: 时间间隔（如 "1h", "1d"）
            fudge: 时间偏移
        
        Returns:
            价格历史列表
        """
        try:
            history = self.client.get_price_history(
                token_id=token_id,
                interval=interval,
                fudge=fudge
            )
            
            logger.debug(
                "查询价格历史",
                token_id=token_id,
                interval=interval,
                history_count=len(history) if history else 0
            )
            
            return history or []
            
        except Exception as e:
            logger.error("查询价格历史失败", token_id=token_id, error=str(e))
            raise ClobClientError(f"查询价格历史失败: {e}")
    
    def get_fee_rate(self, token_id: str) -> int:
        """
        查询手续费率（基点）
        
        Args:
            token_id: 代币 ID
        
        Returns:
            手续费率（基点，如 100 表示 1%）
        """
        try:
            fee_rate = self.client.get_fee_rate(token_id)
            
            fee_rate_bps = int(fee_rate) if fee_rate else 0
            
            logger.debug("查询手续费率", token_id=token_id, fee_rate_bps=fee_rate_bps)
            
            return fee_rate_bps
            
        except Exception as e:
            logger.error("查询手续费率失败", token_id=token_id, error=str(e))
            return 0
    
    def create_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        tick_size: Optional[str] = None,
        neg_risk: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        创建订单（不提交）
        
        Args:
            token_id: 代币 ID
            price: 价格
            size: 数量
            side: 方向（"BUY" 或 "SELL"）
            tick_size: Tick Size（可选，自动查询）
            neg_risk: 是否为 Neg Risk 市场（可选，自动查询）
        
        Returns:
            签名后的订单对象
        """
        try:
            if tick_size is None:
                tick_size = self.get_tick_size(token_id)
            
            if neg_risk is None:
                neg_risk = self.get_neg_risk(token_id)
            
            order_side = BUY if side.upper() == "BUY" else SELL
            
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=order_side
            )
            
            signed_order = self.client.create_order(
                order_args,
                options={
                    "tick_size": tick_size,
                    "neg_risk": neg_risk
                }
            )
            
            logger.info(
                "创建订单",
                token_id=token_id,
                price=price,
                size=size,
                side=side
            )
            
            return signed_order
            
        except Exception as e:
            logger.error("创建订单失败", error=str(e))
            raise ClobClientError(f"创建订单失败: {e}")
    
    def submit_order(
        self,
        signed_order: Dict[str, Any],
        order_type: str = "GTC"
    ) -> Dict[str, Any]:
        """
        提交订单
        
        Args:
            signed_order: 签名后的订单对象
            order_type: 订单类型（"GTC", "GTD", "FOK", "FAK"）
        
        Returns:
            订单响应
        """
        try:
            order_type_enum = OrderType[order_type.upper()]
            
            response = self.client.post_order(signed_order, order_type_enum)
            
            logger.info(
                "提交订单",
                order_id=response.get("orderID"),
                status=response.get("status"),
                order_type=order_type
            )
            
            return response
            
        except Exception as e:
            logger.error("提交订单失败", error=str(e))
            raise ClobClientError(f"提交订单失败: {e}")
    
    @with_retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0)
    def create_and_submit_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        order_type: str = "GTC",
        tick_size: Optional[str] = None,
        neg_risk: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        创建并提交订单（一步完成）
        
        Args:
            token_id: 代币 ID
            price: 价格
            size: 数量
            side: 方向（"BUY" 或 "SELL"）
            order_type: 订单类型（"GTC", "GTD", "FOK", "FAK"）
            tick_size: Tick Size（可选，自动查询）
            neg_risk: 是否为 Neg Risk 市场（可选，自动查询）
        
        Returns:
            订单响应
        """
        try:
            if tick_size is None:
                tick_size = self.get_tick_size(token_id)
            
            if neg_risk is None:
                neg_risk = self.get_neg_risk(token_id)
            
            order_side = BUY if side.upper() == "BUY" else SELL
            order_type_enum = OrderType[order_type.upper()]
            
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=order_side
            )
            
            response = self.client.create_and_post_order(
                order_args,
                options={
                    "tick_size": tick_size,
                    "neg_risk": neg_risk
                },
                order_type=order_type_enum
            )
            
            logger.info(
                "创建并提交订单",
                token_id=token_id,
                price=price,
                size=size,
                side=side,
                order_type=order_type,
                order_id=response.get("orderID"),
                status=response.get("status")
            )
            
            return response
            
        except Exception as e:
            logger.error("创建并提交订单失败", error=str(e))
            raise ClobClientError(f"创建并提交订单失败: {e}")
    
    def create_market_order(
        self,
        token_id: str,
        amount: float,
        side: str,
        price: Optional[float] = None,
        order_type: str = "FAK",
        tick_size: Optional[str] = None,
        neg_risk: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        创建市场订单
        
        Args:
            token_id: 代币 ID
            amount: 数量（买单为 USDC 金额，卖单为份额数量）
            side: 方向（"BUY" 或 "SELL"）
            price: 价格上限（滑点保护）
            order_type: 订单类型（"FOK" 或 "FAK"）
            tick_size: Tick Size（可选，自动查询）
            neg_risk: 是否为 Neg Risk 市场（可选，自动查询）
        
        Returns:
            签名后的市场订单对象
        """
        try:
            if tick_size is None:
                tick_size = self.get_tick_size(token_id)
            
            if neg_risk is None:
                neg_risk = self.get_neg_risk(token_id)
            
            order_side = BUY if side.upper() == "BUY" else SELL
            
            signed_order = self.client.create_market_order(
                token_id=token_id,
                amount=amount,
                side=order_side,
                price=price,
                options={
                    "tick_size": tick_size,
                    "neg_risk": neg_risk
                }
            )
            
            logger.info(
                "创建市场订单",
                token_id=token_id,
                amount=amount,
                side=side,
                price=price,
                order_type=order_type
            )
            
            return signed_order
            
        except Exception as e:
            logger.error("创建市场订单失败", error=str(e))
            raise ClobClientError(f"创建市场订单失败: {e}")
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
        
        Returns:
            取消响应
        """
        try:
            response = self.client.cancel(order_id=order_id)
            
            logger.info("取消订单", order_id=order_id)
            
            return response
            
        except Exception as e:
            logger.error("取消订单失败", order_id=order_id, error=str(e))
            raise ClobClientError(f"取消订单失败: {e}")
    
    def cancel_all_orders(self) -> Dict[str, Any]:
        """
        取消所有订单
        
        Returns:
            取消响应
        """
        try:
            response = self.client.cancel_all()
            
            logger.info("取消所有订单")
            
            return response
            
        except Exception as e:
            logger.error("取消所有订单失败", error=str(e))
            raise ClobClientError(f"取消所有订单失败: {e}")
    
    def get_open_orders(
        self,
        market: Optional[str] = None,
        asset_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查询未成交订单
        
        Args:
            market: 市场 ID（可选）
            asset_id: 代币 ID（可选）
        
        Returns:
            未成交订单列表
        """
        try:
            params = {}
            if market:
                params["market"] = market
            if asset_id:
                params["asset_id"] = asset_id
            
            orders = self.client.get_orders(params=params)
            
            logger.debug(
                "查询未成交订单",
                market=market,
                asset_id=asset_id,
                orders_count=len(orders) if orders else 0
            )
            
            return orders or []
            
        except Exception as e:
            logger.error("查询未成交订单失败", error=str(e))
            raise ClobClientError(f"查询未成交订单失败: {e}")
    
    def get_trades(
        self,
        market: Optional[str] = None,
        asset_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询交易历史
        
        Args:
            market: 市场 ID（可选）
            asset_id: 代币 ID（可选）
            limit: 返回数量限制
        
        Returns:
            交易历史列表
        """
        try:
            params = TradeParams()
            if market:
                params.market = market
            if asset_id:
                params.asset_id = asset_id
            
            trades = self.client.get_trades(params=params)
            
            if trades and len(trades) > limit:
                trades = trades[:limit]
            
            logger.debug(
                "查询交易历史",
                market=market,
                asset_id=asset_id,
                trades_count=len(trades) if trades else 0
            )
            
            return trades or []
            
        except Exception as e:
            logger.error("查询交易历史失败", error=str(e))
            raise ClobClientError(f"查询交易历史失败: {e}")
