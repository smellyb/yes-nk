"""仿 YES-BD2 的 Windows 桌面分身 (CreateDesktopW) 隔离运行管理器。

支持三种可切换运行模式，兼顾不抢占主桌面键鼠与国服 WeGame/ACE 兼容性：
1. desktop_clone           — 独立 Windows 桌面会话（仿 YES-BD2 首选，推荐在分身内 1920x1080 无边框运行）
2. background_post_message — 主桌面后台消息交互（PostMessage + WGC/BitBlt，无需切桌面）
3. foreground_compat       — 主桌面标准前台兼容模式（极端反作弊拦截时的稳定兜底）
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import sys
from typing import Literal, Optional

RunMode = Literal["desktop_clone", "background_post_message", "foreground_compat"]

VALID_RUN_MODES: tuple[RunMode, ...] = (
    "desktop_clone",
    "background_post_message",
    "foreground_compat",
)

# Win32 Desktop access mask: GENERIC_ALL (0x10000000)
DESKTOP_ALL_ACCESS = 0x01FF


@dataclass(frozen=True)
class DesktopCloneConfig:
    run_mode: RunMode = "desktop_clone"
    desktop_name: str = "YES_NK_Desktop"
    switch_hotkey: str = "Ctrl+Alt+F12"
    auto_close_desktop_on_exit: bool = True
    launch_explorer_in_clone: bool = False
    prefer_borderless_1080p: bool = True

    def sanitized_desktop_name(self) -> str:
        """确保传给 CreateDesktopW 的桌面名称仅包含安全 ASCII 字符。"""
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", self.desktop_name).strip("_")
        return cleaned[:48] or "YES_NK_Desktop"


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


class WindowsDesktopCloneManager:
    """封装 Win32 CreateDesktopW / SwitchDesktop / CreateProcessW 的轻量桌面分身控制器。"""

    def __init__(self, config: Optional[DesktopCloneConfig] = None) -> None:
        self.config = config or DesktopCloneConfig()
        self._desktop_handle: Optional[int] = None
        self._original_desktop_handle: Optional[int] = None

    @property
    def desktop_name(self) -> str:
        return self.config.sanitized_desktop_name()

    @property
    def is_supported_os(self) -> bool:
        return sys.platform == "win32"

    def ensure_desktop(self) -> bool:
        """打开或创建隔离桌面会话。非 Windows 环境返回 False。"""
        if not self.is_supported_os:
            return False
        import ctypes

        user32 = ctypes.windll.user32
        current_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self._original_desktop_handle = user32.GetThreadDesktop(current_thread_id)

        handle = user32.OpenDesktopW(self.desktop_name, 0, False, DESKTOP_ALL_ACCESS)
        if not handle:
            handle = user32.CreateDesktopW(
                self.desktop_name, None, None, 0, DESKTOP_ALL_ACCESS, None
            )
        if not handle:
            return False
        self._desktop_handle = int(handle)
        return True

    def switch_to_clone(self) -> bool:
        """切换当前显示画面进入桌面分身。"""
        if not self.is_supported_os:
            return False
        if not self._desktop_handle and not self.ensure_desktop():
            return False
        import ctypes

        return bool(ctypes.windll.user32.SwitchDesktop(self._desktop_handle))

    def switch_to_default(self) -> bool:
        """切回 Windows 主桌面 (Default)。"""
        if not self.is_supported_os:
            return False
        import ctypes

        user32 = ctypes.windll.user32
        default_desk = user32.OpenDesktopW("Default", 0, False, DESKTOP_ALL_ACCESS)
        if not default_desk:
            return False
        try:
            return bool(user32.SwitchDesktop(default_desk))
        finally:
            user32.CloseDesktop(default_desk)

    def build_process_desktop_attr(self) -> str:
        """返回 Win32 STARTUPINFO.lpDesktop 所需的 WindowStation\\Desktop 标识。"""
        return f"WinSta0\\{self.desktop_name}"

    def launch_in_clone(self, command_line: str) -> Optional[int]:
        """在桌面分身会话内启动指定命令行进程，返回进程 PID。"""
        if not self.is_supported_os or not command_line.strip():
            return None
        if not self._desktop_handle and not self.ensure_desktop():
            return None

        import ctypes
        from ctypes import wintypes

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
        ok = ctypes.windll.kernel32.CreateProcessW(
            None,
            cmd_buf,
            None,
            None,
            False,
            0,
            None,
            None,
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if not ok:
            return None

        ctypes.windll.kernel32.CloseHandle(pi.hThread)
        ctypes.windll.kernel32.CloseHandle(pi.hProcess)
        return int(pi.dwProcessId)

    def close(self) -> None:
        """释放桌面句柄（可选退出时安全回收）。"""
        if self.is_supported_os and self._desktop_handle:
            import ctypes

            ctypes.windll.user32.CloseDesktop(self._desktop_handle)
            self._desktop_handle = None
