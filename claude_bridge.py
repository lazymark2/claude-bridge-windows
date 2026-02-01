#!/usr/bin/env python3
"""Claude Bridge - Windows + GLM Version

简化版 MateBot，移除 tmux 依赖，直接调用 Claude Code CLI
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

# 立即刷新输出
sys.stdout.reconfigure(line_buffering=True)

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env 文件可选

# ============================================================
# 配置
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID_FILE = Path.home() / ".claude" / "telegram_chat_id"
PENDING_FILE = Path.home() / ".claude" / "telegram_pending"
UPDATE_OFFSET_FILE = Path.home() / ".claude" / "telegram_offset"

# GLM API 配置
GLM_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
GLM_API_BASE = "https://open.bigmodel.cn/api/paas/v4/"

# Claude Code 权限模式（用于自动化）
PERMISSION_MODE = os.environ.get("PERMISSION_MODE", "default")

# ============================================================
# Telegram API
# ============================================================

def telegram_api(method, data):
    """调用 Telegram API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[Telegram API error] {e}")
        return None

def get_updates(offset=None):
    """获取 Telegram 更新"""
    data = {"timeout": 30}
    if offset:
        data["offset"] = offset
    return telegram_api("getUpdates", data)

def send_message(chat_id, text, reply_markup=None):
    """发送消息到 Telegram

    Args:
        chat_id: Telegram Chat ID
        text: 消息文本
        reply_markup: 可选的内联键盘（InlineKeyboardMarkup）
    """
    # 清理 ANSI 码
    text = clean_ansi(text)

    # 跳过空消息或纯空白消息
    if not text or not text.strip():
        return None

    # 检查消息长度（Telegram 限制 4096 字符）
    if len(text) > 4096:
        text = text[:4090] + "... [截断]"

    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup

    return telegram_api("sendMessage", data)

def create_confirmation_keyboard():
    """创建确认/取消按钮的内联键盘"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ 确认操作", "callback_data": "confirm_yes"},
                {"text": "❌ 取消操作", "callback_data": "confirm_no"}
            ]
        ]
    }
    return json.dumps(keyboard)

def answer_callback_query(callback_query_id, text=None):
    """回答回调查询（避免按钮一直在加载状态）"""
    data = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text
        data["show_alert"] = True
    return telegram_api("answerCallbackQuery", data)

def setup_bot_commands():
    """注册 Telegram Bot 命令菜单"""
    commands = [
        {"command": "pwd", "description": "📂 显示当前工作目录"},
        {"command": "cd", "description": "📁 切换工作目录: /cd <path>"},
        {"command": "home", "description": "🏠 切换到用户主目录"},
        {"command": "downloads", "description": "⬇️ 切换到下载目录"},
        {"command": "desktop", "description": "🖥️ 切换到桌面"},
        {"command": "help", "description": "❓ 显示使用帮助"},
        {"command": "bridge", "description": "🔧 显示 Bridge 控制命令帮助"},
    ]

    result = telegram_api("setMyCommands", {"commands": commands})
    if result and result.get("ok"):
        print("[Telegram] ✓ 命令菜单已注册")
        print("[Telegram] 可用命令:")
        for cmd in commands:
            print(f"  /{cmd['command']:<12} - {cmd['description']}")
    else:
        print("[Telegram] ✗ 命令菜单注册失败")
    return result

def clean_ansi(text):
    """移除 ANSI 转义码（颜色、格式等）

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    # 移除 ANSI 转义序列
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# ============================================================
# Claude Code CLI Wrapper (Windows 版)
# ============================================================

