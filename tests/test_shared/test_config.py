"""
配置模块单元测试

测试配置加载、验证和访问功能
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from shared.config import (
    Config,
    ConfigError,
    ConfigLoadError,
    ConfigValidationError,
    RedisConfig,
    StrategyConfig,
    ModuleConfig,
    load_config
)


class TestRedisConfig:
    """Redis 配置测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = RedisConfig()
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.password == ""
        assert config.db == 0
        assert config.max_connections == 50
    
    def test_validation_success(self):
        """测试验证成功"""
        config = RedisConfig(
            host="redis.example.com",
            port=6380,
            db=5,
            max_connections=100
        )
        config.validate()
    
    def test_validation_empty_host(self):
        """测试空主机验证"""
        config = RedisConfig(host="")
        with pytest.raises(ConfigValidationError, match="host 不能为空"):
            config.validate()
    
    def test_validation_invalid_port(self):
        """测试无效端口验证"""
        config = RedisConfig(port=70000)
        with pytest.raises(ConfigValidationError, match="port 必须在 1-65535"):
            config.validate()
    
    def test_validation_invalid_db(self):
        """测试无效数据库编号验证"""
        config = RedisConfig(db=20)
        with pytest.raises(ConfigValidationError, match="db 必须在 0-15"):
            config.validate()
    
    def test_validation_invalid_max_connections(self):
        """测试无效最大连接数验证"""
        config = RedisConfig(max_connections=0)
        with pytest.raises(ConfigValidationError, match="max_connections 必须大于 0"):
            config.validate()


