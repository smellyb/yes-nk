"""仿 YES-BD2 的 Windows 桌面分身 (CreateDesktopW) 隔离运行管理器。

修复要点（解决“闪一下黑屏什么都没有”问题）：
1. 显式声明 64 位 Win32 ctypes 函数签名（argtypes / restype = HANDLE），避免 HDESK 句柄被截断为 32 位 c_int；
2. 创建桌面采用 GENERIC_ALL (0x10000000)，切回主桌面仅请求最小权限 DESKTOP_SWITCHDESKTOP (0x0100)，避免 Win10/11 UAC 拒绝；
3. CreateProcessW 显式传入工作目录 lpCurrentDirectory，并在 SwitchDesktop 前校验子进程存活与就绪状态，杜绝切入空黑屏；
4. 配合 yes_nk.gui.clone_host 在分身桌面内常驻可视化控制台 + 全局切回热键 (Ctrl+Alt+F12)，维持分身会话生命周期并提供完整错误日志。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Literal, Optional

RunMode = Literal["desktop_clone", "background_post_message", "foreground_compat"]

VALID_RUN_MODES: tuple[RunMode, ...] = (
    "desktop_clone",
    "background_post_message",
    "foreground_compat",
)

# Win32 Desktop access masks
DESKTOP_READOBJECTS = 0x0001
DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_CREATEMENU = 0x0004
DESKTOP_HOOKCONTROL = 0x0008
DESKTOP_JOURNALRECORD = 0x0010
DESKTOP_JOURNALPLAYBACK = 0x0020
DESKTOP_ENUMERATE = 0x0040
DESKTOP_WRITEOBJECTS = 0x0080
DESKTOP_SWITCHDESKTOP = 0x0100
STANDARD_RIGHTS_REQUIRED = 0x000F0000
DESKTOP_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | 0x01FF
GENERIC_ALL = 0x10000000

# Win32 Process creation / wait flags
CREATE_NEW_CONSOLE = 0x00000010
CREATE_NEW_PROCESS_GROUP = 0x00000200
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102

# Win32 RegisterHotKey modifiers
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


@dataclass(frozen=True)
class DesktopCloneConfig:
    run_mode: RunMode = "desktop_clone"
    desktop_name: str = "YES_NK_Desktop"
    switch_hotkey: str = "Ctrl+Alt+F12"
    auto_close_desktop_on_exit: bool = True
    launch_explorer_in_clone: bool = False
    prefer_borderless_1080p: bool = True
    game_exe_path: str = ""

    def sanitized_desktop_name(self) -> str:
        """确保传给 CreateDesktopW 的桌面名称仅包含安全 ASCII 字符。"""
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", self.desktop_name).strip("_")
        return cleaned[:48] or "YES_NK_Desktop"


@dataclass(frozen=True)
class DesktopCloneResult:
    ok: bool
    pid: Optional[int] = None
    switched: bool = False
    reused_existing: bool = False
    error_code: int = 0
    error_message: str = ""
    log_path: str = ""


def resolve_ok_interaction_class(run_mode: RunMode) -> str:
    """根据运行模式返回 ok-script 推荐的 Interaction 交互后端名称。"""
    if run_mode == "desktop_clone":
        # 分身桌面内游戏享有独立前台上下文，ForegroundPostMessage 兼容性与拖拽精度最高
        return "ForegroundPostMessage"
    if run_mode == "background_post_message":
        return "PostMessage"
    return "Pynput"


def validate_run_mode(mode: str) -> RunMode:
    if mode in VALID_RUN_MODES:
        return mode  # type: ignore[return-value]
    return "desktop_clone"


def build_command_line(argv: list[str]) -> str:
    """将参数列表安全转义为 Windows CreateProcessW 可解析的命令行字符串。"""
    return subprocess.list2cmdline(argv)


def parse_hotkey_spec(hotkey: str) -> tuple[int, int]:
    """将类似 'Ctrl+Alt+F12' 的热键配置解析为 Win32 (modifiers, vk_code)。"""
    raw = (hotkey or "Ctrl+Alt+F12").strip()
    tokens = [tok.strip().upper() for tok in raw.split("+") if tok.strip()]
    modifiers = MOD_NOREPEAT
    vk_code = 0x7B  # VK_F12 默认兜底

    special_vk = {
        "HOME": 0x24,
        "END": 0x23,
        "ESC": 0x1B,
        "ESCAPE": 0x1B,
        "TAB": 0x09,
        "SPACE": 0x20,
        "INSERT": 0x2D,
        "DELETE": 0x2E,
        "PGUP": 0x21,
        "PGDN": 0x22,
    }

    for tok in tokens:
        if tok in ("CTRL", "CONTROL"):
            modifiers |= MOD_CONTROL
        elif tok == "ALT":
            modifiers |= MOD_ALT
        elif tok == "SHIFT":
            modifiers |= MOD_SHIFT
        elif tok in ("WIN", "SUPER", "META"):
            modifiers |= MOD_WIN
        elif tok.startswith("F") and tok[1:].isdigit():
            fn_num = int(tok[1:])
            if 1 <= fn_num <= 24:
                vk_code = 0x6F + fn_num  # VK_F1 = 0x70
        elif tok in special_vk:
            vk_code = special_vk[tok]
        elif len(tok) == 1 and ("A" <= tok <= "Z" or "0" <= tok <= "9"):
            vk_code = ord(tok)

    # 避免无修饰键的裸键冲突
    if modifiers == MOD_NOREPEAT:
        modifiers |= MOD_CONTROL | MOD_ALT
    return modifiers, vk_code


def is_windows_admin() -> bool:
    """检测当前进程是否具备 Windows 管理员权限（WeGame / ACE 提权环境下建议开启）。"""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        shell32.IsUserAnAdmin.argtypes = []
        shell32.IsUserAnAdmin.restype = ctypes.c_int
        return bool(shell32.IsUserAnAdmin())
    except Exception:
        return False


def _format_win32_error(err_code: int) -> str:
    if not err_code:
        return ""
    if sys.platform == "win32":
        try:
            import ctypes

            return f"Win32 Error {err_code}: {ctypes.FormatError(err_code).strip()}"
        except Exception:
            pass
    return f"Win32 Error {err_code}"


def _load_win32_apis() -> tuple[Any, Any]:
    """加载显式声明 64 位安全签名的 user32 / kernel32 实例（禁止截断 HANDLE）。"""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # user32 desktop APIs
    user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user32.GetThreadDesktop.restype = wintypes.HANDLE

    user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
    user32.SetThreadDesktop.restype = wintypes.BOOL

    user32.OpenDesktopW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    user32.OpenDesktopW.restype = wintypes.HANDLE

    user32.CreateDesktopW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    user32.CreateDesktopW.restype = wintypes.HANDLE

    user32.SwitchDesktop.argtypes = [wintypes.HANDLE]
    user32.SwitchDesktop.restype = wintypes.BOOL

    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.CloseDesktop.restype = wintypes.BOOL

    # kernel32 process / thread APIs
    kernel32.GetCurrentThreadId.argtypes = []
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL

    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD

    kernel32.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE

    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    return user32, kernel32


def is_pid_alive(pid: int) -> bool:
    """跨平台判断指定 PID 当前是否存活。"""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            _user32, kernel32 = _load_win32_apis()
            h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h_proc:
                return False
            try:
                exit_code = wintypes.DWORD(0)
                if not kernel32.GetExitCodeProcess(h_proc, ctypes.byref(exit_code)):
                    return False
                return int(exit_code.value) == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(h_proc)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_log_tail(log_path: Path, max_chars: int = 1200) -> str:
    if not log_path.exists():
        return ""
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) <= max_chars:
            return content
        return "...\n" + content[-max_chars:]
    except Exception:
        return ""


class WindowsDesktopCloneManager:
    """封装 64 位安全的 Win32 CreateDesktopW / SwitchDesktop / CreateProcessW 桌面分身控制器。"""

    def __init__(self, config: Optional[DesktopCloneConfig] = None) -> None:
        self.config = config or DesktopCloneConfig()
        self._desktop_handle: Optional[int] = None
        self._original_desktop_handle: Optional[int] = None
        self.last_error_code: int = 0
        self.last_error_message: str = ""

    @property
    def desktop_name(self) -> str:
        return self.config.sanitized_desktop_name()

    @property
    def is_supported_os(self) -> bool:
        return sys.platform == "win32"

    def build_process_desktop_attr(self) -> str:
        """返回 Win32 STARTUPINFO.lpDesktop 所需的 WindowStation\\Desktop 标识。"""
        return f"WinSta0\\{self.desktop_name}"

    def _record_win32_error(self, context: str, err_code: Optional[int] = None) -> None:
        import ctypes

        code = ctypes.get_last_error() if err_code is None else int(err_code)
        self.last_error_code = code
        detail = _format_win32_error(code)
        self.last_error_message = f"{context} ({detail})" if detail else context

    def ensure_desktop(self) -> bool:
        """打开或创建隔离桌面会话。非 Windows 环境返回 False。"""
        if not self.is_supported_os:
            self.last_error_message = "桌面分身模式仅支持 Windows 系统"
            return False

        user32, kernel32 = _load_win32_apis()
        current_thread_id = kernel32.GetCurrentThreadId()
        orig = user32.GetThreadDesktop(current_thread_id)
        if orig:
            self._original_desktop_handle = int(orig)

        if self._desktop_handle:
            return True

        # 优先打开已存在的同名分身桌面
        handle = user32.OpenDesktopW(self.desktop_name, 0, False, DESKTOP_ALL_ACCESS)
        if not handle:
            handle = user32.OpenDesktopW(
                self.desktop_name,
                0,
                False,
                DESKTOP_SWITCHDESKTOP | DESKTOP_CREATEWINDOW | DESKTOP_WRITEOBJECTS | DESKTOP_READOBJECTS,
            )
        # 若不存在则使用 GENERIC_ALL 新建分身桌面
        if not handle:
            handle = user32.CreateDesktopW(
                self.desktop_name, None, None, 0, GENERIC_ALL, None
            )
        if not handle:
            handle = user32.CreateDesktopW(
                self.desktop_name, None, None, 0, DESKTOP_ALL_ACCESS, None
            )
        if not handle:
            self._record_win32_error(f"创建或打开分身桌面 [{self.desktop_name}] 失败")
            return False

        self._desktop_handle = int(handle)
        self.last_error_code = 0
        self.last_error_message = ""
        return True

    def switch_to_clone(self) -> bool:
        """切换当前显示画面进入桌面分身。"""
        if not self.is_supported_os:
            return False
        if not self._desktop_handle and not self.ensure_desktop():
            return False

        user32, _kernel32 = _load_win32_apis()
        ok = bool(user32.SwitchDesktop(self._desktop_handle))
        if not ok:
            self._record_win32_error(f"切换进入分身桌面 [{self.desktop_name}] 失败")
        return ok

    def switch_to_default(self) -> bool:
        """切回 Windows 主桌面 (Default)，仅申请 DESKTOP_SWITCHDESKTOP 最小权限以提高兼容性。"""
        if not self.is_supported_os:
            return False

        user32, _kernel32 = _load_win32_apis()
        default_desk = user32.OpenDesktopW("Default", 0, False, DESKTOP_SWITCHDESKTOP)
        if not default_desk:
            default_desk = user32.OpenDesktopW("Default", 0, False, DESKTOP_ALL_ACCESS)
        if default_desk:
            try:
                ok = bool(user32.SwitchDesktop(default_desk))
                if not ok:
                    self._record_win32_error("切回主桌面 Default 失败")
                return ok
            finally:
                user32.CloseDesktop(default_desk)

        if self._original_desktop_handle:
            ok = bool(user32.SwitchDesktop(self._original_desktop_handle))
            if not ok:
                self._record_win32_error("使用原桌面句柄切回主桌面失败")
            return ok

        self._record_win32_error("无法打开主桌面 Default")
        return False

    def launch_in_clone(
        self,
        command_line: str,
        cwd: Optional[Path] = None,
        creation_flags: int = CREATE_NEW_PROCESS_GROUP,
        verify_alive_ms: int = 0,
    ) -> Optional[int]:
        """在桌面分身会话内启动指定命令行进程，返回进程 PID（失败时记录精确 Win32 错误）。"""
        if not self.is_supported_os or not command_line.strip():
            self.last_error_message = "当前系统非 Windows 或启动命令为空"
            return None
        if not self._desktop_handle and not self.ensure_desktop():
            return None

        import ctypes
        from ctypes import wintypes

        _user32, kernel32 = _load_win32_apis()

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR),
                ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD),
                ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD),
                ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD),
                ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
                ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("hProcess", wintypes.HANDLE),
                ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD),
            ]

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        si.lpDesktop = self.build_process_desktop_attr()
        pi = PROCESS_INFORMATION()

        cmd_buf = ctypes.create_unicode_buffer(command_line)
        cwd_str = str(cwd.resolve()) if cwd is not None else None

        ok = kernel32.CreateProcessW(
            None,
            cmd_buf,
            None,
            None,
            False,
            creation_flags,
            None,
            cwd_str,
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if not ok:
            self._record_win32_error(f"CreateProcessW 启动分身进程失败: {command_line}")
            return None

        pid = int(pi.dwProcessId)
        try:
            if verify_alive_ms > 0:
                wait_rc = int(kernel32.WaitForSingleObject(pi.hProcess, verify_alive_ms))
                if wait_rc == WAIT_OBJECT_0:
                    exit_code = wintypes.DWORD(0)
                    kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
                    self.last_error_code = int(exit_code.value)
                    self.last_error_message = (
                        f"分身进程启动后立即退出（退出码 {exit_code.value}），已取消切屏以防黑屏闪退。"
                    )
                    return None
        finally:
            kernel32.CloseHandle(pi.hThread)
            kernel32.CloseHandle(pi.hProcess)

        self.last_error_code = 0
        self.last_error_message = ""
        return pid

    def check_existing_clone_host(self, ready_file: Path) -> Optional[int]:
        """检查目标分身桌面是否已有正在运行的 Clone Host 进程，避免重复拉起。"""
        if not ready_file.exists():
            return None
        try:
            data = json.loads(ready_file.read_text(encoding="utf-8"))
            if data.get("desktop") != self.desktop_name:
                return None
            pid = int(data.get("pid", 0))
            if pid > 0 and is_pid_alive(pid):
                return pid
        except Exception:
            return None
        return None

    def enter_clone_session(
        self,
        host_argv: list[str],
        cwd: Path,
        ready_file: Path,
        log_file: Path,
        wait_ready_sec: float = 4.0,
    ) -> DesktopCloneResult:
        """安全创建并进入桌面分身会话：
        1. 若已有存活的分身控制台进程，直接切入该桌面；
        2. 否则先启动分身控制台进程并等待其窗口就绪（或检测是否秒退）；
        3. 确认就绪后再 SwitchDesktop，彻底根治“黑屏闪一下什么都没有”。
        """
        if not self.is_supported_os:
            return DesktopCloneResult(
                ok=False,
                error_message="桌面分身模式仅支持 Windows 系统。",
                log_path=str(log_file),
            )

        if not self.ensure_desktop():
            return DesktopCloneResult(
                ok=False,
                error_code=self.last_error_code,
                error_message=self.last_error_message,
                log_path=str(log_file),
            )

        # 1. 若已有存活的 Clone Host，直接切换进入
        existing_pid = self.check_existing_clone_host(ready_file)
        if existing_pid:
            switched = self.switch_to_clone()
            return DesktopCloneResult(
                ok=switched,
                pid=existing_pid,
                switched=switched,
                reused_existing=True,
                error_code=0 if switched else self.last_error_code,
                error_message="" if switched else self.last_error_message,
                log_path=str(log_file),
            )

        # 2. 清理旧的就绪标记，准备拉起新的 Clone Host
        log_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            if ready_file.exists():
                ready_file.unlink()
        except Exception:
            pass

        launch_ts = time.time()
        cmd = build_command_line(host_argv)
        pid = self.launch_in_clone(cmd, cwd=cwd, verify_alive_ms=250)
        if not pid:
            tail = read_log_tail(log_file)
            msg = self.last_error_message
            if tail:
                msg = f"{msg}\n\n最近日志 ({log_file.name}):\n{tail}"
            return DesktopCloneResult(
                ok=False,
                error_code=self.last_error_code,
                error_message=msg,
                log_path=str(log_file),
            )

        # 3. 轮询等待 Clone Host 窗口就绪（最长 wait_ready_sec 秒）
        deadline = time.time() + max(0.8, wait_ready_sec)
        ready_confirmed = False
        while time.time() < deadline:
            if ready_file.exists():
                try:
                    info = json.loads(ready_file.read_text(encoding="utf-8"))
                    if int(info.get("pid", 0)) == pid and float(info.get("ts", 0)) >= launch_ts - 1.0:
                        ready_confirmed = True
                        break
                except Exception:
                    pass
            if not is_pid_alive(pid):
                tail = read_log_tail(log_file)
                msg = (
                    f"分身桌面控制台进程 (PID={pid}) 在初始化期间提前退出，已中止切屏以避免黑屏闪退。"
                )
                if tail:
                    msg += f"\n\n错误日志 ({log_file}):\n{tail}"
                return DesktopCloneResult(
                    ok=False,
                    pid=pid,
                    error_message=msg,
                    log_path=str(log_file),
                )
            time.sleep(0.1)

        # 即使未写入 ready_file（如极慢机器），只要进程仍然存活超过等待窗口也允许切入
        if not ready_confirmed and not is_pid_alive(pid):
            tail = read_log_tail(log_file)
            return DesktopCloneResult(
                ok=False,
                pid=pid,
                error_message=f"分身进程未能保持运行。\n{tail}",
                log_path=str(log_file),
            )

        switched = self.switch_to_clone()
        return DesktopCloneResult(
            ok=switched,
            pid=pid,
            switched=switched,
            reused_existing=False,
            error_code=0 if switched else self.last_error_code,
            error_message="" if switched else self.last_error_message,
            log_path=str(log_file),
        )

    def close(self) -> None:
        """释放桌面句柄（可选退出时安全回收）。"""
        if self.is_supported_os and self._desktop_handle:
            user32, _kernel32 = _load_win32_apis()
            user32.CloseDesktop(self._desktop_handle)
            self._desktop_handle = None
