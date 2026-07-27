#!/usr/bin/env python3
"""
NekroAgent 记忆推送入口脚本
供外部 NekroAgent 插件调用，完成事件记录、总结生成、Git推送全流程

使用方式：
1. 推送单条事件：
   python3 nekro_push.py --event "今天完成了博客开发" --type work

2. 推送多条事件后再生成总结：
   python3 nekro_push.py --event "事件1" --type work
   python3 nekro_push.py --event "事件2" --type chat
   python3 nekro_push.py --generate-summary  # 触发总结和推送

3. 一步到位：推送事件并直接生成总结推送
   python3 nekro_push.py --event "今天的工作内容" --type work --generate-summary
"""

import sys
import os
import argparse
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)

# 代理配置（外网访问需要）
PROXY_HOST = "http://192.168.0.92:18081"


def set_proxy_env():
    """配置外网代理"""
    os.environ['http_proxy'] = PROXY_HOST
    os.environ['https_proxy'] = PROXY_HOST
    os.environ['HTTP_PROXY'] = PROXY_HOST
    os.environ['HTTPS_PROXY'] = PROXY_HOST


def push_event(content: str, event_type: str = 'work', date: str = None, tags: list = None) -> bool:
    """记录一条事件到日志"""
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, 'log_event.py'),
        content,
        '--type', event_type,
    ]
    if date:
        cmd.extend(['--date', date])
    if tags:
        for tag in tags:
            cmd.extend(['--tag', tag])

    result = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 事件记录失败: {result.stderr}", file=sys.stderr)
        print(f"   stdout: {result.stdout}", file=sys.stderr)
        return False

    print(result.stdout.strip())
    return True


def generate_summary(date: str = None, auto_push: bool = True) -> bool:
    """生成每日回忆总结并可选自动推送"""
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, 'daily_memory_summary.py'),
    ]
    if date:
        cmd.extend(['--date', date])
    if auto_push:
        cmd.append('--auto-push')

    result = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ 总结生成失败: {result.stderr}", file=sys.stderr)
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description='NekroAgent 记忆推送接口')
    parser.add_argument('--event', '-e', type=str, help='事件内容文本')
    parser.add_argument('--type', '-t', choices=['work', 'chat'], default='work', help='事件类型')
    parser.add_argument('--date', '-d', type=str, help='日期 YYYY-MM-DD，默认今天')
    parser.add_argument('--tag', action='append', default=[], help='标签（可多次指定）')
    parser.add_argument('--generate-summary', '-g', action='store_true', help='记录事件后生成总结并推送')
    parser.add_argument('--summary-only', action='store_true', help='只生成总结，不添加新事件')

    args = parser.parse_args()

    # 配置代理
    set_proxy_env()

    # 确保 GH_TOKEN 在环境中
    if not os.environ.get('GH_TOKEN'):
        # 尝试从配置读取
        token_file = os.path.join(SCRIPT_DIR, '.gh_token')
        if os.path.exists(token_file):
            with open(token_file) as f:
                os.environ['GH_TOKEN'] = f.read().strip()

    if args.summary_only:
        # 仅生成总结
        success = generate_summary(date=args.date)
        sys.exit(0 if success else 1)

    if not args.event:
        print("❌ 错误：必须提供 --event 参数或使用 --summary-only", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # 记录事件
    if not push_event(args.event, args.type, args.date, args.tag):
        sys.exit(1)

    # 生成总结
    if args.generate_summary:
        print("\n" + "=" * 50)
        print("开始生成每日回忆总结...")
        print("=" * 50)
        success = generate_summary(date=args.date)
        sys.exit(0 if success else 1)

    print(f"\n💡 提示：事件已记录，如需生成总结并推送请添加 --generate-summary 参数")
    print(f"   或单独执行：python3 scripts/nekro_push.py --summary-only")


if __name__ == '__main__':
    main()
