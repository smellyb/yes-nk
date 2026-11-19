"""YES-NK 独立桌面分身内常驻控制台 (Clone Session Host)。

运行于 Windows 隔离桌面 (WinSta0\\YES_NK_Desktop) 内部，负责：
1. 维持分身桌面生命周期与可视化界面，彻底解决 CreateDesktopW 切入后“黑屏闪退/空桌面无法操作”的问题；
2. 注册全局切回热键（默认 Ctrl+Alt+F12 + 备用 Ctrl+Alt+Home），随时一键切回 Windows 主桌面且保持游戏与脚本在分身内运行；
3. 直接在分身桌面内拉起国服 WeGame / nikke.exe 与 ok-script 自动化引擎，并实时展示运行/报错日志；
4. 支持一键折叠为顶部精简悬浮条，不遮挡 1920x1080 无边框全屏游戏画面；
5. 自动兼容 PySide6（首选 Fluent UI）与纯标准库 tkinter（无 Qt 依赖兜底）。
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
from typing import Optional

from yes_nk import __version__
from yes_nk.config import (
    LOGS_DIR,
    PROJECT_ROOT,
    RESOURCE_ROOT,
    USER_OVERRIDE_CONFIG,
    build_desktop_clone_config,
    load_user_overrides,
)
from yes_nk.utils.desktop_clone import (
    WindowsDesktopCloneManager,
    is_windows_admin,
    parse_hotkey_spec,
)

WM_HOTKEY = 0x0312
HOTKEY_ID_MAIN = 0x594E  # 'YN'
HOTKEY_ID_FALLBACK = 0x594F


def get_clone_log_path() -> Path:
    return LOGS_DIR / "desktop_clone.log"


def get_clone_ready_path() -> Path:
    return LOGS_DIR / "clone_host_ready.json"


def append_clone_log(message: str) -> None:
    log_path = get_clone_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def write_ready_marker(desktop_name: str) -> None:
    ready_path = get_clone_ready_path()
    try:
        ready_path.parent.mkdir(parents=True, exist_ok=True)
        ready_path.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "desktop": desktop_name,
                    "ts": time.time(),
                    "version": __version__,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def clear_ready_marker() -> None:
    ready_path = get_clone_ready_path()
    try:
        if ready_path.exists():
            data = json.loads(ready_path.read_text(encoding="utf-8"))
            if int(data.get("pid", 0)) == os.getpid():
                ready_path.unlink()
    except Exception:
        pass


def build_in_clone_ok_argv(debug: bool = False) -> list[str]:
    """构造在分身桌面内启动 ok-script 引擎的子进程命令。"""
    if getattr(sys, "frozen", False):
        argv = [sys.executable, "--ok-core", "--in-clone"]
    else:
        argv = [sys.executable, str(PROJECT_ROOT / "main.py"), "--in-clone"]
    if debug:
        argv.append("--debug")
    return argv


def save_game_exe_path(exe_path: str) -> None:
    """将用户在分身中选择的 nikke.exe / wegame.exe 路径写回 yes_nk_config.json。"""
    data = load_user_overrides(USER_OVERRIDE_CONFIG)
    dc = data.setdefault("desktop_clone", {})
    if isinstance(dc, dict):
        dc["game_exe_path"] = exe_path
    try:
        USER_OVERRIDE_CONFIG.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _register_win32_hotkey(hwnd: int, hotkey_id: int, hotkey_str: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.RegisterHotKey.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.RegisterHotKey.restype = wintypes.BOOL
        mods, vk = parse_hotkey_spec(hotkey_str)
        return bool(user32.RegisterHotKey(hwnd or 0, hotkey_id, mods, vk))
    except Exception:
        return False


def _unregister_win32_hotkey(hwnd: int, hotkey_id: int) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.UnregisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey(hwnd or 0, hotkey_id)
    except Exception:
        pass


def _run_pyside6_clone_host(
    manager: WindowsDesktopCloneManager,
    auto_start_ok: bool,
    debug: bool,
) -> int:
    from PySide6.QtCore import QAbstractNativeEventFilter, Qt, QTimer, Signal
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    class HotkeyEventFilter(QAbstractNativeEventFilter):
        def __init__(self, on_trigger) -> None:
            super().__init__()
            self._on_trigger = on_trigger

        def nativeEventFilter(self, eventType, message):  # type: ignore[override]
            if sys.platform == "win32":
                try:
                    import ctypes
                    from ctypes import wintypes

                    msg = wintypes.MSG.from_address(int(message))
                    if msg.message == WM_HOTKEY and msg.wParam in (
                        HOTKEY_ID_MAIN,
                        HOTKEY_ID_FALLBACK,
                    ):
                        self._on_trigger()
                        return True, 0
                except Exception:
                    pass
            return False, 0

    class CloneHostWindow(QWidget):
        log_signal = Signal(str)

        def __init__(self) -> None:
            super().__init__()
            self.manager = manager
            self.debug = debug
            self.ok_process: Optional[subprocess.Popen[str]] = None
            self.is_compact = False
            self._hotkey_registered = False

            self.setWindowTitle(f"YES-NK 桌面分身控制台 [{manager.desktop_name}]")
            self.setWindowFlags(
                Qt.WindowType.Window
                | Qt.WindowType.WindowStaysOnTopHint
            )
            icon_path = RESOURCE_ROOT / "assets" / "icon.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))

            self.setStyleSheet(
                """
                QWidget {
                    background-color: #0F172A;
                    color: #F8FAFC;
                    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
                    font-size: 13px;
                }
                QFrame#Card {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 10px;
                }
                QPushButton {
                    background-color: #334155;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    padding: 7px 14px;
                    color: #F8FAFC;
                }
                QPushButton:hover {
                    background-color: #475569;
                    border-color: #38BDF8;
                }
                QPushButton#Primary {
                    background-color: #0284C7;
                    border-color: #0284C7;
                    font-weight: 600;
                }
                QPushButton#Primary:hover {
                    background-color: #0369A1;
                }
                QPushButton#Danger {
                    background-color: #991B1B;
                    border-color: #DC2626;
                }
                QPushButton#Danger:hover {
                    background-color: #B91C1C;
                }
                QLineEdit, QTextEdit {
                    background-color: #0B1220;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 6px 8px;
                    color: #E2E8F0;
                }
                """
            )

            self.log_signal.connect(self._append_log_ui)
            self._build_ui()
            self.resize(760, 520)

        def _build_ui(self) -> None:
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(16, 14, 16, 14)
            self.main_layout.setSpacing(12)

            # 顶部常驻快捷栏（即使折叠也保留）
            top_bar = QHBoxLayout()
            self.title_label = QLabel(
                f"YES-NK 桌面分身已就绪  ·  会话: {self.manager.desktop_name}  ·  热键: {self.manager.config.switch_hotkey}"
            )
            self.title_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #38BDF8;")
            top_bar.addWidget(self.title_label)
            top_bar.addStretch(1)

            self.btn_compact = QPushButton("精简悬浮条")
            self.btn_compact.clicked.connect(self._toggle_compact)
            top_bar.addWidget(self.btn_compact)

            btn_back = QPushButton(f"切回主桌面 ({self.manager.config.switch_hotkey})")
            btn_back.setObjectName("Primary")
            btn_back.clicked.connect(self._switch_to_default)
            top_bar.addWidget(btn_back)
            self.main_layout.addLayout(top_bar)

            # 主控制面板（精简模式下可隐藏）
            self.body_widget = QWidget()
            body_layout = QVBoxLayout(self.body_widget)
            body_layout.setContentsMargins(0, 0, 0, 0)
            body_layout.setSpacing(10)

            admin_note = (
                "当前已具备管理员权限，可直接拉起国服 WeGame / NIKKE。"
                if is_windows_admin()
                else "提示：当前非管理员权限。若国服 WeGame/NIKKE 触发 UAC 提权，建议以管理员身份启动 YES-NK。"
            )
            hint = QLabel(
                f"本桌面为 Windows 独立隔离会话（无任务栏属正常现象，非黑屏故障）。"
                f"请直接在此启动游戏与脚本；切回主桌面后游戏会继续在分身后台运行。\n{admin_note}"
            )
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #CBD5E1; font-size: 12px;")
            body_layout.addWidget(hint)

            # 卡片 1：游戏 / WeGame 启动区
            game_card = QFrame()
            game_card.setObjectName("Card")
            game_layout = QVBoxLayout(game_card)
            game_layout.setContentsMargins(12, 10, 12, 10)
            game_layout.setSpacing(8)
            game_layout.addWidget(QLabel("1. 在分身桌面内启动国服游戏 / WeGame（分身内需单独拉起游戏进程）"))

            game_row = QHBoxLayout()
            self.game_path_input = QLineEdit(self.manager.config.game_exe_path)
            self.game_path_input.setPlaceholderText("选择 nikke.exe 或 wegame.exe 路径...")
            game_row.addWidget(self.game_path_input, stretch=1)

            btn_browse_game = QPushButton("选择程序...")
            btn_browse_game.clicked.connect(self._browse_game)
            game_row.addWidget(btn_browse_game)

            btn_launch_game = QPushButton("在分身内启动游戏")
            btn_launch_game.setObjectName("Primary")
            btn_launch_game.clicked.connect(self._launch_game)
            game_row.addWidget(btn_launch_game)
            game_layout.addLayout(game_row)
            body_layout.addWidget(game_card)

            # 卡片 2：ok-script 与系统工具控制区
            ctrl_card = QFrame()
            ctrl_card.setObjectName("Card")
            ctrl_layout = QHBoxLayout(ctrl_card)
            ctrl_layout.setContentsMargins(12, 10, 12, 10)
            ctrl_layout.setSpacing(8)

            btn_start_ok = QPushButton("启动 / 重启 ok-script 自动化")
            btn_start_ok.setObjectName("Primary")
            btn_start_ok.clicked.connect(self.start_ok_engine)
            ctrl_layout.addWidget(btn_start_ok)

            btn_cmd = QPushButton("打开 CMD")
            btn_cmd.clicked.connect(lambda: self._launch_tool(["cmd.exe"]))
            ctrl_layout.addWidget(btn_cmd)

            btn_taskmgr = QPushButton("任务管理器")
            btn_taskmgr.clicked.connect(lambda: self._launch_tool(["taskmgr.exe"]))
            ctrl_layout.addWidget(btn_taskmgr)

            ctrl_layout.addStretch(1)

            btn_exit_clone = QPushButton("关闭分身并返回主桌面")
            btn_exit_clone.setObjectName("Danger")
            btn_exit_clone.clicked.connect(self._exit_clone)
            ctrl_layout.addWidget(btn_exit_clone)
            body_layout.addWidget(ctrl_card)

            # 实时日志区
            self.log_view = QTextEdit()
            self.log_view.setReadOnly(True)
            self.log_view.setPlaceholderText("分身控制台与 ok-script 输出日志将显示在此...")
            body_layout.addWidget(self.log_view, stretch=1)

            self.main_layout.addWidget(self.body_widget, stretch=1)

        def _append_log_ui(self, text: str) -> None:
            self.log_view.append(text)
            append_clone_log(text)

        def register_hotkeys(self) -> None:
            hwnd = int(self.winId())
            ok_main = _register_win32_hotkey(hwnd, HOTKEY_ID_MAIN, self.manager.config.switch_hotkey)
            ok_backup = _register_win32_hotkey(hwnd, HOTKEY_ID_FALLBACK, "Ctrl+Alt+Home")
            self._hotkey_registered = ok_main or ok_backup
            self._append_log_ui(
                f"分身桌面控制台已启动 (PID={os.getpid()})；切回热键 {self.manager.config.switch_hotkey} "
                + ("注册成功。" if ok_main else "注册失败，可使用按钮或备用热键 Ctrl+Alt+Home 切回。")
            )

        def _toggle_compact(self) -> None:
            self.is_compact = not self.is_compact
            self.body_widget.setVisible(not self.is_compact)
            self.btn_compact.setText("展开控制台" if self.is_compact else "精简悬浮条")
            if self.is_compact:
                self.resize(560, 56)
                screen = QApplication.primaryScreen()
                if screen is not None:
                    geo = screen.geometry()
                    self.move((geo.width() - self.width()) // 2, 8)
            else:
                self.resize(760, 520)

        def _switch_to_default(self) -> None:
            self._append_log_ui("正在切回 Windows 主桌面 (Default)，分身桌面程序继续在后台运行。")
            if not self.manager.switch_to_default():
                self._append_log_ui(f"切回主桌面失败：{self.manager.last_error_message}")

        def _browse_game(self) -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择 nikke.exe 或 wegame.exe",
                "",
                "可执行文件 (*.exe);;所有文件 (*.*)",
            )
            if file_path:
                self.game_path_input.setText(file_path)
                save_game_exe_path(file_path)

        def _launch_game(self) -> None:
            exe = self.game_path_input.text().strip().strip('"')
            if not exe:
                self._browse_game()
                exe = self.game_path_input.text().strip().strip('"')
            if not exe:
                return
            exe_path = Path(exe)
            if not exe_path.exists():
                QMessageBox.warning(self, "路径不存在", f"未找到可执行文件：\n{exe}")
                return
            save_game_exe_path(str(exe_path))
            try:
                subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
                self._append_log_ui(f"已在分身桌面内启动程序：{exe_path}")
            except Exception as exc:
                self._append_log_ui(f"启动程序失败：{exc}")
                QMessageBox.warning(self, "启动失败", str(exc))

        def _launch_tool(self, argv: list[str]) -> None:
            try:
                subprocess.Popen(argv, cwd=str(PROJECT_ROOT))
                self._append_log_ui(f"已在分身桌面内打开：{' '.join(argv)}")
            except Exception as exc:
                self._append_log_ui(f"打开工具失败：{exc}")

        def start_ok_engine(self) -> None:
            if self.ok_process is not None and self.ok_process.poll() is None:
                self._append_log_ui("正在停止旧的 ok-script 实例...")
                try:
                    self.ok_process.terminate()
                except Exception:
                    pass

            argv = build_in_clone_ok_argv(debug=self.debug)
            self._append_log_ui(f"正在分身桌面内启动 ok-script：{' '.join(argv)}")
            try:
                proc = subprocess.Popen(
                    argv,
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.ok_process = proc
            except Exception as exc:
                self._append_log_ui(f"启动 ok-script 进程失败：{exc}")
                return

            def _pump_output(p: subprocess.Popen[str]) -> None:
                if p.stdout is not None:
                    for raw_line in p.stdout:
                        line = raw_line.rstrip()
                        if line:
                            self.log_signal.emit(f"[ok-script] {line}")
                rc = p.wait()
                self.log_signal.emit(
                    f"[ok-script] 进程已退出（退出码 {rc}）。"
                    + ("若提示缺少 ok-script 依赖，请先运行 pip install -r requirements.txt。" if rc != 0 else "")
                )

            threading.Thread(target=_pump_output, args=(proc,), daemon=True).start()

        def _exit_clone(self) -> None:
            self._append_log_ui("正在关闭分身控制台并切回主桌面...")
            if self.ok_process is not None and self.ok_process.poll() is None:
                try:
                    self.ok_process.terminate()
                except Exception:
                    pass
            clear_ready_marker()
            self.manager.switch_to_default()
            QApplication.quit()

        def closeEvent(self, event) -> None:  # type: ignore[override]
            hwnd = int(self.winId())
            _unregister_win32_hotkey(hwnd, HOTKEY_ID_MAIN)
            _unregister_win32_hotkey(hwnd, HOTKEY_ID_FALLBACK)
            clear_ready_marker()
            self.manager.switch_to_default()
            super().closeEvent(event)

    app = QApplication(sys.argv)
    win = CloneHostWindow()
    hotkey_filter = HotkeyEventFilter(win._switch_to_default)
    app.installNativeEventFilter(hotkey_filter)
    win.show()
    win.register_hotkeys()
    write_ready_marker(manager.desktop_name)

    if auto_start_ok:
        QTimer.singleShot(800, win.start_ok_engine)

    return int(app.exec())


def _run_tkinter_clone_host(
    manager: WindowsDesktopCloneManager,
    auto_start_ok: bool,
    debug: bool,
) -> int:
    """无 PySide6 环境下的纯标准库 tkinter 兜底分身控制台，确保永不黑屏闪退。"""
    import tkinter as tk
    from tkinter import filedialog, scrolledtext

    root = tk.Tk()
    root.title(f"YES-NK 桌面分身控制台 [{manager.desktop_name}]")
    root.geometry("740x480")
    root.configure(bg="#0F172A")
    root.attributes("-topmost", True)

    ok_proc_holder: list[Optional[subprocess.Popen[str]]] = [None]

    def log(msg: str) -> None:
        append_clone_log(msg)
        try:
            log_box.configure(state="normal")
            log_box.insert("end", msg + "\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        except Exception:
            pass

    def switch_back() -> None:
        log("切回 Windows 主桌面 (Default)...")
        manager.switch_to_default()

    def start_ok() -> None:
        argv = build_in_clone_ok_argv(debug=debug)
        log(f"启动 ok-script: {' '.join(argv)}")
        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            ok_proc_holder[0] = proc
        except Exception as exc:
            log(f"启动 ok-script 失败: {exc}")
            return

        def _pump() -> None:
            if proc.stdout is not None:
                for line in proc.stdout:
                    text = line.rstrip()
                    if text:
                        root.after(0, log, f"[ok-script] {text}")
            rc = proc.wait()
            root.after(0, log, f"[ok-script] 已退出（退出码 {rc}）")

        threading.Thread(target=_pump, daemon=True).start()

    def launch_game() -> None:
        path = filedialog.askopenfilename(
            title="选择 nikke.exe 或 wegame.exe",
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")],
        )
        if path:
            save_game_exe_path(path)
            subprocess.Popen([path], cwd=str(Path(path).parent))
            log(f"已在分身内启动：{path}")

    def exit_clone() -> None:
        proc = ok_proc_holder[0]
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        clear_ready_marker()
        manager.switch_to_default()
        root.destroy()

    header = tk.Frame(root, bg="#1E293B", padx=12, pady=10)
    header.pack(fill="x")
    tk.Label(
        header,
        text=f"YES-NK 桌面分身 [{manager.desktop_name}] · 按 {manager.config.switch_hotkey} 切回主桌面",
        bg="#1E293B",
        fg="#38BDF8",
        font=("Microsoft YaHei UI", 11, "bold"),
    ).pack(side="left")
    tk.Button(header, text="切回主桌面", command=switch_back, bg="#0284C7", fg="white").pack(side="right", padx=4)

    bar = tk.Frame(root, bg="#0F172A", padx=12, pady=8)
    bar.pack(fill="x")
    tk.Button(bar, text="启动游戏 / WeGame", command=launch_game, bg="#334155", fg="white").pack(side="left", padx=4)
    tk.Button(bar, text="启动 ok-script", command=start_ok, bg="#0284C7", fg="white").pack(side="left", padx=4)
    tk.Button(bar, text="打开 CMD", command=lambda: subprocess.Popen(["cmd.exe"]), bg="#334155", fg="white").pack(side="left", padx=4)
    tk.Button(bar, text="关闭分身", command=exit_clone, bg="#991B1B", fg="white").pack(side="right", padx=4)

    log_box = scrolledtext.ScrolledText(root, bg="#0B1220", fg="#E2E8F0", state="disabled")
    log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # 独立热键监听线程
    if sys.platform == "win32":
        def _hotkey_loop() -> None:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            _register_win32_hotkey(0, HOTKEY_ID_MAIN, manager.config.switch_hotkey)
            _register_win32_hotkey(0, HOTKEY_ID_FALLBACK, "Ctrl+Alt+Home")
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    manager.switch_to_default()

        threading.Thread(target=_hotkey_loop, daemon=True).start()

    root.protocol("WM_DELETE_WINDOW", exit_clone)
    log(f"分身控制台 (tkinter 兼容模式) 已就绪 PID={os.getpid()}")
    write_ready_marker(manager.desktop_name)
    if auto_start_ok:
        root.after(800, start_ok)
    root.mainloop()
    return 0


def run_clone_host(auto_start_ok: bool = True, debug: bool = False) -> int:
    """在 WinSta0\\YES_NK_Desktop 内部运行常驻控制台主入口。"""
    overrides = load_user_overrides(USER_OVERRIDE_CONFIG)
    dc_cfg = build_desktop_clone_config(overrides)
    manager = WindowsDesktopCloneManager(dc_cfg)
    append_clone_log(
        f"正在初始化分身桌面控制台 desktop={manager.desktop_name} pid={os.getpid()} "
        f"auto_start_ok={auto_start_ok} debug={debug}"
    )

    try:
        try:
            import PySide6  # noqa: F401

            return _run_pyside6_clone_host(manager, auto_start_ok=auto_start_ok, debug=debug)
        except ImportError:
            append_clone_log("未检测到 PySide6，自动切换至 tkinter 兼容模式分身控制台。")
            return _run_tkinter_clone_host(manager, auto_start_ok=auto_start_ok, debug=debug)
    except Exception:
        append_clone_log("分身控制台发生未捕获异常：\n" + traceback.format_exc())
        clear_ready_marker()
        manager.switch_to_default()
        return 1
