# PipClaw

基于终端的 AI 编程助手，左侧对话 + 右侧 [Yazi](https://github.com/sxyazi/yazi) 文件管理器分屏。

模型使用 [Kimi K2.5](https://platform.moonshot.cn)（Moonshot OpenAI 兼容 API），Python + [Textual](https://github.com/Textualize/textual) 实现。

<img width="3840" height="2100" alt="微信图片_20260407132140_12989_100" src="https://github.com/user-attachments/assets/cb0b6e8e-ba7f-4b27-ae9c-2ed436dced42" />


---

## 功能

- **AI 对话** — 流式输出，支持多步工具调用
- **内置工具** — `read_file` / `write_file` / `edit_file` / `bash` / `glob_search` / `grep_search` / `list_dir`
- **联网搜索** — Kimi 原生 `$web_search` 工具，无需额外配置
- **视频分析** — `watch_video_clip` 工具，将视频片段发送给模型分析
- **文件管理器** — Yazi 分屏，与 agent 工作目录自动同步
- **斜杠命令** — `/help` `/clear` `/status` `/cost` `/permissions`
- **会话持久化** — 自动保存到 `~/.pipclaw/sessions/`

---

## 安装

### 前置要求

- Python 3.11+
- [Windows Terminal](https://aka.ms/terminal)（分屏启动用）
- [Yazi](https://github.com/sxyazi/yazi)（可选，文件管理器分屏）
- [Git for Windows](https://git-scm.com/)（Yazi 依赖 `file.exe` 识别 MIME）

### 安装步骤

```bash
git clone https://github.com/chenpipi0807/pipclaw.git
cd pipclaw

# 安装依赖
pip install -e .

# 可选：PDF 预览支持
pip install -e ".[pdf]"
```

### 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 Moonshot API Key
# 申请地址：https://platform.moonshot.cn/console/api-keys
```

---

## 启动

### 方式一：直接启动（仅 agent）

```bash
pipclaw
```

### 方式二：分屏启动（agent + Yazi）

双击 `pipclaw-yazi.bat`，或在终端运行：

```bat
D:\path\to\pipclaw\pipclaw-yazi.bat
```

启动后左侧为 PipClaw 对话界面，右侧为 Yazi 文件管理器，自动导航到当前项目目录。

---

## 使用

| 操作 | 说明 |
|---|---|
| 直接输入消息 | 与 AI 对话，支持中文 |
| `/help` | 显示所有斜杠命令 |
| `/clear` | 清空当前会话 |
| `/status` | 查看 token 使用量 |
| `/cost` | 查看估算费用 |
| `/permissions` | 查看工具权限模式 |
| `Ctrl+Q` | 退出 |
| `Ctrl+L` | 清空对话 |

---

## 项目结构

```
pipclaw/
├── pyproject.toml
├── .env.example          # API Key 模板
├── pipclaw-yazi.bat      # 一键分屏启动
├── launch-yazi.ps1       # Yazi 启动辅助脚本
└── src/pipclaw/
    ├── main.py           # 入口：项目选择 → TUI
    ├── api/              # Kimi API 客户端
    ├── runtime/          # Agent 对话循环、Session、权限
    ├── tools/            # 内置工具实现
    ├── tui/              # Textual TUI 组件
    ├── project/          # 项目管理
    └── commands/         # 斜杠命令
```

---

## 依赖

| 包 | 用途 |
|---|---|
| `openai>=1.0` | Kimi API 调用（兼容 OpenAI 格式） |
| `textual>=0.60` | TUI 框架 |
| `rich>=13.0` | 终端富文本渲染 |
| `python-dotenv` | .env 加载 |
| `pyperclip` | 剪贴板支持 |
| `pathspec` | gitignore 风格文件过滤 |
| `term-image` | 终端图片渲染 |
| `mutagen` | 音频元数据读取 |
| `pymupdf`（可选） | PDF 预览 |

---

## License

MIT
