#!/bin/bash
# ============================================================
# 容器内自调度后台运行脚本（无cron时的替代方案）
# 持续运行，每天00:00执行每日回忆总结
#
# 启动方式（后台运行）：
#   nohup /workspace/default/lvba-blog/scripts/cron_runner.sh &
#
# 停止方式：
#   pkill -f cron_runner.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../data/daily_log/cron.log"

mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] cron_runner 启动，PID=$$" >> "$LOG_FILE"

while true; do
    # 计算到下一个00:00的秒数
    NOW=$(date +%s)
    MIDNIGHT=$(date -d "tomorrow 00:00" +%s)
    SLEEP_SECS=$((MIDNIGHT - NOW))

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 下次执行时间: $(date -d @$MIDNIGHT '+%Y-%m-%d %H:%M'), 等待 ${SLEEP_SECS}秒" >> "$LOG_FILE"

    # 等待到午夜
    sleep $SLEEP_SECS

    # 稍微延迟几秒，确保日期切换
    sleep 5

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行每日总结" >> "$LOG_FILE"

    # 执行总结脚本
    /bin/bash "$SCRIPT_DIR/run_daily_summary.sh" >> "$LOG_FILE" 2>&1

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行完毕" >> "$LOG_FILE"
done
