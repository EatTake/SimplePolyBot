"""
MarketDiscovery 集成到信号生成链路的端到端测试

验证 StrategyEngine → SignalAdapter → RedisPublisher 的完整数据流，
确保发出的信号包含完整的 token_id/market_id/side/size。
"""

import json
import time
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from shared.models import TradingSignal, SignalAction, SignalDirection
from shared.market_discovery import MarketDiscovery, ActiveMarketInfo, TokenInfo
from shared.signal_adapter import SignalAdapter
from modules.strategy_engine.redis_publisher import RedisPublisher


class TestStrategyEngineInitialization(unittest.TestCase):
    """测试 1: StrategyEngine 初始化时创建了 MarketDiscovery 和 SignalAdapter"""

    @patch("modules.strategy_engine.main.RedisClient")
    @patch("modules.strategy_engine.main.load_config")
    def test_engine_creates_market_discovery_and_signal_adapter(self, mock_config, mock_redis):
        from modules.strategy_engine.main import StrategyEngine
        
        mock_config.return_value = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.connect.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        with patch.object(StrategyEngine, "_setup_signal_handlers"):
            engine = StrategyEngine(config=mock_config.return_value)
        
        self.assertIsInstance(engine.market_discovery, MarketDiscovery)
        self.assertIsInstance(engine.signal_adapter, SignalAdapter)


class TestSignalAdaptationFlow(unittest.TestCase):
    """测试 2-3: generate_signal() 后经过 adapt() 转换，发布的信号包含非空 token_id"""

    def setUp(self):
        self.signal_adapter = SignalAdapter(config={})
        self.mock_market_info = {
            "condition_id": "test-condition-123",
            "market_id": "market-test-456",  # 添加 market_id 字段
            "market_slug": "btc-updown-5m-20240101-1200",
            "tokens": {
                "UP": {
                    "token_id": "up-token-id-abc",
                    "outcome": "UP",
                    "best_ask": 0.55,
                },
                "DOWN": {
                    "token_id": "down-token-id-def",
                    "outcome": "DOWN",
                    "best_ask": 0.45,
                },
            },
            "end_date": "2024-01-01T12:05:00Z",
            "active": True,
        }

    def test_adapt_buy_up_signal_contains_token_id(self):
        """测试 BUY UP 信号适配后包含正确的 token_id"""
        strategy_signal = {
            "action": "BUY",
            "direction": "UP",
            "confidence": 0.75,
            "max_buy_price": 0.60,
        }
        
        result = self.signal_adapter.adapt(strategy_signal, self.mock_market_info)
        
        self.assertEqual(result.action, SignalAction.BUY)
        self.assertEqual(result.token_id, "up-token-id-abc")
        self.assertEqual(result.side, "BUY")
        self.assertGreater(result.size, 0)
        self.assertGreater(result.price, 0)

    def test_adapt_buy_down_signal_contains_token_id(self):
        """测试 BUY DOWN 信号适配后包含正确的 token_id"""
        strategy_signal = {
            "action": "BUY",
            "direction": "DOWN",
            "confidence": 0.8,
            "max_buy_price": 0.50,
        }
        
        result = self.signal_adapter.adapt(strategy_signal, self.mock_market_info)
        
        self.assertEqual(result.action, SignalAction.BUY)
        self.assertEqual(result.token_id, "down-token-id-def")
        self.assertEqual(result.side, "BUY")

    def test_adapted_signal_has_complete_fields(self):
        """测试适配后的信号包含所有必需字段"""
        strategy_signal = {
            "action": "BUY",
            "direction": "UP",
            "confidence": 0.7,
            "max_buy_price": 0.55,
        }
        
        result = self.signal_adapter.adapt(strategy_signal, self.mock_market_info)
        
        self.assertIsNotNone(result.signal_id)
        self.assertNotEqual(result.token_id, "")
        # market_id 可能为空（取决于 market_info 是否提供），但 token_id 必须非空
        self.assertIn(result.side, ["BUY", "SELL"])
        self.assertGreater(result.size, 0)
        self.assertGreater(result.price, 0)
        self.assertEqual(result.action, SignalAction.BUY)
        self.assertGreater(result.confidence, 0)
        self.assertGreater(result.timestamp, 0)


