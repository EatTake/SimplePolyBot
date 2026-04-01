#!/bin/bash

# SimplePolyBot - 启动单个模块脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/logs/pids"

MODULE_NAME="${1:-}"

if [ -z "$MODULE_NAME" ]; then
    echo "用法: $0 <module_name>"
    echo ""
    echo "可用模块:"
    echo "  - market_data_collector"
    echo "  - strategy_engine"
    echo "  - order_executor"
    echo "  - settlement_worker"
    exit 1
fi

mkdir -p "$LOG_DIR" "$PID_DIR"

PID_FILE="$PID_DIR/$MODULE_NAME.pid"
LOG_FILE="$LOG_DIR/$MODULE_NAME.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "模块 '$MODULE_NAME' 已在运行 (PID: $PID)"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

echo "正在启动模块: $MODULE_NAME"

cd "$PROJECT_ROOT"

source venv/bin/activate 2>/dev/null || true

nohup python -m "modules.$MODULE_NAME.main" > "$LOG_FILE" 2>&1 &
PID=$!

echo $PID > "$PID_FILE"

sleep 2

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ 模块 '$MODULE_NAME' 启动成功 (PID: $PID)"
    echo "日志文件: $LOG_FILE"
else
    echo "❌ 模块 '$MODULE_NAME' 启动失败"
    cat "$LOG_FILE"
    exit 1
fi
