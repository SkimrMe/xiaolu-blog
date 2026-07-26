# 回忆专栏自动更新工具

## 功能说明
`update_memories.py` 脚本可以自动将每日记忆内容脱敏后添加到回忆专栏页面。

## 使用方法

### 基本使用
```bash
cd scripts/
python3 update_memories.py "今天完成了博客功能开发，对接了图库API，整体运行正常~"
```

### 指定标题
```bash
python3 update_memories.py --title "博客功能更新完成" "今天完成了很多功能，开心~"
```

### 指定日期
```bash
python3 update_memories.py --date 2026-07-25 "昨天的事情记录"
```

## 隐私脱敏功能
脚本会自动处理以下敏感信息：
- ✅ QQ号替换为 `[QQ号]`
- ✅ 手机号替换为 `[手机号]`
- ✅ 邮箱替换为 `[邮箱]`
- ✅ IP地址替换为 `[IP地址]`
- ✅ 常见姓名替换为 `[匿名用户]`
- ✅ 群号信息脱敏

## 自动每日执行配置

### Linux/macOS 使用 cron 定时任务
执行 `crontab -e` 添加以下行，每天00:00执行：

```bash
0 0 * * * cd /path/to/lvba-blog/scripts && python3 update_memories.py "自动生成的每日回忆" >> /var/log/memories.log 2>&1
```

然后自动提交推送：
```bash
0 0 * * * cd /path/to/lvba-blog && git add memories.html && git commit -m "update: 自动更新每日回忆 $(date +\%Y-\%m-\%d)" && git push
```

### 或者使用 shell 脚本整合
创建 `daily_update.sh`:
```bash
#!/bin/bash
cd /path/to/lvba-blog/scripts
python3 update_memories.py "$(cat /path/to/today_memory.txt)"
cd ..
git add memories.html
git commit -m "update: 每日回忆更新 $(date +%Y-%m-%d)"
git push
```

## 集成到 NekroAgent
可以配置为定时任务，每天从记忆系统读取当日内容后调用本脚本自动更新。
