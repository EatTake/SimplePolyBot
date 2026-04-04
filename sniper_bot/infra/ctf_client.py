"""
CTF (Conditional Token Framework) 合约交互

处理已结算市场的获胜代币赎回。
与主交易循环完全解耦，异步执行。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from sniper_bot.core.models import RedemptionResult


logger = logging.getLogger(__name__)


class CTFClient:
    """
    CTF 合约交互客户端

    通过 Web3 + Polygon RPC 执行赎回交易
    """

    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        ctf_address: str = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",
    ):
        self._rpc_url = rpc_url
        self._private_key = private_key
        self._ctf_address = ctf_address
        self._w3: Any = None

    async def initialize(self) -> None:
        """初始化 Web3 连接"""
        loop = asyncio.get_event_loop()
        self._w3 = await loop.run_in_executor(None, self._create_web3)
        logger.info("CTF 客户端已初始化")

    def _create_web3(self) -> Any:
        """同步创建 Web3 实例"""
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(self._rpc_url))
        if not w3.is_connected():
            raise ConnectionError(f"无法连接到 Polygon RPC: {self._rpc_url}")
        return w3

    async def redeem(
        self,
        condition_id: str,
        amounts: list[int],
    ) -> RedemptionResult:
        """
        赎回获胜代币

        Args:
            condition_id: 市场 condition ID
            amounts: 各 outcome 的赎回数量

        Returns:
            赎回结果
        """
        try:
            loop = asyncio.get_event_loop()
            tx_hash = await loop.run_in_executor(
                None, self._execute_redeem, condition_id, amounts
            )

            total = sum(amounts)
            logger.info(
                "赎回成功: condition=%s 数量=%d tx=%s",
                condition_id[:16], total, tx_hash[:16],
            )

            return RedemptionResult(
                condition_id=condition_id,
                redeemed_amount=float(total),
                usdc_received=float(total),  # 1:1 兑换
                tx_hash=tx_hash,
            )

        except Exception as e:
            logger.error("赎回失败: %s", e)
            return RedemptionResult(
                condition_id=condition_id,
                redeemed_amount=0.0,
                usdc_received=0.0,
            )

    def _execute_redeem(
        self,
        condition_id: str,
        amounts: list[int],
    ) -> str:
        """同步执行赎回交易"""
        from web3 import Web3

        # CTF redeemPositions ABI
        abi = [{
            "inputs": [
                {"name": "collateralToken", "type": "address"},
                {"name": "parentCollectionId", "type": "bytes32"},
                {"name": "conditionId", "type": "bytes32"},
                {"name": "indexSets", "type": "uint256[]"},
            ],
            "name": "redeemPositions",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        }]

        contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(self._ctf_address),
            abi=abi,
        )

        account = self._w3.eth.account.from_key(self._private_key)

        # USDC.e on Polygon
        usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
        parent_collection = bytes(32)
        index_sets = [1, 2]  # Up 和 Down

        tx = contract.functions.redeemPositions(
            Web3.to_checksum_address(usdc_address),
            parent_collection,
            bytes.fromhex(condition_id.replace("0x", "")),
            index_sets,
        ).build_transaction({
            "from": account.address,
            "nonce": self._w3.eth.get_transaction_count(account.address),
            "gas": 300000,
            "gasPrice": self._w3.eth.gas_price,
        })

        signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)

        # 等待确认
        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        return receipt["transactionHash"].hex()
