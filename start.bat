@echo off
REM Claude Bridge - Windows 启动脚本

echo ========================================
echo   Claude Bridge - Windows + GLM
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Python 已安装

REM 检查 Claude Code CLI
claude --version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到 Claude Code CLI
    echo 如果有 GLM API Key，可以直接使用
    echo.
    echo 安装 Claude Code CLI:
    echo   npm install -g @anthropic-ai/claude-code
)

echo [2/3] Claude Code 检查完成
echo.

REM 复制配置文件
if not exist .env (
    echo [3/3] 创建配置文件...
    copy .env.example .env
    echo.
    echo 请编辑 .env 文件，配置你的 Token 和 API Key
    notepad .env
    echo.
    pause
)

echo [3/3] 配置已就绪
echo.
echo 启动 Claude Bridge...
echo.

python claude_bridge.py

pause
