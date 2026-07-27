# 开发指南

## 环境搭建

### 前置要求

- Python 3.8+
- Git
- （可选）uv 包管理器（推荐替代 pip）

### 初始化开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/sfghgy249/xiaolu-blog.git
cd xiaolu-blog

# 2. 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
# 或使用 uv：
# uv pip install -r requirements.txt
```

### 外网访问配置

如果需要从无法直接访问 GitHub/B站的环境运行脚本，需要配置代理：

```bash
export http_proxy="http://your-proxy:port"
export https_proxy="http://your-proxy:port"
```

## 本地调试（CORS 跨域问题解决）

### 问题说明

**直接用浏览器打开 HTML 文件（`file://` 协议）会遇到 CORS 错误**：

浏览器出于安全限制，`file://` 协议下的页面无法使用 `fetch()` 加载本地 JSON 文件，控制台会报错：
```
Access to fetch at 'file:///.../data/memories.json' from origin 'null' has been blocked by CORS policy
```

这是浏览器安全机制，不是代码bug。**所有页面数据都需要通过 HTTP 服务器访问才能正常加载**。

### 解决方法：使用内置开发服务器

项目提供了开箱即用的本地开发服务器，已配置好 CORS 头，一键启动：

```bash
# 方法1：Python 脚本（推荐，自动添加CORS头）
python3 serve.py

# 方法2：Shell 脚本
./serve.sh

# 指定端口（默认8000）
python3 serve.py 9000
```

启动后访问 **http://localhost:8000** 即可正常调试，所有功能（数据加载、主题切换、图库等）都能正常工作。

### 服务器特性

- ✅ 自动添加 `Access-Control-Allow-Origin: *` 头，解决跨域问题
- ✅ 禁用缓存，修改代码后刷新即可看到最新效果
- ✅ 支持所有静态文件（HTML/CSS/JS/JSON/图片）
- ✅ 零配置，无需安装额外依赖（仅使用Python标准库）

### 其他替代方法

如果你有其他工具也可以使用：

```bash
# Python 内置 HTTP 服务器（无CORS头，某些浏览器仍可能有问题）
python3 -m http.server 8000

# Node.js
npx serve .

# VS Code 插件：Live Server
```

## 项目结构

```
xiaolu-blog/
├── index.html              # 首页
├── memories.html           # 回忆专栏页面
├── videos.html             # 视频专栏页面
├── articles.html           # 文章专栏页面
├── rumors.html             # 辟谣专栏页面
├── diary.html              # 日记页面
├── gallery.html            # 图库页面
├── about.html              # 关于页面
├── css/                    # 样式文件
├── js/                     # JavaScript 脚本
├── img/                    # 图片资源
├── data/                   # 网站数据目录
│   ├── memories.json       # 回忆数据
│   ├── videos.json         # 视频数据
│   ├── articles.json       # 文章数据
│   ├── rumors.json         # 辟谣数据
│   ├── diary.json          # 日记数据
│   └── daily_log/          # 事件日志目录（git忽略）
├── scripts/                # 自动化脚本
│   ├── nekro_push.py       # NekroAgent外部推送统一入口
│   └── ...                 # 其他功能脚本
├── docs/                   # 文档目录
├── serve.py                # 本地开发服务器（解决CORS问题）
├── serve.sh                # 服务器启动脚本
└── requirements.txt        # Python依赖
```

## 数据格式说明

### memories.json 回忆条目格式

```json
[
  {
    "id": 1,
    "date": "2026-07-26",
    "title": "博客功能更新完成",
    "content": "<p>段落1</p><p>段落2</p>",
    "tags": ["博客开发", "日常"],
    "mood": "开心 😊"
  }
]
```

### daily_log JSONL 事件日志格式

每行一个 JSON 对象：
```json
{"timestamp": "2026-07-27T14:30:00", "type": "work", "content": "事件内容", "source": "manual"}
```

事件类型：
- `work`: 开发工作、代码提交、功能实现
- `chat`: 群聊讨论、话题交流

## 测试

### 脚本功能测试

```bash
cd scripts/

# 测试事件记录
python3 log_event.py "测试事件"
cat ../data/daily_log/$(date +%Y-%m-%d).jsonl

# 测试总结生成（预览模式）
python3 daily_memory_summary.py --dry-run

# 测试B站视频抓取
python3 fetch_bilibili_videos.py --dry-run
```

### 本地预览网站

```bash
# 使用 Python 内置 HTTP 服务器
python3 -m http.server 8000
# 访问 http://localhost:8000
```

## Git 工作流

```bash
# 创建功能分支
git checkout -b feature/your-feature

# 提交更改
git add .
git commit -m "feat: your feature description"

# 推送并创建PR
git push origin feature/your-feature
```

### 提交规范

使用 Conventional Commits 规范：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 格式调整
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

## GitHub Pages 部署

项目使用 GitHub Pages 自动部署，推送到 `main` 分支后自动生效，无需额外 GitHub Action 配置。

部署内容：**仅推送网站静态文件和整理后的公开数据**，原始事件日志 `data/daily_log/*.jsonl` 已通过 `.gitignore` 排除，不会上传保护隐私。

## 每日回忆自动定时任务

项目内置后台持续运行的定时调度器，**每天00:00自动执行前一天的事件总结并推送到GitHub**，和"每三天评论热点"任务使用相同的后台运行模式。

### 定时任务说明

| 项 | 配置 |
|----|------|
| 实现方式 | `scripts/cron_runner.sh` - 纯Shell后台自调度，无需系统cron，容器重启可自动恢复 |
| 执行时间 | 每天 00:00（午夜） |
| 处理内容 | 前一天的所有事件记录（work工作 + chat群聊话题） |
| 自动流程 | 读取日志 → 隐私脱敏 → 生成结构化回忆（自动分类+标签+感想） → git commit → 推送到main分支 → GitHub Pages自动部署 |
| 运行日志 | `data/daily_log/cron.log` |

### 管理命令

```bash
# 查看运行状态
pgrep -af cron_runner

# 手动启动（进程不存在时）
cd /workspace/default/xiaolu-blog/
nohup bash scripts/cron_runner.sh >/dev/null 2>&1 &

# 手动触发一次执行（用于测试）
bash scripts/run_daily_summary.sh

# 停止定时任务
pkill -f cron_runner.sh
```

## NekroAgent 集成

支持两种模式，可同时使用：

1. **自动定时模式（默认）**：工作区每天0点自动处理前一天事件，无需外部干预
2. **主动推送模式**：外部 NekroAgent 可以随时通过 `scripts/nekro_push.py` 主动推送事件，立即触发总结推送

### 主动推送使用方法

```bash
cd /workspace/default/xiaolu-blog/

# 逐条推送事件
python3 scripts/nekro_push.py --event "开发工作内容" --type work --tag 博客开发
python3 scripts/nekro_push.py --event "群聊讨论内容" --type chat

# 触发总结和自动推送
python3 scripts/nekro_push.py --summary-only
```

完整参数说明请查看 [脚本工具文档 - nekro_push.py](scripts.md#nekro_pushpy)。

### 环境配置

- `GH_TOKEN`: GitHub Personal Access Token 已内置配置
- 外网代理已内置在脚本中，GitHub/Git访问自动生效

### 部署与隐私

推送代码到 `main` 分支后，GitHub Pages 自动部署，5分钟内网站即可更新。原始事件日志 `data/daily_log/*.jsonl` 已通过 `.gitignore` 排除，**永远不会上传到GitHub**，仅公开脱敏整理后的回忆内容，隐私安全有保障。
