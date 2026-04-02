import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.order_executor.clob_client import validate_private_key, ClobClientError, ClobClientWrapper


class TestValidatePrivateKey:
    """私钥格式验证单元测试"""

    def test_none_value(self):
        """测试 None 值"""
        with pytest.raises(ClobClientError) as exc_info:
            validate_private_key(None)
        
        assert "缺少私钥配置" in str(exc_info.value)

    def test_empty_string(self):
        """测试空字符串"""
        with pytest.raises(ClobClientError) as exc_info:
            validate_private_key("")
        
        assert "缺少私钥配置" in str(exc_info.value)

    def test_whitespace_string(self):
        """测试空白字符串"""
        with pytest.raises(ClobClientError) as exc_info:
            validate_private_key("   ")
        
        assert "缺少私钥配置" in str(exc_info.value)

    def test_missing_0x_prefix(self):
        """测试缺少 0x 前缀"""
        invalid_key = "a1b2c3d4e5f6" * 4 + "a1b2c3d4"
        
        with pytest.raises(ClobClientError) as exc_info:
            validate_private_key(invalid_key)
        
        assert "私钥格式无效" in str(exc_info.value)

    def test_wrong_length_too_short(self):
        """测试长度过短"""
        short_key = "0x" + "a1b2c3d4" * 7
        
        with pytest.raises(ClobClientError) as exc_info:
            validate_private_key(short_key)
        
        assert "私钥格式无效" in str(exc_info.value)

    def test_wrong_length_too_long(self):
        """测试长度过长"""
        long_key = "0x" + "a1b2c3d4e5f6" * 6
        
        with pytest.raises(ClobClientError) as exc_info:
            validate_private_key(long_key)
        
        assert "私钥格式无效" in str(exc_info.value)

    def test_invalid_characters(self):
        """测试包含非法字符"""
        invalid_key = "0x" + "g1h2i3j4k5l6" * 4 + "m1n2o3p4"
        
        with pytest.raises(ClobClientError) as exc_info:
            validate_private_key(invalid_key)
        
        assert "私钥格式无效" in str(exc_info.value)

    def test_special_characters(self):
        """测试包含特殊字符"""
        invalid_key = "0x" + "a1b2!@#$%^&*()" + "c3d4e5f6" * 3
        
        with pytest.raises(ClobClientError) as exc_info:
            validate_private_key(invalid_key)
        
        assert "私钥格式无效" in str(exc_info.value)

    def test_valid_lowercase_key(self):
        """测试有效的小写私钥"""
        valid_key = "0x" + "a1b2c3d4e5f6" * 4 + "1234567890abcdef"

        result = validate_private_key(valid_key)

        assert result is True

    def test_valid_uppercase_key(self):
        """测试有效的大写私钥"""
        valid_key = "0x" + "A1B2C3D4E5F6" * 4 + "1234567890ABCDEF"

        result = validate_private_key(valid_key)

        assert result is True

    def test_valid_mixed_case_key(self):
        """测试有效的大小写混合私钥"""
        valid_key = "0x" + "a1B2c3D4e5F6" * 4 + "1234567890AbCdEF"

        result = validate_private_key(valid_key)

        assert result is True

    def test_valid_all_zeros(self):
        """测试全零的有效私钥"""
        valid_key = "0x" + "0" * 64
        
        result = validate_private_key(valid_key)
        
        assert result is True

    def test_valid_all_f(self):
        """测试全 F 的有效私钥"""
        valid_key = "0x" + "f" * 64
        
        result = validate_private_key(valid_key)
        
        assert result is True


class TestClobClientWrapperInit:
    """ClobClientWrapper 初始化时的私钥验证测试"""

    def test_init_with_none_key(self):
        """使用 None 私钥初始化应抛出异常"""
        import os
        if 'PRIVATE_KEY' in os.environ:
            del os.environ['PRIVATE_KEY']
        
        with pytest.raises(ClobClientError) as exc_info:
            ClobClientWrapper(private_key=None)
        
        assert "缺少私钥配置" in str(exc_info.value)

    def test_init_with_invalid_format_key(self):
        """使用格式错误的私钥初始化应抛出异常"""
        with pytest.raises(ClobClientError) as exc_info:
            ClobClientWrapper(private_key="invalid_key")
        
        assert "私钥格式无效" in str(exc_info.value)

    def test_init_with_valid_key(self):
        """使用有效私钥初始化应成功"""
        valid_key = "0x" + "a1b2c3d4e5f6" * 4 + "1234567890abcdef"
        
        wrapper = ClobClientWrapper(private_key=valid_key)
        
        assert wrapper.private_key == valid_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
