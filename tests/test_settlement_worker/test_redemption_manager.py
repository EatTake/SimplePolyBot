"""
赎回管理器模块测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from decimal import Decimal

from modules.settlement_worker.redemption_manager import (
    RedemptionManager,
    MarketInfo,
    RedemptionResult,
)
from modules.settlement_worker.ctf_contract import CTFContract


class TestMarketInfo:
    """市场信息数据类测试"""
    
    def test_market_info_creation(self):
        """测试市场信息创建"""
        condition_id = bytes(32)
        question_id = bytes(32)
        token_ids = [12345, 67890]
        
        market = MarketInfo(
            condition_id=condition_id,
            question_id=question_id,
            token_ids=token_ids,
            resolved=True,
            question="Test market?",
        )
        
        assert market.condition_id == condition_id
        assert market.question_id == question_id
        assert market.token_ids == token_ids
        assert market.resolved is True
        assert market.question == "Test market?"
    
    def test_market_info_defaults(self):
        """测试市场信息默认值"""
        market = MarketInfo(
            condition_id=bytes(32),
            question_id=bytes(32),
            token_ids=[],
            resolved=False,
        )
        
        assert market.resolution_date is None
        assert market.question == ""
        assert market.oracle == "0x6A9D222616C90FcA5754cd1333cFD9b7fb6a4F74"


class TestRedemptionResult:
    """赎回结果数据类测试"""
    
    def test_redemption_result_success(self):
        """测试成功的赎回结果"""
        result = RedemptionResult(
            condition_id="abcd" + "0" * 60,
            success=True,
            transaction_hash="0x" + "1" * 64,
            amount_redeemed=Decimal("100"),
        )
        
        assert result.success is True
        assert result.transaction_hash is not None
        assert result.amount_redeemed == Decimal("100")
        assert result.error is None
    
    def test_redemption_result_failure(self):
        """测试失败的赎回结果"""
        result = RedemptionResult(
            condition_id="abcd" + "0" * 60,
            success=False,
            error="交易失败",
        )
        
        assert result.success is False
        assert result.transaction_hash is None
        assert result.error == "交易失败"
    
    def test_redemption_result_timestamp(self):
        """测试赎回结果时间戳"""
        before = datetime.now(timezone.utc)
        result = RedemptionResult(
            condition_id="abcd" + "0" * 60,
            success=True,
        )
        after = datetime.now(timezone.utc)
        
        assert before <= result.timestamp <= after


class TestRedemptionManager:
    """赎回管理器测试类"""
    
    @pytest.fixture
    def mock_ctf_contract(self):
        """创建 Mock CTF 合约实例"""
        contract = MagicMock(spec=CTFContract)
        contract.account_address = "0x1234567890123456789012345678901234567890"
        contract.get_token_balance.return_value = Decimal("100")
        contract.get_usdc_balance.return_value = Decimal("1000")
        contract.get_pol_balance.return_value = Decimal("1")
        contract.check_market_resolved.return_value = True
        contract.redeem_positions.return_value = {
            'transaction_hash': '0x' + '1' * 64,
            'block_number': 12345,
            'gas_used': 50000,
            'status': 1,
        }
        return contract
    
    @pytest.fixture
    def mock_config(self):
        """创建 Mock 配置实例"""
        config = MagicMock()
        config.get_module_config.return_value.config = {
            'settlement': {
                'check_interval': 600,
            }
        }
        return config
    
    @pytest.fixture
    def redemption_manager(self, mock_ctf_contract, mock_config):
        """创建赎回管理器实例"""
        return RedemptionManager(
            ctf_contract=mock_ctf_contract,
            config=mock_config,
        )
    
    @pytest.mark.asyncio
    async def test_fetch_resolved_markets(self, redemption_manager):
        """测试获取已解析市场列表"""
        mock_response = [
            {
                "conditionId": "0x" + "a" * 64,
                "questionId": "0x" + "b" * 64,
                "tokens": [
                    {"token_id": "12345"},
                    {"token_id": "67890"},
                ],
                "resolved": True,
                "resolutionDate": "2024-01-01T00:00:00Z",
                "question": "Test market?",
            }
        ]
        
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.is_closed = False
        
        redemption_manager._http_client = mock_client
        
        markets = await redemption_manager.fetch_resolved_markets()
        
        assert len(markets) == 1
        assert markets[0].resolved is True
        assert markets[0].question == "Test market?"
    
    @pytest.mark.asyncio
    async def test_fetch_resolved_markets_error(self, redemption_manager):
        """测试获取已解析市场列表失败"""
        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            MockClient.return_value = mock_client
            
            redemption_manager._http_client = mock_client
            
            markets = await redemption_manager.fetch_resolved_markets()
            
            assert markets == []
    
    @pytest.mark.asyncio
    async def test_check_winning_token_balance(self, redemption_manager, mock_ctf_contract):
        """测试检查获胜代币余额"""
        token_ids = [12345, 67890]
        
        mock_ctf_contract.get_token_balance.side_effect = [
            Decimal("100"),
            Decimal("0"),
        ]
        
        balances = await redemption_manager.check_winning_token_balance(token_ids)
        
        assert 12345 in balances
        assert balances[12345] == Decimal("100")
        assert 67890 not in balances
    
    @pytest.mark.asyncio
    async def test_redeem_market_success(self, redemption_manager, mock_ctf_contract):
        """测试成功赎回市场"""
        market = MarketInfo(
            condition_id=bytes(32),
            question_id=bytes(32),
            token_ids=[12345, 67890],
            resolved=True,
            question="Test market?",
        )
        
        result = await redemption_manager.redeem_market(market)
        
        assert result.success is True
        assert result.transaction_hash is not None
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_redeem_market_failure_with_retry(self, redemption_manager, mock_ctf_contract):
        """测试赎回失败并重试"""
        market = MarketInfo(
            condition_id=bytes(32),
            question_id=bytes(32),
            token_ids=[12345, 67890],
            resolved=True,
            question="Test market?",
        )
        
        from modules.settlement_worker.ctf_contract import CTFContractError
        mock_ctf_contract.redeem_positions.side_effect = CTFContractError("交易失败")
        
        result = await redemption_manager.redeem_market(market, retry_count=0)
        
        assert result.success is False
        assert "交易失败" in result.error
        
        condition_id_hex = market.condition_id.hex()
        assert condition_id_hex in redemption_manager._pending_redemptions
    
    @pytest.mark.asyncio
    async def test_redeem_market_max_retries_exceeded(self, redemption_manager, mock_ctf_contract):
        """测试赎回超过最大重试次数"""
        market = MarketInfo(
            condition_id=bytes(32),
            question_id=bytes(32),
            token_ids=[12345, 67890],
            resolved=True,
            question="Test market?",
        )
        
        from modules.settlement_worker.ctf_contract import CTFContractError
        mock_ctf_contract.redeem_positions.side_effect = CTFContractError("交易失败")
        
        result = await redemption_manager.redeem_market(market, retry_count=3)
        
        assert result.success is False
        assert "重试 3 次后仍然失败" in result.error
        
        condition_id_hex = market.condition_id.hex()
        assert condition_id_hex in redemption_manager._failed_redemptions
    
    @pytest.mark.asyncio
    async def test_batch_redeem_markets(self, redemption_manager):
        """测试批量赎回"""
        markets = [
            MarketInfo(
                condition_id=bytes([i] + [0] * 31),
                question_id=bytes(32),
                token_ids=[12345, 67890],
                resolved=True,
                question=f"Test market {i}?",
            )
            for i in range(3)
        ]
        
        results = await redemption_manager.batch_redeem_markets(markets)
        
        assert len(results) == 3
        assert all(isinstance(r, RedemptionResult) for r in results)
    
    @pytest.mark.asyncio
    async def test_check_pol_balance(self, redemption_manager, mock_ctf_contract):
        """测试检查 POL 余额"""
        result = await redemption_manager.check_pol_balance()
        
        assert 'balance' in result
        assert 'min_required' in result
        assert 'is_low' in result
        assert result['balance'] == Decimal("1")
    
    @pytest.mark.asyncio
    async def test_check_usdc_balance(self, redemption_manager, mock_ctf_contract):
        """测试检查 USDC 余额"""
        result = await redemption_manager.check_usdc_balance()
        
        assert 'balance' in result
        assert 'min_required' in result
        assert 'is_low' in result
        assert result['balance'] == Decimal("1000")
    
    @pytest.mark.asyncio
    async def test_run_redemption_cycle(self, redemption_manager):
        """测试执行完整赎回周期"""
        with patch.object(
            redemption_manager,
            'get_redeemable_markets',
            return_value=[]
        ):
            result = await redemption_manager.run_redemption_cycle()
            
            assert 'timestamp' in result
            assert 'elapsed_seconds' in result
            assert 'pol_balance' in result
            assert 'usdc_balance' in result
            assert 'total_redemptions' in result
    
    def test_get_statistics(self, redemption_manager):
        """测试获取统计信息"""
        stats = redemption_manager.get_statistics()
        
        assert 'total_redemptions' in stats
        assert 'successful_redemptions' in stats
        assert 'failed_redemptions' in stats
        assert 'success_rate' in stats
        assert 'total_amount_redeemed' in stats
    
    def test_add_to_history(self, redemption_manager):
        """测试添加到历史记录"""
        result = RedemptionResult(
            condition_id="abcd" + "0" * 60,
            success=True,
            transaction_hash="0x" + "1" * 64,
            amount_redeemed=Decimal("100"),
        )
        
        redemption_manager._add_to_history(result)
        
        assert len(redemption_manager._redemption_history) == 1
        assert redemption_manager._redemption_history[0] == result
    
    def test_get_redemption_history(self, redemption_manager):
        """测试获取赎回历史"""
        for i in range(5):
            result = RedemptionResult(
                condition_id=f"{i}" + "0" * 63,
                success=i % 2 == 0,
            )
            redemption_manager._add_to_history(result)
        
        history = redemption_manager.get_redemption_history(limit=3)
        
        assert len(history) == 3
    
    def test_get_redemption_history_only_successful(self, redemption_manager):
        """测试只获取成功的赎回历史"""
        for i in range(5):
            result = RedemptionResult(
                condition_id=f"{i}" + "0" * 63,
                success=i % 2 == 0,
            )
            redemption_manager._add_to_history(result)
        
        history = redemption_manager.get_redemption_history(only_successful=True)
        
        assert all(r.success for r in history)
    
    @pytest.mark.asyncio
    async def test_close(self, redemption_manager):
        """测试关闭 HTTP 客户端"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        redemption_manager._http_client = mock_client
        
        await redemption_manager.close()
        
        mock_client.aclose.assert_called_once()
