"""YES-NK Windows 桌面端主入口（仿 YES-BD2 main.py）。

用法：
- 常规启动：python main.py
- 在仿 YES-BD2 的独立桌面分身中启动（含分身控制台与 Ctrl+Alt+F12 切回热键）：
    python main.py --desktop-clone
- 仅切回 Windows 主桌面（紧急热键兜底）：
    python main.py --switch-default
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from yes_nk.config import (
    PROJECT_ROOT,
    USER_OVERRIDE_CONFIG,
    build_desktop_clone_config,
    config,
    load_user_overrides,
)
from yes_nk.gui.clone_host import (
    append_clone_log,
    get_clone_log_path,
    get_clone_ready_path,
    run_clone_host,
)
from yes_nk.utils.desktop_clone import WindowsDesktopCloneManager
from yes_nk.utils.window_1080p import enable_per_monitor_dpi_awareness


def check_ascii_path() -> None:
    """仿 YES-BD2 路径自检：提示 OpenCV/ONNX 在包含中文路径时的潜在读取问题。"""
    cwd = str(PROJECT_ROOT)
    try:
        cwd.encode("ascii")
    except UnicodeEncodeError:
        print(
            "[YES-NK 警告] 检测到项目路径包含非 ASCII（如中文）字符："
            f"{cwd}\n建议移动到纯英文路径（例如 D:\\YES-NK），以避免 OpenCV / OCR 读取素材异常。"
        )


def build_clone_host_argv(auto_start_ok: bool = True, debug: bool = False) -> list[str]:
    """构造在 WinSta0\\YES_NK_Desktop 内部启动分身控制台的命令行参数列表。"""
    if getattr(sys, "frozen", False):
        argv = [sys.executable, "--clone-host"]
    else:
        argv = [sys.executable, str(Path(__file__).resolve()), "--clone-host"]
    if not auto_start_ok:
        argv.append("--no-auto-start-ok")
    if debug:
        argv.append("--debug")
    return argv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YES-NK 胜利女神：新的希望 自动化入口")
    parser.add_argument(
        "--desktop-clone",
        action="store_true",
        help="仿 YES-BD2：在独立的 Windows 桌面分身 (CreateDesktopW) 中拉起 YES-NK",
    )
    parser.add_argument(
        "--clone-host",
        action="store_true",
        help="内部标志：在桌面分身会话内运行常驻分身控制台与热键守护",
    )
    parser.add_argument(
        "--no-auto-start-ok",
        action="store_true",
        help="进入桌面分身时仅打开分身控制台，不自动拉起 ok-script",
    )
    parser.add_argument(
        "--switch-default",
        action="store_true",
        help="立即切回 Windows 默认主桌面",
    )
    parser.add_argument(
        "--in-clone",
        action="store_true",
        help="内部标志：当前进程已在桌面分身会话内运行 ok-script 核心",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启 ok-script 调试模式（记录详细识别日志与截图标注）",
    )
    args = parser.parse_args(argv)

    enable_per_monitor_dpi_awareness()
    check_ascii_path()

    # 实时读取最新的 yes_nk_config.json（避免桌面客户端修改配置后仍沿用旧值）
    dc_cfg = build_desktop_clone_config(load_user_overrides(USER_OVERRIDE_CONFIG))
    manager = WindowsDesktopCloneManager(dc_cfg)

    if args.switch_default:
        ok = manager.switch_to_default()
        if ok:
            print("已切回 Windows 主桌面 (Default)")
        else:
            print(f"切回主桌面失败：{manager.last_error_message or '仅支持 Windows'}")
        return 0 if ok else 1

    if args.clone_host:
        return run_clone_host(
            auto_start_ok=(not args.no_auto_start_ok),
            debug=args.debug,
        )

    if args.desktop_clone and not args.in_clone:
        host_argv = build_clone_host_argv(
            auto_start_ok=(not args.no_auto_start_ok),
            debug=args.debug,
        )
        append_clone_log(f"主桌面请求进入桌面分身 [{manager.desktop_name}]，启动命令: {host_argv}")
        result = manager.enter_clone_session(
            host_argv=host_argv,
            cwd=PROJECT_ROOT,
            ready_file=get_clone_ready_path(),
            log_file=get_clone_log_path(),
            wait_ready_sec=5.0,
        )
        if not result.ok:
            print(f"[YES-NK] 启动桌面分身失败：{result.error_message}")
            print(f"[YES-NK] 详细日志请查看：{result.log_path}")
            return 1

        if result.reused_existing:
            print(
                f"[YES-NK] 已切换至运行中的桌面分身 [{manager.desktop_name}] (PID={result.pid})，"
                f"按 {dc_cfg.switch_hotkey} 可随时切回主桌面。"
            )
        else:
            print(
                f"[YES-NK] 已创建并进入桌面分身 [{manager.desktop_name}] (控制台 PID={result.pid})，"
                f"按 {dc_cfg.switch_hotkey} 可随时切回主桌面。"
            )
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
