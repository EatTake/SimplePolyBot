"""
配置管理模块

提供统一的配置加载、验证和访问接口
支持从 .env 文件和 YAML 文件加载配置
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    """配置错误基类"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    pass


class ConfigLoadError(ConfigError):
    """配置加载错误"""
    pass


@dataclass
class RedisConfig:
    """Redis 连接配置"""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    max_connections: int = 50
    min_idle_connections: int = 5
    connection_timeout: int = 5
    socket_timeout: int = 5
    max_attempts: int = 3
    retry_delay: int = 1
    exponential_backoff: bool = True
    
    def validate(self) -> None:
        """验证 Redis 配置"""
        if not self.host:
            raise ConfigValidationError("Redis host 不能为空")
        if not (1 <= self.port <= 65535):
            raise ConfigValidationError(f"Redis port 必须在 1-65535 范围内，当前值: {self.port}")
        if not (0 <= self.db <= 15):
            raise ConfigValidationError(f"Redis db 必须在 0-15 范围内，当前值: {self.db}")
        if self.max_connections < 1:
            raise ConfigValidationError(f"max_connections 必须大于 0，当前值: {self.max_connections}")


@dataclass
class StrategyConfig:
    """策略参数配置"""
    base_cushion: float = 0.02
    alpha: float = 0.5
    max_buy_prices: Dict[str, float] = field(default_factory=lambda: {
        "default": 0.95,
        "high_confidence": 0.98,
        "low_volatility": 0.92,
        "fast_market": 0.90
    })
    order_sizes: Dict[str, int] = field(default_factory=lambda: {
        "default": 100,
        "min": 10,
        "max": 1000
    })
    risk_management: Dict[str, Any] = field(default_factory=lambda: {
        "max_position_size": 5000,
        "max_total_exposure": 20000,
        "max_daily_loss": 500,
        "max_drawdown": 0.15,
        "min_balance": 100
    })
    stop_loss_take_profit: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "stop_loss_percentage": 0.10,
        "take_profit_percentage": 0.20
    })
    
    def validate(self) -> None:
        """验证策略配置"""
        if not (0 <= self.base_cushion <= 1):
            raise ConfigValidationError(
                f"base_cushion 必须在 0-1 范围内，当前值: {self.base_cushion}"
            )
        if not (0 <= self.alpha <= 1):
            raise ConfigValidationError(
                f"alpha 必须在 0-1 范围内，当前值: {self.alpha}"
            )
        
        for key, price in self.max_buy_prices.items():
            if not (0 <= price <= 1):
                raise ConfigValidationError(
                    f"max_buy_prices[{key}] 必须在 0-1 范围内，当前值: {price}"
                )
        
        if self.order_sizes["min"] > self.order_sizes["max"]:
            raise ConfigValidationError(
                f"最小订单大小 ({self.order_sizes['min']}) 不能大于最大订单大小 ({self.order_sizes['max']})"
            )
        
        risk = self.risk_management
        if risk["max_drawdown"] <= 0 or risk["max_drawdown"] > 1:
            raise ConfigValidationError(
                f"max_drawdown 必须在 0-1 范围内，当前值: {risk['max_drawdown']}"
            )


