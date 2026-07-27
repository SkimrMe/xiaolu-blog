#!/bin/bash
# ============================================================
# 每日回忆定时任务一键设置脚本
# 在有 cron 的环境下（宿主机/正式服务器）执行此脚本
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_LINE="0 0 * * * /bin/bash $SCRIPT_DIR/run_daily_summary.sh >> $SCRIPT_DIR/../data/daily_log/cron.log 2>&1"

echo "📋 将添加以下 crontab 条目："
echo "   $CRON_LINE"
echo ""

# 检查是否已存在
EXISTING=$(crontab -l 2>/dev/null | grep -F "run_daily_summary.sh" || true)
if [ -n "$EXISTING" ]; then
    echo "⚠️  已存在相关定时任务："
    echo "   $EXISTING"
    echo "   跳过添加。如需重新设置，请先执行 crontab -e 删除旧条目。"
    exit 0
fi

# 添加到 crontab
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

echo "✅ 定时任务设置成功！"
echo "   每天凌晨00:00将自动总结昨天的事件并发布到回忆专栏"
echo ""
echo "📌 查看定时任务：crontab -l"
echo "📌 查看执行日志：tail -f $SCRIPT_DIR/../data/daily_log/cron.log"
echo "📌 手动测试运行：$SCRIPT_DIR/run_daily_summary.sh"
