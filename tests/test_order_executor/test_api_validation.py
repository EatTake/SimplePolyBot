"""
API 凭证验证单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from modules.order_executor.clob_client import ClobClientWrapper, ClobClientError


class TestValidateApiCredentials:
    """API 凭证验证测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.client_wrapper = ClobClientWrapper(
            private_key="0x" + "1" * 64,
            auto_validate=False
        )
        
        self.client_wrapper._client = Mock()
        self.client_wrapper._funder_address = "0xTestAddress"
    
    def test_valid_credentials_success(self):
        """测试有效凭证场景 - get_usdc_balance 返回正常值"""
        self.client_wrapper.get_usdc_balance = Mock(return_value=1000.0)
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is True
        self.client_wrapper.get_usdc_balance.assert_called_once()
    
    def test_valid_credentials_zero_balance(self):
        """测试有效凭证场景 - 余额为 0（仍视为有效）"""
        self.client_wrapper.get_usdc_balance = Mock(return_value=0.0)
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is True
    
    def test_invalid_credentials_authentication_error(self):
        """测试无效凭证场景 - 认证失败异常"""
        self.client_wrapper.get_usdc_balance = Mock(
            side_effect=ClobClientError("认证失败: 无效的 API Key")
        )
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is False
    
    def test_network_exception_timeout(self):
        """测试网络异常场景 - 超时错误"""
        import requests
        
        self.client_wrapper.get_usdc_balance = Mock(
            side_effect=requests.exceptions.Timeout("连接超时")
        )
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is False
    
    def test_network_exception_connection_error(self):
        """测试网络异常场景 - 连接错误"""
        import requests
        
        self.client_wrapper.get_usdc_balance = Mock(
            side_effect=requests.exceptions.ConnectionError("无法连接到服务器")
        )
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is False
    
    def test_generic_exception(self):
        """测试通用异常场景 - 未知错误"""
        self.client_wrapper.get_usdc_balance = Mock(
            side_effect=Exception("未知错误")
        )
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is False
    
    @patch('modules.order_executor.clob_client.logger')
    def test_valid_credentials_logs_info(self, mock_logger):
        """测试有效凭证时记录 info 日志"""
        mock_logger.info = Mock()
        mock_logger.error = Mock()
        
        self.client_wrapper.get_usdc_balance = Mock(return_value=500.0)
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is True
        mock_logger.info.assert_called_once_with(
            "API 凭证验证成功",
            balance=500.0
        )
        mock_logger.error.assert_not_called()
    
    @patch('modules.order_executor.clob_client.logger')
    def test_invalid_credentials_logs_error(self, mock_logger):
        """测试无效凭证时记录 error 日志"""
        mock_logger.info = Mock()
        mock_logger.error = Mock()
        
        test_error = ClobClientError("认证失败")
        self.client_wrapper.get_usdc_balance = Mock(side_effect=test_error)
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is False
        mock_logger.error.assert_called_once_with(
            "API 凭证验证失败",
            error=str(test_error)
        )
        mock_logger.info.assert_not_called()


class TestAutoValidateOnInitialize:
    """初始化自动验证测试类"""
    
    @patch('modules.order_executor.clob_client.ClobClient')
    def test_auto_validate_true_calls_validation(self, mock_clob_client_class):
        """测试 auto_validate=True 时在 initialize() 中调用验证"""
        mock_temp_client = Mock()
        mock_temp_client.create_or_derive_api_creds.return_value = Mock()
        mock_temp_client.get_address.return_value = "0xFunder"
        mock_clob_client_class.side_effect = [mock_temp_client, Mock()]
        
        client_wrapper = ClobClientWrapper(
            private_key="0x" + "1" * 64,
            auto_validate=True
        )
        
        with patch.object(client_wrapper, '_verify_connection'), \
             patch.object(client_wrapper, 'validate_api_credentials', return_value=True) as mock_validate:
            
            client_wrapper.initialize()
            
            mock_validate.assert_called_once()
    
    @patch('modules.order_executor.clob_client.ClobClient')
    def test_auto_validate_false_skips_validation(self, mock_clob_client_class):
        """测试 auto_validate=False 时在 initialize() 中跳过验证"""
        mock_temp_client = Mock()
        mock_temp_client.create_or_derive_api_creds.return_value = Mock()
        mock_temp_client.get_address.return_value = "0xFunder"
        mock_clob_client_class.side_effect = [mock_temp_client, Mock()]
        
        client_wrapper = ClobClientWrapper(
            private_key="0x" + "1" * 64,
            auto_validate=False
        )
        
        with patch.object(client_wrapper, '_verify_connection'), \
             patch.object(client_wrapper, 'validate_api_credentials') as mock_validate:
            
            client_wrapper.initialize()
            
            mock_validate.assert_not_called()
    
    @patch('modules.order_executor.clob_client.ClobClient')
    def test_auto_validate_true_raises_on_failure(self, mock_clob_client_class):
        """测试 auto_validate=True 且验证失败时抛出异常"""
        mock_temp_client = Mock()
        mock_temp_client.create_or_derive_api_creds.return_value = Mock()
        mock_temp_client.get_address.return_value = "0xFunder"
        mock_clob_client_class.side_effect = [mock_temp_client, Mock()]
        
        client_wrapper = ClobClientWrapper(
            private_key="0x" + "1" * 64,
            auto_validate=True
        )
        
        with patch.object(client_wrapper, '_verify_connection'), \
             patch.object(client_wrapper, 'validate_api_credentials', return_value=False):
            
            with pytest.raises(ClobClientError, match="API 凭证验证失败"):
                client_wrapper.initialize()


class TestValidateApiCredentialsEdgeCases:
    """API 凭证验证边界情况测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.client_wrapper = ClobClientWrapper(
            private_key="0x" + "1" * 64,
            auto_validate=False
        )
        
        self.client_wrapper._client = Mock()
        self.client_wrapper._funder_address = "0xTestAddress"
    
    def test_large_balance_value(self):
        """测试大额余额场景"""
        self.client_wrapper.get_usdc_balance = Mock(return_value=999999.99)
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is True
    
    def test_very_small_balance(self):
        """测试极小余额场景"""
        self.client_wrapper.get_usdc_balance = Mock(return_value=0.000001)
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is True
    
    def test_negative_balance_treated_as_valid(self):
        """测试负数余额场景（API 异常但仍返回）"""
        self.client_wrapper.get_usdc_balance = Mock(return_value=-100.0)
        
        result = self.client_wrapper.validate_api_credentials()
        
        assert result is True
    
    def test_multiple_consecutive_validations(self):
        """测试多次连续验证调用"""
        self.client_wrapper.get_usdc_balance = Mock(return_value=100.0)
        
        result1 = self.client_wrapper.validate_api_credentials()
        result2 = self.client_wrapper.validate_api_credentials()
        result3 = self.client_wrapper.validate_api_credentials()
        
        assert result1 is True
        assert result2 is True
        assert result3 is True
        assert self.client_wrapper.get_usdc_balance.call_count == 3
    
    def test_validation_after_failure_then_recovery(self):
        """测试先失败后恢复的场景"""
        call_count = [0]
        
        def mock_balance():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("网络错误")
            return 100.0
        
        self.client_wrapper.get_usdc_balance = Mock(side_effect=mock_balance)
        
        result1 = self.client_wrapper.validate_api_credentials()
        result2 = self.client_wrapper.validate_api_credentials()
        
        assert result1 is False
        assert result2 is True
