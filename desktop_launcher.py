"""YES-NK Windows 桌面客户端统一入口（也是打包 YES-NK.exe 的主入口）。

行为说明：
- 直接双击 YES-NK.exe 或运行 `python desktop_launcher.py` -> 打开原生 PySide6 Fluent 桌面客户端；
- 传入 `--clone-host` -> 在独立桌面分身 (WinSta0\\YES_NK_Desktop) 内运行常驻分身控制台与热键守护；
- 传入 `--ok-core` -> 直接运行 ok-script 自动化引擎（用于从桌面客户端或分身控制台拉起主引擎）。
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--clone-host" in args:
        from yes_nk.gui.clone_host import run_clone_host

        return run_clone_host(
            auto_start_ok=("--no-auto-start-ok" not in args),
            debug=("--debug" in args),
        )

    if "--ok-core" in args:
        forwarded = [a for a in args if a != "--ok-core"]
        from main import main as run_ok_main

        return run_ok_main(forwarded)

    from yes_nk.gui.desktop_client import launch_desktop_client

    return launch_desktop_client()


if __name__ == "__main__":
    raise SystemExit(main())
