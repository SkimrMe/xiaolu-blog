#!/usr/bin/env python3
"""
「群聊记忆」每日更新脚本
功能：
1. 接收当天群聊总结的文本 / Markdown 内容（由 NA 从 astrbot 总结图片解析后传入）
2. 强隐私脱敏：去除群友昵称、QQ号、群号、手机号、链接、@提及 等一切隐私内容
3. 幂等写入 data/group_memory.json：同一天重复执行会覆盖当日条目，不会产生重复
4. 可选 --push 自动 git commit & push 部署到 GitHub Pages

使用方法：
    # 直接传入文本（段落用 \\n 分隔）
    python3 update_group_memory.py "今天大家聊了AI绘画的新模型\\n还讨论了周末的聚餐计划"

    # 从 Markdown 文件读取
    python3 update_group_memory.py --file /path/to/summary.md

    # 指定话题标签（可选，会从内容自动提取）
    python3 update_group_memory.py --topic "AI绘画" --topic "聚餐计划" "正文内容"

    # 指定日期（补录场景）
    python3 update_group_memory.py --date 2026-08-12 "正文内容"

    # 预览不写入
    python3 update_group_memory.py --dry-run "正文内容"

    # 写入并自动推送
    python3 update_group_memory.py --push "正文内容"
"""

import re
import os
import sys
import json
import subprocess
import argparse
from datetime import datetime

# ========== 隐私脱敏规则（群聊记忆专用，比通用版更严格） ==========
# 顺序敏感：先处理结构化模式，再处理通用数字
# 注意：所有占位符统一使用「」全角括号，避免被后续的【】昵称规则二次匹配
SENSITIVE_PATTERNS = [
    # GitHub Token 等密钥
    (r'ghp_[a-zA-Z0-9]{20,}', '「已隐藏」'),
    (r'[a-zA-Z0-9_-]{24}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27,}', '「已隐藏」'),  # 通用token
    # 邮箱
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '「邮箱」'),
    # 链接（http/https/www.）
    (r'https?://\S+', '「链接」'),
    (r'www\.\S+', '「链接」'),
    # IP 地址
    (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '「IP地址」'),
    # 手机号（11位，先于QQ号匹配）
    (r'1[3-9]\d{9}', '「手机号」'),
    # 群号显式表述
    (r'群号[:：]?\s*\d+', '群号「已隐藏」'),
    (r'群\s*[:：]\s*\d{5,}', '群「已隐藏」'),
    # QQ 号显式表述
    (r'[Qq]{2}\s*号?[:：]?\s*\d{5,12}', 'QQ「已隐藏」'),
    # 裸 QQ 号（5-12位数字）
    (r'(?<!\d)[1-9]\d{4,11}(?!\d)', '「QQ号」'),
    # @提及
    (r'@[^\s@，。！？、：:"\'\[\]【】()（）]{1,20}', '「群友」'),
    # 【昵称】 引用格式（仅匹配全角【】，不会误伤已替换的「」占位符）
    (r'【[^\s【】]{1,15}】\s*[:：]?', '「群友」 '),
    # “昵称：发言” 格式（行首或句号后的 2-10 字符昵称 + 冒号）
    (r'(^|[\n。！？])\s*[^\s，。！？：:「」]{2,10}\s*[:：](?=\S)', r'\1「群友」: '),
    # 常见姓名占位（保守处理）
    (r'(张三|李四|王五|赵六|孙七|周八|吴九|郑十)', '「群友」'),
]

# Markdown 结构清理
MD_PATTERNS = [
    (r'^#{1,6}\s*', ''),                    # 标题符号
    (r'^\s*[-*+]\s+', ''),                  # 无序列表符号
    (r'^\s*\d+[.、)]\s*', ''),              # 有序列表符号
    (r'!\[([^\]]*)\]\([^)]*\)', r'\1'),     # 图片 -> 保留alt文本
    (r'\[([^\]]+)\]\([^)]*\)', r'\1'),      # 链接 -> 保留文字
    (r'\*\*([^*]+)\*\*', r'\1'),            # 粗体
    (r'(?<!\w)\*([^*]+)\*(?!\w)', r'\1'),   # 斜体
    (r'`{1,3}([^`]+)`{1,3}', r'\1'),        # 代码
    (r'^>\s*', ''),                         # 引用符号
    (r'^[-*_]{3,}\s*$', ''),                # 分割线
    (r'<[^>]+>', ''),                       # HTML 标签
]

# 自动标签匹配
TAG_KEYWORDS = {
    '群聊': ['群里', '大家', '聊天', '讨论', '话题', '聊到'],
    '日常': ['日常', '吃饭', '天气', '开心', '周末', '放假', '聚餐'],
    '游戏': ['游戏', '通关', '抽卡', '开黑', '联机', '王者', '原神', 'MC', '我的世界'],
    '动漫': ['番', '动画', '漫画', '二次元', '追番', '新番', '角色'],
    '音乐': ['歌', '音乐', '唱歌', 'UTAU', 'Vocaloid', '调声', '术力口'],
    '生图': ['生图', '画图', 'AI绘画', '图片', '表情包'],
    '学习': ['学习', '考试', '作业', '开学', '上课', '考研'],
    '科技': ['AI', '模型', '编程', '代码', '手机', '电脑', '软件'],
    '美食': ['吃', '美食', '奶茶', '火锅', '烧烤', '外卖'],
    '节日': ['儿童节', '春节', '中秋', '圣诞', '元旦', '国庆', '元宵', '七夕'],
}

# 长度限制
MAX_PARAGRAPHS = 6
MAX_TOTAL_CHARS = 400


def clean_markdown(text: str) -> str:
    """清理 Markdown 语法，转为纯文本"""
    result = text
    for pattern, replacement in MD_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.MULTILINE)
    return result


