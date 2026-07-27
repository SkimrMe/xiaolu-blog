#!/usr/bin/env python3
"""
每日回忆自动总结脚本
每天 00:00 由 cron 执行，将当天的事件日志整理成回忆条目，追加到 memories.json

流程：
1. 读取 data/daily_log/YYYY-MM-DD.jsonl 中的当天事件
2. 如果当天没有事件，跳过
3. 对所有内容进行隐私脱敏（QQ号、手机号、姓名、邮箱等）
4. 将事件按时间顺序整理成可读的段落
5. 自动生成标题和标签
6. 追加到 data/memories.json（去重，避免重复写入）
7. 可选：自动 git commit & push 部署到 GitHub Pages

使用方法：
    python3 daily_memory_summary.py                    # 总结今天
    python3 daily_memory_summary.py --date 2026-07-27  # 总结指定日期
    python3 daily_memory_summary.py --dry-run          # 预览不写入
    python3 daily_memory_summary.py --auto-push        # 自动提交并推送
"""

import re
import os
import sys
import json
import subprocess
import argparse
from datetime import datetime, timedelta

# ========== 隐私脱敏 ==========
SENSITIVE_PATTERNS = [
    (r'[1-9]\d{4,11}', '[QQ号]'),
    (r'1[3-9]\d{9}', '[手机号]'),
    (r'群号[:：]\s*\d+', '群号: [已隐藏]'),
    (r'群\s*\d{5,}', '群 [已隐藏]'),
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[邮箱]'),
    (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP地址]'),
    (r'ghp_[a-zA-Z0-9]{30,}', '[GitHub Token]'),
    # 常见中文姓名兜底（不会误伤太多，但能覆盖常见测试名）
    (r'(张三|李四|王五|赵六|孙七|周八|吴九|郑十|SkimrMe)', '[朋友]'),
]

# ========== 自动标签匹配 ==========
TAG_KEYWORDS = {
    '博客开发': ['博客', '网站', '开发', '部署', 'GitHub', '页面', '功能', 'PR', '合并', 'CSS', 'HTML', 'JS', '主题'],
    '日常': ['今天', '日常', '吃饭', '天气', '开心', '快乐', '记录'],
    '生图': ['生图', '画图', '生成图片', 'AI', '图片', 'Anima', 'ComfyUI'],
    '音乐': ['歌', '音乐', '唱歌', 'UTAU', 'Vocaloid', '调声', 'SynthesizerV', 'svp', 'ustx'],
    '游戏': ['游戏', '玩', '通关', '吃豆人', '小游戏'],
    '生日': ['生日', '生日快', '纪念'],
    '节日': ['儿童节', '春节', '中秋', '圣诞', '元旦', '国庆', '元宵'],
    '网络安全': ['上网', '安全', '保护', '不良信息', '诈骗'],
    '修复': ['修复', 'bug', '问题', '解决', '报错'],
    '新功能': ['新增', '添加', '上线', '推出', '实现'],
    '重构': ['重构', '改造', '优化', '重写'],
}


def desensitize(text: str) -> str:
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def generate_tags(events: list) -> list:
    full_text = ' '.join(e['summary'] for e in events)
    tags = []
    for tag, keywords in TAG_KEYWORDS.items():
        for kw in keywords:
            if kw in full_text and tag not in tags:
                tags.append(tag)
                break
    if not tags:
        tags.append('日常')
    return tags[:3]


def generate_title(date_obj: datetime, events: list) -> str:
    """根据当天事件自动生成标题"""
    date_display = date_obj.strftime('%Y年%m月%d日')
    full_text = ' '.join(e['summary'] for e in events).lower()

    # 根据关键事件选标题
    if '生日' in full_text:
        return f"{date_display} 生日快乐！🎂"
    if any(k in full_text for k in ['上线', '部署', '发布', '开站']):
        return f"{date_display} 新功能上线啦！"
    if any(k in full_text for k in ['修复', 'bug', '问题']):
        return f"{date_display} 修复了一些小问题"
    if any(k in full_text for k in ['重构', '改造', '优化']):
        return f"{date_display} 博客优化记录"
    if any(k in full_text for k in ['新功能', '新增', '添加']):
        return f"{date_display} 添加了新功能～"
    if any(k in full_text for k in ['生图', '画图', '图片生成']):
        return f"{date_display} 今天也画了很多图"
    if any(k in full_text for k in ['PR', '合并']):
        return f"{date_display} 收到新贡献，合并PR！"

    return f"{date_display} 日常小记"


def build_content_paragraphs(events: list) -> list:
    """将事件整理成自然段落"""
    if not events:
        return []

    paragraphs = []
    # 开头段：概述
    if len(events) == 1:
        opening = f"今天只做了一件事：{events[0]['summary']}。"
    else:
        opening = f"今天发生了{len(events)}件值得记录的事情，来总结一下吧～"
    paragraphs.append(opening)

    # 中间段：按主题/标签分组描述
    # 简单方案：按时段分组（上午/下午/晚上）
    morning = []
    afternoon = []
    evening = []

    for e in events:
        try:
            hour = int(e['time'].split(':')[0])
        except (ValueError, IndexError):
            hour = 12
        summary = e['summary'].rstrip('。.!！?？') + '。'
        if hour < 12:
            morning.append(summary)
        elif hour < 18:
            afternoon.append(summary)
        else:
            evening.append(summary)

    if morning:
        paragraphs.append('上午' + ''.join(morning))
    if afternoon:
        paragraphs.append('下午' + ''.join(afternoon))
    if evening:
        paragraphs.append('到了晚上，' + ''.join(evening))

    # 结尾段
    endings = [
        '又是充实的一天！明天也要继续加油～💚',
        '今天也辛苦啦！期待明天会更好～',
        '今天过得很有意义，把这些都记录下来留作纪念！',
        '每天都有小进步，继续保持～💪',
    ]
    import random
    paragraphs.append(random.choice(endings))

    return paragraphs


