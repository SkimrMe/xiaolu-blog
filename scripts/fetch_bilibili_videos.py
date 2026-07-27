#!/usr/bin/env python3
"""
B站绿坝娘视频自动抓取脚本
功能：
1. 调用B站公开搜索API获取"绿坝娘"关键词的最新视频
2. 自动去重，与现有videos.json合并
3. 按发布日期倒序排列，更新videos.json文件
4. 可配置定时任务定期执行

使用方法：
    python3 fetch_bilibili_videos.py [--count 20] [--keyword "绿坝娘"]

依赖：pip install requests
"""

import json
import os
import sys
import argparse
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("错误：需要安装requests库，请执行 pip install requests")
    sys.exit(1)


# B站搜索API
BILIBILI_SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
DEFAULT_KEYWORD = "绿坝娘"
DEFAULT_COUNT = 20

# 请求头，模拟浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://search.bilibili.com/",
}


def fetch_bilibili_videos(keyword: str, count: int) -> list:
    """从B站搜索API获取视频列表"""
    params = {
        "search_type": "video",
        "keyword": keyword,
        "order": "pubdate",  # 按最新发布排序
        "page_size": min(count, 50),
        "page": 1,
    }

    try:
        resp = requests.get(BILIBILI_SEARCH_API, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            print(f"API返回错误：{data.get('message', '未知错误')}")
            return []

        videos = []
        for item in data.get("data", {}).get("result", []):
            # 转换发布时间
            pubdate = datetime.fromtimestamp(item.get("pubdate", 0)).strftime("%Y-%m-%d")

            videos.append({
                "bvid": item.get("bvid", ""),
                "title": item.get("title", "").replace('<em class="keyword">', '').replace('</em>', ''),  # 移除高亮标签
                "up": item.get("author", ""),
                "views": item.get("play", 0),
                "pubdate": pubdate,
                "description": item.get("description", ""),
                "thumbnail": "🎬",
            })

        return videos

    except Exception as e:
        print(f"获取视频失败：{e}")
        return []


def merge_videos(existing: list, new: list) -> list:
    """合并新旧视频列表，按bvid去重"""
    existing_bvids = {v["bvid"] for v in existing}
    merged = existing.copy()

    added = 0
    for v in new:
        if v["bvid"] not in existing_bvids and v["bvid"]:
            # 分配新ID
            max_id = max((x.get("id", 0) for x in existing), default=0)
            v["id"] = max_id + added + 1
            merged.append(v)
            existing_bvids.add(v["bvid"])
            added += 1

    # 按发布日期倒序排序
    merged.sort(key=lambda x: x.get("pubdate", ""), reverse=True)
    return merged, added


def main():
    parser = argparse.ArgumentParser(description='B站绿坝娘视频自动抓取脚本')
    parser.add_argument('--count', '-c', type=int, default=DEFAULT_COUNT, help='获取视频数量')
    parser.add_argument('--keyword', '-k', default=DEFAULT_KEYWORD, help='搜索关键词')
    parser.add_argument('--dry-run', action='store_true', help='试运行，不写入文件')

    args = parser.parse_args()

    # 获取脚本所在目录，确定videos.json路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, '..', 'data', 'videos.json')

    print(f"🔍 正在搜索B站关键词：\"{args.keyword}\"，获取 {args.count} 个最新视频...")
    new_videos = fetch_bilibili_videos(args.keyword, args.count)
    print(f"✅ 从B站获取到 {len(new_videos)} 个视频")

    # 读取现有数据
    existing = []
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        print(f"📂 现有视频数量：{len(existing)}")

    # 合并
    merged, added = merge_videos(existing, new_videos)
    print(f"🆕 新增视频：{added} 个，合并后总数：{len(merged)}")

    if args.dry_run:
        print("\n试运行结果：")
        for v in new_videos[:5]:
            print(f"  - {v['pubdate']} | {v['up']} | {v['title']} ({v['bvid']})")
        if len(new_videos) > 5:
            print(f"  ... 还有 {len(new_videos) - 5} 个")
        return

    # 写入文件
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=4)

    print(f"💾 已更新 {json_path}")

    if added > 0:
        print("\n新增视频列表：")
        for v in merged[:added]:
            print(f"  + {v['pubdate']} | {v['up']} | {v['title']}")

    print("\n✅ 完成！可以提交git后部署到GitHub Pages。")


if __name__ == '__main__':
    main()
