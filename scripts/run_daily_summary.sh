#!/bin/bash
# ============================================================
# 每日回忆自动总结 cron 执行脚本
# 每天 00:00 执行，总结昨天的事件并推送到 GitHub
#
# crontab 配置：
# 0 0 * * * /workspace/default/xiaolu-blog/scripts/run_daily_summary.sh >> /workspace/default/xiaolu-blog/data/daily_log/cron.log 2>&1
# 注意：脚本使用 BASH_SOURCE 动态定位自身，可在任意 cwd 下执行；
#       请勿依赖硬编码绝对路径（仓库曾用名 lvba-blog，已统一改为 xiaolu-blog）。
# ============================================================

set -e

# 外网代理（访问 GitHub 需要），已注入环境则不覆盖
PROXY_HOST="http://192.168.0.92:18081"
export http_proxy="${http_proxy:-$PROXY_HOST}"
export https_proxy="${https_proxy:-$PROXY_HOST}"
export HTTP_PROXY="${HTTP_PROXY:-$PROXY_HOST}"
export HTTPS_PROXY="${HTTPS_PROXY:-$PROXY_HOST}"

# 配置
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# GitHub Token 从环境变量或配置文件读取
# 方式1：设置环境变量 GH_TOKEN
# 方式2：在 scripts/.gh_token 文件中写入 token（已加入 .gitignore，不会提交）
if [ -z "$GH_TOKEN" ] && [ -n "$NEKRO_RESOURCE_GITHUB_GITHUB" ]; then
    GH_TOKEN="$NEKRO_RESOURCE_GITHUB_GITHUB"
fi
if [ -z "$GH_TOKEN" ] && [ -f "$SCRIPT_DIR/.gh_token" ]; then
    GH_TOKEN=$(cat "$SCRIPT_DIR/.gh_token" | tr -d '[:space:]')
fi

echo "============================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始每日回忆总结"
echo "============================================"

# 切换到仓库目录
cd "$REPO_DIR"

# 确保日志目录存在
mkdir -p data/daily_log

# 执行总结脚本（总结昨天，自动推送）
export GH_TOKEN="$GH_TOKEN"
/usr/bin/python3 "$SCRIPT_DIR/daily_memory_summary.py" --auto-push

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 完成"
echo ""
