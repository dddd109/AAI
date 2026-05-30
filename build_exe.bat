@echo off
echo === 莲华 Agent EXE 构建 ===

set HTTP_PROXY=http://127.0.0.1:7897
set HTTPS_PROXY=http://127.0.0.1:7897

echo [1/3] Installing PyInstaller...
C:/Users/AD/.conda/envs/torch/python.exe -m pip uninstall pyinstaller -y 2>nul
C:/Users/AD/.conda/envs/torch/python.exe -m pip install pyinstaller --proxy=http://127.0.0.1:7897
if %errorlevel% neq 0 (
    echo PyInstaller install failed. Trying without proxy...
    C:/Users/AD/.conda/envs/torch/python.exe -m pip install pyinstaller
)

echo [2/3] Building EXE...
C:/Users/AD/.conda/envs/torch/Scripts/pyinstaller.exe --onefile --windowed --name RengeAgent ^
    --add-data "src;src" ^
    --add-data "vits_infer;vits_infer" ^
    --hidden-import sounddevice ^
    --hidden-import soundfile ^
    --hidden-import openai ^
    --hidden-import httpx ^
    --hidden-import tkinter ^
    --hidden-import numpy ^
    --hidden-import commons ^
    --hidden-import attentions ^
    --hidden-import monotonic_align ^
    agent_gui.py

if %errorlevel% equ 0 (
    echo [3/3] Done! EXE at: dist\RengeAgent.exe
) else (
    echo Build failed. Check errors above.
)
pause