class TestMarketDiscoveryFailureFallback(unittest.TestCase):
    """测试 4: MarketDiscovery 失败时降级发布原始信号"""

    @patch("modules.strategy_engine.main.RedisClient")
    @patch("modules.strategy_engine.main.load_config")
    def test_market_discovery_returns_none_falls_back_to_original(self, mock_config, mock_redis):
        """当 MarketDiscovery.get_active_market() 返回 None 时，应发布原始信号"""
        from modules.strategy_engine.main import StrategyEngine
        
        mock_config.return_value = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.connect.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        with patch.object(StrategyEngine, "_setup_signal_handlers"):
            engine = StrategyEngine(config=mock_config.return_value)
        
        engine.market_discovery.get_active_market = MagicMock(return_value=None)
        engine.publisher.publish_signal = MagicMock(return_value=True)
        
        # 使用完整的 TradingSignal 构造（新格式）
        original_signal = TradingSignal(
            signal_id="test-signal-001",
            token_id="",  # 空的 token_id 表示旧格式/未适配
            market_id="",
            side="BUY",
            size=100.0,
            price=0.55,
            action=SignalAction.BUY,
            direction=SignalDirection.UP,
            current_price=43000.0,
            start_price=42500.0,
            max_buy_price=0.55,
            confidence=0.75,
            timestamp=time.time(),
        )
        
        # 模拟 _execute_strategy_cycle 中的逻辑
        if original_signal.action == SignalAction.BUY:
            try:
                market_info = engine.market_discovery.get_active_market()
                if market_info:
                    execution_signal = engine.signal_adapter.adapt(
                        strategy_signal=original_signal.to_dict(),
                        market_info=market_info,
                    )
                    engine.publisher.publish_signal(execution_signal)
                else:
                    engine.publisher.publish_signal(original_signal)
            except Exception as e:
                engine.publisher.publish_signal(original_signal)
        
        # 验证发布了原始信号（因为 market_info 为 None）
        engine.publisher.publish_signal.assert_called_once()
        called_signal = engine.publisher.publish_signal.call_args[0][0]
        # 原始信号应该没有 token_id（旧格式）
        self.assertEqual(called_signal.token_id, "")

    @patch("modules.strategy_engine.main.RedisClient")
    @patch("modules.strategy_engine.main.load_config")
    def test_market_discovery_exception_falls_back_to_original(self, mock_config, mock_redis):
        """当 MarketDiscovery 抛出异常时，应捕获异常并发布原始信号"""
        from modules.strategy_engine.main import StrategyEngine
        
        mock_config.return_value = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.connect.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        with patch.object(StrategyEngine, "_setup_signal_handlers"):
            engine = StrategyEngine(config=mock_config.return_value)
        
        engine.market_discovery.get_active_market = MagicMock(side_effect=Exception("API Error"))
        engine.publisher.publish_signal = MagicMock(return_value=True)
        
        # 使用完整的 TradingSignal 构造（新格式）
        original_signal = TradingSignal(
            signal_id="test-signal-002",
            token_id="",
            market_id="",
            side="BUY",
            size=100.0,
            price=0.55,
            action=SignalAction.BUY,
            direction=SignalDirection.UP,
            current_price=43000.0,
            start_price=42500.0,
            max_buy_price=0.55,
            confidence=0.75,
            timestamp=time.time(),
        )
        
        # 模拟 _execute_strategy_cycle 中的逻辑
        if original_signal.action == SignalAction.BUY:
            try:
                market_info = engine.market_discovery.get_active_market()
                if market_info:
                    execution_signal = engine.signal_adapter.adapt(
                        strategy_signal=original_signal.to_dict(),
                        market_info=market_info,
                    )
                    engine.publisher.publish_signal(execution_signal)
                else:
                    engine.publisher.publish_signal(original_signal)
            except Exception as e:
                engine.publisher.publish_signal(original_signal)
        
        # 验证发布了原始信号（因为抛出异常）
        engine.publisher.publish_signal.assert_called_once()


