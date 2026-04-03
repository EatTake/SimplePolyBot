"""
统一 TradingSignal 数据结构集成测试

验证策略引擎和订单执行器使用相同的 TradingSignal 定义，
确保信号在两个模块之间的序列化/反序列化兼容性。
"""

import pytest

from shared.models import (
    TradingSignal,
    SignalAction,
    SignalDirection,
    generate_signal_id,
)
from modules.strategy_engine.signal_generator import SignalGenerator


class TestSignalUnifiedStructure:
    """测试统一 TradingSignal 数据结构"""

    def test_signal_generator_contains_execution_fields(self):
        """
        测试 1: signal_generator 生成的信号包含执行所需字段
        
        验证 signal_generator 生成的信号包含 token_id, signal_id, 
        market_id, side, size, price 等执行器需要的字段
        """
        generator = SignalGenerator(
            min_time_remaining=10.0,
            max_time_remaining=100.0,
            min_price_difference=0.01,
            min_r_squared=0.5,
            min_confidence=0.6,
        )

        signal = generator.generate_signal(
            current_price=0.50,
            start_price=0.45,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
        )

        assert hasattr(signal, "signal_id"), "信号缺少 signal_id 字段"
        assert hasattr(signal, "token_id"), "信号缺少 token_id 字段"
        assert hasattr(signal, "market_id"), "信号缺少 market_id 字段"
        assert hasattr(signal, "side"), "信号缺少 side 字段"
        assert hasattr(signal, "size"), "信号缺少 size 字段"
        assert hasattr(signal, "price"), "信号缺少 price 字段"

        assert isinstance(signal.signal_id, str)
        assert len(signal.signal_id) > 0
        assert isinstance(signal.token_id, str)
        assert isinstance(signal.market_id, str)
        assert signal.side in ["BUY", "SELL", "HOLD"]
        assert isinstance(signal.size, float)
        assert isinstance(signal.price, float)

    def test_to_dict_output_parseable_by_from_dict(self):
        """
        测试 2: signal_generator.to_dict() 输出可被 from_dict() 解析
        
        验证信号序列化为字典后可以完整反序列化，且字段保持一致
        """
        generator = SignalGenerator()

        original_signal = generator.generate_signal(
            current_price=0.52,
            start_price=0.47,
            slope_k=0.0008,
            r_squared=0.85,
            time_remaining=60.0,
        )

        signal_dict = original_signal.to_dict()

        restored_signal = TradingSignal.from_dict(signal_dict)

        assert restored_signal.signal_id == original_signal.signal_id
        assert restored_signal.action == original_signal.action
        assert restored_signal.direction == original_signal.direction
        assert restored_signal.current_price == original_signal.current_price
        assert restored_signal.start_price == original_signal.start_price
        assert restored_signal.price_difference == pytest.approx(
            original_signal.price_difference, rel=1e-6
        )
        assert restored_signal.max_buy_price == pytest.approx(
            original_signal.max_buy_price, rel=1e-6
        )
        assert restored_signal.confidence == pytest.approx(
            original_signal.confidence, rel=1e-6
        )
        assert restored_signal.side == original_signal.side
        assert restored_signal.price == pytest.approx(
            original_signal.price, rel=1e-6
        )

    def test_validate_passes_for_valid_signal(self):
        """
        测试 3: validate() 对有效信号通过
        
        构造一个完整的有效交易信号，验证校验逻辑正确放行
        """
        valid_signal = TradingSignal(
            signal_id=generate_signal_id(),
            token_id="test_token_123",
            market_id="market_456",
            side="BUY",
            size=10.0,
            price=0.55,
            action=SignalAction.BUY,
            confidence=0.75,
            timestamp=__import__("time").time(),
            strategy="fast_market",
            direction=SignalDirection.UP,
            current_price=0.58,
            start_price=0.53,
            price_difference=0.05,
            max_buy_price=0.55,
            safety_cushion=0.03,
            slope_k=0.001,
            r_squared=0.88,
            time_remaining=45.0,
        )

        assert valid_signal.validate() is True

    def test_same_dataclass_type_between_modules(self):
        """
        测试 4: 两端使用相同的 dataclass 类型 (isinstance 检查)
        
        验证从 shared.models 导入的 TradingSignal 与 signal_generator
        和 redis_subscriber 使用的是同一个类
        """
        from modules.strategy_engine.signal_generator import TradingSignal as SgSignal
        from modules.order_executor.redis_subscriber import TradingSignal as RsSignal

        generator = SignalGenerator()
        signal_from_generator = generator.generate_signal(
            current_price=0.50,
            start_price=0.45,
            slope_k=0.001,
            r_squared=0.9,
            time_remaining=50.0,
        )

        assert isinstance(signal_from_generator, TradingSignal)
        assert isinstance(signal_from_generator, SgSignal)
        assert isinstance(signal_from_generator, RsSignal)

        assert SgSignal is RsSignal
        assert SgSignal is TradingSignal

    def test_enum_serialization_deserialization_compatible(self):
        """
        测试 5: 枚举值序列化/反序列化兼容
        
        验证 SignalAction 和 SignalDirection 枚举在 to_dict/from_dict 
        过程中能正确转换
        """
        test_cases = [
            (SignalAction.BUY, SignalDirection.UP),
            (SignalAction.BUY, SignalDirection.DOWN),
            (SignalAction.WAIT, None),
            (SignalAction.HOLD, None),
        ]

        for action, direction in test_cases:
            signal = TradingSignal(
                signal_id=generate_signal_id(),
                token_id="token_test",
                market_id="market_test",
                side="BUY" if action == SignalAction.BUY else "HOLD",
                size=5.0,
                price=0.50,
                action=action,
                confidence=0.7,
                timestamp=__import__("time").time(),
                direction=direction,
            )

            signal_dict = signal.to_dict()

            assert signal_dict["action"] == action.value
            if direction:
                assert signal_dict["direction"] == direction.value
            else:
                assert signal_dict["direction"] is None

            restored = TradingSignal.from_dict(signal_dict)
            assert restored.action == action
            assert restored.direction == direction

    def test_backward_compatibility_missing_optional_fields(self):
        """
        测试 6: 向后兼容 - 缺少可选字段时有默认值
        
        验证当字典中缺少部分可选字段时，from_dict 能使用默认值填充
        """
        minimal_dict = {
            "signal_id": "test-signal-001",
            "token_id": "minimal-token",
            "market_id": "minimal-market",
            "side": "BUY",
            "size": 10.0,
            "price": 0.50,
            "action": "BUY",
            "confidence": 0.80,
            "timestamp": 1700000000.0,
        }

        signal = TradingSignal.from_dict(minimal_dict)

        assert signal.signal_id == "test-signal-001"
        assert signal.token_id == "minimal-token"
        assert signal.market_id == "minimal-market"
        assert signal.side == "BUY"
        assert signal.size == 10.0
        assert signal.price == 0.50
        assert signal.action == SignalAction.BUY
        assert signal.confidence == 0.80

        assert signal.strategy == "fast_market", "strategy 应有默认值"
        assert signal.direction is None, "direction 缺失时应为 None"
        assert signal.current_price == 0.0, "current_price 应有默认值"
        assert signal.start_price == 0.0, "start_price 应有默认值"
        assert signal.price_difference == 0.0, "price_difference 应有默认值"
        assert signal.metadata == {}, "metadata 应有默认空字典"

    def test_full_roundtrip_with_strategy_fields(self):
        """
        额外测试: 完整往返测试 - 包含所有策略分析字段
        
        确保策略引擎生成的完整信号（含分析字段）经过序列化/反序列化
        后所有字段都保留
        """
        import time as time_module

        generator = SignalGenerator()
        original = generator.generate_signal(
            current_price=0.54321,
            start_price=0.49876,
            slope_k=0.00123,
            r_squared=0.9234,
            time_remaining=73.5,
        )

        serialized = original.to_dict()
        deserialized = TradingSignal.from_dict(serialized)

        strategy_fields = [
            "current_price", "start_price", "price_difference",
            "max_buy_price", "safety_cushion", "slope_k",
            "r_squared", "time_remaining", "confidence",
        ]

        for field in strategy_fields:
            orig_val = getattr(original, field)
            deser_val = getattr(deserialized, field)
            assert deser_val == pytest.approx(orig_val, rel=1e-6), \
                f"字段 {field} 不匹配: {orig_val} vs {deser_val}"

        execution_fields = [
            "signal_id", "token_id", "market_id", "side", "size", "price",
            "action", "strategy", "timestamp",
        ]

        for field in execution_fields:
            orig_val = getattr(original, field)
            deser_val = getattr(deserialized, field)
            assert deser_val == orig_val, \
                f"字段 {field} 不匹配: {orig_val} vs {deser_val}"