class TestStrategyConfig:
    """策略配置测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = StrategyConfig()
        assert config.base_cushion == 0.02
        assert config.alpha == 0.5
        assert "default" in config.max_buy_prices
        assert config.max_buy_prices["default"] == 0.95
    
    def test_validation_success(self):
        """测试验证成功"""
        config = StrategyConfig(
            base_cushion=0.05,
            alpha=0.7,
            max_buy_prices={"default": 0.90},
            order_sizes={"min": 10, "max": 1000, "default": 100}
        )
        config.validate()
    
    def test_validation_invalid_base_cushion(self):
        """测试无效基础缓冲值验证"""
        config = StrategyConfig(base_cushion=1.5)
        with pytest.raises(ConfigValidationError, match="base_cushion 必须在 0-1"):
            config.validate()
    
    def test_validation_invalid_alpha(self):
        """测试无效 alpha 值验证"""
        config = StrategyConfig(alpha=-0.1)
        with pytest.raises(ConfigValidationError, match="alpha 必须在 0-1"):
            config.validate()
    
    def test_validation_invalid_max_buy_price(self):
        """测试无效最大买入价格验证"""
        config = StrategyConfig(
            max_buy_prices={"default": 1.5}
        )
        with pytest.raises(ConfigValidationError, match="max_buy_prices"):
            config.validate()
    
    def test_validation_invalid_order_sizes(self):
        """测试无效订单大小验证"""
        config = StrategyConfig(
            order_sizes={"min": 100, "max": 10, "default": 50}
        )
        with pytest.raises(ConfigValidationError, match="最小订单大小.*不能大于最大订单大小"):
            config.validate()
    
    def test_validation_invalid_max_drawdown(self):
        """测试无效最大回撤验证"""
        config = StrategyConfig(
            risk_management={
                "max_position_size": 5000,
                "max_total_exposure": 20000,
                "max_daily_loss": 500,
                "max_drawdown": 1.5,
                "min_balance": 100
            }
        )
        with pytest.raises(ConfigValidationError, match="max_drawdown 必须在 0-1"):
            config.validate()


class TestConfig:
    """配置管理器测试"""
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """创建临时配置目录"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return tmp_path
    
    @pytest.fixture
    def sample_config(self):
        """示例配置数据"""
        return {
            "strategy": {
                "base_cushion": 0.03,
                "alpha": 0.6,
                "max_buy_prices": {
                    "default": 0.95
                },
                "order_sizes": {
                    "min": 10,
                    "max": 1000,
                    "default": 100
                },
                "risk_management": {
                    "max_position_size": 5000,
                    "max_total_exposure": 20000,
                    "max_daily_loss": 500,
                    "max_drawdown": 0.15,
                    "min_balance": 100
                }
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "pool": {
                    "max_connections": 50
                }
            },
            "modules": {
                "test_module": {
                    "enabled": True,
                    "param": "value"
                }
            }
        }
    
    @pytest.fixture
    def sample_env_file(self, temp_config_dir):
        """创建示例 .env 文件"""
        env_file = temp_config_dir / ".env"
        env_file.write_text("TEST_VAR=test_value\nREDIS_HOST=redis.example.com")
        return str(env_file)
    
    @pytest.fixture
    def sample_config_file(self, temp_config_dir, sample_config):
        """创建示例配置文件"""
        config_dir = temp_config_dir / "config"
        config_file = config_dir / "settings.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(sample_config, f)
        return str(config_file)
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        config1 = Config()
        config2 = Config()
        assert config1 is config2
    
    def test_load_yaml_success(self, sample_config_file, temp_config_dir):
        """测试成功加载 YAML 配置"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        
        assert config._config_loaded
        assert "strategy" in config._config
        assert config._config["strategy"]["base_cushion"] == 0.03
    
    def test_load_yaml_file_not_found(self, temp_config_dir):
        """测试加载不存在的配置文件"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        
        with pytest.raises(ConfigLoadError, match="配置文件不存在"):
            config.load_yaml("nonexistent.yaml")
    
    def test_load_env_success(self, sample_env_file):
        """测试成功加载环境变量"""
        config = Config()
        config._initialized = True
        
        config.load_env(sample_env_file)
        
        assert os.getenv("TEST_VAR") == "test_value"
        assert os.getenv("REDIS_HOST") == "redis.example.com"
    
    def test_load_env_file_not_found(self):
        """测试加载不存在的环境变量文件"""
        config = Config()
        config._initialized = True
        
        with pytest.raises(ConfigLoadError, match="环境变量文件不存在"):
            config.load_env("/nonexistent/.env")
    
    def test_replace_env_vars(self):
        """测试环境变量替换"""
        config = Config()
        config._initialized = True
        
        os.environ["TEST_VAR"] = "test_value"
        
        test_config = {
            "key1": "${TEST_VAR}",
            "key2": "${NONEXISTENT:default_value}",
            "nested": {
                "key3": "prefix_${TEST_VAR}_suffix"
            }
        }
        
        result = config._replace_env_vars(test_config)
        
        assert result["key1"] == "test_value"
        assert result["key2"] == "default_value"
        assert result["nested"]["key3"] == "prefix_test_value_suffix"
    
    def test_replace_env_vars_missing_required(self):
        """测试缺少必需的环境变量"""
        config = Config()
        config._initialized = True
        
        test_config = {"key": "${NONEXISTENT_VAR}"}
        
        with pytest.raises(ConfigValidationError, match="环境变量.*未设置"):
            config._replace_env_vars(test_config)
    
    def test_get_config_value(self, sample_config_file, temp_config_dir):
        """测试获取配置值"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        
        assert config.get("strategy.base_cushion") == 0.03
        assert config.get("strategy.alpha") == 0.6
        assert config.get("redis.host") == "localhost"
        assert config.get("nonexistent.key", "default") == "default"
    
    def test_get_redis_config(self, sample_config_file, temp_config_dir):
        """测试获取 Redis 配置对象"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        redis_config = config.get_redis_config()
        
        assert isinstance(redis_config, RedisConfig)
        assert redis_config.host == "localhost"
        assert redis_config.port == 6379
    
    def test_get_strategy_config(self, sample_config_file, temp_config_dir):
        """测试获取策略配置对象"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        strategy_config = config.get_strategy_config()
        
        assert isinstance(strategy_config, StrategyConfig)
        assert strategy_config.base_cushion == 0.03
        assert strategy_config.alpha == 0.6
    
    def test_get_module_config(self, sample_config_file, temp_config_dir):
        """测试获取模块配置"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        module_config = config.get_module_config("test_module")
        
        assert isinstance(module_config, ModuleConfig)
        assert module_config.enabled is True
        assert module_config.config["param"] == "value"
    
    def test_validate_success(self, sample_config_file, temp_config_dir):
        """测试配置验证成功"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        config.validate()
    
    def test_validate_not_loaded(self):
        """测试未加载配置时验证"""
        config = Config()
        config._initialized = True
        config._config_loaded = False
        
        with pytest.raises(ConfigError, match="配置尚未加载"):
            config.validate()
    
    def test_reload(self, sample_config_file, temp_config_dir):
        """测试重新加载配置"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        first_load = config.get("strategy.base_cushion")
        
        config.reload()
        second_load = config.get("strategy.base_cushion")
        
        assert first_load == second_load
    
    def test_get_all(self, sample_config_file, temp_config_dir):
        """测试获取所有配置"""
        config = Config()
        config._base_path = temp_config_dir
        config._config_path = temp_config_dir / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        all_config = config.get_all()
        
        assert isinstance(all_config, dict)
        assert "strategy" in all_config
        assert "redis" in all_config


class TestLoadConfigFunction:
    """测试便捷加载函数"""
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """创建临时配置目录"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return tmp_path
    
    @pytest.fixture
    def sample_config_file(self, temp_config_dir):
        """创建示例配置文件"""
        config_data = {
            "strategy": {
                "base_cushion": 0.02,
                "alpha": 0.5,
                "max_buy_prices": {"default": 0.95},
                "order_sizes": {"min": 10, "max": 1000, "default": 100},
                "risk_management": {
                    "max_position_size": 5000,
                    "max_total_exposure": 20000,
                    "max_daily_loss": 500,
                    "max_drawdown": 0.15,
                    "min_balance": 100
                }
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            }
        }
        
        config_dir = temp_config_dir / "config"
        config_file = config_dir / "settings.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f)
        
        return temp_config_dir
    
    def test_load_config_with_validation(self, sample_config_file):
        """测试带验证的配置加载"""
        Config._instance = None
        config = Config.get_instance()
        config._base_path = sample_config_file
        config._config_path = sample_config_file / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        config.validate()
        
        assert config._config_loaded
        assert config.get("strategy.base_cushion") == 0.02
    
    def test_load_config_without_validation(self, sample_config_file):
        """测试不带验证的配置加载"""
        Config._instance = None
        config = Config.get_instance()
        config._base_path = sample_config_file
        config._config_path = sample_config_file / "config"
        config._initialized = True
        config._config = {}
        config._config_loaded = False
        
        config.load_yaml("settings.yaml")
        
        assert config._config_loaded
