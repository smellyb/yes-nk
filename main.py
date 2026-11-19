"""YES-NK Windows 桌面端主入口（完全对齐 YES-BD2 架构）。

用法：
- 常规启动：python main.py
- 在 YES-BD2 同款桌面分身窗口中运行：python main.py --desktop-clone
- 第一次设定桌面分身：python main.py --setup-clone
- 一键还原桌面分身：python main.py --undo-clone
- 结束正在运行的桌面分身：python main.py --end-clone
"""

from __future__ import annotations

import argparse
import sys

from yes_nk.config import (
    PROJECT_ROOT,
    USER_OVERRIDE_CONFIG,
    build_desktop_clone_config,
    config,
    load_user_overrides,
)
from yes_nk.utils import desktop_clone as clone
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YES-NK 胜利女神：新的希望 自动化入口")
    parser.add_argument(
        "--desktop-clone",
        action="store_true",
        help="打开与 YES-BD2 一致的 Windows Child Session 桌面分身窗口并在分身内启动 YES-NK",
    )
    parser.add_argument(
        "--setup-clone",
        action="store_true",
        help="运行 tools/clone_desktop/setup.ps1 完成第一次桌面分身设定",
    )
    parser.add_argument(
        "--undo-clone",
        action="store_true",
        help="运行 tools/clone_desktop/setup.ps1 -Undo 完整还原桌面分身设定",
    )
    parser.add_argument(
        "--end-clone",
        action="store_true",
        help="关闭桌面分身窗口并注销子会话",
    )
    parser.add_argument(
        "--in-clone",
        action="store_true",
        help="内部标志：由 CloneDesktop.exe 在分身子会话中自动拉起 ok-script 核心",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启 ok-script 调试模式（记录详细识别日志与截图标注）",
    )
    args = parser.parse_args(argv)

    enable_per_monitor_dpi_awareness()
    check_ascii_path()

    if args.setup_clone:
        ok = clone.run_setup(undo=False)
        print("已打开桌面分身设定窗口，请按提示完成。" if ok else "桌面分身设定仅支持 Windows 系统。")
        return 0 if ok else 1

    if args.undo_clone:
        ok = clone.run_setup(undo=True)
        print("已打开桌面分身还原窗口，请按提示完成。" if ok else "桌面分身还原仅支持 Windows 系统。")
        return 0 if ok else 1

    if args.end_clone:
        ok = clone.end_clone()
        print("已结束桌面分身并注销子会话。" if ok else "结束桌面分身失败或当前无运行中的分身。")
        return 0 if ok else 1

    if args.desktop_clone and not args.in_clone:
        if sys.platform != "win32":
            print("[YES-NK] 桌面分身仅支持 Windows 10/11 专业版/企业版/教育版。")
            return 1
        if not clone.supported():
            print("[YES-NK] 检测到当前为 Windows 家庭版，不支持子会话桌面分身，请改用主桌面后台模式。")
            return 1
        if not clone.ready():
            print("[YES-NK] 尚未完成「第一次设定」，正在打开 tools\\clone_desktop\\setup.ps1 ...")
            clone.run_setup(undo=False)
            print("[YES-NK] 设定完成后请重新运行本命令，或在桌面客户端点击「在桌面分身跑」。")
            return 0
        svc = clone.remote_desktop_service()
        if svc == "disabled":
            print("[YES-NK] 检测到「远程桌面服务」被禁用，请先在桌面客户端点击「帮我打开」或运行 sc config TermService start= demand。")
            return 1
        if svc == "missing":
            print("[YES-NK] 本机缺少「远程桌面服务 (TermService)」，精简版系统无法使用桌面分身。")
            return 1
        if clone.hello_only():
            print("[YES-NK] 检测到当前微软账户开启了「仅允许 Windows Hello 登录」，请先在桌面客户端点击「帮我关掉」。")
            return 1

        dc_cfg = build_desktop_clone_config(load_user_overrides(USER_OVERRIDE_CONFIG))
        opened = clone.open_viewer(
            launch_tool=True,
            debug=args.debug,
            move_uri=dc_cfg.game_exe_path or None,
        )
        if not opened:
            why = clone.open_failure.get("why", "")
            if why == "declined":
                print("[YES-NK] 已取消管理员权限确认，未打开桌面分身。")
            else:
                print(
                    f"[YES-NK] 无法启动 CloneDesktop.exe（可能被杀毒软件拦截），"
                    f"请将 {clone.DATA_DIR} 加入信任区后重新执行「第一次设定」。"
                )
            return 1

        print(
            "[YES-NK] 已打开 YES-NK 桌面分身窗口（1920x1080 独立子会话，最小化也会继续跑）。\n"
            "  - 首次登录请填写 Windows 账户密码（非 PIN），勾选「记住」后下次免输。\n"
            f"  - 日志路径：{clone.VIEWER_LOG}"
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
