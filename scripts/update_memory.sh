#!/bin/bash
# ============================================================
# 小绿博客 · 每日记忆更新 统一入口（新流程）
#
# 设计目标：
#   - 自定位：用 BASH_SOURCE 动态定位脚本目录，可在任意 cwd 下执行，
#             不依赖任何硬编码绝对路径（修复历史 lvba-blog 路径问题）
#   - 自动配置：代理 + GitHub Token（GH_TOKEN / NEKRO_RESOURCE_GITHUB_GITHUB / .gh_token）
#   - 带自检：check 子命令可快速确认整条链路是否就绪
#
# 用法：
#   bash scripts/update_memory.sh check                       # 环境自检（不写数据）
#   bash scripts/update_memory.sh log "完成了XX开发" [chat]    # 记录一条事件（默认 work，第二参可传 chat）
#   bash scripts/update_memory.sh summary [YYYY-MM-DD]        # 生成指定日期（默认今天）回忆并推送
#   bash scripts/update_memory.sh today                       # 记录标准输入多条事件后生成今日回忆（见下）
#
# 说明：
#   - 事件日志写入 data/daily_log/YYYY-MM-DD.jsonl，自动脱敏后由
#     daily_memory_summary.py 汇总进 data/memories.json（「记忆长廊·小绿回忆」）。
#   - 群聊记忆（data/group_memory.json）由 update_group_memory.py 单独维护，
#     依赖 astrbot 群总结素材，不在本脚本范围。
# ============================================================

set -euo pipefail

# ---------- 自定位 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PY="${PYTHON:-/usr/bin/python3}"

# ---------- 代理（GitHub 访问需要，已注入则不覆盖） ----------
PROXY_HOST="http://192.168.0.92:18081"
export http_proxy="${http_proxy:-$PROXY_HOST}"
export https_proxy="${https_proxy:-$PROXY_HOST}"
export HTTP_PROXY="${HTTP_PROXY:-$PROXY_HOST}"
export HTTPS_PROXY="${HTTPS_PROXY:-$PROXY_HOST}"

# ---------- Token ----------
if [ -z "${GH_TOKEN:-}" ] && [ -n "${NEKRO_RESOURCE_GITHUB_GITHUB:-}" ]; then
    export GH_TOKEN="$NEKRO_RESOURCE_GITHUB_GITHUB"
fi
if [ -z "${GH_TOKEN:-}" ] && [ -f "$SCRIPT_DIR/.gh_token" ]; then
    export GH_TOKEN="$(tr -d '[:space:]' < "$SCRIPT_DIR/.gh_token")"
fi

cmd="${1:-check}"

case "$cmd" in
  check)
    echo "== 小绿博客记忆流程 · 环境自检 =="
    echo "仓库目录 : $REPO_DIR"
    echo "脚本目录 : $SCRIPT_DIR"
    [ -f "$SCRIPT_DIR/nekro_push.py" ]            && echo "✅ nekro_push.py 存在"           || echo "❌ nekro_push.py 缺失"
    [ -f "$SCRIPT_DIR/daily_memory_summary.py" ] && echo "✅ daily_memory_summary.py 存在" || echo "❌ daily_memory_summary.py 缺失"
    [ -f "$REPO_DIR/data/memories.json" ]        && echo "✅ data/memories.json 存在"      || echo "⚠️  data/memories.json 不存在"
    command -v "$PY" >/dev/null 2>&1             && echo "✅ Python: $($PY --version 2>&1)" || echo "❌ Python 不可用"
    command -v git  >/dev/null 2>&1              && echo "✅ git 可用"                      || echo "❌ git 不可用"
    [ -n "${GH_TOKEN:-}" ]                       && echo "✅ GitHub Token 已配置（${#GH_TOKEN} 字符）" || echo "⚠️  GitHub Token 未配置（推送将失败）"
    mkdir -p "$REPO_DIR/data/daily_log"
    echo "✅ 日志目录: $REPO_DIR/data/daily_log"
    echo "自检完成。"
    ;;

  log)
    shift
    text="${1:-}"
    etype="${2:-work}"
    [ -z "$text" ] && { echo "用法: update_memory.sh log \"事件内容\" [work|chat]"; exit 1; }
    "$PY" "$SCRIPT_DIR/nekro_push.py" --event "$text" --type "$etype"
    ;;

  summary)
    shift
    date_arg="${1:-$(date +%F)}"
    echo "== 生成 $date_arg 的回忆并推送 =="
    "$PY" "$SCRIPT_DIR/nekro_push.py" --summary-only --date "$date_arg"
    ;;

  *)
    echo "未知子命令: $cmd"; echo "可用: check | log | summary [YYYY-MM-DD]"; exit 1
    ;;
esac
