@echo off
echo === 莲华 Agent 服务器连接 ===
echo.

REM Start SSH tunnel (skip if already running)
echo [1/2] Starting SSH tunnel to school server...
ssh -f -N -L 8080:localhost:8080 -L 8081:localhost:8081 gdut 2>nul
if %errorlevel% equ 0 (
    echo   Tunnel started: localhost:8080 -^> gdut:8080
) else (
    echo   Tunnel may already be active (port in use = OK)
)

REM Start Anthropic proxy for Claude Code
echo [2/2] Starting Anthropic proxy...
start "Renge Proxy" /B C:/Users/AD/.conda/envs/torch/python.exe proxy_server.py 8787
echo   Proxy: localhost:8787 -^> Anthropic API

echo.
echo === Ready! ===
echo.
echo Agent GUI:  run agent_gui.py, select "🏫 学校服务器 Qwen-32B" in LLM settings
echo Claude Code: set ANTHROPIC_BASE_URL=http://localhost:8787
echo.
pause
