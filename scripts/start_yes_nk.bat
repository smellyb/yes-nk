@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo [YES-NK] 正在检查 Python 桌面客户端运行环境...
if not exist ".venv\Scripts\python.exe" (
    echo [YES-NK] 首次运行，正在创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 未检测到 Python 3.11+，请先安装 Python 或直接从 GitHub Releases 下载免安装 YES-NK.exe。
        pause
        exit /b 1
    )
    echo [YES-NK] 正在安装 ok-script 与 PySide6 桌面依赖...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\pip.exe install -r requirements.txt
)

if not exist "assets\icon.png" (
    .venv\Scripts\python.exe tools\generate_icon.py
)

echo [YES-NK] 正在启动原生 Windows 桌面客户端...
start "" ".venv\Scripts\pythonw.exe" desktop_launcher.py
exit /b 0