class ClaudeCodeCLI:
    """Claude Code CLI 包装器 - Windows 版本"""

    def __init__(self, project_path=None):
        # 默认路径：环境变量 → 家目录
        default_path = Path(os.environ.get("PROJECT_PATH", Path.home()))
        self.project_path = project_path or default_path
        self.is_windows = sys.platform == "win32"

        # 查找 claude 命令
        self.claude_cmd = self._find_claude_command()

    def set_project_path(self, path):
        """设置项目路径"""
        self.project_path = Path(path)
        return self.project_path

    def _find_claude_command(self):
        """查找 Claude Code CLI 命令"""
        # 优先级: PATH → npm 全局目录
        try:
            # Windows 上需要 shell=True 来运行 .cmd 文件
            subprocess.run("claude --version",
                       shell=True,
                       capture_output=True,
                       check=True,
                       timeout=5)
            return "claude"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 尝试 npx 方式
            try:
                subprocess.run("npx -y @anthropic-ai/claude-code --version",
                           shell=True,
                           capture_output=True,
                           check=True,
                           timeout=10)
                return "npx -y @anthropic-ai/claude-code"
            except:
                return None

    def send_prompt_stream(self, prompt, chat_id, callback, timeout=300):
        """发送提示词到 Claude Code CLI 并流式输出

        Args:
            prompt: 用户提示词
            chat_id: Telegram Chat ID
            callback: 接收到新内容时的回调函数 callback(text_chunk)
            timeout: 超时时间（秒）

        Returns:
            (success: bool, error: str)
        """
        try:
            if self.is_windows:
                # Windows: 使用 shell=True 来运行 .cmd 文件
                # 构建完整的命令（包含权限模式）
                cmd = self.claude_cmd
                if PERMISSION_MODE != "default":
                    cmd += f" --permission-mode {PERMISSION_MODE}"
                    print(f"[Claude CLI] 使用权限模式: {PERMISSION_MODE}")

                # 启动进程并实时读取输出
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                    text=True,
                    cwd=self.project_path
                )

                # 发送输入
                process.stdin.write(prompt + "\n")
                process.stdin.flush()
                process.stdin.close()  # 关闭 stdin 以发送 EOF

                # 实时读取输出
                output_buffer = []
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        # 清理 ANSI 转义码
                        clean_line = clean_ansi(line)
                        output_buffer.append(clean_line)
                        # 每累计约 500 字符就发送一次
                        current_output = "".join(output_buffer)
                        if len(current_output) >= 500:
                            callback(current_output)
                            output_buffer = []

                # 发送剩余内容
                if output_buffer:
                    callback("".join(output_buffer))

                # 等待进程结束
                process.wait(timeout=timeout)

                return True, ""

        except subprocess.TimeoutExpired:
            process.kill()
            return False, f"命令超时（{timeout}秒）"
        except Exception as e:
            return False, f"执行错误: {str(e)}"

    def send_prompt(self, prompt, timeout=300):
        """发送提示词到 Claude Code CLI（非流式，用于 GLM 模式）

        Args:
            prompt: 用户提示词
            timeout: 超时时间（秒）

        Returns:
            (success: bool, output: str, error: str)
        """
        try:
            if self.is_windows:
                # Windows: 使用 shell=True 来运行 .cmd 文件
                # 使用 stdin 发送输入
                result = subprocess.run(
                    self.claude_cmd,
                    shell=True,
                    input=prompt,
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False
                )

                output = result.stdout
                error = result.stderr

                # 检查是否有错误
                if result.returncode != 0:
                    if "API key" in error or "ANTHROPIC" in error:
                        return False, "", "API密钥错误或未配置"
                    elif "network" in error.lower():
                        return False, "", "网络连接错误"
                    else:
                        # 其他错误可能仍然有输出
                        pass

                return True, output, error

        except subprocess.TimeoutExpired:
            return False, "", f"命令超时（{timeout}秒）"
        except Exception as e:
            return False, "", f"执行错误: {str(e)}"

    def is_available(self):
        """检查 Claude Code CLI 是否可用"""
        return self.claude_cmd is not None

# ============================================================
# GLM API Client (备用方案)
# ============================================================

class GLMClient:
    """GLM-4 API 客户端"""

    def __init__(self):
        self.api_key = GLM_API_KEY
        self.base_url = GLM_API_BASE

    def chat(self, messages, tools=None):
        """调用 GLM-4 API

        Args:
            messages: 消息历史 [{"role": "...", "content": "..."}]
            tools: 工具列表（可选）

        Returns:
            (success: bool, content: str, error: str)
        """
        if not self.api_key:
            return False, "", "未配置 GLM_API_KEY"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "glm-4.7",
            "messages": messages,
            "temperature": 0.7
        }

        if tools:
            data["tools"] = tools

        try:
            req = urllib.request.Request(
                self.base_url + "chat/completions",
                data=json.dumps(data).encode(),
                headers=headers
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read())

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return True, content, ""
            else:
                return False, "", f"API错误: {result.get('error', 'Unknown')}"

        except urllib.request.HTTPError as e:
            return False, "", f"HTTP错误: {e.code}"
        except Exception as e:
            return False, "", f"请求错误: {str(e)}"

    def is_available(self):
        """检查 GLM API 是否可用"""
        return bool(self.api_key)

