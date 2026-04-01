#!/bin/bash

# SimplePolyBot - 启动所有模块脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODULES=(
    "market_data_collector"
    "strategy_engine"
    "order_executor"
    "settlement_worker"
)

FAILED_MODULES=()

for MODULE in "${MODULES[@]}"; do
    echo ""
    echo "正在启动模块: $MODULE"
    bash "$SCRIPT_DIR/start_module.sh" "$MODULE" || FAILED_MODULES+=("$MODULE")
done

echo ""
if [ ${#FAILED_MODULES[@]} -gt 0 ]; then
    echo "❌ 以下模块启动失败: ${FAILED_MODULES[@]}"
    exit 1
else
    echo "✅ 所有模块启动成功"
fi
