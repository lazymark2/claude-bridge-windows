# Claude Bridge - Telegram Bot for Claude Code CLI

> **Windows 原生版本** - 基于 MateBot 修改，无需 tmux 和 transcript

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

---

## ✨ 特性

- ✅ **Windows 原生支持** - 无需 WSL、tmux、node-pty
- ✅ **Claude Code CLI 集成** - 直接调用本地 Claude Code CLI
- ✅ **GLM API 支持** - 支持 GLM API 作为替代方案
- ✅ **流式输出** - 实时返回 AI 响应，无阻塞
- ✅ **项目切换** - 轻松切换不同工作目录
- ✅ **斜杠命令** - Telegram 原生命令菜单支持

---

## 🔄 与原 MateBot 的区别

### 架构简化

**原 MateBot：**
```
Telegram → MateBot → tmux → Claude Code CLI
                           ↓
                    监控 transcript 文件
```

**本项目：**
```
Telegram → Claude Bridge → Claude Code CLI / GLM API
```

### 主要变化

| 特性 | MateBot | 本项目 |
|------|---------|--------|
| **Transcript 依赖** | 必需 | 不需要 |
| **tmux 依赖** | 必需 | 不需要 |
| **WSL** | Linux/Mac only | Windows 原生 |
| **node-pty** | 必需 | 不需要 |
| **API 选择** | 仅 Claude | Claude + GLM |
| **部署难度** | 较复杂 | 简单 |

### 为什么不需要 Transcript？

原 MateBot 通过监控 Claude Code CLI 的 transcript 文件来获取 AI 的响应。本项目使用两种更直接的方式：

1. **Claude Code CLI 模式**：直接通过 subprocess 获取输出
2. **GLM API 模式**：直接调用 GLM API，无需本地 CLI

---

## 🚀 快速开始

### 1. 环境要求

- Windows 10/11
- Python 3.8+
- Claude Code CLI（或 GLM API Key）

### 2. 选择 API 方案

**方案 A：Claude Code CLI（推荐）**
```bash
npm install -g @anthropic-ai/claude-code
```

**方案 B：GLM API**
1. 访问 [智谱 AI 开放平台](https://open.bigmodel.cn/)
2. 注册账号并创建 API Key
3. 新用户有免费额度

### 3. 创建 Telegram Bot

1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot` 创建 bot
3. 获取 Bot Token

### 4. 配置项目

```bash
# 克隆项目
git clone https://github.com/lazymark2/claude-bridge-windows.git
cd claude-bridge-windows

# 复制配置文件
copy .env.example .env

# 编辑 .env 文件
notepad .env
```

在 `.env` 文件中配置：

```bash
# Telegram Bot Token（必填）
TELEGRAM_BOT_TOKEN=你的_bot_token

# GLM API Key（可选，如果不用 Claude Code CLI）
ZHIPU_API_KEY=你的_GLM_API_key

# 默认项目路径（可选）
PROJECT_PATH=C:\Your\Default\Project
```

### 5. 安装依赖

```bash
pip install python-dotenv
```

### 6. 启动 Bot

```bash
python claude_bridge.py
# 或
start.bat
```

---

## 📱 Telegram 命令

### Bridge 控制命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `/pwd` | 显示当前工作目录 | `/pwd` |
| `/cd <path>` | 切换到指定目录 | `/cd C:\Projects` |
| `/home` | 切换到用户主目录 | `/home` |
| `/downloads` | 切换到下载目录 | `/downloads` |
| `/desktop` | 切换到桌面 | `/desktop` |
| `/bridge` | 显示 Bridge 帮助 | `/bridge` |

**注意**：直接发送任何文本都会作为提示词发送给 Claude Code CLI。无需特殊命令，直接与 AI 对话即可。

---

## 💡 使用示例

### 查看和切换目录
```
/pwd                    # 查看当前目录
/cd C:\Projects         # 切换到项目目录
```

### 执行命令
```
ls                      # 列出文件
cat README.md          # 查看文件
```

### AI 交互
```
帮我重构这个函数
解释这段代码
创建用户认证模块
```

---

## 🏗️ 项目结构

```
claude-bridge-windows/
├── claude_bridge.py         # 主程序
├── .env.example             # 配置模板
├── start.bat                # 启动脚本
├── README.md                # 项目文档
├── .gitignore               # Git 忽略文件
└── LICENSE                  # MIT 许可证
```

---

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ✅ |
| `ZHIPU_API_KEY` | 智谱 AI API Key | ❌（有 Claude Code CLI 时） |
| `PROJECT_PATH` | 默认项目路径 | ❌ |

---

## 📝 技术实现

### 工作流程

```
1. Telegram 接收消息
2. Claude Bridge 处理消息
3. 根据 API 选择：
   a) Claude Code CLI：subprocess 调用
   b) GLM API：HTTP 请求
4. 流式返回结果到 Telegram
```

### 关键技术点

- **subprocess.Popen** - 实时读取 Claude Code CLI 输出
- **流式输出** - 每 ~500 字符发送一次，避免速率限制
- **stdin.close()** - 正确处理 EOF，避免进程挂起

---

## 🐛 故障排查

### Bot 不响应
1. 检查 Bot Token 是否正确
2. 确认 Claude Code CLI 或 GLM API 可用
3. 查看控制台错误日志

### 切换目录失败
- 确保路径存在
- 使用绝对路径更可靠
- 支持相对路径

---

## 📚 基于

本项目基于 [MateBot](https://github.com/aresbit/MateBot) 修改，主要变更：

- 移除 tmux 依赖
- 移除 transcript 文件依赖
- 添加 Windows 原生支持
- 添加 GLM API 支持
- 添加项目目录切换功能

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Made with ❤️ for Claude Code CLI users on Windows**
