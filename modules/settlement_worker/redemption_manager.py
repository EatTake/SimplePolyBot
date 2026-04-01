"""
赎回管理器模块

管理已完结市场的代币赎回流程：
- 查询已完结市场 Condition IDs
- 检查获胜份额余额
- 批量赎回逻辑
- 赎回失败重试机制
- POL/MATIC 余额监控
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
import httpx

from shared.logger import get_logger, LoggerMixin
from shared.config import Config
from shared.constants import (
    POLYMARKET_GAMMA_API_URL,
    POLYMARKET_DATA_API_URL,
    UMA_ADAPTER_ADDRESS,
    MIN_BALANCE_RESERVE,
)
from modules.settlement_worker.ctf_contract import CTFContract, CTFContractError


@dataclass
class MarketInfo:
    """市场信息数据类"""
    condition_id: bytes
    question_id: bytes
    token_ids: List[int]
    resolved: bool
    resolution_date: Optional[datetime] = None
    question: str = ""
    oracle: str = UMA_ADAPTER_ADDRESS


@dataclass
class RedemptionResult:
    """赎回结果数据类"""
    condition_id: str
    success: bool
    transaction_hash: Optional[str] = None
    amount_redeemed: Optional[Decimal] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RedemptionManager(LoggerMixin):
    """
    赎回管理器
    
    负责：
    1. 查询已完结市场
    2. 检查用户持仓
    3. 执行赎回操作
    4. 管理重试逻辑
    5. 监控余额
    """
    
    def __init__(
        self,
        ctf_contract: CTFContract,
        config: Optional[Config] = None,
        gamma_api_url: Optional[str] = None,
        data_api_url: Optional[str] = None,
    ) -> None:
        """
        初始化赎回管理器
        
        参数:
            ctf_contract: CTF 合约交互实例
            config: 配置管理器实例
            gamma_api_url: Gamma API URL
            data_api_url: Data API URL
        """
        self.ctf_contract = ctf_contract
        self.config = config or Config.get_instance()
        
        self.gamma_api_url = gamma_api_url or POLYMARKET_GAMMA_API_URL
        self.data_api_url = data_api_url or POLYMARKET_DATA_API_URL
        
        self._http_client: Optional[httpx.AsyncClient] = None
        
        self._pending_redemptions: Dict[str, Dict[str, Any]] = {}
        self._failed_redemptions: Dict[str, List[Dict[str, Any]]] = {}
        self._processed_conditions: Set[str] = set()
        
        self._max_retries = 3
        self._retry_delay_base = 60
        self._min_pol_balance = Decimal("0.1")
        self._min_usdc_balance = Decimal(str(MIN_BALANCE_RESERVE))
        
        self._redemption_history: List[RedemptionResult] = []
        self._max_history_size = 1000
        
        self.logger.info(
            "赎回管理器已初始化",
            gamma_api_url=self.gamma_api_url,
            data_api_url=self.data_api_url,
        )
    
    @property
    async def http_client(self) -> httpx.AsyncClient:
        """
        获取 HTTP 客户端（延迟初始化）
        
        返回:
            httpx AsyncClient 实例
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self.logger.info("HTTP 客户端已关闭")
    
    async def fetch_resolved_markets(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MarketInfo]:
        """
        从 Gamma API 获取已解析的市场列表
        
        参数:
            limit: 返回结果数量限制
            offset: 偏移量
        
        返回:
            市场信息列表
        """
        try:
            client = await self.http_client
            
            params = {
                "closed": "true",
                "resolved": "true",
                "limit": limit,
                "offset": offset,
                "order": "resolution_date",
                "ascending": "false",
            }
            
            response = await client.get(
                f"{self.gamma_api_url}/markets",
                params=params,
            )
            response.raise_for_status()
            
            markets_data = response.json()
            markets = []
            
            for market in markets_data:
                try:
                    condition_id = bytes.fromhex(market.get("conditionId", "").replace("0x", ""))
                    question_id = bytes.fromhex(market.get("questionId", "").replace("0x", ""))
                    
                    tokens = market.get("tokens", [])
                    token_ids = []
                    for token in tokens:
                        token_id = token.get("token_id")
                        if token_id:
                            token_ids.append(int(token_id))
                    
                    resolution_date_str = market.get("resolutionDate")
                    resolution_date = None
                    if resolution_date_str:
                        try:
                            resolution_date = datetime.fromisoformat(
                                resolution_date_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass
                    
                    market_info = MarketInfo(
                        condition_id=condition_id,
                        question_id=question_id,
                        token_ids=token_ids,
                        resolved=market.get("resolved", False),
                        resolution_date=resolution_date,
                        question=market.get("question", ""),
                        oracle=market.get("oracle", UMA_ADAPTER_ADDRESS),
                    )
                    
                    markets.append(market_info)
                    
                except Exception as e:
                    self.logger.warning(
                        "解析市场数据失败",
                        market_id=market.get("id"),
                        error=str(e),
                    )
                    continue
            
            self.logger.info(
                "获取已解析市场列表",
                count=len(markets),
                limit=limit,
                offset=offset,
            )
            
            return markets
            
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "获取市场列表失败",
                status_code=e.response.status_code,
                error=str(e),
            )
            return []
        
        except Exception as e:
            self.logger.error(
                "获取市场列表异常",
                error=str(e),
            )
            return []
    
    async def fetch_user_positions(
        self,
        address: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        从 Data API 获取用户持仓
        
        参数:
            address: 用户地址，默认使用当前账户地址
        
        返回:
            持仓列表
        """
        try:
            if address is None:
                address = self.ctf_contract.account_address
            
            client = await self.http_client
            
            response = await client.get(
                f"{self.data_api_url}/positions",
                params={"user": address},
            )
            response.raise_for_status()
            
            positions = response.json()
            
            self.logger.info(
                "获取用户持仓",
                address=address,
                count=len(positions),
            )
            
            return positions
            
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "获取用户持仓失败",
                status_code=e.response.status_code,
                error=str(e),
            )
            return []
        
        except Exception as e:
            self.logger.error(
                "获取用户持仓异常",
                error=str(e),
            )
            return []
    
    async def check_winning_token_balance(
        self,
        token_ids: List[int],
    ) -> Dict[int, Decimal]:
        """
        检查获胜代币余额
        
        参数:
            token_ids: 代币 ID 列表
        
        返回:
            代币 ID 到余额的映射
        """
        balances = {}
        
        for token_id in token_ids:
            try:
                balance = self.ctf_contract.get_token_balance(token_id)
                if balance > 0:
                    balances[token_id] = balance
                    self.logger.info(
                        "发现代币余额",
                        token_id=hex(token_id),
                        balance=str(balance),
                    )
            except Exception as e:
                self.logger.warning(
                    "查询代币余额失败",
                    token_id=hex(token_id),
                    error=str(e),
                )
        
        return balances
    
    async def get_redeemable_markets(self) -> List[MarketInfo]:
        """
        获取可赎回的市场列表
        
        筛选出已解析且用户持有代币的市场
        
        返回:
            可赎回的市场信息列表
        """
        resolved_markets = await self.fetch_resolved_markets()
        redeemable = []
        
        for market in resolved_markets:
            condition_id_hex = market.condition_id.hex()
            
            if condition_id_hex in self._processed_conditions:
                continue
            
            if not market.resolved:
                continue
            
            if not market.token_ids:
                continue
            
            balances = await self.check_winning_token_balance(market.token_ids)
            
            if balances:
                market_info = MarketInfo(
                    condition_id=market.condition_id,
                    question_id=market.question_id,
                    token_ids=market.token_ids,
                    resolved=market.resolved,
                    resolution_date=market.resolution_date,
                    question=market.question,
                    oracle=market.oracle,
                )
                redeemable.append(market_info)
                
                self.logger.info(
                    "发现可赎回市场",
                    condition_id=condition_id_hex,
                    question=market.question[:50] if market.question else "",
                    token_count=len(balances),
                )
        
        self.logger.info(
            "可赎回市场统计",
            total_resolved=len(resolved_markets),
            redeemable=len(redeemable),
        )
        
        return redeemable
    
    async def redeem_market(
        self,
        market: MarketInfo,
        retry_count: int = 0,
    ) -> RedemptionResult:
        """
        赎回单个市场的代币
        
        参数:
            market: 市场信息
            retry_count: 当前重试次数
        
        返回:
            赎回结果
        """
        condition_id_hex = market.condition_id.hex()
        
        try:
            self.logger.info(
                "开始赎回市场代币",
                condition_id=condition_id_hex,
                question=market.question[:50] if market.question else "",
                retry_count=retry_count,
            )
            
            pre_balance = self.ctf_contract.get_usdc_balance()
            
            result = self.ctf_contract.redeem_positions(
                condition_id=market.condition_id,
                index_sets=[1, 2],
            )
            
            post_balance = self.ctf_contract.get_usdc_balance()
            amount_redeemed = post_balance - pre_balance
            
            redemption_result = RedemptionResult(
                condition_id=condition_id_hex,
                success=True,
                transaction_hash=result.get('transaction_hash'),
                amount_redeemed=amount_redeemed,
            )
            
            self._processed_conditions.add(condition_id_hex)
            
            if condition_id_hex in self._pending_redemptions:
                del self._pending_redemptions[condition_id_hex]
            
            self._add_to_history(redemption_result)
            
            self.logger.info(
                "赎回成功",
                condition_id=condition_id_hex,
                amount=str(amount_redeemed),
                tx_hash=result.get('transaction_hash'),
            )
            
            return redemption_result
            
        except CTFContractError as e:
            self.logger.error(
                "赎回失败",
                condition_id=condition_id_hex,
                error=str(e),
                retry_count=retry_count,
            )
            
            if retry_count < self._max_retries:
                retry_delay = self._retry_delay_base * (2 ** retry_count)
                
                self._pending_redemptions[condition_id_hex] = {
                    'market': market,
                    'retry_count': retry_count + 1,
                    'next_retry': datetime.now(timezone.utc) + timedelta(seconds=retry_delay),
                }
                
                self.logger.info(
                    "计划重试赎回",
                    condition_id=condition_id_hex,
                    retry_delay=retry_delay,
                    next_retry_count=retry_count + 1,
                )
                
                return RedemptionResult(
                    condition_id=condition_id_hex,
                    success=False,
                    error=str(e),
                )
            else:
                if condition_id_hex not in self._failed_redemptions:
                    self._failed_redemptions[condition_id_hex] = []
                
                self._failed_redemptions[condition_id_hex].append({
                    'timestamp': datetime.now(timezone.utc),
                    'error': str(e),
                    'retry_count': retry_count,
                })
                
                self.logger.error(
                    "赎回最终失败",
                    condition_id=condition_id_hex,
                    total_retries=retry_count,
                )
                
                return RedemptionResult(
                    condition_id=condition_id_hex,
                    success=False,
                    error=f"重试 {retry_count} 次后仍然失败: {e}",
                )
        
        except Exception as e:
            self.logger.error(
                "赎回异常",
                condition_id=condition_id_hex,
                error=str(e),
            )
            
            return RedemptionResult(
                condition_id=condition_id_hex,
                success=False,
                error=str(e),
            )
    
    async def batch_redeem_markets(
        self,
        markets: List[MarketInfo],
    ) -> List[RedemptionResult]:
        """
        批量赎回多个市场
        
        参数:
            markets: 市场信息列表
        
        返回:
            赎回结果列表
        """
        results = []
        
        self.logger.info(
            "开始批量赎回",
            total_markets=len(markets),
        )
        
        for i, market in enumerate(markets):
            self.logger.info(
                "批量赎回进度",
                current=i + 1,
                total=len(markets),
                condition_id=market.condition_id.hex(),
            )
            
            result = await self.redeem_market(market)
            results.append(result)
            
            if i < len(markets) - 1:
                await asyncio.sleep(2)
        
        successful = sum(1 for r in results if r.success)
        
        self.logger.info(
            "批量赎回完成",
            total=len(markets),
            successful=successful,
            failed=len(markets) - successful,
        )
        
        return results
    
    async def process_pending_redemptions(self) -> List[RedemptionResult]:
        """
        处理待重试的赎回
        
        返回:
            赎回结果列表
        """
        results = []
        now = datetime.now(timezone.utc)
        
        to_retry = []
        for condition_id_hex, pending in list(self._pending_redemptions.items()):
            if pending['next_retry'] <= now:
                to_retry.append((condition_id_hex, pending))
        
        self.logger.info(
            "处理待重试赎回",
            pending_count=len(self._pending_redemptions),
            to_retry_count=len(to_retry),
        )
        
        for condition_id_hex, pending in to_retry:
            result = await self.redeem_market(
                market=pending['market'],
                retry_count=pending['retry_count'],
            )
            results.append(result)
        
        return results
    
    async def check_pol_balance(self) -> Dict[str, Any]:
        """
        检查 POL 余额
        
        返回:
            包含余额信息的字典
        """
        try:
            balance = self.ctf_contract.get_pol_balance()
            
            is_low = balance < self._min_pol_balance
            
            result = {
                'balance': balance,
                'min_required': self._min_pol_balance,
                'is_low': is_low,
                'timestamp': datetime.now(timezone.utc),
            }
            
            if is_low:
                self.logger.warning(
                    "POL 余额过低",
                    balance=str(balance),
                    min_required=str(self._min_pol_balance),
                )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "检查 POL 余额失败",
                error=str(e),
            )
            return {
                'balance': Decimal("0"),
                'error': str(e),
                'timestamp': datetime.now(timezone.utc),
            }
    
    async def check_usdc_balance(self) -> Dict[str, Any]:
        """
        检查 USDC.e 余额
        
        返回:
            包含余额信息的字典
        """
        try:
            balance = self.ctf_contract.get_usdc_balance()
            
            is_low = balance < self._min_usdc_balance
            
            result = {
                'balance': balance,
                'min_required': self._min_usdc_balance,
                'is_low': is_low,
                'timestamp': datetime.now(timezone.utc),
            }
            
            if is_low:
                self.logger.warning(
                    "USDC.e 余额过低",
                    balance=str(balance),
                    min_required=str(self._min_usdc_balance),
                )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "检查 USDC.e 余额失败",
                error=str(e),
            )
            return {
                'balance': Decimal("0"),
                'error': str(e),
                'timestamp': datetime.now(timezone.utc),
            }
    
    async def run_redemption_cycle(self) -> Dict[str, Any]:
        """
        执行完整的赎回周期
        
        包括：
        1. 检查余额
        2. 处理待重试的赎回
        3. 查找新的可赎回市场
        4. 执行赎回
        
        返回:
            周期执行结果
        """
        self.logger.info("开始赎回周期")
        
        start_time = time.time()
        
        pol_status = await self.check_pol_balance()
        usdc_status = await self.check_usdc_balance()
        
        retry_results = await self.process_pending_redemptions()
        
        redeemable_markets = await self.get_redeemable_markets()
        
        new_results = []
        if redeemable_markets:
            new_results = await self.batch_redeem_markets(redeemable_markets)
        
        all_results = retry_results + new_results
        successful = sum(1 for r in all_results if r.success)
        failed = len(all_results) - successful
        
        elapsed_time = time.time() - start_time
        
        result = {
            'timestamp': datetime.now(timezone.utc),
            'elapsed_seconds': elapsed_time,
            'pol_balance': pol_status,
            'usdc_balance': usdc_status,
            'retry_count': len(retry_results),
            'new_redemptions': len(new_results),
            'total_redemptions': len(all_results),
            'successful': successful,
            'failed': failed,
            'pending_count': len(self._pending_redemptions),
            'failed_count': len(self._failed_redemptions),
        }
        
        self.logger.info(
            "赎回周期完成",
            elapsed_seconds=round(elapsed_time, 2),
            total_redemptions=len(all_results),
            successful=successful,
            failed=failed,
        )
        
        return result
    
    def _add_to_history(self, result: RedemptionResult) -> None:
        """
        添加赎回结果到历史记录
        
        参数:
            result: 赎回结果
        """
        self._redemption_history.append(result)
        
        if len(self._redemption_history) > self._max_history_size:
            self._redemption_history = self._redemption_history[-self._max_history_size:]
    
    def get_redemption_history(
        self,
        limit: int = 100,
        only_successful: bool = False,
    ) -> List[RedemptionResult]:
        """
        获取赎回历史记录
        
        参数:
            limit: 返回结果数量限制
            only_successful: 是否只返回成功的记录
        
        返回:
            赎回结果列表
        """
        history = self._redemption_history
        
        if only_successful:
            history = [r for r in history if r.success]
        
        return history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取赎回统计信息
        
        返回:
            统计信息字典
        """
        total_redemptions = len(self._redemption_history)
        successful_redemptions = sum(1 for r in self._redemption_history if r.success)
        
        total_amount = sum(
            r.amount_redeemed for r in self._redemption_history
            if r.success and r.amount_redeemed
        )
        
        return {
            'total_redemptions': total_redemptions,
            'successful_redemptions': successful_redemptions,
            'failed_redemptions': total_redemptions - successful_redemptions,
            'success_rate': successful_redemptions / total_redemptions if total_redemptions > 0 else 0,
            'total_amount_redeemed': str(total_amount),
            'pending_redemptions': len(self._pending_redemptions),
            'failed_markets': len(self._failed_redemptions),
        }
