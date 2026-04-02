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
import re
from typing import Any, Dict, List, Optional

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType, TradeParams
from py_clob_client.order_builder.constants import BUY, SELL
import structlog

from shared.constants import (
    POLYMARKET_CLOB_API_URL,
    POLYGON_CHAIN_ID,
    SIGNER_TYPE_EOA,
)
from shared.retry_decorator import with_retry, ClobClientError
from shared.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from shared.error_context import ErrorContext

logger = structlog.get_logger()


def validate_private_key(private_key: Optional[str]) -> bool:
    """
    验证私钥格式

    Args:
        private_key: 私钥字符串

    Returns:
        True: 格式正确

    Raises:
        ClobClientError: 空值或格式错误
    """
    pattern = r'^0x[a-fA-F0-9]{64}$'

    if not private_key or not private_key.strip():
        raise ClobClientError("缺少私钥配置，请设置 PRIVATE_KEY 环境变量")

    if not re.match(pattern, private_key):
        raise ClobClientError("私钥格式无效，应为 0x 开头的 64 位十六进制字符串")

    return True


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
        auto_validate: bool = False,
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
            auto_validate: 初始化后是否自动验证 API 凭证（默认 False）
        """
        self.host = host
        self.chain_id = chain_id
        self.private_key = private_key or os.getenv("PRIVATE_KEY")

        validate_private_key(self.private_key)

        self.api_key = api_key or os.getenv("POLYMARKET_API_KEY")
        self.api_secret = api_secret or os.getenv("POLYMARKET_API_SECRET")
        self.api_passphrase = api_passphrase or os.getenv("POLYMARKET_API_PASSPHRASE")
        self.auto_validate = auto_validate
        
        self._client: Optional[ClobClient] = None
        self._funder_address: Optional[str] = None
        
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout_seconds=60.0,
        )
        
        logger.info(
            "初始化 CLOB 客户端封装",
            host=host,
            chain_id=chain_id,
            auto_validate=auto_validate
        )
    
    def initialize(self) -> None:
        """
        初始化客户端连接
        
        使用 EOA 模式（signature_type=0）初始化
        如果没有 API 凭证，则自动派生
        """
        try:
            with ErrorContext("initialize_clob_client", host=self.host, chain_id=self.chain_id) as ctx:
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
                
                if self.auto_validate:
                    is_valid = self.validate_api_credentials()
                    if not is_valid:
                        raise ClobClientError("API 凭证验证失败")
            
        except Exception as e:
            logger.error("初始化 CLOB 客户端失败", error=str(e), error_context=ctx.to_dict())
            raise ClobClientError(f"初始化客户端失败: {e}")
    
    def _verify_connection(self) -> None:
        """验证客户端连接"""
        try:
            server_time = self._client.get_server_time()
            logger.info("CLOB 客户端连接验证成功", server_time=server_time)
        except Exception as e:
            raise ClobClientError(f"客户端连接验证失败: {e}")
    
    def validate_api_credentials(self) -> bool:
        """
        验证 API 凭证是否有效
        
        通过尝试获取 USDC.e 余额来验证 API 凭证的有效性。
        捕获所有异常（网络超时、认证失败等）。
        
        Returns:
            True: 凭证有效
            False: 凭证无效或验证过程中发生错误
        """
        try:
            balance = self.get_usdc_balance()
            
            logger.info("API 凭证验证成功", balance=balance)
            
            return True
            
        except Exception as e:
            logger.error("API 凭证验证失败", error=str(e))
            
            return False
    
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
        try:
            with ErrorContext("get_balance", asset_type="COLLATERAL") as ctx:
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
        def _execute():
            if tick_size is None:
                _tick_size = self.get_tick_size(token_id)
            else:
                _tick_size = tick_size
            
            if neg_risk is None:
                _neg_risk = self.get_neg_risk(token_id)
            else:
                _neg_risk = neg_risk
            
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
                    "tick_size": _tick_size,
                    "neg_risk": _neg_risk
                },
                order_type=order_type_enum
            )
            
            return response

        try:
            with ErrorContext(
                "create_and_submit_order",
                token_id=token_id,
                price=price,
                size=size,
                side=side,
                order_type=order_type,
            ) as ctx:
                response = self._circuit_breaker.call(_execute)
                
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
                
        except CircuitBreakerOpenError as e:
            logger.error("断路器打开，订单被拒绝", error=str(e))
            raise ClobClientError(f"断路器打开，订单被拒绝: {e}")
        except Exception as e:
            logger.error("创建并提交订单失败", error=str(e), error_context=ctx.to_dict())
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
