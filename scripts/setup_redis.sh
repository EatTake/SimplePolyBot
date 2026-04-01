#!/bin/bash

#####################################
# Redis 安装与配置脚本
# 适用于 Ubuntu/Debian 系统
# 用于 Polymarket 量化交易系统
#####################################

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_warn "建议使用 sudo 运行此脚本"
    fi
}

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS=$DISTRIB_ID
        VER=$DISTRIB_RELEASE
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    log_info "检测到操作系统: $OS $VER"
}

# 更新系统包
update_system() {
    log_info "更新系统包..."
    
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        apt-get update -y
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        yum update -y
    else
        log_warn "未知的操作系统，跳过更新"
    fi
}

# 安装 Redis
install_redis() {
    log_info "开始安装 Redis..."
    
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        # 安装依赖
        apt-get install -y software-properties-common
        
        # 添加 Redis 官方仓库（可选，获取最新版本）
        # add-apt-repository -y ppa:redislabs/redis
        
        # 安装 Redis
        apt-get install -y redis-server
        
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        # 安装 EPEL 仓库
        yum install -y epel-release
        
        # 安装 Redis
        yum install -y redis
        
    else
        log_error "不支持的操作系统: $OS"
        exit 1
    fi
    
    log_info "Redis 安装完成"
}

# 配置 Redis
configure_redis() {
    log_info "配置 Redis..."
    
    REDIS_CONF="/etc/redis/redis.conf"
    
    if [ ! -f "$REDIS_CONF" ]; then
        log_warn "Redis 配置文件不存在，使用默认配置"
        return
    fi
    
    # 备份原配置文件
    cp "$REDIS_CONF" "${REDIS_CONF}.backup"
    
    # 设置 Redis 密码（从环境变量或生成随机密码）
    if [ -z "$REDIS_PASSWORD" ]; then
        REDIS_PASSWORD=$(openssl rand -base64 32)
        log_warn "未设置 REDIS_PASSWORD 环境变量，已生成随机密码"
    fi
    
    log_info "设置 Redis 密码..."
    sed -i "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" "$REDIS_CONF"
    sed -i "s/requirepass foobared/requirepass $REDIS_PASSWORD/" "$REDIS_CONF"
    
    # 绑定地址（允许远程连接，根据需要调整）
    log_info "配置绑定地址..."
    sed -i "s/bind 127.0.0.1 ::1/bind 0.0.0.0/" "$REDIS_CONF"
    
    # 保护模式（如果允许远程连接，需要关闭保护模式或设置密码）
    log_info "配置保护模式..."
    sed -i "s/protected-mode yes/protected-mode no/" "$REDIS_CONF"
    
    # 最大内存设置（根据系统内存调整，这里设置为 2GB）
    log_info "配置最大内存..."
    sed -i "s/# maxmemory <bytes>/maxmemory 2gb/" "$REDIS_CONF"
    
    # 内存淘汰策略
    log_info "配置内存淘汰策略..."
    sed -i "s/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/" "$REDIS_CONF"
    
    # 持久化配置（AOF）
    log_info "配置 AOF 持久化..."
    sed -i "s/appendonly no/appendonly yes/" "$REDIS_CONF"
    
    # 日志级别
    log_info "配置日志级别..."
    sed -i "s/loglevel notice/loglevel warning/" "$REDIS_CONF"
    
    # 保存配置到文件
    echo "REDIS_PASSWORD=$REDIS_PASSWORD" > /root/.redis_credentials
    chmod 600 /root/.redis_credentials
    
    log_info "Redis 配置完成"
    log_warn "Redis 密码已保存到 /root/.redis_credentials"
}

# 启动 Redis 服务
start_redis() {
    log_info "启动 Redis 服务..."
    
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        systemctl enable redis-server
        systemctl start redis-server
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        systemctl enable redis
        systemctl start redis
    fi
    
    log_info "Redis 服务已启动"
}

# 验证 Redis 安装
verify_redis() {
    log_info "验证 Redis 安装..."
    
    sleep 2
    
    if command -v redis-cli &> /dev/null; then
        redis-cli ping
        log_info "Redis 安装验证成功"
    else
        log_error "Redis 安装验证失败"
        exit 1
    fi
}

# 配置防火墙（可选）
configure_firewall() {
    log_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 6379/tcp
        log_info "已开放 Redis 端口 6379"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=6379/tcp
        firewall-cmd --reload
        log_info "已开放 Redis 端口 6379"
    else
        log_warn "未检测到防火墙，跳过配置"
    fi
}

# 创建 Redis 配置文件（用于项目）
create_project_config() {
    log_info "创建项目 Redis 配置文件..."
    
    CONFIG_DIR="$(dirname "$0")/../config"
    CONFIG_FILE="$CONFIG_DIR/redis_config.yaml"
    
    mkdir -p "$CONFIG_DIR"
    
    cat > "$CONFIG_FILE" <<EOF
# Redis 配置文件
# 用于 Polymarket 量化交易系统

redis:
  host: "localhost"
  port: 6379
  password: "${REDIS_PASSWORD}"
  db: 0
  
  # 连接池配置
  pool:
    max_connections: 50
    min_connections: 5
    max_idle_time: 300
    
  # 超时配置
  timeout:
    connect: 5
    read: 5
    write: 5
    
  # 重试配置
  retry:
    max_attempts: 3
    delay: 1
    
  # Pub/Sub 配置
  pubsub:
    channels:
      - "market_updates"
      - "order_updates"
      - "price_alerts"
      - "system_events"
EOF
    
    log_info "项目 Redis 配置文件已创建: $CONFIG_FILE"
}

# 显示安装信息
show_info() {
    echo ""
    echo "========================================="
    echo "Redis 安装完成！"
    echo "========================================="
    echo ""
    echo "Redis 服务状态:"
    systemctl status redis-server --no-pager || systemctl status redis --no-pager
    echo ""
    echo "Redis 版本:"
    redis-server --version
    echo ""
    echo "Redis 连接信息:"
    echo "  主机: localhost"
    echo "  端口: 6379"
    echo "  密码: 查看 /root/.redis_credentials 或项目配置文件"
    echo ""
    echo "常用命令:"
    echo "  启动服务: sudo systemctl start redis-server"
    echo "  停止服务: sudo systemctl stop redis-server"
    echo "  重启服务: sudo systemctl restart redis-server"
    echo "  查看状态: sudo systemctl status redis-server"
    echo "  连接客户端: redis-cli -a <password>"
    echo ""
    echo "配置文件位置:"
    echo "  Redis 配置: /etc/redis/redis.conf"
    echo "  项目配置: config/redis_config.yaml"
    echo ""
}

# 主函数
main() {
    log_info "开始 Redis 安装与配置..."
    
    check_root
    detect_os
    update_system
    install_redis
    configure_redis
    start_redis
    verify_redis
    configure_firewall
    create_project_config
    show_info
    
    log_info "Redis 安装与配置完成！"
}

# 执行主函数
main