# ============================================================
# 主 Bot 逻辑
# ============================================================

class ClaudeBridge:
    """Claude Bridge - 主控制器"""

    def __init__(self):
        self.claude = ClaudeCodeCLI()
        self.glm = GLMClient()
        self.mode = "claude"  # 或 "glm"

        # Transcript 监控相关
        self.transcript_dir = Path.home() / ".claude" / "transcripts"
        self.last_transcript_path = None
        self.last_position = 0

        # 待确认命令存储 {chat_id: {"command": str, "timestamp": float}}
        self.pending_confirmations = {}

        # 优先使用 Claude Code CLI，失败则使用 GLM API
        if self.claude.is_available():
            self.mode = "claude"
            print(f"[ClaudeBridge] 使用模式: Claude Code CLI")
        elif self.glm.is_available():
            self.mode = "glm"
            print(f"[ClaudeBridge] 使用模式: GLM API")
        else:
            print("[ClaudeBridge] 警告: Claude Code 和 GLM API 都不可用!")
            print("[ClaudeBridge] 请配置以下之一:")
            print("  1. 安装 Claude Code CLI: npm install -g @anthropic-ai/claude-code")
            print("  2. 配置 GLM API Key: export ZHIPU_API_KEY=your_key")

    def _handle_bridge_commands(self, command, chat_id):
        """处理 Bridge 特殊控制命令

        Args:
            command: 命令（已去掉开头的 /）
            chat_id: Telegram Chat ID

        Returns:
            True 如果是特殊命令并已处理，False 否则
        """
        command = command.strip()

        # pwd - 显示当前工作目录
        if command == "pwd":
            current_path = self.claude.project_path
            msg = f"📂 当前工作目录:\n\n```\n{current_path}\n```"
            send_message(chat_id, msg)
            print(f"[Bridge] 当前目录: {current_path}")
            return True

        # cd <path> - 切换工作目录
        if command.startswith("cd "):
            new_path = command[3:].strip()
            try:
                path_obj = Path(new_path)

                # 支持相对路径
                if not path_obj.is_absolute():
                    path_obj = self.claude.project_path / path_obj

                # 展开 ~ 和 ..
                path_obj = path_obj.expanduser().resolve()

                if not path_obj.exists():
                    msg = f"❌ 路径不存在:\n\n```\n{new_path}\n```"
                    send_message(chat_id, msg)
                    return True

                if not path_obj.is_dir():
                    msg = f"❌ 不是目录:\n\n```\n{path_obj}\n```"
                    send_message(chat_id, msg)
                    return True

                # 切换目录
                self.claude.set_project_path(path_obj)
                msg = f"✅ 已切换到:\n\n```\n{path_obj}\n```"
                send_message(chat_id, msg)
                print(f"[Bridge] 切换目录: {path_obj}")
                return True

            except Exception as e:
                msg = f"❌ 切换目录失败:\n\n```\n{str(e)}\n```"
                send_message(chat_id, msg)
                return True

        # home - 切换到用户主目录
        if command == "home":
            home_path = Path.home()
            self.claude.set_project_path(home_path)
            msg = f"✅ 已切换到主目录:\n\n```\n{home_path}\n```"
            send_message(chat_id, msg)
            print(f"[Bridge] 切换到主目录: {home_path}")
            return True

        # bridge - 显示 Bridge 控制命令帮助
        if command == "bridge":
            help_text = """🔧 Bridge 控制命令:

`/pwd` - 显示当前工作目录
`/cd <path>` - 切换到指定目录
`/home` - 切换到用户主目录
`/downloads` - 切换到下载目录
`/desktop` - 切换到桌面

💡 提示:
- 支持相对路径: `/cd ../..`
- 支持绝对路径: `/cd C:\\Projects`
- 切换后所有命令都会在新目录执行"""
            send_message(chat_id, help_text)
            return True

        # downloads - 切换到下载目录
        if command == "downloads":
            downloads_path = Path.home() / "Downloads"
            if downloads_path.exists():
                self.claude.set_project_path(downloads_path)
                msg = f"✅ 已切换到下载目录:\n\n```\n{downloads_path}\n```"
                send_message(chat_id, msg)
                print(f"[Bridge] 切换到下载目录: {downloads_path}")
                return True
            else:
                send_message(chat_id, "❌ 下载目录不存在")
                return True

        # desktop - 切换到桌面
        if command == "desktop":
            desktop_path = Path.home() / "Desktop"
            if desktop_path.exists():
                self.claude.set_project_path(desktop_path)
                msg = f"✅ 已切换到桌面:\n\n```\n{desktop_path}\n```"
                send_message(chat_id, msg)
                print(f"[Bridge] 切换到桌面: {desktop_path}")
                return True
            else:
                send_message(chat_id, "❌ 桌面目录不存在")
                return True

        # help - 显示帮助信息
        if command == "help":
            help_text = """🤖 Claude Bridge 使用说明

**Bridge 控制命令：**
`/pwd` - 显示当前工作目录
`/cd <path>` - 切换到指定目录
`/home` - 切换到用户主目录
`/downloads` - 切换到下载目录
`/desktop` - 切换到桌面
`/bridge` - 显示此帮助信息

**AI 对话：**
直接发送任何文本都会作为提示词发送给 Claude Code CLI。

例如：
• "帮我分析这个文件"
• "创建一个 Python 脚本"
• "解释这段代码"

**工作目录：**
• 使用 `/cd` 切换到你的项目目录
• 之后所有 AI 操作都会在该目录下进行

**更多信息：**
https://github.com/lazymark2/claude-bridge-windows"""
            send_message(chat_id, help_text)
            print(f"[Bridge] 显示帮助信息")
            return True

        return False

    def process_message(self, user_message, chat_id, skip_danger_check=False):
        """处理用户消息

        Args:
            user_message: 用户消息
            chat_id: Telegram Chat ID
            skip_danger_check: 是否跳过危险操作检查（内部使用）
        """
        print(f"\n[ClaudeBridge] 处理消息: {user_message[:50]}...")

        # 处理斜杠命令
        # Bridge 特殊命令（pwd, cd, home, downloads, desktop, bridge, help）需要去掉斜杠
        BRIDGE_COMMANDS = {"pwd", "cd", "home", "downloads", "desktop", "bridge", "help"}

        if user_message.startswith("/"):
            # 提取命令名（不包含参数）
            cmd_with_args = user_message[1:].strip()
            cmd_name = cmd_with_args.split()[0] if cmd_with_args else ""

            # 只有 Bridge 特殊命令才去掉斜杠
            if cmd_name in BRIDGE_COMMANDS:
                user_message = cmd_with_args
                print(f"[ClaudeBridge] Bridge 命令，去掉斜杠: {user_message}")
            else:
                # Claude Code CLI 内置命令保留斜杠
                print(f"[ClaudeBridge] Claude CLI 命令，保留斜杠: {user_message}")

        # 处理特殊的 Bridge 控制命令
        if self._handle_bridge_commands(user_message, chat_id):
            return

        # 危险操作检测和确认系统（仅当 skip_danger_check=False 时检查）
        if not skip_danger_check:
            dangerous_keywords = [
                "删除", "delete", "remove", "rm",
                "重命名", "rename", "mv",
                "移动", "move",
                "清空", "clear", "clean",
                "格式化", "format"
            ]
            message_lower = user_message.lower()
            detected_dangerous = [kw for kw in dangerous_keywords if kw in message_lower]

            if detected_dangerous:
                # 存储待确认命令
                self.pending_confirmations[chat_id] = {
                    "command": user_message,
                    "timestamp": time.time()
                }
                warning_msg = f"⚠️ 检测到危险操作: {', '.join(detected_dangerous)}\n\n命令: {user_message[:100]}...\n\n请点击下方按钮选择操作"
                send_message(chat_id, warning_msg, reply_markup=create_confirmation_keyboard())
                print(f"[ClaudeBridge] 危险操作，等待确认: {detected_dangerous}")
                return  # 不执行，等待用户确认

        # 发送"正在思考"通知
        telegram_api("sendChatAction", {"chat_id": chat_id, "action": "typing"})

        # 流式发送回调
        last_sent_length = 0

        def stream_callback(content):
            """流式发送内容到 Telegram"""
            nonlocal last_sent_length

            # 只发送新增的内容
            new_content = content[last_sent_length:]
            if not new_content or not new_content.strip():
                return

            # 分块发送（Telegram 限制4096字符）
            chunks = self._split_message(new_content, max_length=4000)
            for chunk in chunks:
                result = send_message(chat_id, chunk)
                if result and result.get("ok"):
                    print(f"[ClaudeBridge] 发送 {len(chunk)} 字符")

            last_sent_length = len(content)

        # 根据模式调用
        if self.mode == "claude":
            success, error = self.claude.send_prompt_stream(user_message, chat_id, stream_callback)
        else:  # glm
            messages = [
                {"role": "system", "content": "You are Claude Code, a helpful AI coding assistant."},
                {"role": "user", "content": user_message}
            ]
            success, output, error = self.glm.chat(messages)
            if success:
                stream_callback(output)

        if not success:
            # 发送错误消息
            error_msg = f"❌ 执行失败\n\n错误信息: {error}"
            send_message(chat_id, error_msg)
            print(f"[ClaudeBridge] ✗ 错误: {error}")
        else:
            print(f"[ClaudeBridge] ✓ 完成")

    def _execute_prompt(self, user_message, chat_id):
        """内部方法：直接执行提示词（跳过所有检查）

        Args:
            user_message: 用户消息
            chat_id: Telegram Chat ID
        """
        print(f"\n[ClaudeBridge] 执行命令: {user_message[:50]}...")

        # 在命令前添加中文提示，确保回复使用中文
        # 这样可以保持语言一致性
        prompt_to_send = user_message
        if not user_message.startswith("请用中文") and not user_message.startswith("Please"):
            # 检测是否包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_message)
            if has_chinese:
                prompt_to_send = f"请用中文回答以下问题：\n\n{user_message}"

        # 发送"正在思考"通知
        telegram_api("sendChatAction", {"chat_id": chat_id, "action": "typing"})

        # 流式发送回调
        last_sent_length = 0

        def stream_callback(content):
            """流式发送内容到 Telegram"""
            nonlocal last_sent_length

            # 只发送新增的内容
            new_content = content[last_sent_length:]
            if not new_content or not new_content.strip():
                return

            # 分块发送（Telegram 限制4096字符）
            chunks = self._split_message(new_content, max_length=4000)
            for chunk in chunks:
                result = send_message(chat_id, chunk)
                if result and result.get("ok"):
                    print(f"[ClaudeBridge] 发送 {len(chunk)} 字符")

            last_sent_length = len(content)

        # 根据模式调用
        if self.mode == "claude":
            success, error = self.claude.send_prompt_stream(prompt_to_send, chat_id, stream_callback)
        else:  # glm
            messages = [
                {"role": "system", "content": "You are Claude Code, a helpful AI coding assistant."},
                {"role": "user", "content": prompt_to_send}
            ]
            success, output, error = self.glm.chat(messages)
            if success:
                stream_callback(output)

        if not success:
            # 发送错误消息
            error_msg = f"❌ 执行失败\n\n错误信息: {error}"
            send_message(chat_id, error_msg)
            print(f"[ClaudeBridge] ✗ 错误: {error}")
        else:
            print(f"[ClaudeBridge] ✓ 完成")

    def _split_message(self, text, max_length=4000):
        """分割长消息

        Args:
            text: 消息文本
            max_length: 最大长度

        Returns:
            消息块列表
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current = ""

        # 按行分割
        for line in text.split('\n'):
            if len(current) + len(line) + 1 > max_length:
                if current:
                    chunks.append(current)
                    current = line
                else:
                    # 单行太长，强制分割
                    for i in range(0, len(line), max_length):
                        chunks.append(line[i:i+max_length])
            else:
                if current:
                    current += "\n" + line
                else:
                    current = line

        if current:
            chunks.append(current)

        return chunks

# ============================================================
# 主程序
# ============================================================

def main():
    """主程序"""
    print("=" * 60)
    print("Claude Bridge - Windows + GLM Version")
    print("=" * 60)

    # 检查 Token
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("\n❌ 错误: 未配置 TELEGRAM_BOT_TOKEN")
        print("\n请设置环境变量:")
        print("export TELEGRAM_BOT_TOKEN='your_bot_token'")
        return

    # 创建 Chat ID 文件
    CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 初始化 Bridge
    bridge = ClaudeBridge()

    print(f"\n[启动] Bot Token: {os.environ.get('TELEGRAM_BOT_TOKEN')[:10]}...")
    print(f"[启动] Chat ID: 将保存在 {CHAT_ID_FILE}")
    print(f"[启动] 模式: {bridge.mode}")

    # 注册 Telegram Bot 命令菜单
    setup_bot_commands()

    print("\n[轮询] 开始监听 Telegram 消息...\n")

    # 主循环 - 轮询 Telegram
    offset = None
    if UPDATE_OFFSET_FILE.exists():
        with open(UPDATE_OFFSET_FILE) as f:
            try:
                offset = int(f.read().strip())
            except:
                offset = None

    try:
        while True:
            try:
                # 获取更新
                result = get_updates(offset)

                if not result or not result.get("ok"):
                    time.sleep(5)
                    continue

                updates = result.get("result", [])
                if not updates:
                    continue

                for update in updates:
                    update_id = update.get("update_id", 0)

                    try:
                        # 提取消息
                        if "message" in update:
                            message = update["message"]
                            chat_id = str(message["chat"]["id"])
                            text = message.get("text", "")

                            if not text:
                                continue

                            # 保存 Chat ID
                            with open(CHAT_ID_FILE, "w") as f:
                                f.write(chat_id)

                            print(f"\n[消息 #{update_id}] 用户 {chat_id}: {text[:50]}...")

                            # 处理消息
                            bridge.process_message(text, chat_id)

                        # 处理回调查询（按钮点击）
                        elif "callback_query" in update:
                            callback_query = update["callback_query"]
                            callback_id = callback_query.get("id", "")
                            data = callback_query.get("data", "")
                            message_obj = callback_query.get("message", {})
                            chat_id = str(message_obj.get("chat", {}).get("id", ""))

                            print(f"\n[回调查询 #{update_id}] 用户 {chat_id}: {data}")

                            # 处理确认按钮
                            if chat_id in bridge.pending_confirmations:
                                pending = bridge.pending_confirmations[chat_id]

                                # 检查超时（5分钟）
                                if time.time() - pending["timestamp"] > 300:
                                    del bridge.pending_confirmations[chat_id]
                                    answer_callback_query(callback_id, "⏱️ 确认已超时")
                                    send_message(chat_id, "⏱️ 确认已超时，请重新发送命令。")
                                    continue

                                if data == "confirm_yes":
                                    # 确认执行
                                    actual_command = pending["command"]
                                    del bridge.pending_confirmations[chat_id]
                                    answer_callback_query(callback_id, "✅ 已确认，正在执行...")
                                    send_message(chat_id, "✅ 已确认，正在执行...")
                                    print(f"[ClaudeBridge] 用户确认执行: {actual_command[:50]}...")
                                    bridge._execute_prompt(actual_command, chat_id)

                                elif data == "confirm_no":
                                    # 取消操作
                                    del bridge.pending_confirmations[chat_id]
                                    answer_callback_query(callback_id, "❌ 已取消操作")
                                    send_message(chat_id, "❌ 已取消操作。")
                                    print(f"[ClaudeBridge] 用户取消操作")
                                else:
                                    # 未知数据
                                    answer_callback_query(callback_id)
                            else:
                                # 没有待确认的命令
                                answer_callback_query(callback_id, "❌ 没有待确认的操作")

                    except Exception as e:
                        print(f"[错误] 处理更新 {update_id}: {e}")

                    # 更新 offset
                    offset = update_id + 1
                    with open(UPDATE_OFFSET_FILE, "w") as f:
                        f.write(str(offset))

            except Exception as e:
                print(f"[轮询错误] {e}")
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n[停止] Bot 已停止")
    except Exception as e:
        print(f"\n[错误] 主循环异常: {e}")

if __name__ == "__main__":
    main()