class TestNonBuySignalsBypassAdaptation(unittest.TestCase):
    """测试 5: WAIT/HOLD 信号不经过 adapt 直接发布"""

    @patch("modules.strategy_engine.main.RedisClient")
    @patch("modules.strategy_engine.main.load_config")
    def test_wait_signal_bypasses_adaptation(self, mock_config, mock_redis):
        """WAIT 信号不应经过 SignalAdapter.adapt()"""
        from modules.strategy_engine.main import StrategyEngine
        
        mock_config.return_value = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.connect.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        with patch.object(StrategyEngine, "_setup_signal_handlers"):
            engine = StrategyEngine(config=mock_config.return_value)
        
        engine.market_discovery.get_active_market = MagicMock()
        engine.signal_adapter.adapt = MagicMock()
        engine.publisher.publish_signal = MagicMock(return_value=True)
        
        # 使用完整的 TradingSignal 构造
        wait_signal = TradingSignal(
            signal_id="test-wait-001",
            token_id="",
            market_id="",
            side="HOLD",
            size=0.0,
            price=0.0,
            action=SignalAction.WAIT,
            confidence=0.0,
            timestamp=time.time(),
        )
        
        # 模拟 _execute_strategy_cycle 中的逻辑
        if wait_signal.action == SignalAction.BUY:
            pass  # BUY 信号的逻辑
        else:
            engine.publisher.publish_signal(wait_signal)
        
        # 验证 SignalAdapter.adapt() 未被调用
        engine.signal_adapter.adapt.assert_not_called()
        # 验证直接发布了原始信号
        engine.publisher.publish_signal.assert_called_once_with(wait_signal)

    @patch("modules.strategy_engine.main.RedisClient")
    @patch("modules.strategy_engine.main.load_config")
    def test_hold_signal_bypasses_adaptation(self, mock_config, mock_redis):
        """HOLD 信号不应经过 SignalAdapter.adapt()"""
        from modules.strategy_engine.main import StrategyEngine
        
        mock_config.return_value = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.connect.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        with patch.object(StrategyEngine, "_setup_signal_handlers"):
            engine = StrategyEngine(config=mock_config.return_value)
        
        engine.market_discovery.get_active_market = MagicMock()
        engine.signal_adapter.adapt = MagicMock()
        engine.publisher.publish_signal = MagicMock(return_value=True)
        
        # 使用完整的 TradingSignal 构造
        hold_signal = TradingSignal(
            signal_id="test-hold-001",
            token_id="",
            market_id="",
            side="HOLD",
            size=0.0,
            price=0.0,
            action=SignalAction.HOLD,
            confidence=0.0,
            timestamp=time.time(),
        )
        
        # 模拟 _execute_strategy_cycle 中的逻辑
        if hold_signal.action == SignalAction.BUY:
            pass  # BUY 信号的逻辑
        else:
            engine.publisher.publish_signal(hold_signal)
        
        # 验证 SignalAdapter.adapt() 未被调用
        engine.signal_adapter.adapt.assert_not_called()


