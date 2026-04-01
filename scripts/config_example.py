"""
配置管理系统使用示例

演示如何加载和使用配置
"""

import os
from shared.config import load_config, Config

def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 设置必要的环境变量（实际使用时应该在 .env 文件中设置）
    os.environ.setdefault("POLYMARKET_API_KEY", "test_key")
    os.environ.setdefault("POLYMARKET_API_SECRET", "test_secret")
    os.environ.setdefault("POLYMARKET_API_PASSPHRASE", "test_passphrase")
    
    # 加载配置
    config = load_config()
    
    # 获取简单配置值
    print(f"策略 Base Cushion: {config.get('strategy.base_cushion')}")
    print(f"策略 Alpha: {config.get('strategy.alpha')}")
    print(f"Redis 主机: {config.get('redis.host')}")
    print(f"Redis 端口: {config.get('redis.port')}")
    
    # 获取嵌套配置值
    print(f"默认最大买入价格: {config.get('strategy.max_buy_prices.default')}")
    print(f"默认订单大小: {config.get('strategy.order_sizes.default')}")


def example_typed_config():
    """类型化配置对象示例"""
    print("\n=== 类型化配置对象示例 ===")
    
    config = Config.get_instance()
    
    # 获取 Redis 配置对象
    redis_config = config.get_redis_config()
    print(f"Redis 配置:")
    print(f"  - 主机: {redis_config.host}")
    print(f"  - 端口: {redis_config.port}")
    print(f"  - 数据库: {redis_config.db}")
    print(f"  - 最大连接数: {redis_config.max_connections}")
    
    # 获取策略配置对象
    strategy_config = config.get_strategy_config()
    print(f"\n策略配置:")
    print(f"  - Base Cushion: {strategy_config.base_cushion}")
    print(f"  - Alpha: {strategy_config.alpha}")
    print(f"  - 最大买入价格: {strategy_config.max_buy_prices}")
    print(f"  - 订单大小: {strategy_config.order_sizes}")
    print(f"  - 风险管理: {strategy_config.risk_management}")


def example_module_config():
    """模块配置示例"""
    print("\n=== 模块配置示例 ===")
    
    config = Config.get_instance()
    
    # 获取市场数据收集器模块配置
    market_data_config = config.get_module_config("market_data_collector")
    print(f"市场数据收集器模块:")
    print(f"  - 启用状态: {market_data_config.enabled}")
    print(f"  - WebSocket URL: {market_data_config.config.get('websocket', {}).get('url')}")
    
    # 获取策略引擎模块配置
    strategy_engine_config = config.get_module_config("strategy_engine")
    print(f"\n策略引擎模块:")
    print(f"  - 启用状态: {strategy_engine_config.enabled}")
    print(f"  - 活跃策略: {strategy_engine_config.config.get('active_strategies', [])}")


def example_env_var_replacement():
    """环境变量替换示例"""
    print("\n=== 环境变量替换示例 ===")
    
    config = Config.get_instance()
    
    # 配置文件中使用 ${REDIS_HOST:localhost} 格式
    # 如果环境变量 REDIS_HOST 存在，则使用环境变量的值
    # 否则使用默认值 localhost
    print(f"Redis 主机（从环境变量）: {config.get('redis.host')}")
    
    # 配置文件中使用 ${POLYMARKET_API_KEY} 格式（无默认值）
    # 环境变量必须存在，否则会抛出异常
    print(f"Polymarket API Key: {config.get('api.polymarket.api_key')}")


def example_config_validation():
    """配置验证示例"""
    print("\n=== 配置验证示例 ===")
    
    from shared.config import ConfigValidationError
    
    config = Config.get_instance()
    
    try:
        # 验证所有配置
        config.validate()
        print("✓ 配置验证通过")
    except ConfigValidationError as e:
        print(f"✗ 配置验证失败: {e}")


def example_config_reload():
    """配置热重载示例"""
    print("\n=== 配置热重载示例 ===")
    
    config = Config.get_instance()
    
    print(f"重载前的 Base Cushion: {config.get('strategy.base_cushion')}")
    
    # 重新加载配置
    config.reload()
    
    print(f"重载后的 Base Cushion: {config.get('strategy.base_cushion')}")


if __name__ == "__main__":
    # 运行所有示例
    example_basic_usage()
    example_typed_config()
    example_module_config()
    example_env_var_replacement()
    example_config_validation()
    example_config_reload()
    
    print("\n=== 所有示例运行完成 ===")
