"""YES-NK Windows 桌面端主入口（仿 YES-BD2 main.py）。

用法：
- 常规启动：python main.py
- 在仿 YES-BD2 的独立桌面分身中启动：python main.py --desktop-clone
- 仅切回 Windows 主桌面（紧急热键兜底）：python main.py --switch-default
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from yes_nk.config import config, desktop_clone_config
from yes_nk.utils.desktop_clone import WindowsDesktopCloneManager
from yes_nk.utils.window_1080p import enable_per_monitor_dpi_awareness


def check_ascii_path() -> None:
    """仿 YES-BD2 路径自检：提示 OpenCV/ONNX 在包含中文路径时的潜在读取问题。"""
    cwd = str(Path(__file__).resolve().parent)
    try:
        cwd.encode("ascii")
    except UnicodeEncodeError:
        print(
            "[YES-NK 警告] 检测到项目路径包含非 ASCII（如中文）字符："
            f"{cwd}\n建议移动到纯英文路径（例如 D:\\YES-NK），以避免 OpenCV / OCR 读取素材异常。"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YES-NK 胜利女神：新的希望 自动化入口")
    parser.add_argument(
        "--desktop-clone",
        action="store_true",
        help="仿 YES-BD2：在独立的 Windows 桌面分身 (CreateDesktopW) 中拉起 YES-NK",
    )
    parser.add_argument(
        "--switch-default",
        action="store_true",
        help="立即切回 Windows 默认主桌面",
    )
    parser.add_argument(
        "--in-clone",
        action="store_true",
        help="内部标志：当前进程已在桌面分身会话内运行",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启 ok-script 调试模式（记录详细识别日志与截图标注）",
    )
    args = parser.parse_args(argv)

    enable_per_monitor_dpi_awareness()
    check_ascii_path()

    manager = WindowsDesktopCloneManager(desktop_clone_config)

    if args.switch_default:
        ok = manager.switch_to_default()
        print("已切回主桌面" if ok else "切回主桌面失败（仅支持 Windows）")
        return 0 if ok else 1

    if args.desktop_clone and not args.in_clone:
        if not manager.is_supported_os:
            print("[YES-NK] 桌面分身模式仅支持 Windows 系统。")
            return 1
        if not manager.ensure_desktop():
            print("[YES-NK] 创建桌面分身失败，请尝试以管理员身份运行或改用后台消息模式。")
            return 1
        if getattr(sys, "frozen", False):
            cmd = f'"{sys.executable}" --ok-core --in-clone'
        else:
            cmd = f'"{sys.executable}" "{Path(__file__).resolve()}" --in-clone'
        if args.debug:
            cmd += " --debug"
        pid = manager.launch_in_clone(cmd)
        if not pid:
            print("[YES-NK] 无法在桌面分身内启动 YES-NK 进程。")
            return 1
        print(
            f"[YES-NK] 已在桌面分身 [{manager.desktop_name}] 启动进程 PID={pid}，"
            f"正在切换进入分身桌面（切回主桌面可运行 python main.py --switch-default）。"
        )
        manager.switch_to_clone()
        return 0

    if args.debug:
        config["debug"] = True

    try:
        from ok import OK
    except ImportError:
        print(
            "[YES-NK] 未检测到 ok-script 依赖。请在 Windows Python 3.11+ 环境执行：\n"
            "  pip install -r requirements.txt\n"
            "  python main.py"
        )
        return 1

    ok_runtime = OK(config)
    ok_runtime.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