def load_events(log_path: str) -> list:
    """加载当天事件"""
    if not os.path.exists(log_path):
        return []
    events = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def load_memories(json_path: str) -> list:
    if not os.path.exists(json_path):
        return []
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_memories(memories: list, json_path: str):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=4)
        f.write('\n')


def git_commit_and_push(repo_dir: str, date_str: str):
    """自动提交并推送到 GitHub"""
    try:
        # 检查是否有 GH_TOKEN 环境变量
        gh_token = os.environ.get('GH_TOKEN', '')
        if gh_token:
            # 设置带token的remote（临时）
            subprocess.run(
                ['git', 'remote', 'set-url', 'origin',
                 f'https://sfghgy249:{gh_token}@github.com/sfghgy249/xiaolu-blog.git'],
                cwd=repo_dir, capture_output=True
            )

        # Stage data changes
        subprocess.run(['git', 'add', 'data/'], cwd=repo_dir, capture_output=True, check=True)

        # Check if there are staged changes
        result = subprocess.run(
            ['git', 'diff', '--cached', '--stat'],
            cwd=repo_dir, capture_output=True, text=True
        )
        if not result.stdout.strip():
            print("ℹ️  没有数据变化需要提交")
            # Restore remote URL
            if gh_token:
                subprocess.run(
                    ['git', 'remote', 'set-url', 'origin', 'https://github.com/sfghgy249/xiaolu-blog.git'],
                    cwd=repo_dir, capture_output=True
                )
            return False

        # Commit
        commit_msg = f"docs: {date_str} 每日回忆自动更新"
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=repo_dir, capture_output=True, check=True)

        # Push
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=repo_dir, capture_output=True, check=True)

        # Restore remote URL
        if gh_token:
            subprocess.run(
                ['git', 'remote', 'set-url', 'origin', 'https://github.com/sfghgy249/xiaolu-blog.git'],
                cwd=repo_dir, capture_output=True
            )

        print(f"🚀 已提交并推送到 GitHub！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git 操作失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='每日回忆自动总结脚本')
    parser.add_argument('--date', '-d', help='日期 YYYY-MM-DD，默认昨天（因为凌晨00:00执行）')
    parser.add_argument('--dry-run', action='store_true', help='预览不写入')
    parser.add_argument('--auto-push', action='store_true', help='自动提交并推送到GitHub')
    parser.add_argument('--force', action='store_true', help='即使该日期已有回忆也强制写入')
    args = parser.parse_args()

    # 确定日期 - cron在00:00执行时，应该总结"昨天"
    if args.date:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        date_obj = datetime.now() - timedelta(days=1)  # 默认昨天
    date_str = date_obj.strftime('%Y-%m-%d')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.abspath(os.path.join(script_dir, '..'))
    log_path = os.path.join(repo_dir, 'data', 'daily_log', f'{date_str}.jsonl')
    memories_path = os.path.join(repo_dir, 'data', 'memories.json')

    print(f"📅 处理日期: {date_str}")
    print(f"📂 日志路径: {log_path}")

    # 加载事件
    events = load_events(log_path)
    if not events:
        print(f"ℹ️  {date_str} 没有事件记录，跳过")
        return

    print(f"📊 当天共有 {len(events)} 条事件记录")

    # 检查是否已存在该日期的自动回忆（避免重复）
    if not args.force:
        memories = load_memories(memories_path)
        for m in memories:
            if m.get('date') == date_str and m.get('auto_generated'):
                print(f"⚠️  {date_str} 已有自动生成的回忆，跳过（使用 --force 强制覆盖）")
                return

    # 脱敏
    for e in events:
        e['summary'] = desensitize(e['summary'])

    # 生成内容
    title = desensitize(generate_title(date_obj, events))
    paragraphs = [desensitize(p) for p in build_content_paragraphs(events)]
    tags = generate_tags(events)

    new_entry = {
        'id': 0,  # 后面会重新分配
        'date': date_str,
        'title': title,
        'content': paragraphs,
        'tags': tags,
        'auto_generated': True,
    }

    print(f"\n📝 生成回忆：{title}")
    print(f"🏷️  标签：{', '.join(tags)}")
    print(f"📄 段落数：{len(paragraphs)}")
    for i, p in enumerate(paragraphs, 1):
        print(f"   {i}. {p[:80]}{'...' if len(p) > 80 else ''}")

    if args.dry_run:
        print("\n[预览模式] 将写入以下条目：")
        print(json.dumps(new_entry, ensure_ascii=False, indent=2))
        return

    # 写入 memories.json
    memories = load_memories(memories_path)
    new_id = max((m.get('id', 0) for m in memories), default=0) + 1
    new_entry['id'] = new_id
    memories.insert(0, new_entry)

    # 按日期倒序
    memories.sort(key=lambda m: m.get('date', ''), reverse=True)
    for i, m in enumerate(memories, 1):
        m['id'] = i

    save_memories(memories, memories_path)
    print(f"\n✅ 已保存到 {memories_path}")
    print(f"📊 当前共有 {len(memories)} 条回忆")

    # 清理日志文件（已处理）
    # 保留日志但添加标记
    processed_marker = log_path + '.processed'
    with open(processed_marker, 'w') as f:
        f.write(datetime.now().isoformat() + '\n')
    print(f"🗑️  日志已标记为已处理")

    # 自动提交推送
    if args.auto_push:
        git_commit_and_push(repo_dir, date_str)


if __name__ == '__main__':
    main()