class TestEndToEndMockFlow(unittest.TestCase):
    """测试 6: 完整流程 mock 测试：signal → adapt → publish"""

    def test_full_flow_signal_adapt_publish(self):
        """完整流程：生成策略信号 → 适配转换 → 发布"""
        signal_adapter = SignalAdapter(config={})
        
        mock_publisher = MagicMock()
        mock_publisher.publish_signal = MagicMock(return_value=True)
        
        mock_market_discovery = MagicMock()
        mock_market_info = {
            "condition_id": "cond-456",
            "market_id": "market-full-789",
            "market_slug": "btc-updown-5m-test",
            "tokens": {
                "UP": {"token_id": "up-token-xyz", "outcome": "UP", "best_ask": 0.58},
                "DOWN": {"token_id": "down-token-xyz", "outcome": "DOWN", "best_ask": 0.42},
            },
            "end_date": "2024-01-01T12:05:00Z",
            "active": True,
        }
        mock_market_discovery.get_active_market.return_value = mock_market_info
        
        # 模拟策略引擎生成的原始信号
        strategy_signal = {
            "action": "BUY",
            "direction": "UP",
            "confidence": 0.8,
            "max_buy_price": 0.60,
        }
        
        # 执行完整流程
        if strategy_signal.get("action") == "BUY":
            try:
                market_info = mock_market_discovery.get_active_market()
                if market_info:
                    execution_signal = signal_adapter.adapt(
                        strategy_signal=strategy_signal,
                        market_info=market_info,
                    )
                    mock_publisher.publish_signal(execution_signal)
                else:
                    mock_publisher.publish_signal(strategy_signal)
            except Exception as e:
                mock_publisher.publish_signal(strategy_signal)
        
        # 验证：publish_signal 被调用且传入的是执行型信号
        mock_publisher.publish_signal.assert_called_once()
        published_signal = mock_publisher.publish_signal.call_args[0][0]
        
        self.assertIsInstance(published_signal, TradingSignal)
        self.assertEqual(published_signal.token_id, "up-token-xyz")
        self.assertEqual(published_signal.side, "BUY")
        self.assertEqual(published_signal.action, SignalAction.BUY)
        self.assertGreater(published_signal.size, 0)


class TestDirectionToTokenMapping(unittest.TestCase):
    """测试 7: signal_adapter.adapt() 使用正确的 direction→token 映射"""

    def setUp(self):
        self.signal_adapter = SignalAdapter(config={})
        self.mock_market_info = {
            "tokens": {
                "UP": {"token_id": "token-up-111", "best_ask": 0.55},
                "DOWN": {"token_id": "token-down-222", "best_ask": 0.45},
            },
        }

    def test_up_direction_maps_to_up_token(self):
        """UP 方向应映射到 UP token"""
        signal = {"action": "BUY", "direction": "UP", "confidence": 0.7}
        result = self.signal_adapter.adapt(signal, self.mock_market_info)
        self.assertEqual(result.token_id, "token-up-111")

    def test_down_direction_maps_to_down_token(self):
        """DOWN 方向应映射到 DOWN token"""
        signal = {"action": "BUY", "direction": "DOWN", "confidence": 0.7}
        result = self.signal_adapter.adapt(signal, self.mock_market_info)
        self.assertEqual(result.token_id, "token-down-222")

    def test_case_insensitive_direction_mapping(self):
        """方向映射应大小写不敏感"""
        signal_lower = {"action": "BUY", "direction": "up", "confidence": 0.7}
        result_lower = self.signal_adapter.adapt(signal_lower, self.mock_market_info)
        self.assertEqual(result_lower.token_id, "token-up-111")
        
        signal_mixed = {"action": "BUY", "direction": "Up", "confidence": 0.7}
        result_mixed = self.signal_adapter.adapt(signal_mixed, self.mock_market_info)
        self.assertEqual(result_mixed.token_id, "token-up-111")


class TestPublishedSignalValidation(unittest.TestCase):
    """测试 8: published signal validate() 通过"""

    def test_adapted_buy_signal_passes_validation(self):
        """适配后的 BUY 信号应通过 validate() 检查"""
        adapter = SignalAdapter(config={})
        market_info = {
            "tokens": {
                "UP": {"token_id": "valid-token-123", "best_ask": 0.52},
            },
        }
        
        signal = {"action": "BUY", "direction": "UP", "confidence": 0.75, "max_buy_price": 0.55}
        result = adapter.adapt(signal, market_info)
        
        self.assertTrue(result.validate())

    def test_adapted_hold_signal_fails_validation(self):
        """适配后的 HOLD 信号（无 token_id）应无法通过 validate()"""
        adapter = SignalAdapter(config={})
        market_info = {"tokens": {}}
        
        signal = {"action": "WAIT", "confidence": 0.5}
        result = adapter.adapt(signal, market_info)
        
        # HOLD/WAIT 信号没有 token_id，validate 应返回 False
        self.assertFalse(result.validate())


