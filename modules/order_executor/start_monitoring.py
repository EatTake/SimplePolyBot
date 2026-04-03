"""
独立止损止盈监控启动脚本

作为独立进程运行 StopLossMonitor，
定期检查持仓状态并在触发止损/止盈条件时自动执行卖出订单。
与 settlement_worker 解耦，可独立部署和扩缩容。
"""

import asyncio
import signal
import sys
from typing import Any, Dict, Optional

from shared.logger import get_logger, setup_logging
from shared.config import Config, load_config
from shared.position_tracker import PositionTracker
from shared.redis_client import RedisClient, RedisConnectionConfig
from modules.order_executor.stop_loss_monitor import StopLossMonitor

logger = get_logger(__name__)


class MonitoringService:
    """
    止损止盈监控服务
    
    负责初始化和生命周期管理：
    - Redis 客户端（用于 PositionTracker 订阅 TRADE_RESULT_CHANNEL）
    - PositionTracker（持仓状态管理）
    - StopLossMonitor（止损止盈监控核心）
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self._redis_client: Optional[RedisClient] = None
        self._position_tracker: Optional[PositionTracker] = None
        self._stop_loss_monitor: Optional[StopLossMonitor] = None
        self._running = False

    def _initialize_redis(self) -> RedisClient:
        """初始化 Redis 客户端"""
        redis_config = self.config.get_redis_config()
        conn_config = RedisConnectionConfig(
            host=redis_config.host,
            port=redis_config.port,
            password=redis_config.password or None,
            db=redis_config.db,
            max_connections=redis_config.max_connections,
            min_connections=redis_config.min_idle_connections,
            connect_timeout=redis_config.connection_timeout,
            read_timeout=redis_config.socket_timeout,
            retry_attempts=redis_config.max_attempts,
            retry_delay=redis_config.retry_delay,
        )
        client = RedisClient(conn_config)
        if not client.connect():
            raise RuntimeError("无法连接到 Redis 服务器")
        return client

    def _build_sltp_config(self) -> Dict[str, Any]:
        """从配置中提取 stop_loss_take_profit 参数"""
        strategy_config = self.config.get_strategy_config()
        return {
            "stop_loss_take_profit": strategy_config.stop_loss_take_profit
        }

    def initialize(self) -> None:
        """初始化所有组件"""
        logger.info("开始初始化止损止盈监控服务")

        self._redis_client = self._initialize_redis()
        logger.info("Redis 客户端已连接")

        self._position_tracker = PositionTracker(redis_client=self._redis_client)
        logger.info("PositionTracker 已初始化")

        sltp_config = self._build_sltp_config()

        self._stop_loss_monitor = StopLossMonitor(
            order_manager=None,
            position_tracker=self._position_tracker,
            config=sltp_config,
        )
        logger.info(
            "StopLossMonitor 已初始化",
            enabled=self._stop_loss_monitor.enabled,
            stop_loss_pct=self._stop_loss_monitor.stop_loss_pct,
            take_profit_pct=self._stop_loss_monitor.take_profit_pct,
        )

    def start(self) -> None:
        """启动监控服务"""
        if self._running:
            logger.warning("监控服务已在运行中")
            return

        if self._stop_loss_monitor is None:
            raise RuntimeError("监控服务未初始化，请先调用 initialize()")

        self._running = True

        logger.info("启动止损止盈监控服务")

        self._position_tracker.subscribe_to_trade_results(self._redis_client)
        logger.info("PositionTracker 已订阅 TRADE_RESULT_CHANNEL")

        self._stop_loss_monitor.start()
        logger.info("StopLossMonitor 已启动")

    def stop(self) -> None:
        """优雅停止监控服务"""
        if not self._running:
            return

        logger.info("正在停止止损止盈监控服务...")

        self._running = False

        if self._stop_loss_monitor:
            self._stop_loss_monitor.stop()
            logger.info("StopLossMonitor 已停止")

        if self._position_tracker:
            self._position_tracker.unsubscribe()
            logger.info("PositionTracker 已取消订阅")

        if self._redis_client:
            self._redis_client.disconnect()
            logger.info("Redis 客户端已断开")

        logger.info("止损止盈监控服务已停止")

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            "running": self._running,
            "redis_connected": (
                self._redis_client is not None
                and getattr(self._redis_client, "_is_connected", False)
            ),
        }
        if self._stop_loss_monitor:
            status["monitor_stats"] = self._stop_loss_monitor.get_stats()
        if self._position_tracker:
            status["open_positions"] = len(
                self._position_tracker.get_open_positions()
            )
        return status


def main() -> None:
    """主函数"""
    setup_logging(log_level="INFO")

    logger.info("止损止盈监控服务启动中")

    service = MonitoringService()

    def _signal_handler(signum, frame):
        logger.info("接收到关闭信号", signal=signum)
        service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        service.initialize()
        service.start()

        logger.info("监控服务运行中，按 Ctrl+C 停止")

        while service._running:
            import time
            time.sleep(1)

    except Exception as e:
        logger.error("监控服务启动失败", error=str(e))
        service.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
