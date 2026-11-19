@echo off
chcp 65001 >nul
cd /d "%~dp0.."

if exist "dist\YES-NK\YES-NK.exe" (
    echo [YES-NK] 正在通过已打包客户端创建并进入仿 YES-BD2 桌面分身...
    "dist\YES-NK\YES-NK.exe" --ok-core --desktop-clone
    if errorlevel 1 (
        echo [YES-NK] 启动桌面分身失败，请查看 logs\desktop_clone.log 获取详细原因。
        pause
        exit /b 1
    )
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py --desktop-clone
) else (
    python main.py --desktop-clone
)
if errorlevel 1 (
    echo [YES-NK] 启动桌面分身失败，请查看 logs\desktop_clone.log 获取详细原因。
    pause
)
