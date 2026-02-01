# Claude Bridge - Telegram Bot for Claude Code CLI

> **Windows 原生版本** - 通过 Telegram 远程控制 Claude Code CLI

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

---

## ✨ 特性

- ✅ **Windows 原生支持** - 无需 WSL、tmux、node-pty
- ✅ **Claude Code CLI 集成** - 直接调用本地 Claude Code CLI
- ✅ **GLM API 备用** - Claude Code CLI 不可用时自动切换
- ✅ **流式输出** - 实时返回 AI 响应，无阻塞
- ✅ **项目切换** - 随意切换工作目录
- ✅ **斜杠命令** - Telegram 原生命令菜单支持
- ✅ **局域友好** - Bot 在本地运行，无需公网 IP

---

## 🚀 快速开始

### 1. 环境要求

- Windows 10/11
- Python 3.8+
- Claude Code CLI（或 GLM API Key）

### 2. 安装 Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
```

或者使用 GLM API（备用方案）：
- 访问 [智谱 AI 开放平台](https://open.bigmodel.cn/) 获取 API Key

### 3. 创建 Telegram Bot

1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot` 创建 bot
3. 获取 Bot Token

### 4. 配置项目

```bash
# 克隆项目
git clone https://github.com/your-username/claude-bridge-windows.git
cd claude-bridge-windows

# 复制配置文件
copy .env.example .env

# 编辑 .env 文件，填入你的 Token
notepad .env
```

在 `.env` 文件中配置：

```bash
TELEGRAM_BOT_TOKEN=你的_bot_token
ZHIPU_API_KEY=你的_GLM_API_key  # 可选
PROJECT_PATH=C:\Your\Default\Project  # 可选
```

### 5. 安装依赖

```bash
pip install python-dotenv
```

### 6. 启动 Bot

**方式 1：使用批处理文件（推荐）**
```bash
start.bat
```

**方式 2：直接运行 Python**
```bash
python claude_bridge.py
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

### Claude Code 命令

| 命令 | 功能 |
|------|------|
| `/help` | 显示 Claude Code 帮助 |
| `/clear` | 清空对话历史 |
| `/model` | 查看当前模型 |
| `/cost` | 查看使用成本 |

---

## 💡 使用示例

### 查看当前目录
```
/pwd
```

### 切换到项目目录
```
/cd C:\Users\YourName\Projects\MyProject
```

### 在项目中执行操作
```
ls                          # 列出文件
cat README.md               # 查看文件
find . -name "*.py"         # 查找 Python 文件
```

### 使用 Claude Code
```
帮我重构这个函数
解释这段代码的作用
创建一个新的用户认证模块
```

---

## 🏗️ 项目结构

```
claude-bridge-windows/
├── claude_bridge.py         # 主程序
├── .env.example             # 配置模板
├── start.bat                # 启动脚本
├── run.bat                  # 运行脚本
├── README.md                # 项目文档
├── .gitignore               # Git 忽略文件
└── LICENSE                  # 许可证
```

---

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ✅ | - |
| `ZHIPU_API_KEY` | 智谱 AI API Key | ❌ | - |
| `PROJECT_PATH` | 默认项目路径 | ❌ | 当前目录 |

### 高级配置

```bash
# 设置超时时间（秒）
TIMEOUT=300

# 启用调试模式
DEBUG=true
```

---

## 🛡️ 安全性

- ✅ 只向外连接 Telegram API，不接收入站连接
- ✅ 支持局域网部署，无需公网 IP
- ✅ 敏感信息存储在本地 `.env` 文件（不提交到 Git）
- ✅ 所有 AI 对话历史存储在本地 `~/.claude/` 目录

---

## 📝 技术架构

```
Telegram → Claude Bridge → Claude Code CLI
                           ↓
                      执行命令/生成代码
                           ↓
                      流式返回结果
                           ↓
                       Telegram
```

**关键特性：**
- 使用 `subprocess.Popen` 实时读取 Claude Code CLI 输出
- 每 ~500 字符发送一次，避免 Telegram 速率限制
- 支持 stdin/stderr 分离处理
- 自动 EOF 处理，避免进程挂起

---

## 🐛 故障排查

### Bot 不响应
1. 检查 Bot Token 是否正确
2. 确认 Claude Code CLI 已安装：`claude --version`
3. 查看控制台错误日志

### 429 Too Many Requests
- 流式输出已优化，正常使用不会触发
- 如遇到，等待几秒后重试

### 无法切换目录
- 确保路径存在：`/pwd` 查看当前路径
- 使用绝对路径更可靠：`/cd C:\Projects`
- 支持相对路径：`/cd ..`

---

## 📚 原项目

本项目基于 [MateBot](https://github.com/aresbit/MateBot) 修改，移除了 tmux 和 node-pty 依赖，实现 Windows 原生支持。

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## ⭐ Star History

如果这个项目对你有帮助，请给个 Star ⭐

---

**Made with ❤️ for Claude Code CLI users on Windows**
