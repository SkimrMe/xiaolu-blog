#!/usr/bin/env python3
"""
记录每日事件到日志文件，供午夜自动总结脚本使用

使用方法：
    # 记录开发/工作事件（默认类型）
    python3 log_event.py "完成了XX功能开发"
    python3 log_event.py --tag 博客开发 --tag 修复 "修复了主题切换bug"

    # 记录群聊话题讨论
    python3 log_event.py --type chat --tag 主题设计 "群里讨论了新主题配色方案，大家觉得蒸汽波风格很酷"
    python3 log_event.py --type chat "大家聊到了暑假计划，好多人说想去海边玩"

    # 指定时间
    python3 log_event.py --time "14:30" "下午完成了代码审查"

事件类型（--type）：
    work  - 开发工作/任务完成（默认）
    chat  - 群聊话题讨论/聊天内容
"""

import json
import os
import sys
import argparse
from datetime import datetime


def get_log_path(date_str=None):
    """获取当天的日志文件路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, '..', 'data', 'daily_log')
    os.makedirs(log_dir, exist_ok=True)
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(log_dir, f'{date_str}.jsonl')


def log_event(summary, tags=None, event_time=None, date_str=None, event_type='work'):
    """记录一条事件到日志

    Args:
        summary: 事件摘要
        tags: 标签列表
        event_time: 事件时间 HH:MM
        date_str: 日期 YYYY-MM-DD
        event_type: 'work' 开发任务 / 'chat' 群聊讨论
    """
    if tags is None:
        tags = []
    if event_time is None:
        event_time = datetime.now().strftime('%H:%M')

    event = {
        'time': event_time,
        'summary': summary.strip(),
        'tags': tags,
        'type': event_type,
    }

    log_path = get_log_path(date_str)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')

    type_label = '💬 群聊' if event_type == 'chat' else '🔧 工作'
    print(f"✅ 已记录{type_label} [{event_time}] {summary[:50]}{'...' if len(summary) > 50 else ''}")
    print(f"   标签: {', '.join(tags) if tags else '无'}")
    print(f"   日志: {log_path}")
    return event


def main():
    parser = argparse.ArgumentParser(description='记录每日事件')
    parser.add_argument('summary', help='事件摘要')
    parser.add_argument('--tag', '-t', action='append', default=[], help='标签（可多次指定）')
    parser.add_argument('--time', help='事件时间 HH:MM，默认当前时间')
    parser.add_argument('--date', help='日期 YYYY-MM-DD，默认今天')
    parser.add_argument('--type', choices=['work', 'chat'], default='work',
                        help='事件类型：work=开发工作（默认），chat=群聊讨论')
    args = parser.parse_args()

    log_event(args.summary, args.tag, args.time, args.date, args.type)


if __name__ == '__main__':
    main()
