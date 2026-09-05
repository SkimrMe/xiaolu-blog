"""
通过 BV 号查询哔哩哔哩视频信息并合并写入 data/videos.json

功能：
1. 调用哔哩哔哩公开 API 获取指定 BV 号的视频信息
2. 按 bvid 自动去重，与现有 videos.json 合并
3. 按发布日期倒序排列并重新编号 id，更新 videos.json

使用方法：
    python3 input_bilibili_videos.py <BV号>              预览精简信息（不写文件）
    python3 input_bilibili_videos.py <BV号> --write      合并写入 videos.json
    python3 input_bilibili_videos.py <BV号> --raw        打印 API 原始完整 JSON
    python3 input_bilibili_videos.py --list              列出现有 videos.json 数据

依赖：pip install requests
（truststore 仅在系统证书较旧时需要，可选）
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ---------- 常量 ----------
API_URL = "https://api.bilibili.com/x/web-interface/view"
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "videos.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
BVID_PATTERN = re.compile(r"^BV[0-9A-Za-z]{10}$")
CST = timezone(timedelta(hours=8))  # B站时间戳按东八区换算日期


def fetch_video(bvid: str) -> dict:
    """查询 BV 号并返回精简后的视频字典；出错时抛出带中文提示的异常。"""
    if not BVID_PATTERN.match(bvid):
        raise ValueError(f"BV 号格式不正确：{bvid}（应为 BV 开头加 10 位字母数字）")

    try:
        r = requests.get(API_URL, params={"bvid": bvid},
                         headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        raise RuntimeError(f"网络请求失败：{e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"返回内容不是有效 JSON（可能被风控拦截，可稍后重试）：{e}") from e

    if data.get("code") != 0:
        raise RuntimeError(f"B站接口返回错误 code={data.get('code')}：{data.get('message')}")

    d = data["data"]
    pubdate = datetime.fromtimestamp(d["pubdate"], tz=CST).strftime("%Y-%m-%d")
    return {
        "bvid": d["bvid"],
        "title": d["title"],
        "up": d["owner"]["name"],
        "views": d["stat"]["view"],
        "pubdate": pubdate,
        "description": d.get("desc", ""),
        "thumbnail": "🎬",
    }


def load_existing() -> list:
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_and_save(video: dict) -> tuple[int, int]:
    """合并视频到 videos.json：按 bvid 去重、按 pubdate 倒序、id 重新编号。
    返回 (合并后总数, 是否为新增)。"""
    existing = load_existing()
    is_new = not any(v.get("bvid") == video["bvid"] for v in existing)

    merged = [v for v in existing if v.get("bvid") != video["bvid"]]
    merged.append(video)
    merged.sort(key=lambda v: v.get("pubdate", ""), reverse=True)
    for i, v in enumerate(merged, start=1):
        v["id"] = i  # 与现有数据保持一致：id 为整数

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=4)
    return len(merged), is_new


def main():
    parser = argparse.ArgumentParser(description="按 BV 号手动添加哔哩哔哩视频到 videos.json")
    parser.add_argument("bvid", nargs="?", help="视频 BV 号，如 BV1ay3v6JEin")
    parser.add_argument("--write", "-w", action="store_true", help="合并写入 videos.json（默认仅预览）")
    parser.add_argument("--raw", action="store_true", help="打印 API 返回的完整原始 JSON")
    parser.add_argument("--list", "-l", action="store_true", help="列出现有 videos.json 数据")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(load_existing(), ensure_ascii=False, indent=4))
        return

    if not args.bvid:
        parser.print_help()
        sys.exit(1)

    try:
        if args.raw:
            r = requests.get(API_URL, params={"bvid": args.bvid},
                             headers=HEADERS, timeout=15)
            print(json.dumps(r.json(), ensure_ascii=False, indent=4))
            return

        video = fetch_video(args.bvid)
        if not args.write:
            print("🔍 查询结果（预览，未写入文件，加 --write 写入）：")
            print(json.dumps(video, ensure_ascii=False, indent=4))
            return

        total, is_new = merge_and_save(video)
        if is_new:
            print(f"✅ 已添加：{video['title']}（{video['bvid']}）")
        else:
            print(f"♻️ 该视频已存在，已更新信息：{video['title']}（{video['bvid']}）")
        print(f"📂 videos.json 当前共 {total} 条，已按发布日期倒序排列")
    except (ValueError, RuntimeError) as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
