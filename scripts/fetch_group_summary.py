#!/usr/bin/env python3
"""
每日群聊总结图片拉取脚本（OneBot v11）

用途：
    从指定 QQ 群的聊天记录中，找到"每日总结机器人"发送的群聊总结图片消息，
    下载并保存为 shared/group_summary/YYYY-MM-DD.jpg，供 group-memory-update
    技能读取生成博客「群聊记忆」。

原理：
    调用 OneBot v11 标准动作 get_group_msg_history 拉取群消息历史，
    筛选指定发送者（默认 QQ 434672754）发出的含图片消息，按消息日期下载图片。

⚠️ 运行位置：
    本脚本必须在**能访问 OneBot HTTP 服务**的机器上运行（即运行 NapCat/Lagrange/
    go-cqhttp 的 bot 主机，通常与 NA 同机）。cc-sandbox 无法直连 bot 端口，
    因此在 cc 内运行会提示连接失败——这是网络边界问题，不是脚本问题。

使用示例：
    # 拉取最近 2 天的总结图片，存到默认目录
    python3 fetch_group_summary.py --base http://127.0.0.1:3000 --token YOUR_TOKEN

    # 只拉取某一天
    python3 fetch_group_summary.py --base http://127.0.0.1:3000 -t TOKEN --date 2026-09-06

    # 只列出会下载哪些图片，不实际下载
    python3 fetch_group_summary.py --base http://127.0.0.1:3000 -t TOKEN --dry-run

参数也可用环境变量：ONEBOT_BASE / ONEBOT_TOKEN / GROUP_ID / SUMMARY_SENDER / GROUP_SUMMARY_DIR
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))  # 东八区

DEFAULT_GROUP = 798378266          # 目标群号
DEFAULT_SENDER = 434672754         # 每日发送 astrbot 群总结的 QQ
DEFAULT_OUTPUT = "/workspace/default/shared/group_summary"


def call_onebot(base: str, token: str, action: str, params: dict, timeout: int = 20):
    """调用 OneBot v11 HTTP API，返回 data 字段。"""
    url = base.rstrip("/") + "/" + action
    body = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"无法连接 OneBot 服务 {url}：{e}\n"
            f"请确认：1) 在运行 bot（NapCat 等）的机器上执行；2) --base 地址端口正确；3) token 正确。"
        )
    except json.JSONDecodeError as e:
        raise RuntimeError(f"OneBot 返回了非 JSON 内容（地址可能不是 OneBot HTTP API）：{e}")

    retcode = payload.get("retcode", payload.get("code", -1))
    if retcode != 0:
        raise RuntimeError(f"OneBot 动作 {action} 返回错误 retcode={retcode}：{payload.get('msg') or payload.get('message')}")
    return payload.get("data", {})


def extract_images(message) -> list:
    """从一条消息中提取图片 URL 列表，兼容 消息段数组 和 CQ 码字符串 两种格式。"""
    urls = []
    if isinstance(message, list):
        for seg in message:
            if isinstance(seg, dict) and seg.get("type") == "image":
                data = seg.get("data", {})
                u = data.get("url") or data.get("file_url") or ""
                if u:
                    urls.append(u)
                elif data.get("file"):
                    urls.append(data["file"])  # 某些实现给本地/相对路径
    elif isinstance(message, str):
        # CQ 码：[CQ:image,file=...,url=https://...,subType=0]
        for m in re.finditer(r"\[CQ:image[^\]]*\]", message):
            seg = m.group(0)
            mu = re.search(r"url=([^,\]]+)", seg)
            if mu:
                urls.append(mu.group(1))
            else:
                mf = re.search(r"file=([^,\]]+)", seg)
                if mf:
                    urls.append(mf.group(1))
    return urls


def fetch_messages(base, token, group_id, days):
    """拉取最近 days 天的群消息（分页向后翻）。"""
    collected = []
    cutoff = datetime.now(CST) - timedelta(days=days)
    seq = 0
    for _ in range(20):  # 最多翻 20 页，防止无限循环
        params = {"group_id": group_id, "count": 50}
        if seq:
            params["message_seq"] = seq
        data = call_onebot(base, token, "get_group_msg_history", params)
        msgs = data.get("messages", []) if isinstance(data, dict) else []
        if not msgs:
            break
        # 消息一般按时间正序；取最旧的 seq 继续向前翻页
        oldest = min(msgs, key=lambda m: m.get("message_seq", m.get("message_id", 0)))
        collected.extend(msgs)
        oldest_time = datetime.fromtimestamp(min(m.get("time", 0) for m in msgs), CST)
        new_seq = oldest.get("message_seq", 0)
        if not new_seq or new_seq == seq or oldest_time < cutoff:
            break
        seq = new_seq

    # 去重 + 时间过滤
    seen = set()
    out = []
    for m in collected:
        mid = m.get("message_id")
        if mid in seen:
            continue
        seen.add(mid)
        try:
            t = datetime.fromtimestamp(m.get("time", 0), CST)
        except (ValueError, OSError):
            continue
        if t >= cutoff:
            out.append(m)
    return out


def download(url: str, dest: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def main():
    p = argparse.ArgumentParser(description="拉取 QQ 群每日总结图片到 group_summary 目录")
    p.add_argument("--base", default=os.environ.get("ONEBOT_BASE", "http://127.0.0.1:3000"),
                   help="OneBot HTTP API 地址（默认 http://127.0.0.1:3000）")
    p.add_argument("--token", "-t", default=os.environ.get("ONEBOT_TOKEN", ""),
                   help="OneBot access_token（也可用环境变量 ONEBOT_TOKEN）")
    p.add_argument("--group", type=int, default=int(os.environ.get("GROUP_ID", DEFAULT_GROUP)),
                   help=f"群号（默认 {DEFAULT_GROUP}）")
    p.add_argument("--sender", type=int, default=int(os.environ.get("SUMMARY_SENDER", DEFAULT_SENDER)),
                   help=f"每日总结发送者 QQ（默认 {DEFAULT_SENDER}）")
    p.add_argument("--output", "-o", default=os.environ.get("GROUP_SUMMARY_DIR", DEFAULT_OUTPUT),
                   help=f"图片保存目录（默认 {DEFAULT_OUTPUT}）")
    p.add_argument("--days", type=int, default=2, help="回溯天数（默认 2）")
    p.add_argument("--date", help="只处理指定日期 YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true", help="只列出将下载的图片，不实际下载")
    p.add_argument("--force", action="store_true", help="已存在同名文件也重新下载")
    args = p.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print(f"🔌 连接 OneBot：{args.base}（群 {args.group}，总结发送者 {args.sender}）")
    try:
        msgs = fetch_messages(args.base, args.token, args.group, args.days)
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    print(f"📨 最近 {args.days} 天共拉取 {len(msgs)} 条群消息")

    found = []
    for m in msgs:
        sender_id = m.get("sender", {}).get("user_id", m.get("user_id", 0))
        if sender_id != args.sender:
            continue
        imgs = extract_images(m.get("message", m.get("raw_message", "")))
        if not imgs:
            continue
        date_str = datetime.fromtimestamp(m.get("time", 0), CST).strftime("%Y-%m-%d")
        for idx, u in enumerate(imgs):
            suffix = "" if len(imgs) == 1 and idx == 0 else f"_{idx+1}"
            fname = f"{date_str}{suffix}.jpg"
            found.append((date_str, fname, u))

    if args.date:
        found = [f for f in found if f[0] == args.date]

    if not found:
        print("ℹ️  没有找到符合条件的总结图片。可能原因：当天机器人未发总结、发送者 QQ 不对、或回溯天数不够。")
        return

    saved = 0
    for date_str, fname, url in found:
        dest = os.path.join(args.output, fname)
        if os.path.exists(dest) and not args.force:
            print(f"⏭️  已存在，跳过：{fname}")
            continue
        if args.dry_run:
            print(f"🔍 [预览] 将下载 {date_str}：{url[:90]}")
            continue
        try:
            download(url, dest)
            print(f"✅ 已保存：{dest}")
            saved += 1
        except Exception as e:
            print(f"❌ 下载失败 {fname}：{e}", file=sys.stderr)

    if not args.dry_run:
        print(f"\n🎉 完成，本次新下载 {saved} 张总结图片到 {args.output}")
        print("   随后即可触发 group-memory-update 流程生成群聊记忆。")


if __name__ == "__main__":
    main()
