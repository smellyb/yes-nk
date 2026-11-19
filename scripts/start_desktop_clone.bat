@echo off
chcp 65001 >nul
cd /d "%~dp0.."

if exist "dist\YES-NK\YES-NK.exe" (
    echo [YES-NK] 正在启动与 YES-BD2 一致的桌面分身窗口...
    "dist\YES-NK\YES-NK.exe" --ok-core --desktop-clone
    if errorlevel 1 pause
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py --desktop-clone
) else (
    python main.py --desktop-clone
)
if errorlevel 1 pause