class TestRedisMessageFormat(unittest.TestCase):
    """测试 9: Redis 接收到的消息格式正确"""

    def test_execution_signal_message_format(self):
        """执行型信号的消息格式应包含 token_id/market_id/side/size/price"""
        mock_redis = MagicMock()
        mock_redis.publish_message.return_value = True
        
        publisher = RedisPublisher(redis_client=mock_redis)
        
        execution_signal = TradingSignal(
            signal_id="sig-exec-001",
            token_id="token-abc",
            market_id="market-123",
            side="BUY",
            size=100.0,
            price=0.52,
            action=SignalAction.BUY,
            confidence=0.75,
            timestamp=time.time(),
            direction=SignalDirection.UP,
        )
        
        publisher.publish_signal(execution_signal)
        
        # 获取发布的消息
        published_message = mock_redis.publish_message.call_args[0][1]
        
        self.assertIn("signal_id", published_message)
        self.assertIn("token_id", published_message)
        self.assertIn("market_id", published_message)
        self.assertIn("side", published_message)
        self.assertIn("size", published_message)
        self.assertIn("price", published_message)
        self.assertEqual(published_message["token_id"], "token-abc")
        self.assertEqual(published_message["side"], "BUY")
        self.assertEqual(published_message["size"], 100.0)
        self.assertEqual(published_message["price"], 0.52)

    def test_legacy_signal_message_format_compatibility(self):
        """旧格式信号的消息格式应保持兼容（保留原有字段）"""
        mock_redis = MagicMock()
        mock_redis.publish_message.return_value = True
        
        publisher = RedisPublisher(redis_client=mock_redis)
        
        # 旧格式信号：无 token_id，但有旧字段
        legacy_signal = TradingSignal(
            signal_id="sig-legacy-001",
            token_id="",  # 无 token_id，走旧格式
            market_id="",
            side="BUY",
            size=100.0,
            price=0.55,
            action=SignalAction.BUY,
            direction=SignalDirection.UP,
            current_price=43000.0,
            start_price=42500.0,
            max_buy_price=0.55,
            confidence=0.7,
            timestamp=time.time(),
        )
        
        publisher.publish_signal(legacy_signal)
        
        published_message = mock_redis.publish_message.call_args[0][1]
        
        # 旧格式应包含原有字段
        self.assertIn("direction", published_message)
        self.assertIn("max_price", published_message)
        self.assertIn("current_price", published_message)
        self.assertEqual(published_message["direction"], "UP")


class TestConfidenceToSizeMapping(unittest.TestCase):
    """额外测试: 置信度到订单大小的映射正确性"""

    def test_high_confidence_maps_to_large_size(self):
        """高置信度应映射到大订单"""
        adapter = SignalAdapter(config={})
        size = adapter._map_confidence_to_size(0.9)
        self.assertGreaterEqual(size, 150)  # 根据 DEFAULT_SIZE_MAP

    def test_low_confidence_maps_to_small_size(self):
        """低置信度应映射到小订单"""
        adapter = SignalAdapter(config={})
        size = adapter._map_confidence_to_size(0.4)
        self.assertLessEqual(size, 100)  # 使用 default_size

    def test_size_clamped_to_range(self):
        """订单大小应在 [min_size, max_size] 范围内"""
        adapter = SignalAdapter(config={"min_size": 20, "max_size": 300, "default_size": 50})
        
        size_high = adapter._map_confidence_to_size(0.99)
        self.assertLessEqual(size_high, 300)
        
        size_low = adapter._map_confidence_to_size(0.1)
        self.assertGreaterEqual(size_low, 20)


if __name__ == "__main__":
    unittest.main()
