# 脚本工具文档

xiaolu-blog 项目提供了一系列自动化脚本，用于内容更新、回忆生成、数据维护等功能。

## 脚本列表

| 脚本 | 功能 | 依赖 |
|------|------|------|
| [nekro_push.py](#nekro_pushpy) | **NekroAgent 外部推送统一入口**，事件记录+总结+推送一键完成 | 标准库 |
| [log_event.py](#log_eventpy) | 记录每日事件（开发工作/群聊话题）到日志文件 | 标准库 |
| [daily_memory_summary.py](#daily_memory_summarypy) | 每日回忆自动总结生成，支持脱敏、自动提交推送 | 标准库 |
| [update_memories.py](#update_memoriespy) | 手动添加回忆条目，直接写入 memories.json | 标准库 |
| [fetch_bilibili_videos.py](#fetch_bilibili_videospy) | B站视频自动抓取，更新视频专栏数据 | requests |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 目录结构

```
xiaolu-blog/
├── scripts/
│   ├── log_event.py              # 事件记录脚本
│   ├── daily_memory_summary.py   # 每日总结脚本
│   ├── update_memories.py        # 手动添加回忆
│   ├── fetch_bilibili_videos.py  # B站视频抓取
│   ├── run_daily_summary.sh      # 每日总结执行入口
│   ├── cron_runner.sh            # 后台定时调度器
│   └── setup_cron.sh             # 系统cron配置
├── data/
│   ├── memories.json             # 回忆专栏数据
│   ├── videos.json               # 视频专栏数据
│   ├── articles.json             # 文章专栏数据
│   ├── rumors.json               # 辟谣专栏数据
│   ├── diary.json                # 日记数据
│   └── daily_log/                # 每日事件日志目录
│       └── YYYY-MM-DD.jsonl      # 每日事件JSONL格式日志
```

---

## log_event.py

**功能**：记录每日事件到日志文件，供后续总结使用。支持事件类型：`work`（开发工作）、`chat`（群聊话题讨论）。

### 使用方法

```bash
cd scripts/

# 记录开发工作事件
python3 log_event.py "完成博客多主题切换功能，修复非首页主题切换bug"

# 记录群聊话题事件
python3 log_event.py --type chat "群里讨论了绿坝娘新同人作品，大家都很喜欢新的立绘"

# 指定日期记录事件
python3 log_event.py --date 2026-07-26 "补记昨天的内容：调试部署脚本"

# 指定事件来源
python3 log_event.py --source "group-798378266" "群消息记录"
```

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `content` | str | (必填) | 事件内容文本 |
| `--type` | str | `work` | 事件类型：`work`/`chat` |
| `--date` | str | 今天日期 | 事件日期，格式 YYYY-MM-DD |
| `--source` | str | `manual` | 事件来源标识 |

### 输出格式

事件以 JSONL 格式追加到 `data/daily_log/YYYY-MM-DD.jsonl`，每行一条：
```json
{"timestamp": "2026-07-27T23:50:00", "type": "work", "content": "完成文档编写", "source": "manual"}
```

---

## nekro_push.py

**功能**：NekroAgent 外部推送统一入口脚本，封装了事件记录、总结生成、Git推送全流程，供外部 NekroAgent 插件直接调用。**工作区不主动运行定时任务，完全由外部主动推送**。

### 核心特性

- ✅ **统一入口**：外部系统只需要调用这一个脚本即可完成所有操作
- ✅ **自动代理**：内置外网代理配置，Git推送无需额外配置
- ✅ **灵活流程**：支持逐条推送事件，支持一次性推送+总结
- ✅ **环境自检**：自动读取 GH_TOKEN 环境变量或配置文件
- ✅ **错误处理**：清晰的错误码和输出信息，方便外部系统集成

### 使用方法

```bash
cd scripts/

# === 场景1：逐条推送事件，最后统一生成总结 ===
# 推送工作事件
python3 nekro_push.py --event "完成了博客主题切换功能开发" --type work --tag 博客开发
# 推送群聊事件
python3 nekro_push.py --event "群里讨论了新的配色方案" --type chat --tag 设计
# 最后触发总结并自动推送到GitHub
python3 nekro_push.py --summary-only


# === 场景2：推送事件并立即生成总结推送 ===
python3 nekro_push.py --event "今日工作全部完成" --type work --generate-summary


# === 场景3：指定日期推送补录 ===
python3 nekro_push.py --date 2026-07-26 --event "补录昨天的工作" --type work --generate-summary
```

### 命令行参数

| 参数 | 缩写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--event` | `-e` | str | (必填) | 事件内容文本 |
| `--type` | `-t` | str | `work` | 事件类型：`work`(开发工作) / `chat`(群聊话题) |
| `--date` | `-d` | str | 今天 | 日期 YYYY-MM-DD，用于补录历史 |
| `--tag` |  | str | (可多次指定) | 事件标签，用于分类 |
| `--generate-summary` | `-g` | flag | false | 记录事件后立即生成总结并推送 |
| `--summary-only` |  | flag | false | 不添加新事件，仅对已有事件生成总结并推送 |

### 运行模式

**默认模式：自动定时调度**
- `cron_runner.sh` 在后台持续运行，每天 00:00 自动处理前一天的所有事件
- 无需外部触发，和"每三天评论热点"任务使用相同的运行方式
- 自动完成脱敏、总结、提交、推送全流程

**可选模式：外部主动推送**
- NekroAgent 可主动调用本脚本推送事件并立即触发总结
- 两种模式可共存，互不冲突

### NekroAgent 集成流程（主动推送模式）

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  NekroAgent     │      │  nekro_push.py  │      │   GitHub Pages  │
│  外部插件       │ ───> │  工作区脚本     │ ───> │  自动部署       │
└─────────────────┘      └─────────────────┘      └─────────────────┘
     1. 收集事件           2. 记录日志              3. 总结脱敏
     4. 处理敏感信息       5. 自动Git推送           6. 网站更新
```

**重要约定**：
1. 工作区**不运行任何后台定时任务**，完全被动接收外部推送
2. 外部 NekroAgent 负责事件收集、预处理、调用时机
3. 脚本负责：脱敏、格式化、commit、push 到 GitHub
4. GitHub Pages 自动部署，无需额外 Action

### 环境变量要求

| 变量 | 说明 |
|------|------|
| `GH_TOKEN` | GitHub Personal Access Token，用于推送代码（如未设置会读取 `scripts/.gh_token` 文件） |

代理已内置在脚本中，外网访问自动生效。

### 返回码

- `0`：成功
- `1`：失败（错误信息输出到 stderr）

---

## daily_memory_summary.py

**功能**：每日回忆自动总结脚本，读取当天事件日志，经过隐私脱敏后整理成结构化回忆条目，支持自动 commit 和 push 到 GitHub。

### 核心特性

- ✅ **隐私脱敏**：自动替换QQ号、手机号、邮箱、IP、Token、敏感群号等
- ✅ **智能分类**：区分开发工作和群聊话题，分别整理段落
- ✅ **自动标签**：根据内容关键词自动匹配标签
- ✅ **感想生成**：自动为每条回忆生成个人感想/评价结尾
- ✅ **去重机制**：避免重复生成同一天的回忆
- ✅ **Git 自动推送**：一键提交并部署到 GitHub Pages

### 使用方法

```bash
cd scripts/

# 总结昨天的事件（默认）
python3 daily_memory_summary.py

# 总结指定日期
python3 daily_memory_summary.py --date 2026-07-27

# 预览模式，不写入文件
python3 daily_memory_summary.py --dry-run

# 自动提交并推送到GitHub
python3 daily_memory_summary.py --auto-push

# 强制覆盖已有回忆
python3 daily_memory_summary.py --force --date 2026-07-27
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--date YYYY-MM-DD` | 指定要总结的日期，默认为昨天 |
| `--dry-run` | 预览模式，只输出结果不写入文件 |
| `--auto-push` | 处理完成后自动 git commit 并 push |
| `--force` | 即使该日期已有回忆也强制覆盖 |

### 脱敏处理规则

| 模式 | 替换为 |
|------|--------|
| QQ号（5-12位数字） | `[QQ号]` |
| 手机号 | `[手机号]` |
| 邮箱地址 | `[邮箱]` |
| IP地址 | `[IP地址]` |
| GitHub Token (`ghp_xxx`) | `[GitHub Token]` |
| 群号信息 | `群号: [已隐藏]` |
| 常见姓名（张三/李四等） | `[朋友]` |

### NekroAgent 集成说明

从外部 NekroAgent 推送记忆到本系统的流程：
1. 调用 `log_event.py` 将事件写入对应日期的 JSONL 日志
2. 事件全部写入完成后，调用 `daily_memory_summary.py --auto-push` 生成总结并推送
3. 工作区无需运行任何后台定时任务

---

## update_memories.py

**功能**：手动直接添加回忆条目到 `data/memories.json`，同样支持自动脱敏。

### 使用方法

```bash
cd scripts/

# 基础用法：添加一条回忆
python3 update_memories.py "今天天气很好，出去散步了~"

# 指定标题
python3 update_memories.py --title "夏日散步" "今天天气很好，出去散步了~"

# 指定日期
python3 update_memories.py --date 2026-07-25 "回忆昨天的开心事"
```

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `content` | str | (必填) | 回忆内容 |
| `--title` | str | 自动生成 | 回忆标题 |
| `--date` | str | 今天日期 | 日期，格式 YYYY-MM-DD |

---

## fetch_bilibili_videos.py

**功能**：从 B 站搜索 API 自动抓取绿坝娘相关视频，去重后更新视频专栏数据。

### 使用方法

```bash
cd scripts/

# 默认抓取20个最新"绿坝娘"视频
python3 fetch_bilibili_videos.py

# 抓取指定数量
python3 fetch_bilibili_videos.py --count 50

# 指定关键词
python3 fetch_bilibili_videos.py --keyword "绿坝娘 同人"

# 试运行不写入
python3 fetch_bilibili_videos.py --dry-run
```

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--count`, `-c` | int | 20 | 获取视频数量（最大50） |
| `--keyword`, `-k` | str | "绿坝娘" | B站搜索关键词 |
| `--dry-run` | flag | false | 试运行，不写入文件 |

### 数据字段说明

抓取的视频包含以下字段：
- `id`: 递增ID
- `bvid`: B站视频BV号
- `title`: 视频标题（自动移除高亮标签）
- `up`: UP主名称
- `views`: 播放量
- `pubdate`: 发布日期（YYYY-MM-DD）
- `description`: 视频简介
- `thumbnail`: 缩略图标识
