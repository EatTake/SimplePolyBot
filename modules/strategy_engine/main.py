"""
策略引擎主模块

集成所有子模块，实现完整的策略分析流程
支持每秒执行一次策略判断和优雅关闭
"""

import queue
import signal
import sys
import time
from typing import Optional, Dict, Any, List

from shared.logger import get_logger
from shared.config import Config, load_config
from shared.redis_client import RedisClient, RedisConnectionConfig
from shared.constants import MARKET_DATA_CHANNEL, FAST_MARKET_DURATION_SECONDS, TRADE_RESULT_CHANNEL
from shared.error_context import ErrorContext

from modules.strategy_engine.redis_subscriber import RedisSubscriber
from modules.strategy_engine.price_queue import PriceQueue
from modules.strategy_engine.ols_regression import OLSRegression
from modules.strategy_engine.safety_cushion import SafetyCushionCalculator
from modules.strategy_engine.signal_generator import SignalGenerator, SignalAction
from modules.strategy_engine.market_lifecycle import MarketLifecycleManager
from modules.strategy_engine.redis_publisher import RedisPublisher
from shared.position_tracker import PositionTracker
from shared.market_discovery import MarketDiscovery
from shared.signal_adapter import SignalAdapter


logger = get_logger(__name__)


class StrategyEngine:
    """
    策略引擎类
    
    集成所有子模块，实现完整的策略分析流程
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化策略引擎
        
        Args:
            config: 配置对象，默认自动加载
        """
        self.config = config or load_config()
        
        self._initialize_components()
        
        self._running = False
        self._shutdown_requested = False
        
        self._message_buffer: queue.Queue = queue.Queue(maxsize=1000)
        self._last_batch_process_time = 0.0
        self._batch_size_threshold = 10
        self._batch_timeout_seconds = 1.0
        self._last_cycle_id = None
        
        self._setup_signal_handlers()
        
        logger.info("策略引擎初始化完成")
    
    def _initialize_components(self) -> None:
        """初始化所有组件"""
        redis_config = self.config.get_redis_config()
        
        redis_connection_config = RedisConnectionConfig(
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
        
        self.redis_client = RedisClient(redis_connection_config)
        
        if not self.redis_client.connect():
            raise RuntimeError("无法连接到 Redis 服务器")
        
        self.price_queue = PriceQueue(window_seconds=180)
        
        self.regression = OLSRegression(min_samples=10)
        
        self.safety_cushion = SafetyCushionCalculator()
        
        self.signal_generator = SignalGenerator()
        
        self.lifecycle_manager = MarketLifecycleManager(
            cycle_duration=FAST_MARKET_DURATION_SECONDS
        )
        
        self.publisher = RedisPublisher(self.redis_client)

        self.market_discovery = MarketDiscovery(
            redis_client=self.redis_client,
            config=self.config,
        )
        self.signal_adapter = SignalAdapter(config=self.config)

        self.position_tracker = PositionTracker(redis_client=self.redis_client)
        self.position_tracker.subscribe_to_trade_results(self.redis_client)
        
        self.subscriber = RedisSubscriber(
            redis_client=self.redis_client,
            message_handler=self._handle_market_data,
            channels=[MARKET_DATA_CHANNEL],
        )
        
        logger.info("所有组件初始化完成（含 TRADE_RESULT_CHANNEL 订阅）")
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.debug("信号处理器已设置")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """
        信号处理函数
        
        Args:
            signum: 信号编号
            frame: 栈帧
        """
        logger.info("接收到关闭信号", signal=signum)
        self._shutdown_requested = True
    
    def start(self) -> None:
        """启动策略引擎"""
        if self._running:
            logger.warn("策略引擎已在运行中")
            return
        
        logger.info("启动策略引擎")
        
        self._running = True
        self._shutdown_requested = False
        
        if not self.subscriber.start():
            logger.error("Redis 订阅者启动失败")
            return
        
        logger.info("策略引擎已启动，开始主循环")
        
        self._main_loop()
    
    def stop(self) -> None:
        """停止策略引擎"""
        if not self._running:
            return
        
        logger.info("正在停止策略引擎")
        
        self._running = False
        self._shutdown_requested = True
        
        if hasattr(self, "position_tracker") and self.position_tracker:
            self.position_tracker.unsubscribe()
        
        self.subscriber.stop()
        
        self.redis_client.disconnect()
        
        logger.info("策略引擎已停止")
    
    def _main_loop(self) -> None:
        """
        主循环
        
        每秒执行一次策略判断
        """
        last_check_time: float = 0.0
        check_interval = 1.0
        
        while self._running and not self._shutdown_requested:
            try:
                current_time = time.time()
                
                if current_time - last_check_time >= check_interval:
                    self._flush_message_buffer()
                    self._execute_strategy_cycle()
                    last_check_time = current_time
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error("主循环异常", error=str(e))
                time.sleep(1)
        
        self.stop()
    
    def _execute_strategy_cycle(self) -> None:
        try:
            with ErrorContext("execute_strategy_cycle", price_queue_size=self.price_queue.size()) as ctx:
                cycle = self.lifecycle_manager.get_current_cycle()
                
                if cycle.start_price is None and self.price_queue.size() > 0:
                    start_price = self.price_queue.get_earliest_price()
                    if start_price is not None:
                        self.lifecycle_manager.set_start_price(start_price)
                        logger.info(
                            "设置周期起始价格",
                            cycle_id=cycle.cycle_id,
                            start_price=start_price
                        )
                
                if cycle.cycle_id != self._last_cycle_id:
                    old_cycle_id = self._last_cycle_id
                    queue_size_before_clear = self.price_queue.size()
                    
                    logger.info(
                        "检测到周期切换，清空 PriceQueue",
                        old_cycle_id=old_cycle_id,
                        new_cycle_id=cycle.cycle_id,
                        queue_size_before_clear=queue_size_before_clear
                    )
                    
                    self.price_queue.clear()
                    self._last_cycle_id = cycle.cycle_id
                
                timestamps, prices = self.price_queue.get_timestamps_and_prices()
                
                if len(prices) < 10:
                    logger.debug("价格数据不足，跳过策略判断", price_count=len(prices))
                    return
                
                regression_result = self.regression.fit(timestamps, prices)
                
                if regression_result is None:
                    logger.debug("回归分析失败，跳过策略判断")
                    return
                
                current_price = prices[-1]
                start_price = cycle.start_price or prices[0]
                
                signal = self.signal_generator.generate_signal(
                    current_price=current_price,
                    start_price=start_price,
                    slope_k=regression_result.slope,
                    r_squared=regression_result.r_squared,
                    time_remaining=cycle.time_remaining,
                )
                
                if self._check_duplicate_signal():
                    logger.debug("重复信号检查通过，跳过本次信号发布")
                    return
                
                # 通过 SignalAdapter 转换为执行型信号（仅 BUY 信号需要转换）
                if signal.action == SignalAction.BUY:
                    try:
                        market_info = self.market_discovery.get_active_market()
                        if market_info:
                            execution_signal = self.signal_adapter.adapt(
                                strategy_signal=signal.to_dict(),
                                market_info=market_info,
                            )
                            self.publisher.publish_signal(execution_signal)
                        else:
                            logger.warning("无法获取活跃市场信息，发布原始信号")
                            self.publisher.publish_signal(signal)
                    except Exception as e:
                        logger.error("信号适配失败，发布原始信号", error=str(e))
                        self.publisher.publish_signal(signal)
                else:
                    self.publisher.publish_signal(signal)
                
                logger.info(
                    "策略周期执行完成",
                    action=signal.action.value,
                    direction=signal.direction.value if signal.direction else None,
                    current_price=current_price,
                    slope=regression_result.slope,
                    r_squared=regression_result.r_squared,
                    time_remaining=cycle.time_remaining
                )
        except Exception as e:
            logger.error("策略周期执行异常", error=str(e), error_context=ctx.to_dict())
    
    def _process_messages_batch(self, messages: List[Dict[str, Any]]) -> None:
        """
        批量处理消息（顺序处理保证时序）
        
        所有消息统一按 timestamp 排序后逐条顺序处理，
        确保时间序列数据的时序正确性，避免并行处理导致的数据乱序
        
        Args:
            messages: 消息列表
        """
        start_time = time.time()
        
        sorted_messages = sorted(
            messages,
            key=lambda m: m.get("timestamp") or m.get("_timestamp") or 0.0
        )
        
        for msg in sorted_messages:
            self._handle_single_message(msg)
        
        duration = time.time() - start_time
        logger.info(
            "批量消息处理完成",
            count=len(messages),
            duration=round(duration, 3)
        )
    
    def _handle_single_message(self, data: Dict[str, Any]) -> None:
        """
        处理单条市场数据（内部方法）
        
        Args:
            data: 市场数据字典
        """
        price = data.get("price")
        timestamp = data.get("timestamp") or data.get("_timestamp")
        
        if price is None:
            logger.warn("市场数据缺少价格字段", data=data)
            return
        
        if timestamp is None:
            timestamp = time.time()
        
        self.price_queue.push(price=price, timestamp=timestamp)
        
        logger.debug(
            "市场数据已处理",
            price=price,
            timestamp=timestamp,
            queue_size=self.price_queue.size()
        )
    
    def _flush_message_buffer(self) -> None:
        """刷新消息缓冲区，触发批量处理"""
        messages_to_process = []
        while not self._message_buffer.empty():
            try:
                messages_to_process.append(self._message_buffer.get_nowait())
            except queue.Empty:
                break
        
        if messages_to_process:
            self._last_batch_process_time = time.time()
            self._process_messages_batch(messages_to_process)
    
    def _check_and_flush_buffer(self) -> None:
        """检查是否需要刷新缓冲区（基于时间或大小）"""
        current_time = time.time()
        
        should_flush = (
            self._message_buffer.qsize() >= self._batch_size_threshold or
            (self._message_buffer.qsize() > 0 and 
             (current_time - self._last_batch_process_time) >= self._batch_timeout_seconds)
        )
        
        if should_flush:
            self._flush_message_buffer()

    def _handle_market_data(self, data: Dict[str, Any]) -> None:
        """
        处理市场数据（入口方法）
        
        将消息添加到缓冲区，根据批量策略决定是否立即处理
        
        Args:
            data: 市场数据字典
        """
        try:
            with ErrorContext("handle_market_data", price=data.get("price")) as ctx:
                try:
                    self._message_buffer.put_nowait(data)
                except queue.Full:
                    logger.warning("消息缓冲区已满，丢弃消息")
                self._check_and_flush_buffer()
        except Exception as e:
            logger.error("处理市场数据异常", error=str(e), error_context=ctx.to_dict(), data=data)

    def _handle_trade_result(self, data: Dict[str, Any]) -> None:
        """
        处理交易结果反馈
        
        接收来自 order_executor 的交易执行结果，
        通过 PositionTracker 更新持仓状态，实现策略引擎感知闭环。
        
        Args:
            data: 交易结果字典，包含 token_id、result 等字段
        """
        try:
            result = data.get("result", {})
            order_result = data.get("order_result", {})
            token_id = data.get("token_id", "")
            success = order_result.get("success", False) if order_result else result.get("success", False)

            self.position_tracker.update_from_trade_result(data)

            logger.info(
                "收到交易结果反馈",
                token_id=token_id,
                success=success,
                open_positions=len(self.position_tracker.get_open_positions()),
            )
        except Exception as e:
            logger.error("处理交易结果反馈失败", error=str(e))

    def _check_duplicate_signal(self) -> bool:
        """
        重复信号检查框架
        
        在生成信号前检查当前持仓状态，
        避免对已有持仓的同一方向重复下单。
        
        Returns:
            True 表示应跳过信号生成（存在重复风险），
            False 表示可以正常生成信号。
        """
        open_positions = self.position_tracker.get_open_positions()

        if not open_positions:
            return False

        for pos in open_positions:
            if pos.quantity > 1e-9:
                target_token_id = getattr(pos, "token_id", "")
                if target_token_id:
                    logger.debug(
                        "已有持仓，跳过信号生成",
                        token_id=target_token_id,
                        quantity=pos.quantity,
                    )
                    return True

        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取引擎状态

        Returns:
            状态信息字典
        """
        status = {
            "running": self._running,
            "shutdown_requested": self._shutdown_requested,
            "price_queue_size": self.price_queue.size(),
            "publisher_stats": self.publisher.get_statistics(),
            "subscriber_running": self.subscriber.is_running(),
        }
        
        if hasattr(self, "position_tracker") and self.position_tracker:
            status["open_positions_count"] = len(
                self.position_tracker.get_open_positions()
            )
            status["total_exposure"] = self.position_tracker.get_total_exposure()
        
        return status


def main() -> None:
    """主函数"""
    try:
        logger.info("正在启动策略引擎...")
        
        config = load_config()
        
        engine = StrategyEngine(config)
        
        engine.start()
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭...")
    except Exception as e:
        logger.error("策略引擎启动失败", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