@dataclass
class ModuleConfig:
    """模块配置"""
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class Config:
    """
    配置管理类
    
    功能：
    1. 从 .env 文件加载环境变量
    2. 从 YAML 文件加载配置
    3. 配置验证
    4. 配置访问接口
    5. 支持环境变量替换
    """
    
    _instance: Optional['Config'] = None
    _config_cache: Dict[str, Any] = field(default_factory=dict)
    
    def __new__(cls) -> 'Config':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if self._initialized:
            return
        
        self._config: Dict[str, Any] = {}
        self._env_loaded: bool = False
        self._config_loaded: bool = False
        self._initialized = True
        
        self._base_path = Path(__file__).parent.parent
        self._config_path = self._base_path / "config"
        self._env_file = self._base_path / ".env"
    
    def load_env(self, env_file: Optional[str] = None) -> None:
        """
        从 .env 文件加载环境变量
        
        Args:
            env_file: .env 文件路径，默认为项目根目录下的 .env
        """
        if env_file:
            env_path = Path(env_file)
        else:
            env_path = self._env_file
        
        if env_path.exists():
            load_dotenv(env_path, override=True)
            self._env_loaded = True
        else:
            if env_file:
                raise ConfigLoadError(f"环境变量文件不存在: {env_path}")
    
    def load_yaml(self, config_file: str = "settings.yaml") -> None:
        """
        从 YAML 文件加载配置
        
        Args:
            config_file: 配置文件名，默认为 settings.yaml
        """
        config_path = self._config_path / config_file
        
        if not config_path.exists():
            raise ConfigLoadError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data is None:
                config_data = {}
            
            self._config = self._replace_env_vars(config_data)
            self._config_loaded = True
            
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"YAML 解析错误: {e}")
        except Exception as e:
            raise ConfigLoadError(f"加载配置文件失败: {e}")
    
    def _replace_env_vars(self, config: Any) -> Any:
        """
        递归替换配置中的环境变量
        
        支持格式：
        - ${ENV_VAR} - 必须存在
        - ${ENV_VAR:default} - 如果不存在则使用默认值
        
        Args:
            config: 配置数据
        
        Returns:
            替换后的配置数据
        """
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._replace_env_var(config)
        else:
            return config
    
    def _replace_env_var(self, value: str) -> str:
        """
        替换单个环境变量
        
        Args:
            value: 包含环境变量的字符串
        
        Returns:
            替换后的值
        """
        pattern = r'\$\{([^}]+)\}'
        
        def replacer(match):
            env_expr = match.group(1)
            
            if ':' in env_expr:
                env_var, default = env_expr.split(':', 1)
                return os.getenv(env_var, default)
            else:
                env_value = os.getenv(env_expr)
                if env_value is None:
                    raise ConfigValidationError(
                        f"环境变量 {env_expr} 未设置且没有默认值"
                    )
                return env_value
        
        return re.sub(pattern, replacer, value)
    
    def validate(self) -> None:
        """验证所有配置"""
        if not self._config_loaded:
            raise ConfigError("配置尚未加载，请先调用 load_yaml()")
        
        errors: List[str] = []
        
        try:
            redis_config = self.get_redis_config()
            redis_config.validate()
        except ConfigValidationError as e:
            errors.append(f"Redis 配置错误: {e}")
        
        try:
            strategy_config = self.get_strategy_config()
            strategy_config.validate()
        except ConfigValidationError as e:
            errors.append(f"策略配置错误: {e}")
        
        if errors:
            raise ConfigValidationError(
                "配置验证失败:\n" + "\n".join(f"  - {err}" for err in errors)
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的路径）
        
        Args:
            key: 配置键，支持点号分隔，如 "redis.host"
            default: 默认值
        
        Returns:
            配置值
        """
        if not self._config_loaded:
            raise ConfigError("配置尚未加载，请先调用 load_yaml()")
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_redis_config(self) -> RedisConfig:
        """
        获取 Redis 配置对象
        
        Returns:
            RedisConfig 实例
        """
        redis_data = self.get('redis', {})
        pool_data = redis_data.get('pool', {})
        retry_data = redis_data.get('retry', {})
        
        return RedisConfig(
            host=redis_data.get('host', 'localhost'),
            port=int(redis_data.get('port', 6379)),
            password=redis_data.get('password', ''),
            db=int(redis_data.get('db', 0)),
            max_connections=int(pool_data.get('max_connections', 50)),
            min_idle_connections=int(pool_data.get('min_idle_connections', 5)),
            connection_timeout=int(pool_data.get('connection_timeout', 5)),
            socket_timeout=int(pool_data.get('socket_timeout', 5)),
            max_attempts=int(retry_data.get('max_attempts', 3)),
            retry_delay=int(retry_data.get('retry_delay', 1)),
            exponential_backoff=retry_data.get('exponential_backoff', True)
        )
    
    def get_strategy_config(self) -> StrategyConfig:
        """
        获取策略配置对象
        
        Returns:
            StrategyConfig 实例
        """
        strategy_data = self.get('strategy', {})
        
        return StrategyConfig(
            base_cushion=float(strategy_data.get('base_cushion', 0.02)),
            alpha=float(strategy_data.get('alpha', 0.5)),
            max_buy_prices=strategy_data.get('max_buy_prices', {}),
            order_sizes=strategy_data.get('order_sizes', {}),
            risk_management=strategy_data.get('risk_management', {}),
            stop_loss_take_profit=strategy_data.get('stop_loss_take_profit', {})
        )
    
    def get_module_config(self, module_name: str) -> ModuleConfig:
        """
        获取模块配置
        
        Args:
            module_name: 模块名称
        
        Returns:
            ModuleConfig 实例
        """
        module_data = self.get(f'modules.{module_name}', {})
        
        return ModuleConfig(
            enabled=module_data.get('enabled', True),
            config=module_data
        )
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            完整配置字典
        """
        if not self._config_loaded:
            raise ConfigError("配置尚未加载，请先调用 load_yaml()")
        
        return self._config.copy()
    
    def reload(self) -> None:
        """重新加载配置"""
        self._config = {}
        self._config_loaded = False
        self.load_yaml()
        self.validate()
    
    @classmethod
    def get_instance(cls) -> 'Config':
        """
        获取配置管理器单例
        
        Returns:
            Config 实例
        """
        return cls()


def load_config(
    env_file: Optional[str] = None,
    config_file: str = "settings.yaml",
    validate: bool = True
) -> Config:
    """
    便捷函数：加载配置
    
    Args:
        env_file: .env 文件路径
        config_file: YAML 配置文件名
        validate: 是否验证配置
    
    Returns:
        Config 实例
    """
    config = Config.get_instance()
    config.load_env(env_file)
    config.load_yaml(config_file)
    
    if validate:
        config.validate()
    
    return config
