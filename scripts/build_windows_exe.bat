@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo [YES-NK] 正在准备打包 Windows 免安装桌面客户端 (YES-NK.exe)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt pyinstaller
.venv\Scripts\python.exe tools\generate_icon.py
.venv\Scripts\pyinstaller.exe yes_nk.spec --noconfirm --clean

if errorlevel 1 (
    echo [错误] 打包失败，请检查上方输出日志。
    pause
    exit /b 1
)

echo [YES-NK] 打包完成！输出目录：dist\YES-NK\YES-NK.exe
pause
