"""
订单管理器单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from modules.order_executor.order_manager import (
    OrderManager,
    OrderValidation,
    OrderResult,
    OrderManagerError
)
from modules.order_executor.clob_client import ClobClientWrapper
from modules.order_executor.fee_calculator import FeeCalculator


class TestOrderValidation:
    """订单验证测试类"""
    
    def test_valid_order_validation(self):
        """测试有效的订单验证结果"""
        validation = OrderValidation(is_valid=True)
        
        assert validation.is_valid is True
        assert validation.reason == ""
    
    def test_invalid_order_validation(self):
        """测试无效的订单验证结果"""
        validation = OrderValidation(
            is_valid=False,
            reason="价格超出范围"
        )
        
        assert validation.is_valid is False
        assert validation.reason == "价格超出范围"
    
    def test_order_validation_with_adjustments(self):
        """测试带调整的订单验证结果"""
        validation = OrderValidation(
            is_valid=True,
            reason="订单大小已调整",
            adjusted_price=0.50,
            adjusted_size=100
        )
        
        assert validation.is_valid is True
        assert validation.adjusted_price == 0.50
        assert validation.adjusted_size == 100


class TestOrderResult:
    """订单结果测试类"""
    
    def test_successful_order_result(self):
        """测试成功的订单结果"""
        result = OrderResult(
            success=True,
            order_id="order_123",
            status="matched",
            filled_size=100,
            avg_price=0.50,
            fee=0.90
        )
        
        assert result.success is True
        assert result.order_id == "order_123"
        assert result.filled_size == 100
        assert result.avg_price == 0.50
    
    def test_failed_order_result(self):
        """测试失败的订单结果"""
        result = OrderResult(
            success=False,
            error_message="余额不足"
        )
        
        assert result.success is False
        assert result.error_message == "余额不足"
        assert result.filled_size == 0.0
    
    def test_order_result_to_dict(self):
        """测试订单结果转换为字典"""
        result = OrderResult(
            success=True,
            order_id="order_123",
            status="matched",
            filled_size=100,
            avg_price=0.50,
            fee=0.90,
            metadata={"test": "data"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["order_id"] == "order_123"
        assert result_dict["filled_size"] == 100
        assert result_dict["metadata"]["test"] == "data"


class TestOrderManager:
    """订单管理器测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.mock_clob_client = Mock(spec=ClobClientWrapper)
        self.mock_clob_client.get_usdc_balance.return_value = 1000.0
        self.mock_clob_client.get_token_balance.return_value = 500.0
        self.mock_clob_client.get_tick_size.return_value = "0.01"
        self.mock_clob_client.get_neg_risk.return_value = False
        self.mock_clob_client.get_order_book.return_value = {
            "bids": [{"price": "0.49", "size": "100"}],
            "asks": [{"price": "0.51", "size": "100"}]
        }
        self.mock_clob_client.create_and_submit_order.return_value = {
            "success": True,
            "orderID": "order_123",
            "status": "matched",
            "errorMsg": ""
        }
        
        self.mock_config = Mock()
        self.mock_config.get_strategy_config.return_value = Mock(
            max_buy_prices={"default": 0.95},
            order_sizes={"min": 10, "max": 1000},
            risk_management={"max_position_size": 5000}
        )
        
        self.fee_calculator = FeeCalculator()
        
        self.order_manager = OrderManager(
            clob_client=self.mock_clob_client,
            fee_calculator=self.fee_calculator,
            config=self.mock_config
        )
    
    def test_validate_price_buy_order_valid(self):
        """测试买单价格验证（有效）"""
        validation = self.order_manager.validate_price(
            token_id="token_123",
            price=0.50,
            side="BUY",
            max_buy_price=0.95
        )
        
        assert validation.is_valid is True
    
    def test_validate_price_buy_order_exceeds_max(self):
        """测试买单价格验证（超过最大值）"""
        validation = self.order_manager.validate_price(
            token_id="token_123",
            price=0.96,
            side="BUY",
            max_buy_price=0.95
        )
        
        assert validation.is_valid is False
        assert "超过最高可买入价格" in validation.reason
    
    def test_validate_price_buy_order_out_of_range(self):
        """测试买单价格验证（超出范围）"""
        validation = self.order_manager.validate_price(
            token_id="token_123",
            price=1.5,
            side="BUY",
            max_buy_price=0.95
        )
        
        assert validation.is_valid is False
    
    def test_validate_order_size_valid(self):
        """测试订单大小验证（有效）"""
        validation = self.order_manager.validate_order_size(
            size=100,
            available_balance=1000
        )
        
        assert validation.is_valid is True
    
    def test_validate_order_size_too_small(self):
        """测试订单大小验证（过小）"""
        validation = self.order_manager.validate_order_size(
            size=5,
            available_balance=1000
        )
        
        assert validation.is_valid is False
        assert "小于最小值" in validation.reason
    
    def test_validate_order_size_exceeds_balance(self):
        """测试订单大小验证（超过余额）"""
        validation = self.order_manager.validate_order_size(
            size=1500,
            available_balance=1000
        )
        
        assert validation.is_valid is True
        assert validation.adjusted_size == 1000
    
    def test_check_order_book_depth_sufficient(self):
        """测试订单簿深度检查（充足）"""
        is_sufficient, available = self.order_manager.check_order_book_depth(
            token_id="token_123",
            required_size=50,
            price=0.51,
            side="BUY"
        )
        
        assert is_sufficient is True
        assert available == 100
    
    def test_check_order_book_depth_insufficient(self):
        """测试订单簿深度检查（不足）"""
        is_sufficient, available = self.order_manager.check_order_book_depth(
            token_id="token_123",
            required_size=150,
            price=0.51,
            side="BUY"
        )
        
        assert is_sufficient is False
        assert available == 100
    
    def test_adjust_price_to_tick_size(self):
        """测试价格调整到 Tick Size"""
        adjusted = self.order_manager.adjust_price_to_tick_size(
            price=0.505,
            tick_size="0.01",
            round_down=True
        )
        
        assert adjusted == 0.50
    
    def test_adjust_price_to_tick_size_round_up(self):
        """测试价格调整到 Tick Size（向上）"""
        adjusted = self.order_manager.adjust_price_to_tick_size(
            price=0.505,
            tick_size="0.01",
            round_down=False
        )
        
        assert adjusted == 0.50
    
    def test_execute_buy_order_success(self):
        """测试执行买入订单（成功）"""
        result = self.order_manager.execute_buy_order(
            token_id="token_123",
            size=100,
            max_price=0.60
        )
        
        assert result.success is True
        assert result.order_id == "order_123"
        assert result.filled_size == 100
        assert result.fee > 0
    
    def test_execute_buy_order_insufficient_balance(self):
        """测试执行买入订单（余额不足）"""
        self.mock_clob_client.get_usdc_balance.return_value = 50
        
        result = self.order_manager.execute_buy_order(
            token_id="token_123",
            size=100,
            max_price=0.60
        )
        
        assert result.success is True
        assert result.filled_size == 50
    
    def test_execute_buy_order_price_exceeds_max(self):
        """测试执行买入订单（价格超过最大值）"""
        result = self.order_manager.execute_buy_order(
            token_id="token_123",
            size=100,
            max_price=0.99
        )
        
        assert result.success is False
        assert "超过最高可买入价格" in result.error_message
    
    def test_execute_sell_order_success(self):
        """测试执行卖出订单（成功）"""
        result = self.order_manager.execute_sell_order(
            token_id="token_123",
            size=100,
            min_price=0.40
        )
        
        assert result.success is True
        assert result.order_id == "order_123"
    
    def test_execute_sell_order_insufficient_tokens(self):
        """测试执行卖出订单（代币不足）"""
        self.mock_clob_client.get_token_balance.return_value = 50
        
        result = self.order_manager.execute_sell_order(
            token_id="token_123",
            size=100,
            min_price=0.40
        )
        
        assert result.success is False
        assert "代币余额不足" in result.error_message
    
    def test_get_order_history(self):
        """测试获取订单历史"""
        self.order_manager.execute_buy_order(
            token_id="token_123",
            size=100,
            max_price=0.60
        )
        
        history = self.order_manager.get_order_history()
        
        assert len(history) == 1
        assert history[0]["result"]["success"] is True
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        self.order_manager.execute_buy_order(
            token_id="token_123",
            size=100,
            max_price=0.60
        )
        
        stats = self.order_manager.get_statistics()
        
        assert stats["total_orders"] == 1
        assert stats["successful_orders"] == 1
        assert stats["success_rate"] == 1.0
