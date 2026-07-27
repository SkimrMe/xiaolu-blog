#!/usr/bin/env python3
"""
每日回忆自动更新脚本（JSON数据驱动版）
功能：
1. 接收回忆内容，进行隐私脱敏处理（去除人名、QQ号、群号、手机号等敏感信息）
2. 将新回忆条目追加到 data/memories.json 文件
3. 页面通过JS动态加载JSON渲染，无需直接修改HTML
4. 可配置定时任务每天00:00执行

使用方法：
    python3 update_memories.py "今天发生的事情内容"
    python3 update_memories.py --title "标题" "内容正文"
    python3 update_memories.py --date 2026-07-27 --title "标题" "内容正文"
    python3 update_memories.py --dry-run "测试内容"   # 预览不写入
"""

import re
import os
import sys
import json
from datetime import datetime
import argparse

# 隐私脱敏正则模式
SENSITIVE_PATTERNS = [
    # QQ号 - 5-12位数字
    (r'[1-9]\d{4,11}', '[QQ号]'),
    # 手机号 - 11位手机号
    (r'1[3-9]\d{9}', '[手机号]'),
    # 群号模式 - 常见QQ群号描述
    (r'群号[:：]\s*\d+', '群号: [已隐藏]'),
    (r'群\s*\d+', '群 [已隐藏]'),
    # 邮箱
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[邮箱]'),
    # IP地址
    (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP地址]'),
    # 真实姓名模式 - 常见中文姓名（简单匹配）
    (r'(张三|李四|王五|赵六|孙七|周八|吴九|郑十)', '[匿名用户]'),
]

# 默认标签根据内容匹配
TAG_KEYWORDS = {
    '博客开发': ['博客', '网站', '开发', '部署', 'GitHub', '页面', '功能', 'PR', '合并'],
    '日常': ['今天', '日常', '吃饭', '天气', '开心', '快乐', '记录'],
    '生图': ['生图', '画图', '生成图片', 'AI', '图片'],
    '音乐': ['歌', '音乐', '唱歌', 'UTAU', 'Vocaloid', '调声', 'SynthesizerV'],
    '游戏': ['游戏', '玩', '通关', '吃豆人', '小游戏'],
    '生日': ['生日', '生日快', '纪念'],
    '节日': ['儿童节', '春节', '中秋', '圣诞', '元旦', '国庆', '元宵', '劳动', '妇女'],
    '网络安全': ['上网', '安全', '保护', '不良信息', '诈骗'],
    '修复': ['修复', 'bug', '问题', '解决'],
}


def desensitize(text: str) -> str:
    """对文本进行隐私脱敏处理"""
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


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
    return tags[:3]  # 最多3个标签


def load_memories(json_path: str) -> list:
    """加载现有memories.json"""
    if not os.path.exists(json_path):
        return []
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_memories(memories: list, json_path: str):
    """保存memories.json，保持美观缩进"""
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=4)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description='每日回忆自动更新脚本（JSON版）')
    parser.add_argument('content', nargs='+', help='回忆内容（支持多段，用换行\\n分隔段落）')
    parser.add_argument('--title', '-t', help='回忆标题，不填自动用日期')
    parser.add_argument('--date', '-d', help='日期，格式YYYY-MM-DD，默认今天')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不写入文件')

    args = parser.parse_args()

    # 处理内容 - 支持换行分隔段落
    raw_content = ' '.join(args.content)
    # 替换 \\n 为实际换行
    raw_content = raw_content.replace('\\n', '\n')
    paragraphs = [line.strip() for line in raw_content.split('\n') if line.strip()]
    content_paragraphs = [desensitize(p) for p in paragraphs]

    # 处理日期
    if args.date:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        date_obj = datetime.now()
    date_str = date_obj.strftime('%Y-%m-%d')

    # 处理标题
    if args.title:
        title = args.title
    else:
        date_display = date_obj.strftime('%Y年%m月%d日')
        title = f"{date_display} 日常记录"

    # 自动生成标签
    full_content = ' '.join(content_paragraphs)
    tags = generate_tags(full_content)

    print(f"📝 生成回忆：{date_str} - {title}")
    print(f"📄 段落数：{len(content_paragraphs)}")
    print(f"🔒 脱敏完成，标签：{'、'.join(tags)}")

    # 构建新条目
    # 计算新ID
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, '..', 'data', 'memories.json')
    memories = load_memories(json_path)
    new_id = max([m.get('id', 0) for m in memories], default=0) + 1

    new_entry = {
        "id": new_id,
        "date": date_str,
        "title": title,
        "content": content_paragraphs,
        "tags": tags
    }

    if args.dry_run:
        print("\n[预览模式] 将写入以下条目：")
        print(json.dumps(new_entry, ensure_ascii=False, indent=2))
        print(f"\n文件路径：{json_path}")
        return

    # 追加新条目到末尾，ID永久递增永不修改
    memories.append(new_entry)

    # 保存
    save_memories(memories, json_path)
    print(f"\n✅ 回忆已成功添加到 {json_path}")
    print(f"📊 当前共有 {len(memories)} 条回忆")
    print(f"💡 页面会自动加载最新数据，请执行 git commit 和 git push 部署更新")


if __name__ == '__main__':
    main()
