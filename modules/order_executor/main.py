"""
订单执行器模块主入口

集成 Redis 订阅者、CLOB 客户端、手续费计算、订单管理器
实现主循环监听交易信号并执行订单
"""

import signal
import sys
import time
from typing import Optional

import structlog

from modules.order_executor.redis_subscriber import RedisSubscriber, TradingSignal
from modules.order_executor.clob_client import ClobClientWrapper, ClobClientError
from modules.order_executor.fee_calculator import FeeCalculator
from modules.order_executor.order_manager import OrderManager, OrderResult
from shared.config import Config, load_config
from shared.logger import setup_logging
from shared.constants import TRADING_SIGNAL_CHANNEL, TRADE_RESULT_CHANNEL
from shared.redis_client import RedisClient, RedisConnectionConfig

logger = structlog.get_logger()


class OrderExecutor:
    """
    订单执行器
    
    集成所有组件，监听交易信号并执行订单
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化订单执行器
        
        Args:
            config: 配置实例
        """
        self.config = config or Config.get_instance()
        
        self._setup_logging()
        
        self.clob_client: Optional[ClobClientWrapper] = None
        self.fee_calculator: Optional[FeeCalculator] = None
        self.order_manager: Optional[OrderManager] = None
        self.redis_subscriber: Optional[RedisSubscriber] = None
        self.redis_client: Optional[RedisClient] = None
        
        self._running = False
        self._shutdown_requested = False
        
        self._setup_signal_handlers()
        
        logger.info("初始化订单执行器")
    
    def _setup_logging(self) -> None:
        """设置日志"""
        log_level = self.config.get("system.log_level", "INFO")
        setup_logging(log_level=log_level)
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        """信号处理函数"""
        logger.info("接收到关闭信号", signal=signum)
        self._shutdown_requested = True
    
    def initialize(self) -> None:
        """
        初始化所有组件
        """
        try:
            logger.info("开始初始化订单执行器组件")
            
            logger.info("初始化 CLOB 客户端")
            self.clob_client = ClobClientWrapper()
            self.clob_client.initialize()
            
            logger.info("初始化手续费计算器")
            self.fee_calculator = FeeCalculator()
            
            logger.info("初始化订单管理器")
            self.order_manager = OrderManager(
                clob_client=self.clob_client,
                fee_calculator=self.fee_calculator,
                config=self.config
            )
            
            logger.info("初始化 Redis 客户端")
            redis_config = self.config.get_redis_config()
            redis_conn_config = RedisConnectionConfig(
                host=redis_config.host,
                port=redis_config.port,
                password=redis_config.password if redis_config.password else None,
                db=redis_config.db,
                max_connections=redis_config.max_connections,
                min_connections=redis_config.min_idle_connections,
                connect_timeout=redis_config.connection_timeout,
                read_timeout=redis_config.socket_timeout,
                retry_attempts=redis_config.max_attempts,
                retry_delay=redis_config.retry_delay,
            )
            self.redis_client = RedisClient(redis_conn_config)
            self.redis_client.connect()
            
            logger.info("初始化 Redis 订阅者")
            self.redis_subscriber = RedisSubscriber(
                redis_client=self.redis_client,
                signal_handler=self._handle_trading_signal,
                config=self.config
            )
            
            logger.info("订单执行器初始化完成")
            
        except Exception as e:
            logger.error("初始化订单执行器失败", error=str(e))
            raise
    
    def _handle_trading_signal(self, signal: TradingSignal) -> None:
        """
        处理交易信号
        
        Args:
            signal: 交易信号
        """
        try:
            logger.info(
                "处理交易信号",
                signal_id=signal.signal_id,
                token_id=signal.token_id,
                side=signal.side,
                price=signal.price,
                size=signal.size,
                confidence=signal.confidence,
                strategy=signal.strategy
            )
            
            if signal.confidence < 0.6:
                logger.info(
                    "信号置信度过低，忽略",
                    signal_id=signal.signal_id,
                    confidence=signal.confidence
                )
                return
            
            result: OrderResult | None = None
            
            if self.order_manager is None:
                logger.error("订单管理器未初始化")
                return
            
            if signal.side == "BUY":
                result = self.order_manager.execute_buy_order(
                    token_id=signal.token_id,
                    size=signal.size,
                    max_price=signal.price,
                    category=signal.metadata.get("category")
                )
            elif signal.side == "SELL":
                result = self.order_manager.execute_sell_order(
                    token_id=signal.token_id,
                    size=signal.size,
                    min_price=signal.price,
                    category=signal.metadata.get("category")
                )
            else:
                logger.warning(
                    "未知的交易方向",
                    signal_id=signal.signal_id,
                    side=signal.side
                )
                return
            
            if result:
                self._publish_trade_result(signal, result)
            
        except Exception as e:
            logger.error(
                "处理交易信号异常",
                signal_id=signal.signal_id,
                error=str(e)
            )
    
    def _publish_trade_result(
        self,
        signal: TradingSignal,
        result: OrderResult
    ) -> None:
        """
        发布交易结果到 Redis
        
        Args:
            signal: 原始交易信号
            result: 订单执行结果
        """
        try:
            if self.redis_client is None:
                logger.error("Redis 客户端未初始化，无法发布交易结果")
                return
            
            trade_result = {
                "signal_id": signal.signal_id,
                "token_id": signal.token_id,
                "market_id": signal.market_id,
                "strategy": signal.strategy,
                "order_result": result.to_dict(),
                "timestamp": int(time.time())
            }
            
            self.redis_client.publish_message(
                channel=TRADE_RESULT_CHANNEL,
                message=trade_result
            )
            
            logger.info(
                "发布交易结果",
                signal_id=signal.signal_id,
                success=result.success,
                order_id=result.order_id
            )
            
        except Exception as e:
            logger.error(
                "发布交易结果失败",
                signal_id=signal.signal_id,
                error=str(e)
            )
    
    def start(self) -> None:
        """
        启动订单执行器
        """
        if self._running:
            logger.warning("订单执行器已在运行")
            return
        
        self._running = True
        
        logger.info("启动订单执行器")
        
        try:
            if self.redis_subscriber is None:
                logger.error("Redis 订阅者未初始化")
                return
            
            self.redis_subscriber.start()
            
            logger.info("订单执行器已启动，等待交易信号...")
            
            while self._running and not self._shutdown_requested:
                time.sleep(1)
                
        except Exception as e:
            logger.error("订单执行器运行异常", error=str(e))
        finally:
            self.stop()
    
    def stop(self) -> None:
        """
        停止订单执行器
        """
        if not self._running:
            return
        
        logger.info("停止订单执行器")
        
        self._running = False
        
        if self.redis_subscriber:
            self.redis_subscriber.stop()
        
        if self.redis_client:
            self.redis_client.disconnect()
        
        logger.info("订单执行器已停止")
    
    def get_status(self) -> dict:
        """
        获取订单执行器状态
        
        Returns:
            状态字典
        """
        status = {
            "running": self._running,
            "shutdown_requested": self._shutdown_requested,
            "components": {
                "clob_client": self.clob_client is not None,
                "fee_calculator": self.fee_calculator is not None,
                "order_manager": self.order_manager is not None,
                "redis_subscriber": self.redis_subscriber is not None if self.redis_subscriber else False,
                "redis_client": self.redis_client._is_connected if self.redis_client else False,
            }
        }
        
        if self.order_manager:
            status["order_statistics"] = self.order_manager.get_statistics()
        
        if self.redis_subscriber:
            status["subscriber_stats"] = self.redis_subscriber.get_stats()
        
        return status


def main() -> None:
    """主函数"""
    try:
        config = load_config(
            env_file=".env",
            config_file="settings.yaml",
            validate=True
        )
        
        executor = OrderExecutor(config)
        executor.initialize()
        executor.start()
        
    except Exception as e:
        logger.error("订单执行器启动失败", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
