"""
CTF 合约交互模块测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from decimal import Decimal
from web3 import Web3

from modules.settlement_worker.ctf_contract import (
    CTFContract,
    CTFContractError,
    InsufficientBalanceError,
    TransactionFailedError,
)


class TestCTFContract:
    """CTF 合约交互测试类"""
    
    @pytest.fixture
    def mock_web3(self):
        """创建 Mock Web3 实例"""
        web3 = MagicMock()
        web3.is_connected.return_value = True
        
        web3.eth = MagicMock()
        web3.eth.chain_id = 137
        web3.eth.get_balance.return_value = 10 ** 18
        web3.eth.gas_price = 30 * 10 ** 9
        web3.eth.get_transaction_count.return_value = 1
        web3.eth.estimate_gas.return_value = 100000
        
        web3.to_checksum_address = Web3.to_checksum_address
        web3.to_wei = Web3.to_wei
        web3.from_wei = Web3.from_wei
        
        web3.eth.send_raw_transaction = MagicMock()
        web3.eth.send_raw_transaction.return_value = bytes.fromhex('abcd' * 16)
        
        web3.eth.wait_for_transaction_receipt = MagicMock()
        web3.eth.wait_for_transaction_receipt.return_value = {
            'status': 1,
            'blockNumber': 12345,
            'gasUsed': 50000,
            'effectiveGasPrice': 30 * 10 ** 9,
        }
        
        return web3
    
    @pytest.fixture
    def mock_ctf_contract(self):
        """创建 Mock CTF 合约实例"""
        contract = MagicMock()
        
        contract.functions.balanceOf.return_value.call.return_value = 100 * 10 ** 6
        
        contract.functions.payoutNumerators.return_value.call.return_value = 1
        
        contract.functions.getConditionId.return_value.call.return_value = bytes(32)
        
        contract.functions.getCollectionId.return_value.call.return_value = bytes(32)
        
        contract.functions.getPositionId.return_value.call.return_value = 12345
        
        build_transaction = MagicMock()
        build_transaction.return_value = {
            'from': '0x1234567890123456789012345678901234567890',
            'nonce': 1,
            'gasPrice': 33 * 10 ** 9,
            'chainId': 137,
        }
        contract.functions.redeemPositions.return_value.build_transaction = build_transaction
        
        return contract
    
    @pytest.fixture
    def mock_usdc_contract(self):
        """创建 Mock USDC 合约实例"""
        contract = MagicMock()
        contract.functions.balanceOf.return_value.call.return_value = 1000 * 10 ** 6
        return contract
    
    @pytest.fixture
    def ctf_contract(self, mock_web3, mock_ctf_contract, mock_usdc_contract):
        """创建 CTF 合约实例"""
        test_private_key = '0x' + '1' * 64
        
        with patch('modules.settlement_worker.ctf_contract.Web3') as MockWeb3:
            MockWeb3.return_value = mock_web3
            MockWeb3.HTTPProvider = MagicMock()
            MockWeb3.to_checksum_address = Web3.to_checksum_address
            MockWeb3.to_wei = Web3.to_wei
            MockWeb3.from_wei = Web3.from_wei
            
            ctf = CTFContract(
                rpc_url="https://polygon-rpc.com",
                private_key=test_private_key,
            )
            
            ctf._web3 = mock_web3
            ctf._ctf_contract = mock_ctf_contract
            ctf._usdc_contract = mock_usdc_contract
            
            return ctf
    
    def test_initialization(self, ctf_contract):
        """测试初始化"""
        assert ctf_contract.rpc_url == "https://polygon-rpc.com"
        assert ctf_contract.ctf_address == Web3.to_checksum_address(
            "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
        )
        assert ctf_contract.usdc_address == Web3.to_checksum_address(
            "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
        )
    
    def test_get_token_balance(self, ctf_contract):
        """测试查询代币余额"""
        balance = ctf_contract.get_token_balance(token_id=12345)
        
        assert isinstance(balance, Decimal)
        assert balance == Decimal("100")
    
    def test_get_usdc_balance(self, ctf_contract):
        """测试查询 USDC 余额"""
        balance = ctf_contract.get_usdc_balance()
        
        assert isinstance(balance, Decimal)
        assert balance == Decimal("1000")
    
    def test_get_pol_balance(self, ctf_contract, mock_web3):
        """测试查询 POL 余额"""
        balance = ctf_contract.get_pol_balance()
        
        assert isinstance(balance, Decimal)
        assert balance == Decimal("1")
    
    def test_check_market_resolved_true(self, ctf_contract):
        """测试检查市场已解析"""
        condition_id = bytes(32)
        
        is_resolved = ctf_contract.check_market_resolved(condition_id)
        
        assert is_resolved is True
    
    def test_check_market_resolved_false(self, ctf_contract, mock_ctf_contract):
        """测试检查市场未解析"""
        condition_id = bytes(32)
        
        mock_ctf_contract.functions.payoutNumerators.return_value.call.return_value = 0
        
        is_resolved = ctf_contract.check_market_resolved(condition_id)
        
        assert is_resolved is False
    
    def test_get_condition_id(self, ctf_contract):
        """测试计算条件 ID"""
        oracle = "0x6A9D222616C90FcA5754cd1333cFD9b7fb6a4F74"
        question_id = bytes(32)
        
        condition_id = ctf_contract.get_condition_id(oracle, question_id)
        
        assert isinstance(condition_id, bytes)
        assert len(condition_id) == 32
    
    def test_get_position_id(self, ctf_contract):
        """测试计算位置 ID"""
        condition_id = bytes(32)
        index_set = 1
        
        position_id = ctf_contract.get_position_id(condition_id, index_set)
        
        assert isinstance(position_id, int)
    
    def test_redeem_positions_success(self, ctf_contract, mock_web3):
        """测试成功赎回代币"""
        condition_id = bytes(32)
        
        mock_account = MagicMock()
        mock_account.address = '0x1234567890123456789012345678901234567890'
        mock_account.sign_transaction.return_value.raw_transaction = b'signed_transaction'
        
        ctf_contract._account = mock_account
        
        result = ctf_contract.redeem_positions(condition_id)
        
        assert result['status'] == 1
        assert 'transaction_hash' in result
        assert 'block_number' in result
        assert 'gas_used' in result
    
    def test_redeem_positions_without_private_key(self, ctf_contract):
        """测试无私钥时赎回失败"""
        ctf_contract._account = None
        condition_id = bytes(32)
        
        with pytest.raises(CTFContractError, match="未设置私钥"):
            ctf_contract.redeem_positions(condition_id)
    
    def test_redeem_positions_transaction_failed(self, ctf_contract, mock_web3):
        """测试赎回交易失败"""
        condition_id = bytes(32)
        
        mock_account = MagicMock()
        mock_account.address = '0x1234567890123456789012345678901234567890'
        mock_account.sign_transaction.return_value.raw_transaction = b'signed_transaction'
        
        ctf_contract._account = mock_account
        
        mock_web3.eth.wait_for_transaction_receipt.return_value = {
            'status': 0,
            'blockNumber': 12345,
            'gasUsed': 50000,
        }
        
        with pytest.raises(TransactionFailedError, match="赎回交易失败"):
            ctf_contract.redeem_positions(condition_id)
    
    def test_batch_redeem_positions(self, ctf_contract):
        """测试批量赎回"""
        condition_ids = [bytes(32), bytes(32)]
        
        mock_account = MagicMock()
        mock_account.address = '0x1234567890123456789012345678901234567890'
        mock_account.sign_transaction.return_value.raw_transaction = b'signed_transaction'
        
        ctf_contract._account = mock_account
        
        results = ctf_contract.batch_redeem_positions(condition_ids)
        
        assert len(results) == 2
        assert all('condition_id' in r for r in results)
    
    def test_account_address_property(self, ctf_contract):
        """测试账户地址属性"""
        address = ctf_contract.account_address
        
        assert address.startswith("0x")
        assert len(address) == 42
    
    def test_account_address_without_private_key(self, ctf_contract):
        """测试无私钥时获取账户地址失败"""
        ctf_contract._account = None
        
        with pytest.raises(CTFContractError, match="未设置私钥"):
            _ = ctf_contract.account_address


class TestCTFContractIntegration:
    """CTF 合约集成测试类（需要测试网）"""
    
    @pytest.mark.skip(reason="需要测试网环境和真实私钥")
    def test_real_polygon_connection(self):
        """测试真实 Polygon 网络连接"""
        ctf = CTFContract(
            rpc_url="https://polygon-rpc.com",
        )
        
        assert ctf.web3.is_connected()
        assert ctf.web3.eth.chain_id == 137
    
    @pytest.mark.skip(reason="需要测试网环境和真实私钥")
    def test_real_balance_query(self):
        """测试真实余额查询"""
        import os
        
        private_key = os.getenv("TEST_PRIVATE_KEY")
        if not private_key:
            pytest.skip("未设置 TEST_PRIVATE_KEY 环境变量")
        
        ctf = CTFContract(
            rpc_url="https://polygon-rpc.com",
            private_key=private_key,
        )
        
        pol_balance = ctf.get_pol_balance()
        usdc_balance = ctf.get_usdc_balance()
        
        assert isinstance(pol_balance, Decimal)
        assert isinstance(usdc_balance, Decimal)
