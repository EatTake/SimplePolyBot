"""
结算工作器模块入口

实现定时赎回任务：
- 每 10 分钟执行一次赎回周期
- 集成 CTF 合约交互与赎回管理器
- 实现优雅关闭逻辑
- 提供健康检查接口
"""

import asyncio
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from shared.logger import get_logger, setup_logging
from shared.config import Config, load_config
from shared.constants import POLYGON_RPC_URL
from shared.error_context import ErrorContext
from modules.settlement_worker.ctf_contract import CTFContract, CTFContractError
from modules.settlement_worker.redemption_manager import RedemptionManager


logger = get_logger(__name__)


class SettlementWorker:
    """
    结算工作器
    
    负责：
    1. 初始化 CTF 合约交互
    2. 初始化赎回管理器
    3. 执行定时赎回任务
    4. 管理优雅关闭
    5. 提供状态查询接口
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        check_interval: int = 600,
    ) -> None:
        """
        初始化结算工作器
        
        参数:
            config: 配置管理器实例
            check_interval: 检查间隔（秒），默认 600 秒（10 分钟）
        """
        self.config = config or Config.get_instance()
        self.check_interval = check_interval
        
        self._ctf_contract: Optional[CTFContract] = None
        self._redemption_manager: Optional[RedemptionManager] = None
        
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._last_run_time: Optional[datetime] = None
        self._last_run_result: Optional[Dict[str, Any]] = None
        self._total_runs = 0
        self._start_time: Optional[datetime] = None
        
        self._setup_signal_handlers()
        
        logger.info(
            "结算工作器已创建",
            check_interval=check_interval,
        )
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """
        信号处理器
        
        参数:
            signum: 信号编号
            frame: 当前栈帧
        """
        signal_name = signal.Signals(signum).name
        logger.info(
            "接收到关闭信号",
            signal=signal_name,
        )
        self._shutdown_event.set()
    
    def _initialize(self) -> None:
        """
        初始化组件
        
        异常:
            CTFContractError: 初始化失败
        """
        logger.info("开始初始化结算工作器组件")
        
        import os
        
        private_key = os.getenv("PRIVATE_KEY")
        if not private_key:
            raise CTFContractError("未设置 PRIVATE_KEY 环境变量")
        
        rpc_url = os.getenv("POLYGON_RPC_URL", POLYGON_RPC_URL)
        
        self._ctf_contract = CTFContract(
            rpc_url=rpc_url,
            private_key=private_key,
        )
        
        logger.info(
            "CTF 合约已初始化",
            address=self._ctf_contract.account_address,
        )
        
        self._redemption_manager = RedemptionManager(
            ctf_contract=self._ctf_contract,
            config=self.config,
        )
        
        logger.info("赎回管理器已初始化")
    
    async def run_once(self) -> Dict[str, Any]:
        """
        执行一次赎回周期
        
        返回:
            执行结果
        
        异常:
            RuntimeError: 如果工作器未初始化
        """
        if self._redemption_manager is None:
            raise RuntimeError("结算工作器未初始化")
        
        self._total_runs += 1
        self._last_run_time = datetime.now(timezone.utc)
        
        logger.info(
            "开始执行赎回周期",
            run_number=self._total_runs,
        )
        
        try:
            with ErrorContext("run_redemption_cycle", run_number=self._total_runs) as ctx:
                result = await self._redemption_manager.run_redemption_cycle()
                self._last_run_result = result
                
                logger.info(
                    "赎回周期执行完成",
                    run_number=self._total_runs,
                    successful=result.get('successful', 0),
                    failed=result.get('failed', 0),
                )
                
                return result
                
        except Exception as e:
            logger.error(
                "赎回周期执行失败",
                run_number=self._total_runs,
                error=str(e),
                error_context=ctx.to_dict(),
            )
            
            self._last_run_result = {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc),
            }
            
            raise
    
    async def run(self) -> None:
        """
        运行结算工作器主循环
        
        每 check_interval 秒执行一次赎回周期
        """
        if self._running:
            logger.warning("结算工作器已在运行中")
            return
        
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        
        logger.info(
            "结算工作器启动",
            check_interval=self.check_interval,
            start_time=self._start_time.isoformat(),
        )
        
        try:
            self._initialize()
            
            while not self._shutdown_event.is_set():
                try:
                    await self.run_once()
                    
                except Exception as e:
                    logger.error(
                        "赎回周期异常",
                        error=str(e),
                    )
                
                logger.info(
                    "等待下次检查",
                    interval_seconds=self.check_interval,
                )
                
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.check_interval,
                    )
                    logger.info("收到关闭信号，退出主循环")
                    break
                except asyncio.TimeoutError:
                    pass
            
        except Exception as e:
            logger.error(
                "结算工作器运行异常",
                error=str(e),
            )
            raise
        
        finally:
            await self._cleanup()
            self._running = False
    
    async def _cleanup(self) -> None:
        """清理资源"""
        logger.info("开始清理资源")
        
        if self._redemption_manager:
            await self._redemption_manager.close()
        
        logger.info("资源清理完成")
    
    def stop(self) -> None:
        """停止结算工作器"""
        logger.info("请求停止结算工作器")
        self._shutdown_event.set()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取工作器状态
        
        返回:
            状态信息字典
        """
        status = {
            'running': self._running,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'total_runs': self._total_runs,
            'last_run_time': self._last_run_time.isoformat() if self._last_run_time else None,
            'last_run_result': self._last_run_result,
            'check_interval': self.check_interval,
            'uptime_seconds': (
                (datetime.now(timezone.utc) - self._start_time).total_seconds()
                if self._start_time else 0
            ),
        }
        
        if self._redemption_manager:
            status['redemption_stats'] = self._redemption_manager.get_statistics()
        
        if self._ctf_contract:
            status['wallet_address'] = self._ctf_contract.account_address
        
        return status
    
    def get_health(self) -> Dict[str, Any]:
        """
        获取健康状态
        
        返回:
            健康状态字典
        """
        is_healthy = self._running
        
        issues = []
        
        if not self._running:
            issues.append("工作器未运行")
        
        if self._last_run_result and self._last_run_result.get('error'):
            issues.append(f"上次运行失败: {self._last_run_result['error']}")
        
        if self._redemption_manager:
            stats = self._redemption_manager.get_statistics()
            if stats['pending_redemptions'] > 10:
                issues.append(f"待重试赎回过多: {stats['pending_redemptions']}")
        
        return {
            'healthy': is_healthy and len(issues) == 0,
            'issues': issues,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }


async def main() -> None:
    """
    主函数
    
    加载配置并启动结算工作器
    """
    setup_logging(log_level="INFO")
    
    logger.info("结算工作器启动中")
    
    try:
        config = load_config(validate=False)
        
        module_config = config.get_module_config("settlement_worker")
        check_interval = module_config.config.get("settlement", {}).get("check_interval", 600)
        
        worker = SettlementWorker(
            config=config,
            check_interval=check_interval,
        )
        
        await worker.run()
        
    except Exception as e:
        logger.error(
            "结算工作器启动失败",
            error=str(e),
        )
        sys.exit(1)
    
    logger.info("结算工作器已退出")


def run_worker() -> None:
    """
    运行结算工作器入口函数
    
    用于命令行启动
    """
    asyncio.run(main())


if __name__ == "__main__":
    run_worker()
