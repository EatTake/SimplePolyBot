"""
结算工作器主模块测试
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from modules.settlement_worker.main import SettlementWorker


class TestSettlementWorker:
    """结算工作器测试类"""
    
    @pytest.fixture
    def mock_config(self):
        """创建 Mock 配置实例"""
        config = MagicMock()
        config.get_module_config.return_value.config = {
            'settlement': {
                'check_interval': 60,
            }
        }
        return config
    
    @pytest.fixture
    def worker(self, mock_config):
        """创建结算工作器实例"""
        return SettlementWorker(
            config=mock_config,
            check_interval=60,
        )
    
    def test_initialization(self, worker):
        """测试初始化"""
        assert worker.check_interval == 60
        assert worker._running is False
        assert worker._total_runs == 0
    
    def test_signal_handler(self, worker):
        """测试信号处理器"""
        import signal
        
        worker._signal_handler(signal.SIGINT, None)
        
        assert worker._shutdown_event.is_set()
    
    @patch.dict('os.environ', {
        'PRIVATE_KEY': '0x' + '1' * 64,
        'POLYGON_RPC_URL': 'https://polygon-rpc.com',
    })
    def test_initialize(self, worker):
        """测试初始化组件"""
        worker._initialize()
        
        assert worker._ctf_contract is not None
        assert worker._redemption_manager is not None
    
    def test_initialize_without_private_key(self, worker):
        """测试无私钥时初始化失败"""
        import os
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):
                worker._initialize()
    
    @pytest.mark.asyncio
    async def test_run_once(self, worker):
        """测试执行一次赎回周期"""
        worker._redemption_manager = AsyncMock()
        worker._redemption_manager.run_redemption_cycle.return_value = {
            'successful': 1,
            'failed': 0,
        }
        
        result = await worker.run_once()
        
        assert result['successful'] == 1
        assert worker._total_runs == 1
        assert worker._last_run_time is not None
    
    @pytest.mark.asyncio
    async def test_run_once_without_manager(self, worker):
        """测试未初始化时执行失败"""
        with pytest.raises(RuntimeError, match="未初始化"):
            await worker.run_once()
    
    @pytest.mark.asyncio
    async def test_run_once_with_error(self, worker):
        """测试执行时发生错误"""
        worker._redemption_manager = AsyncMock()
        worker._redemption_manager.run_redemption_cycle.side_effect = Exception("测试错误")
        
        with pytest.raises(Exception, match="测试错误"):
            await worker.run_once()
    
    @pytest.mark.asyncio
    async def test_run(self, worker):
        """测试运行主循环"""
        worker._initialize = MagicMock()
        worker._redemption_manager = AsyncMock()
        worker._redemption_manager.run_redemption_cycle.return_value = {
            'successful': 1,
            'failed': 0,
        }
        worker._redemption_manager.close = AsyncMock()
        
        async def set_shutdown_after_delay():
            await asyncio.sleep(0.1)
            worker._shutdown_event.set()
        
        asyncio.create_task(set_shutdown_after_delay())
        
        await worker.run()
        
        assert worker._total_runs >= 1
        assert worker._running is False
    
    @pytest.mark.asyncio
    async def test_run_already_running(self, worker):
        """测试重复运行"""
        worker._running = True
        
        await worker.run()
        
        assert worker._total_runs == 0
    
    def test_stop(self, worker):
        """测试停止工作器"""
        worker.stop()
        
        assert worker._shutdown_event.is_set()
    
    def test_get_status(self, worker):
        """测试获取状态"""
        worker._start_time = datetime.now(timezone.utc)
        worker._total_runs = 5
        worker._last_run_time = datetime.now(timezone.utc)
        worker._last_run_result = {'successful': 1}
        worker._redemption_manager = MagicMock()
        worker._redemption_manager.get_statistics.return_value = {
            'total_redemptions': 10,
        }
        worker._ctf_contract = MagicMock()
        worker._ctf_contract.account_address = "0x1234"
        
        status = worker.get_status()
        
        assert status['running'] is False
        assert status['total_runs'] == 5
        assert 'uptime_seconds' in status
        assert 'redemption_stats' in status
        assert 'wallet_address' in status
    
    def test_get_health_healthy(self, worker):
        """测试健康状态 - 健康"""
        worker._running = True
        
        health = worker.get_health()
        
        assert health['healthy'] is True
        assert len(health['issues']) == 0
    
    def test_get_health_not_running(self, worker):
        """测试健康状态 - 未运行"""
        worker._running = False
        
        health = worker.get_health()
        
        assert health['healthy'] is False
        assert "工作器未运行" in health['issues']
    
    def test_get_health_with_error(self, worker):
        """测试健康状态 - 有错误"""
        worker._running = True
        worker._last_run_result = {'error': '测试错误'}
        
        health = worker.get_health()
        
        assert health['healthy'] is False
        assert any("测试错误" in issue for issue in health['issues'])
    
    def test_get_health_with_pending_redemptions(self, worker):
        """测试健康状态 - 待重试过多"""
        worker._running = True
        worker._redemption_manager = MagicMock()
        worker._redemption_manager.get_statistics.return_value = {
            'pending_redemptions': 15,
        }
        
        health = worker.get_health()
        
        assert health['healthy'] is False
        assert any("待重试赎回过多" in issue for issue in health['issues'])
    
    @pytest.mark.asyncio
    async def test_cleanup(self, worker):
        """测试清理资源"""
        worker._redemption_manager = AsyncMock()
        worker._redemption_manager.close = AsyncMock()
        
        await worker._cleanup()
        
        worker._redemption_manager.close.assert_called_once()


class TestSettlementWorkerIntegration:
    """结算工作器集成测试"""
    
    @pytest.mark.skip(reason="需要完整环境和真实私钥")
    @pytest.mark.asyncio
    async def test_full_cycle(self):
        """测试完整周期"""
        import os
        
        private_key = os.getenv("TEST_PRIVATE_KEY")
        if not private_key:
            pytest.skip("未设置 TEST_PRIVATE_KEY 环境变量")
        
        worker = SettlementWorker(check_interval=10)
        
        async def stop_after_delay():
            await asyncio.sleep(15)
            worker.stop()
        
        asyncio.create_task(stop_after_delay())
        
        await worker.run()
        
        assert worker._total_runs >= 1
