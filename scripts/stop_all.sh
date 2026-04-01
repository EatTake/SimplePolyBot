#!/bin/bash

# SimplePolyBot - 停止所有模块脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/logs/pids"

MODULES=(
    "market_data_collector"
    "strategy_engine"
    "order_executor"
    "settlement_worker"
)

for MODULE in "${MODULES[@]}"; do
    PID_FILE="$PID_DIR/$MODULE.pid"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        
        if ps -p $PID > /dev/null 2>&1; then
            echo "正在停止模块: $MODULE (PID: $PID)"
            kill $PID
            rm -f "$PID_FILE"
        else
            echo "模块 '$MODULE' 未运行"
            rm -f "$PID_FILE"
        fi
    else
        echo "模块 '$MODULE' 未运行"
    fi
done

echo ""
echo "✅ 所有模块已停止"
