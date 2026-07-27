#!/bin/bash
# 本地开发服务器启动脚本
# 解决 CORS 跨域问题

cd "$(dirname "$0")"

PORT=${1:-8000}

echo "🌱 启动 xiaolu-blog 本地开发服务器..."
echo "🔗 访问地址: http://localhost:$PORT"
echo "⏹️  按 Ctrl+C 停止"
echo ""

python3 serve.py "$PORT"
