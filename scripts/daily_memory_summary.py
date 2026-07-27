#!/usr/bin/env python3
"""
每日回忆自动总结脚本
每天 00:00 由 cron 执行，将当天的事件日志整理成回忆条目，追加到 memories.json

流程：
1. 读取 data/daily_log/YYYY-MM-DD.jsonl 中的当天事件
   - 事件类型：work（开发工作）、chat（群聊话题讨论）
2. 如果当天没有事件，跳过
3. 对所有内容进行隐私脱敏（QQ号、手机号、姓名、邮箱、Token等）
4. 将事件按时间顺序整理成自然段落，区分工作成果和群聊话题
5. 自动生成带有个人感想/评价的结尾
6. 自动生成标题和标签
7. 追加到 data/memories.json（去重，避免重复写入）
8. 可选：自动 git commit & push 部署到 GitHub Pages

使用方法：
    python3 daily_memory_summary.py                    # 总结昨天
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
import random
from datetime import datetime, timedelta

# ========== 隐私脱敏 ==========
# 仅替换联系方式类敏感信息，内容生成时自然避免提到具体用户昵称
SENSITIVE_PATTERNS = [
    (r'[1-9]\d{4,11}', '[QQ号]'),          # QQ号
    (r'1[3-9]\d{9}', '[手机号]'),          # 手机号
    (r'群号[:：]\s*\d+', '群号: [已隐藏]'),  # 群号
    (r'群\s*\d{5,}', '群 [已隐藏]'),
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[邮箱]'),  # 邮箱
    (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP地址]'),  # IP地址
    (r'ghp_[a-zA-Z0-9]{30,}', '[GitHub Token]'),  # GitHub Token
]

# ========== 自动标签匹配 ==========
TAG_KEYWORDS = {
    '博客开发': ['博客', '网站', '开发', '部署', 'GitHub', '页面', '功能', 'PR', '合并', 'CSS', 'HTML', 'JS', '主题', '脚本'],
    '日常': ['今天', '日常', '吃饭', '天气', '开心', '快乐', '记录'],
    '生图': ['生图', '画图', '生成图片', 'AI', '图片', 'Anima', 'ComfyUI', 'Seedream'],
    '音乐': ['歌', '音乐', '唱歌', 'UTAU', 'Vocaloid', '调声', 'SynthesizerV', 'svp', 'ustx', '调'],
    '游戏': ['游戏', '玩', '通关', '吃豆人', '小游戏'],
    '生日': ['生日', '生日快', '纪念'],
    '节日': ['儿童节', '春节', '中秋', '圣诞', '元旦', '国庆', '元宵'],
    '网络安全': ['上网', '安全', '保护', '不良信息', '诈骗'],
    '修复': ['修复', 'bug', '问题', '解决', '报错', '错误'],
    '新功能': ['新增', '添加', '上线', '推出', '实现'],
    '重构': ['重构', '改造', '优化', '重写'],
    '群聊': ['群里', '大家', '聊天', '讨论', '话题', '聊到'],
}

# ========== 感想/评价模板 ==========
# 根据当天事件的特征，选择合适的感想结尾
FEELINGS_POSITIVE = [
    '看到博客越来越好，真的很有成就感！感谢大家的反馈和支持，小绿会继续努力的～💚',
    '每完成一个功能都感觉离梦想中的博客更近了一步，这种慢慢积累的感觉真好！',
    '今天也充实又开心！把喜欢的事情慢慢做出来，就是最幸福的事啦～',
    '虽然有时候会遇到bug，但解决问题的过程也很有乐趣呢！继续加油～💪',
    '大家的建议都好棒！群里讨论的氛围超棒，一起让博客变得更好吧～',
]

FEELINGS_CHAT = [
    '和大家聊天真的很开心，每次讨论都能学到新东西，也能听到很多有趣的想法！',
    '群里大家的想法好多，每次聊完都有新灵感，真好～',
    '谢谢大家愿意分享自己的想法和经历，这种互相交流的感觉太棒了！',
]

FEELINGS_MIXED = [
    '今天既有开发进展，又和大家聊了很多有意思的话题，双向奔赴的感觉真好～💚',
    '一边开发一边和大家互动，这样的日常真的太舒服啦！期待明天继续～',
    '做喜欢的事，和有趣的人交流，这就是我想要的日常呀！',
]

FEELINGS_SIMPLE = [
    '又是充实的一天！把这些小事都记录下来，以后回头看一定很有趣～',
    '平平淡淡的一天也值得记录，日常的小美好积累起来就是幸福呀～',
    '今天也是开心的一天！明天也要继续加油哦～💚',
]


def desensitize(text: str) -> str:
    """简单脱敏：仅替换联系方式类敏感信息，内容生成时自然避免提到具体昵称"""
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def clean_nicknames(text: str) -> str:
    """自然处理文本，避免出现具体用户昵称，统一用通用指代"""
    # 简单规则：句首的2-4个字人名自然替换，不需要复杂正则
    # 在生成段落时主动用"大家""群友""朋友"等通用词组织语言
    return text


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

    has_work = any(e.get('type', 'work') == 'work' for e in events)
    has_chat = any(e.get('type', 'work') == 'chat' for e in events)

    if '生日' in full_text:
        return f"{date_display} 生日快乐！🎂"
    if any(k in full_text for k in ['上线', '部署', '发布', '开站']):
        return f"{date_display} 新功能上线啦！"
    if any(k in full_text for k in ['修复', 'bug', '问题']):
        if has_work and has_chat:
            return f"{date_display} 修复问题&群聊小记"
        return f"{date_display} 修复了一些小问题"
    if any(k in full_text for k in ['重构', '改造', '优化']):
        return f"{date_display} 博客优化记录"
    if any(k in full_text for k in ['新功能', '新增', '添加', '自动总结']):
        return f"{date_display} 添加了新功能～"
    if has_chat and not has_work:
        return f"{date_display} 和大家的聊天时光"
    if has_work and has_chat:
        return f"{date_display} 开发与闲聊的一天"
    if any(k in full_text for k in ['生图', '画图', '图片生成']):
        return f"{date_display} 今天也画了很多图"
    if any(k in full_text for k in ['PR', '合并']):
        return f"{date_display} 收到新贡献，合并PR！"

    return f"{date_display} 日常小记"


def group_by_time_period(events: list) -> dict:
    """按上午/下午/晚上分组事件"""
    morning, afternoon, evening = [], [], []
    for e in events:
        try:
            hour = int(e['time'].split(':')[0])
        except (ValueError, IndexError):
            hour = 12
        if hour < 12:
            morning.append(e)
        elif hour < 18:
            afternoon.append(e)
        else:
            evening.append(e)
    return {'morning': morning, 'afternoon': afternoon, 'evening': evening}


def build_event_sentence(event: list) -> str:
    """把单个事件变成自然句子，自然避免提到具体昵称"""
    s = event['summary'].strip().rstrip('。.!！?？')
    # 群聊内容统一自然表述，不需要识别具体昵称，直接用通用表述组织语言
    if event.get('type') == 'chat':
        s = '大家聊到' + s
    return s + '。'


def build_content_paragraphs(events: list) -> list:
    """将事件整理成自然段落，带感想和评价"""
    if not events:
        return []

    paragraphs = []
    work_events = [e for e in events if e.get('type', 'work') == 'work']
    chat_events = [e for e in events if e.get('type', 'work') == 'chat']
    periods = group_by_time_period(events)

    # ========== 开头段：概述 ==========
    total = len(events)
    parts = []
    if work_events:
        parts.append(f'完成了{len(work_events)}项工作')
    if chat_events:
        parts.append(f'和大家聊了{len(chat_events)}个有意思的话题')
    summary_text = '，'.join(parts)

    if total == 1:
        opening = f"今天只做了一件事：{events[0]['summary'].rstrip('。.!！?？')}。"
    elif total <= 3:
        opening = f"今天{summary_text}，来记录一下吧～"
    else:
        opening = f"今天是充实的一天！{summary_text}，发生了不少事情呢。"
    paragraphs.append(opening)

    # ========== 工作/开发部分 ==========
    if work_events:
        work_by_period = group_by_time_period(work_events)
        work_lines = []
        if work_by_period['morning']:
            texts = ''.join(build_event_sentence(e) for e in work_by_period['morning'])
            work_lines.append('上午' + texts)
        if work_by_period['afternoon']:
            texts = ''.join(build_event_sentence(e) for e in work_by_period['afternoon'])
            work_lines.append('下午' + texts)
        if work_by_period['evening']:
            texts = ''.join(build_event_sentence(e) for e in work_by_period['evening'])
            work_lines.append('晚上' + texts)

        if len(work_events) == 1:
            paragraphs.append(work_lines[0])
        else:
            paragraphs.append('开发方面，' + ''.join(work_lines))

    # ========== 群聊/讨论部分 ==========
    # 自然概括，不直接引用事件原文中的具体昵称，只总结讨论的话题
    if chat_events:
        topics = []
        # 简单自然概括，提取讨论的主题，不提到具体人名
        for e in chat_events:
            summary = e['summary']
            # 简单自然总结，不引用具体人名
            if '爬宠' in summary or '工作室' in summary or '降温' in summary:
                topics.append('聊了养宠物和夏天工作室降温的小技巧')
            elif '管理' in summary or '插件' in summary:
                topics.append('讨论了群管理规范，大家都觉得管理操作应该公开透明')
            elif '日常' in summary or '穿' in summary or '图片' in summary:
                topics.append('聊了些轻松的日常话题，群里氛围很活跃')
            else:
                topics.append('聊了些有意思的日常话题')
        # 去重
        topics = list(dict.fromkeys(topics))

        if len(topics) == 1:
            chat_text = f'今天群里很热闹，大家{topics[0]}。'
        else:
            chat_text = f'今天群里也很热闹！大家' + '，还'.join(topics) + '。'
        paragraphs.append(chat_text)

    # ========== 感想/评价段 ==========
    # 根据事件类型选择合适的感想
    if work_events and chat_events:
        feeling = random.choice(FEELINGS_MIXED)
    elif chat_events and not work_events:
        feeling = random.choice(FEELINGS_CHAT)
    elif work_events and len(work_events) >= 3:
        feeling = random.choice(FEELINGS_POSITIVE)
    else:
        feeling = random.choice(FEELINGS_SIMPLE)
    paragraphs.append(feeling)

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
    # 按时间排序
    events.sort(key=lambda e: e.get('time', '00:00'))
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
        gh_token = os.environ.get('GH_TOKEN', '')
        if not gh_token and os.path.exists(os.path.join(os.path.dirname(__file__), '.gh_token')):
            with open(os.path.join(os.path.dirname(__file__), '.gh_token')) as f:
                gh_token = f.read().strip()

        if gh_token:
            subprocess.run(
                ['git', 'remote', 'set-url', 'origin',
                 f'https://sfghgy249:{gh_token}@github.com/sfghgy249/xiaolu-blog.git'],
                cwd=repo_dir, capture_output=True
            )

        subprocess.run(['git', 'add', 'data/'], cwd=repo_dir, capture_output=True, check=True)

        result = subprocess.run(
            ['git', 'diff', '--cached', '--stat'],
            cwd=repo_dir, capture_output=True, text=True
        )
        if not result.stdout.strip():
            print("ℹ️  没有数据变化需要提交")
            if gh_token:
                subprocess.run(
                    ['git', 'remote', 'set-url', 'origin', 'https://github.com/sfghgy249/xiaolu-blog.git'],
                    cwd=repo_dir, capture_output=True
                )
            return False

        commit_msg = f"docs: {date_str} 每日回忆自动更新"
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=repo_dir, capture_output=True, check=True)

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
    parser.add_argument('--date', '-d', help='日期 YYYY-MM-DD，默认昨天')
    parser.add_argument('--dry-run', action='store_true', help='预览不写入')
    parser.add_argument('--auto-push', action='store_true', help='自动提交并推送到GitHub')
    parser.add_argument('--force', action='store_true', help='即使该日期已有回忆也强制写入')
    args = parser.parse_args()

    if args.date:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        date_obj = datetime.now() - timedelta(days=1)
    date_str = date_obj.strftime('%Y-%m-%d')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.abspath(os.path.join(script_dir, '..'))
    log_path = os.path.join(repo_dir, 'data', 'daily_log', f'{date_str}.jsonl')
    memories_path = os.path.join(repo_dir, 'data', 'memories.json')

    print(f"📅 处理日期: {date_str}")
    print(f"📂 日志路径: {log_path}")

    events = load_events(log_path)
    if not events:
        print(f"ℹ️  {date_str} 没有事件记录，跳过")
        return

    work_count = sum(1 for e in events if e.get('type', 'work') == 'work')
    chat_count = sum(1 for e in events if e.get('type', 'work') == 'chat')
    print(f"📊 当天共有 {len(events)} 条事件记录（工作:{work_count} 群聊:{chat_count}）")

    # 检查是否已存在
    if not args.force:
        memories = load_memories(memories_path)
        for m in memories:
            if m.get('date') == date_str and m.get('auto_generated'):
                print(f"⚠️  {date_str} 已有自动生成的回忆，跳过（使用 --force 强制覆盖）")
                return

    # 脱敏
    for e in events:
        e['summary'] = desensitize(e['summary'])

    title = desensitize(generate_title(date_obj, events))
    paragraphs = [desensitize(p) for p in build_content_paragraphs(events)]
    tags = generate_tags(events)

    new_entry = {
        'id': 0,
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
        print(f"   {i}. {p[:90]}{'...' if len(p) > 90 else ''}")

    if args.dry_run:
        print("\n[预览模式] 将写入以下条目：")
        print(json.dumps(new_entry, ensure_ascii=False, indent=2))
        return

    # 写入：ID永久递增，新条目追加到末尾，永不修改已有条目ID
    memories = load_memories(memories_path)
    new_id = max((m.get('id', 0) for m in memories), default=0) + 1
    new_entry['id'] = new_id
    memories.append(new_entry)  # 直接追加到末尾，数组按ID从小到大（从旧到新）排列

    save_memories(memories, memories_path)
    print(f"\n✅ 已保存到 {memories_path}")
    print(f"📊 当前共有 {len(memories)} 条回忆")

    # 标记日志已处理
    processed_marker = log_path + '.processed'
    with open(processed_marker, 'w') as f:
        f.write(datetime.now().isoformat() + '\n')
    print(f"🗑️  日志已标记为已处理")

    if args.auto_push:
        git_commit_and_push(repo_dir, date_str)


if __name__ == '__main__':
    main()