def desensitize(text: str) -> str:
    """隐私脱敏：去除一切可能的个人隐私信息"""
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    # 清理脱敏后可能产生的多余空白
    result = re.sub(r'[ \t]{2,}', ' ', result)
    result = re.sub(r'\s+([，。！？、；：])', r'\1', result)
    return result.strip()


def generate_tags(content: str) -> list:
    """根据内容自动生成标签"""
    tags = []
    for tag, keywords in TAG_KEYWORDS.items():
        for kw in keywords:
            if kw in content and tag not in tags:
                tags.append(tag)
                break
    if not tags:
        tags.append('日常')
    if '群聊' not in tags:
        tags.insert(0, '群聊')
    return tags[:3]


def load_entries(json_path: str) -> list:
    if not os.path.exists(json_path):
        return []
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_entries(entries: list, json_path: str):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
        f.write('\n')


def git_push(repo_dir: str, date_str: str) -> bool:
    """提交并推送到 origin/main"""
    proxy = 'http://192.168.0.92:18081'
    env = dict(os.environ)
    env.setdefault('http_proxy', proxy)
    env.setdefault('https_proxy', proxy)
    env.setdefault('HTTP_PROXY', proxy)
    env.setdefault('HTTPS_PROXY', proxy)
    try:
        subprocess.run(['git', 'add', 'data/group_memory.json'],
                       cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m',
                        f'docs: {date_str} 群聊记忆更新'],
                       cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(['git', 'push', 'origin', 'main'],
                       cwd=repo_dir, check=True, capture_output=True, env=env)
        print('✅ 已提交并推送到 GitHub，Pages 将在几分钟内部署')
        return True
    except subprocess.CalledProcessError as e:
        print(f'⚠️ Git 操作失败: {e.stderr.decode(errors="ignore") if e.stderr else e}')
        return False


def main():
    parser = argparse.ArgumentParser(description='「群聊记忆」每日更新脚本')
    parser.add_argument('content', nargs='*', help='总结正文（多段用 \\n 分隔）')
    parser.add_argument('--file', '-f', help='从文件读取正文（支持 Markdown）')
    parser.add_argument('--title', '-t', help='条目标题，不填自动生成')
    parser.add_argument('--topic', action='append', dest='topics',
                        help='话题标签，可多次指定；不填则留空由页面只展示正文')
    parser.add_argument('--date', '-d', help='日期 YYYY-MM-DD，默认今天')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不写入文件')
    parser.add_argument('--push', action='store_true', help='写入后自动 git commit & push')

    args = parser.parse_args()

    # ---- 读取正文 ----
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            raw = f.read()
        raw = clean_markdown(raw)
    else:
        raw = ' '.join(args.content)
    raw = raw.replace('\\n', '\n')

    paragraphs = [p.strip() for p in raw.split('\n') if p.strip()]
    paragraphs = [desensitize(p) for p in paragraphs]
    paragraphs = [p for p in paragraphs if p and p not in ('[群友]',)]

    if not paragraphs:
        print('❌ 正文为空（或脱敏后无有效内容），未写入')
        sys.exit(1)

    # ---- 长度控制 ----
    truncated = False
    if len(paragraphs) > MAX_PARAGRAPHS:
        paragraphs = paragraphs[:MAX_PARAGRAPHS]
        truncated = True
    total_chars = sum(len(p) for p in paragraphs)
    if total_chars > MAX_TOTAL_CHARS:
        print(f'⚠️ 正文偏长（{total_chars} 字 > 建议 {MAX_TOTAL_CHARS} 字），请考虑精简')
    if truncated:
        print(f'⚠️ 段落过多，已截取前 {MAX_PARAGRAPHS} 段')

    # ---- 日期与标题 ----
    if args.date:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        date_obj = datetime.now()
    date_str = date_obj.strftime('%Y-%m-%d')

    if args.title:
        title = desensitize(args.title)
    else:
        title = f"{date_obj.month}月{date_obj.day}日 群聊话题小记"

    topics = [desensitize(t) for t in args.topics] if args.topics else []
    tags = generate_tags(' '.join(paragraphs + topics))

    # ---- 幂等写入：同一天覆盖 ----
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)
    json_path = os.path.join(repo_dir, 'data', 'group_memory.json')
    entries = load_entries(json_path)

    existing_idx = next((i for i, e in enumerate(entries) if e.get('date') == date_str), None)
    if existing_idx is not None:
        entry_id = entries[existing_idx].get('id', 1)
        action = f'覆盖当日已有条目 (id={entry_id})'
    else:
        entry_id = max([e.get('id', 0) for e in entries], default=0) + 1
        action = f'新增条目 (id={entry_id})'

    new_entry = {
        'id': entry_id,
        'date': date_str,
        'title': title,
        'topics': topics,
        'content': paragraphs,
        'tags': tags,
        'source': 'group_summary',
        'auto_generated': True,
    }

    print(f'📝 {date_str} - {title}')
    print(f'🔧 动作：{action}')
    print(f'📄 段落数：{len(paragraphs)}（{total_chars} 字）')
    print(f'🏷️ 话题：{topics or "（无）"}')
    print(f'🔒 标签：{tags}')

    if args.dry_run:
        print('\n[预览模式] 条目内容：')
        print(json.dumps(new_entry, ensure_ascii=False, indent=2))
        return

    if existing_idx is not None:
        entries[existing_idx] = new_entry
    else:
        entries.append(new_entry)

    save_entries(entries, json_path)
    print(f'\n✅ 已写入 {json_path}（当前共 {len(entries)} 条）')

    if args.push:
        git_push(repo_dir, date_str)
    else:
        print('💡 如需部署，请执行 git commit & push，或下次使用 --push 参数')


if __name__ == '__main__':
    main()
