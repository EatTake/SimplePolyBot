#!/usr/bin/env bash

# SimplePolyBot - 监控脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/logs/pids"

ALERT_LOG="$LOG_DIR/alerts.log"

mkdir -p "$LOG_DIR"

ERROR_KEYWORDS=("ERROR" "CRITICAL" "FAILED" "Exception" "Traceback")
WARNING_KEYWORDS=("WARNING" "WARN")

check_process_health() {
    local MODULE=$1
    local PID_FILE="$PID_DIR/$MODULE.pid"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        
        if ! ps -p $PID > /dev/null 2>&1; then
            log_alert "CRITICAL" "模块 '$MODULE' 进程已崩溃 (PID: $PID)"
            
            if [ "$AUTO_RESTART" = "true" ]; then
                log_alert "INFO" "尝试自动重启模块 '$MODULE'"
                bash "$SCRIPT_DIR/start_module.sh" "$MODULE"
            fi
            
            return 1
        fi
    fi
    
    return 0
}

check_logs_for_errors() {
    local MODULE=$1
    local LOG_FILE="$LOG_DIR/$MODULE.log"
    
    if [ ! -f "$LOG_FILE" ]; then
        return
    fi
    
    LAST_LINES=$(tail -n 100 "$LOG_FILE" 2>/dev/null || true)
    
    for KEYWORD in "${ERROR_KEYWORDS[@]}"; do
        if echo "$LAST_LINES" | grep -q "$KEYWORD"; then
            log_alert "ERROR" "模块 '$MODULE' 发现错误关键字: $KEYWORD"
        fi
    done
    
    for KEYWORD in "${WARNING_KEYWORDS[@]}"; do
        if echo "$LAST_LINES" | grep -q "$KEYWORD"; then
            log_alert "WARNING" "模块 '$MODULE' 发现警告关键字: $KEYWORD"
        fi
    done
}

log_alert() {
    local LEVEL=$1
    local MESSAGE=$2
    local TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$TIMESTAMP] [$LEVEL] $MESSAGE" | tee -a "$ALERT_LOG"
    
    if [ -n "$WEBHOOK_URL" ]; then
        send_webhook_alert "$LEVEL" "$MESSAGE"
    fi
    
    if [ -n "$ALERT_EMAIL" ] && [ "$LEVEL" = "CRITICAL" ] || [ "$LEVEL" = "ERROR" ]; then
        send_email_alert "$LEVEL" "$MESSAGE"
    fi
}

send_webhook_alert() {
    local LEVEL=$1
    local MESSAGE=$2
    
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\": \"[$LEVEL] $MESSAGE\"}" \
        "$WEBHOOK_URL" > /dev/null 2>&1 || true
}

send_email_alert() {
    local LEVEL=$1
    local MESSAGE=$2
    
    echo "$MESSAGE" | mail -s "SimplePolyBot Alert: $LEVEL" "$ALERT_EMAIL" 2>/dev/null || true
}

print_status() {
    echo ""
    echo "==================================="
    echo "  SimplePolyBot 系统状态"
    echo "==================================="
    echo ""
    
    for MODULE in market_data_collector strategy_engine order_executor settlement_worker; do
        PID_FILE="$PID_DIR/$MODULE.pid"
        
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            
            if ps -p $PID > /dev/null 2>&1; then
                CPU=$(ps -p $PID -o %cpu= 2>/dev/null || echo "N/A")
                MEM=$(ps -p $PID -o %mem= 2>/dev/null || echo "N/A")
                echo "✅ $MODULE: 运行中 (PID: $PID, CPU: ${CPU}%, MEM: ${MEM}%)"
            else
                echo "❌ $MODULE: 已崩溃"
            fi
        else
            echo "⚠️ $MODULE: 未运行"
        fi
    done
    
    echo ""
}

if [ "$1" = "--status" ]; then
    print_status
    exit 0
fi

echo "开始监控 SimplePolyBot 系统..."
echo "监控间隔: ${MONITOR_INTERVAL:-60} 秒"
echo ""

while true; do
    for MODULE in market_data_collector strategy_engine order_executor settlement_worker; do
        check_process_health "$MODULE"
        check_logs_for_errors "$MODULE"
    done
    
    sleep ${MONITOR_INTERVAL:-60}
done
