#!/usr/bin/env python3
"""
每日回忆自动更新脚本
功能：
1. 从记忆系统检索当天记忆内容
2. 隐私脱敏处理（去除人名、QQ号、群号、手机号等敏感信息）
3. 生成回忆条目HTML
4. 更新 memories.html 页面
5. 可配置定时任务每天00:00执行

使用方法：
    python3 update_memories.py "今天发生的事情内容"
    python3 update_memories.py --title "标题" "内容正文"
"""

import re
import os
import sys
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
    '博客开发': ['博客', '网站', '开发', '部署', 'GitHub', '页面', '功能'],
    '日常': ['今天', '日常', '吃饭', '天气', '开心', '快乐'],
    '生图': ['生图', '画图', '生成图片', 'AI', '图片'],
    '音乐': ['歌', '音乐', '唱歌', 'UTAU', 'Vocaloid', '调声'],
    '游戏': ['游戏', '玩', '通关', '吃豆人'],
    '生日': ['生日', '生日快', '纪念'],
    '节日': ['儿童节', '春节', '中秋', '圣诞', '元旦', '国庆'],
    '网络安全': ['上网', '安全', '保护', '不良信息'],
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


def build_memory_html(date_str: str, title: str, content: str, tags: list) -> str:
    """构建回忆条目HTML"""
    # 处理内容换行
    content_paragraphs = ''.join([f'<p>{line.strip()}</p>\n                    ' for line in content.split('\n') if line.strip()])

    # 标签HTML
    tags_html = ''.join([f'<span class="memory-tag">#{tag}</span>' for tag in tags])

    return f'''                <div class="memory-card">
                    <span class="memory-date">📅 {date_str}</span>
                    <h3 class="memory-title">{title}</h3>
                    <div class="memory-content">
                    {content_paragraphs}
                    </div>
                    <div class="memory-tags">
                        {tags_html}
                    </div>
                </div>

                '''


def update_memories_html(new_entry_html: str, html_path: str = '../memories.html'):
    """将新的回忆条目插入到memories.html"""
    if not os.path.exists(html_path):
        print(f"错误：找不到文件 {html_path}")
        return False

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 找到插入点：在 <div id="memoriesContainer"> 后面插入
    insert_marker = '<div id="memoriesContainer">'
    if insert_marker not in content:
        print("错误：找不到回忆容器")
        return False

    # 插入新条目（在最前面）
    new_content = content.replace(insert_marker, insert_marker + '\n' + new_entry_html, 1)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def main():
    parser = argparse.ArgumentParser(description='每日回忆自动更新脚本')
    parser.add_argument('content', nargs='+', help='回忆内容')
    parser.add_argument('--title', '-t', help='回忆标题，不填自动用日期')
    parser.add_argument('--date', '-d', help='日期，格式YYYY-MM-DD，默认今天')

    args = parser.parse_args()

    # 处理内容
    raw_content = ' '.join(args.content)
    content = desensitize(raw_content)

    # 处理日期
    if args.date:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        date_obj = datetime.now()
    date_str = date_obj.strftime('%Y年%m月%d日')
    date_file = date_obj.strftime('%Y-%m-%d')

    # 处理标题
    if args.title:
        title = args.title
    else:
        title = f"{date_str} 日常记录"

    # 自动生成标签
    tags = generate_tags(content)

    print(f"📝 生成回忆：{date_str} - {title}")
    print(f"🔒 脱敏完成，标签：{'、'.join(tags)}")

    # 生成HTML
    entry_html = build_memory_html(date_str, title, content, tags)

    # 更新文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, '..', 'memories.html')

    if update_memories_html(entry_html, html_path):
        print(f"✅ 回忆已成功添加到 memories.html")
        print(f"💡 请执行 git commit 和 git push 部署更新")
    else:
        print("❌ 更新失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
