"""
CTF 合约交互模块

实现与 Polymarket Conditional Tokens Framework (CTF) 合约的交互功能：
- 连接 Polygon 网络
- 加载 CTF 合约 ABI
- 实现 redeemPositions 函数调用
- 实现交易签名与 Gas 费支付
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError, TransactionNotFound
from web3.types import TxReceipt, Wei, Address, ChecksumAddress
from eth_account import Account
from eth_account.signers.local import LocalAccount

from shared.logger import get_logger, LoggerMixin
from shared.constants import (
    CTF_CONTRACT_ADDRESS,
    USDC_E_ADDRESS,
    POLYGON_CHAIN_ID,
    POLYGON_RPC_URL,
    USDC_E_DECIMALS,
)


CTF_ABI: List[Dict[str, Any]] = [
    {
        "inputs": [
            {"internalType": "contract IERC20", "name": "collateralToken", "type": "address"},
            {"internalType": "bytes32", "name": "parentCollectionId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "conditionId", "type": "bytes32"},
            {"internalType": "uint256[]", "name": "indexSets", "type": "uint256[]"},
        ],
        "name": "redeemPositions",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "uint256", "name": "id", "type": "uint256"},
        ],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "operator", "type": "address"},
            {"internalType": "bool", "name": "approved", "type": "bool"},
        ],
        "name": "setApprovalForAll",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "operator", "type": "address"},
        ],
        "name": "isApprovedForAll",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "oracle", "type": "address"},
            {"internalType": "bytes32", "name": "questionId", "type": "bytes32"},
            {"internalType": "uint256", "name": "outcomeSlotCount", "type": "uint256"},
        ],
        "name": "getConditionId",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "pure",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "parentCollectionId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "conditionId", "type": "bytes32"},
            {"internalType": "uint256", "name": "indexSet", "type": "uint256"},
        ],
        "name": "getCollectionId",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "contract IERC20", "name": "collateralToken", "type": "address"},
            {"internalType": "bytes32", "name": "collectionId", "type": "bytes32"},
        ],
        "name": "getPositionId",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "pure",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "conditionId", "type": "bytes32"},
        ],
        "name": "getOutcomeSlotCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "", "type": "bytes32"},
        ],
        "name": "payoutNumerators",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


ERC20_ABI: List[Dict[str, Any]] = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class CTFContractError(Exception):
    """CTF 合约错误基类"""
    pass


class InsufficientBalanceError(CTFContractError):
    """余额不足错误"""
    pass


class TransactionFailedError(CTFContractError):
    """交易失败错误"""
    pass


class CTFContract(LoggerMixin):
    """
    CTF 合约交互类
    
    提供与 Polymarket Conditional Tokens Framework 合约的交互功能：
    - 查询代币余额
    - 赎回获胜代币
    - 查询市场状态
    - 管理授权
    """
    
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        ctf_address: Optional[str] = None,
        usdc_address: Optional[str] = None,
    ) -> None:
        """
        初始化 CTF 合约交互实例
        
        参数:
            rpc_url: Polygon RPC URL，默认使用环境变量或公共 RPC
            private_key: 钱包私钥，用于签名交易
            ctf_address: CTF 合约地址，默认使用主网地址
            usdc_address: USDC.e 合约地址，默认使用主网地址
        """
        self.rpc_url = rpc_url or os.getenv("POLYGON_RPC_URL", POLYGON_RPC_URL)
        self.ctf_address = Web3.to_checksum_address(
            ctf_address or CTF_CONTRACT_ADDRESS
        )
        self.usdc_address = Web3.to_checksum_address(
            usdc_address or USDC_E_ADDRESS
        )
        
        self._web3: Optional[Web3] = None
        self._ctf_contract: Optional[Contract] = None
        self._usdc_contract: Optional[Contract] = None
        self._account: Optional[LocalAccount] = None
        
        if private_key:
            self._account = Account.from_key(private_key)
        
        self._gas_price_multiplier = 1.1
        self._gas_limit_buffer = 1.2
        
        self.logger.info(
            "CTF 合约交互实例已创建",
            ctf_address=self.ctf_address,
            usdc_address=self.usdc_address,
            chain_id=POLYGON_CHAIN_ID,
        )
    
    @property
    def web3(self) -> Web3:
        """
        获取 Web3 实例（延迟初始化）
        
        返回:
            Web3 实例
        """
        if self._web3 is None:
            self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if not self._web3.is_connected():
                raise CTFContractError(f"无法连接到 Polygon 网络: {self.rpc_url}")
            self.logger.info("已连接到 Polygon 网络", chain_id=self._web3.eth.chain_id)
        return self._web3
    
    @property
    def ctf_contract(self) -> Contract:
        """
        获取 CTF 合约实例（延迟初始化）
        
        返回:
            CTF 合约实例
        """
        if self._ctf_contract is None:
            self._ctf_contract = self.web3.eth.contract(
                address=self.ctf_address,
                abi=CTF_ABI,
            )
        return self._ctf_contract
    
    @property
    def usdc_contract(self) -> Contract:
        """
        获取 USDC.e 合约实例（延迟初始化）
        
        返回:
            USDC.e 合约实例
        """
        if self._usdc_contract is None:
            self._usdc_contract = self.web3.eth.contract(
                address=self.usdc_address,
                abi=ERC20_ABI,
            )
        return self._usdc_contract
    
    @property
    def account_address(self) -> ChecksumAddress:
        """
        获取账户地址
        
        返回:
            账户地址
        
        异常:
            CTFContractError: 如果未设置私钥
        """
        if self._account is None:
            raise CTFContractError("未设置私钥，无法获取账户地址")
        return self._account.address
    
    def get_token_balance(
        self,
        token_id: int,
        address: Optional[ChecksumAddress] = None,
    ) -> Decimal:
        """
        查询 CTF 代币余额
        
        参数:
            token_id: 代币 ID (Position ID)
            address: 要查询的地址，默认使用当前账户地址
        
        返回:
            代币余额（已转换为可读格式）
        """
        if address is None:
            address = self.account_address
        
        balance_wei = self.ctf_contract.functions.balanceOf(
            address,
            token_id,
        ).call()
        
        balance = Decimal(balance_wei) / Decimal(10 ** USDC_E_DECIMALS)
        
        self.logger.debug(
            "查询 CTF 代币余额",
            token_id=hex(token_id),
            address=address,
            balance=str(balance),
        )
        
        return balance
    
    def get_usdc_balance(self, address: Optional[ChecksumAddress] = None) -> Decimal:
        """
        查询 USDC.e 余额
        
        参数:
            address: 要查询的地址，默认使用当前账户地址
        
        返回:
            USDC.e 余额（已转换为可读格式）
        """
        if address is None:
            address = self.account_address
        
        balance_wei = self.usdc_contract.functions.balanceOf(address).call()
        balance = Decimal(balance_wei) / Decimal(10 ** USDC_E_DECIMALS)
        
        self.logger.debug(
            "查询 USDC.e 余额",
            address=address,
            balance=str(balance),
        )
        
        return balance
    
    def get_pol_balance(self, address: Optional[ChecksumAddress] = None) -> Decimal:
        """
        查询 POL (MATIC) 余额
        
        参数:
            address: 要查询的地址，默认使用当前账户地址
        
        返回:
            POL 余额（已转换为可读格式，单位: POL）
        """
        if address is None:
            address = self.account_address
        
        balance_wei = self.web3.eth.get_balance(address)
        balance = Decimal(balance_wei) / Decimal(10 ** 18)
        
        self.logger.debug(
            "查询 POL 余额",
            address=address,
            balance=str(balance),
        )
        
        return balance
    
    def get_condition_id(
        self,
        oracle: str,
        question_id: bytes,
        outcome_slot_count: int = 2,
    ) -> bytes:
        """
        计算条件 ID
        
        参数:
            oracle: Oracle 合约地址
            question_id: 问题 ID (bytes32)
            outcome_slot_count: 结果槽位数量，二元市场默认为 2
        
        返回:
            条件 ID (bytes32)
        """
        condition_id = self.ctf_contract.functions.getConditionId(
            Web3.to_checksum_address(oracle),
            question_id,
            outcome_slot_count,
        ).call()
        
        self.logger.debug(
            "计算条件 ID",
            oracle=oracle,
            question_id=question_id.hex(),
            condition_id=condition_id.hex(),
        )
        
        return condition_id
    
    def get_position_id(
        self,
        condition_id: bytes,
        index_set: int,
    ) -> int:
        """
        计算位置 ID (Token ID)
        
        参数:
            condition_id: 条件 ID
            index_set: 索引集 (1 表示 Yes, 2 表示 No)
        
        返回:
            位置 ID (Token ID)
        """
        parent_collection_id = b'\x00' * 32
        
        collection_id = self.ctf_contract.functions.getCollectionId(
            parent_collection_id,
            condition_id,
            index_set,
        ).call()
        
        position_id = self.ctf_contract.functions.getPositionId(
            self.usdc_address,
            collection_id,
        ).call()
        
        self.logger.debug(
            "计算位置 ID",
            condition_id=condition_id.hex(),
            index_set=index_set,
            position_id=hex(position_id),
        )
        
        return position_id
    
    def check_market_resolved(self, condition_id: bytes) -> bool:
        """
        检查市场是否已解析
        
        通过检查 payoutNumerators 是否非零来判断
        
        参数:
            condition_id: 条件 ID
        
        返回:
            市场是否已解析
        """
        try:
            payout_numerator = self.ctf_contract.functions.payoutNumerators(
                condition_id,
            ).call()
            
            is_resolved = payout_numerator > 0
            
            self.logger.debug(
                "检查市场解析状态",
                condition_id=condition_id.hex(),
                is_resolved=is_resolved,
                payout_numerator=payout_numerator,
            )
            
            return is_resolved
        except Exception as e:
            self.logger.warning(
                "检查市场解析状态失败",
                condition_id=condition_id.hex(),
                error=str(e),
            )
            return False
    
    def redeem_positions(
        self,
        condition_id: bytes,
        index_sets: Optional[List[int]] = None,
        gas_price: Optional[int] = None,
        wait_for_confirmation: bool = True,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """
        赎回获胜代币
        
        将已解析市场的获胜代币兑换为 USDC.e
        
        参数:
            condition_id: 条件 ID
            index_sets: 索引集列表，默认为 [1, 2]（同时赎回 Yes 和 No）
            gas_price: Gas 价格 (Gwei)，默认自动获取
            wait_for_confirmation: 是否等待交易确认
            timeout: 等待确认超时时间（秒）
        
        返回:
            包含交易信息的字典:
            - transaction_hash: 交易哈希
            - block_number: 区块号
            - gas_used: 实际 Gas 消耗
            - status: 交易状态 (1=成功, 0=失败)
        
        异常:
            InsufficientBalanceError: 余额不足
            TransactionFailedError: 交易失败
        """
        if self._account is None:
            raise CTFContractError("未设置私钥，无法签名交易")
        
        if index_sets is None:
            index_sets = [1, 2]
        
        parent_collection_id = b'\x00' * 32
        
        self.logger.info(
            "准备赎回代币",
            condition_id=condition_id.hex(),
            index_sets=index_sets,
        )
        
        try:
            nonce = self.web3.eth.get_transaction_count(self.account_address)
            
            if gas_price is None:
                current_gas_price = self.web3.eth.gas_price
                gas_price = int(current_gas_price * self._gas_price_multiplier)
            else:
                gas_price = self.web3.to_wei(gas_price, 'gwei')
            
            transaction = self.ctf_contract.functions.redeemPositions(
                self.usdc_address,
                parent_collection_id,
                condition_id,
                index_sets,
            ).build_transaction({
                'from': self.account_address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'chainId': POLYGON_CHAIN_ID,
            })
            
            estimated_gas = self.web3.eth.estimate_gas(transaction)
            transaction['gas'] = int(estimated_gas * self._gas_limit_buffer)
            
            self.logger.debug(
                "构建赎回交易",
                nonce=nonce,
                gas_price=self.web3.from_wei(gas_price, 'gwei'),
                estimated_gas=estimated_gas,
                gas_limit=transaction['gas'],
            )
            
            signed_txn = self._account.sign_transaction(transaction)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            self.logger.info(
                "赎回交易已提交",
                tx_hash=tx_hash.hex(),
            )
            
            if wait_for_confirmation:
                receipt = self.web3.eth.wait_for_transaction_receipt(
                    tx_hash,
                    timeout=timeout,
                )
                
                if receipt['status'] == 0:
                    raise TransactionFailedError(
                        f"赎回交易失败: {tx_hash.hex()}"
                    )
                
                self.logger.info(
                    "赎回交易已确认",
                    tx_hash=tx_hash.hex(),
                    block_number=receipt['blockNumber'],
                    gas_used=receipt['gasUsed'],
                )
                
                return {
                    'transaction_hash': tx_hash.hex(),
                    'block_number': receipt['blockNumber'],
                    'gas_used': receipt['gasUsed'],
                    'status': receipt['status'],
                    'effective_gas_price': receipt.get('effectiveGasPrice', 0),
                }
            else:
                return {
                    'transaction_hash': tx_hash.hex(),
                    'status': 'pending',
                }
                
        except ContractLogicError as e:
            self.logger.error(
                "合约逻辑错误",
                error=str(e),
                condition_id=condition_id.hex(),
            )
            raise TransactionFailedError(f"合约执行失败: {e}")
        
        except Exception as e:
            self.logger.error(
                "赎回交易失败",
                error=str(e),
                condition_id=condition_id.hex(),
            )
            raise TransactionFailedError(f"赎回交易失败: {e}")
    
    def batch_redeem_positions(
        self,
        condition_ids: List[bytes],
        index_sets: Optional[List[int]] = None,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        批量赎回多个市场的获胜代币
        
        参数:
            condition_ids: 条件 ID 列表
            index_sets: 索引集列表，默认为 [1, 2]
            max_retries: 最大重试次数
        
        返回:
            交易结果列表
        """
        results = []
        
        for i, condition_id in enumerate(condition_ids):
            self.logger.info(
                "批量赎回进度",
                current=i + 1,
                total=len(condition_ids),
                condition_id=condition_id.hex(),
            )
            
            for attempt in range(max_retries):
                try:
                    result = self.redeem_positions(
                        condition_id=condition_id,
                        index_sets=index_sets,
                    )
                    results.append({
                        'condition_id': condition_id.hex(),
                        'success': True,
                        'result': result,
                    })
                    break
                    
                except Exception as e:
                    self.logger.warning(
                        "赎回失败，准备重试",
                        condition_id=condition_id.hex(),
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                    )
                    
                    if attempt == max_retries - 1:
                        results.append({
                            'condition_id': condition_id.hex(),
                            'success': False,
                            'error': str(e),
                        })
        
        successful = sum(1 for r in results if r['success'])
        self.logger.info(
            "批量赎回完成",
            total=len(condition_ids),
            successful=successful,
            failed=len(condition_ids) - successful,
        )
        
        return results
    
    def check_and_redeem(
        self,
        condition_id: bytes,
        token_ids: List[int],
    ) -> Optional[Dict[str, Any]]:
        """
        检查市场是否已解析，如果是则赎回代币
        
        参数:
            condition_id: 条件 ID
            token_ids: 代币 ID 列表 [yes_token_id, no_token_id]
        
        返回:
            如果成功赎回则返回交易信息，否则返回 None
        """
        if not self.check_market_resolved(condition_id):
            self.logger.info(
                "市场尚未解析",
                condition_id=condition_id.hex(),
            )
            return None
        
        has_balance = False
        for token_id in token_ids:
            balance = self.get_token_balance(token_id)
            if balance > 0:
                has_balance = True
                self.logger.info(
                    "发现可赎回代币",
                    token_id=hex(token_id),
                    balance=str(balance),
                )
        
        if not has_balance:
            self.logger.info(
                "无可赎回代币",
                condition_id=condition_id.hex(),
            )
            return None
        
        return self.redeem_positions(condition_id)
