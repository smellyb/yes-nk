"""YES-NK 桌面分身核心模块（与 nobell001/YES-BD2 完全一致的 Windows Child Session 架构）。

设计原理：
- 基于 Windows 10/11 专业版内置的终端服务子会话 (WTSEnableChildSessions) + 本地 RDP 窗口
  (tools/clone_desktop/CloneDesktop.exe)，在主桌面上打开一个独立的 1920x1080 虚拟桌面窗口。
- 最小化分身窗口后仍保持画面渲染（RemoteDesktop_SuppressWhenMinimized = 2），脚本在分身内
  操作游戏完全不抢占主桌面鼠标键盘。
- 登录分身后，CloneDesktop.exe 通过一次性 Windows 任务计划程序 (TASK_RUN_USE_SESSION_ID)
  在子会话中免密拉起 YES-NK，并自动清理子会话内弹出的第三方开机自启程序。
- 支持一键「第一次设定」(setup.ps1) 与一键「还原桌面分身」(setup.ps1 -Undo)。
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import functools
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


def _resolve_roots() -> tuple[Path, Path]:
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).resolve().parent
        res_root = Path(getattr(sys, "_MEIPASS", app_root)).resolve()
    else:
        app_root = Path(__file__).resolve().parents[2]
        res_root = app_root
    return app_root, res_root


APP_ROOT, RESOURCE_ROOT = _resolve_roots()
SETUP_SCRIPT = RESOURCE_ROOT / "tools" / "clone_desktop" / "setup.ps1"
VIEWER_SOURCE = RESOURCE_ROOT / "tools" / "clone_desktop" / "CloneDesktop.cs"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "yes-nk" / "clone-desktop"
VIEWER = DATA_DIR / "CloneDesktop.exe"
SETUP_STATE = DATA_DIR / "setup-state.json"
SETUP_LOG = DATA_DIR / "setup.log"
VIEWER_LOG = DATA_DIR / "viewer.log"
LAUNCH_RESULT = DATA_DIR / "launch-result.txt"
END_REQUEST = DATA_DIR / "end-request.txt"
END_JUST_CLOSE = "end"
END_MOVE_TO_DESKTOP = "move"
JOB_FILE = DATA_DIR / "pending-run.json"
STATUS_FILE = DATA_DIR / "clone-status.json"
CONTROL_FILE = DATA_DIR / "clone-control.txt"
STARTUP_LIST = DATA_DIR / "startup-programs.txt"
STARTUP_TASK_LIST = DATA_DIR / "startup-tasks.txt"

SAVED_SIGN_IN_TARGET = "yes-nk/clone-desktop"
REMOTE_DESKTOP_SERVICE_KEY = r"SYSTEM\CurrentControlSet\Services\TermService"
HELLO_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device"
CONNECT_FAILURES = frozenset({260, 264, 516, 520, 772, 1028, 1288, 2308})

GAME_NAMES = {"nikke.exe", "wegame.exe", "tgp_daemon.exe"}
KEEP_NAMES = {
    "python.exe",
    "pythonw.exe",
    "yes-nk.exe",
    "nikke.exe",
    "wegame.exe",
    "tgp_daemon.exe",
    "explorer.exe",
    "conhost.exe",
    "cmd.exe",
}
SIGN_IN_PARENTS = {"explorer.exe", "userinit.exe"}
TASK_PARENTS = {"svchost.exe", "taskhostw.exe"}
_RUN_KEYS = (
    r"Software\Microsoft\Windows\CurrentVersion\Run",
    r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
)

LOGOFF_WAIT_SECONDS = 60.0
END_REQUEST_WAIT_SECONDS = 10.0

# 最近一次 open_viewer() 失败原因："" | "declined" | "blocked" | "unsupported"
open_failure: dict[str, str] = {"why": ""}

OK, WARN, BAD = "ok", "warn", "bad"


@dataclass(frozen=True)
class DesktopCloneConfig:
    run_mode: RunMode = "desktop_clone"
    desktop_name: str = "YES_NK_Desktop"
    switch_hotkey: str = "Minimize / Tray"
    auto_close_desktop_on_exit: bool = False
    launch_explorer_in_clone: bool = True
    prefer_borderless_1080p: bool = True
    game_exe_path: str = ""

    def sanitized_desktop_name(self) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", self.desktop_name).strip("_")
        return cleaned[:48] or "YES_NK_Desktop"


@dataclass(frozen=True)
class CloneCheck:
    """与 YES-BD2 clone_guide_page.py 完全一致的本机桌面分身自检条目。"""

    label: str
    tone: str  # "ok" | "warn" | "bad"
    text: str
    action: str = ""  # "" | "第一次设定" | "帮我打开" | "帮我关掉"


CLONE_TROUBLESHOOT_QA: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    (
        "提示「登录失败」",
        (
            "密码请填写上方「要打的密码」对应那组，不要填 PIN 码。",
            "平时只用 PIN 或人脸开机时：先按 Win+L，点钥匙图标用密码登录电脑一次。",
            "再回到 YES-NK 点击「在桌面分身跑」。",
        ),
        False,
    ),
    (
        "提示「连不上桌面分身」（代码 516 等）",
        (
            "关闭分身窗口与 YES-NK，重新打开后再点一次「在桌面分身跑」。",
            "重启电脑后再试（首次开启子会话常需要重启才能生效）。",
            "如果装过 RDP Wrapper 或用过系统精简优化工具，远程桌面服务可能受损。",
        ),
        False,
    ),
    (
        "提示「分身程序不见了」",
        (
            "在杀毒软件（如 360、火绒、Windows Defender）中把分身文件夹加入信任区。",
            "点击上方「第一次设定」重新编译生成 CloneDesktop.exe。",
        ),
        True,
    ),
    (
        "为什么提示 Windows 家庭版不能用",
        (
            "Windows 子会话桌面分身需要 Windows 10/11 专业版、企业版或教育版。",
            "家庭版请直接选择「后台窗口消息模式 (PostMessage)」在主桌面挂机。",
        ),
        False,
    ),
    (
        "账户没有设置密码",
        (
            "Windows 规定无密码账户不能登录本地子会话桌面分身。",
            "请到系统「设置 > 账户 > 登录选项 > 密码」添加一个密码后再试。",
        ),
        False,
    ),
    (
        "还是进不去 / 查看日志",
        (
            "点击下方按钮打开分身文件夹，检查 viewer.log 与 setup.log 里的具体错误码。",
            "若确认是网络/远程桌面策略限制，可尝试命令行运行 setup.ps1 -AllowRdp。",
        ),
        True,
    ),
)


def resolve_ok_interaction_class(run_mode: RunMode) -> str:
    """根据运行模式返回 ok-script 推荐的 Interaction 交互后端名称。"""
    if run_mode == "desktop_clone":
        return "ForegroundPostMessage"
    if run_mode == "background_post_message":
        return "PostMessage"
    return "Pynput"


def validate_run_mode(mode: str) -> RunMode:
    if mode in VALID_RUN_MODES:
        return mode  # type: ignore[return-value]
    return "desktop_clone"


def _read_hklm(path: str, name: str) -> Any:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except (ImportError, OSError):
        return None


def supported() -> bool:
    """Windows 家庭版 (EditionID Core*) 不支持子会话桌面分身。"""
    if sys.platform != "win32":
        return False
    edition = _read_hklm(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "EditionID")
    return bool(edition) and not str(edition).startswith("Core")


def child_sessions_enabled() -> bool:
    """检查 Windows 子会话是否已通过 WTSEnableChildSessions 开启。"""
    if sys.platform != "win32":
        return False
    try:
        enabled = ctypes.c_int(0)
        ok = ctypes.windll.wtsapi32.WTSIsChildSessionsEnabled(ctypes.byref(enabled))
        return bool(ok) and bool(enabled.value)
    except (AttributeError, OSError):
        return False


def ready() -> bool:
    """一次性设定是否已完成：CloneDesktop.exe 存在且子会话已开启。"""
    return VIEWER.exists() and child_sessions_enabled()


def viewer_removed() -> bool:
    """曾完成设定但 CloneDesktop.exe 不见了（常见于 360 / 火绒误删）。"""
    return SETUP_STATE.exists() and not VIEWER.exists()


def remote_desktop_service() -> str:
    """检查远程桌面服务 (TermService) 状态：ok / disabled / missing / replaced / unknown。"""
    if sys.platform != "win32":
        return "unknown"
    try:
        import winreg  # noqa: F401
    except ImportError:
        return "unknown"
    start = _read_hklm(REMOTE_DESKTOP_SERVICE_KEY, "Start")
    if start is None and _read_hklm(REMOTE_DESKTOP_SERVICE_KEY, "ImagePath") is None:
        return "missing"
    if start == 4:
        return "disabled"
    dll = _read_hklm(REMOTE_DESKTOP_SERVICE_KEY + r"\Parameters", "ServiceDll")
    if isinstance(dll, str) and dll and not dll.lower().rstrip('"').endswith("termsrv.dll"):
        return "replaced"
    return "ok"


def _wait_until(predicate, timeout: float, poll: float = 0.5) -> bool:
    deadline = time.monotonic() + max(0.5, timeout)
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(poll)
    return bool(predicate())


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def enable_remote_desktop_service(wait: float = 20.0) -> bool:
    """将远程桌面服务 (TermService) 恢复为系统默认的手动启动（不开放外部 RDP）。"""
    if sys.platform != "win32":
        return False
    arguments = ["config", "TermService", "start=", "demand"]
    if is_admin():
        try:
            subprocess.run(
                ["sc.exe", *arguments],
                capture_output=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return remote_desktop_service() != "disabled"
    try:
        shell_execute = ctypes.windll.shell32.ShellExecuteW
        shell_execute.restype = ctypes.c_void_p
        result = shell_execute(
            None, "runas", "sc.exe", subprocess.list2cmdline(arguments), None, 0
        )
    except (AttributeError, OSError):
        return False
    if (result or 0) <= 32:
        return False
    return _wait_until(lambda: remote_desktop_service() != "disabled", wait)


def launch_failure(result: str) -> tuple[str, Optional[int]]:
    """解析 CloneDesktop.exe 写入的 launch-result.txt 失败行。"""
    words = (result or "").split()
    if len(words) >= 3 and words[1] == "noconnect" and words[2].isdigit():
        return "noconnect", int(words[2])
    return "other", None


class _UserInfo24(ctypes.Structure):
    _fields_ = [
        ("internet_identity", ctypes.c_int),
        ("flags", ctypes.c_ulong),
        ("provider", ctypes.c_wchar_p),
        ("principal", ctypes.c_wchar_p),
        ("sid", ctypes.c_void_p),
    ]


def _windows_identity() -> Optional[tuple[bool, str, str]]:
    """通过 NetUserGetInfo(level=24) 判断当前用户是微软账户还是本地账户。"""
    if sys.platform != "win32":
        return None
    try:
        netapi = ctypes.windll.netapi32
        size = ctypes.c_ulong(257)
        name = ctypes.create_unicode_buffer(size.value)
        if not ctypes.windll.advapi32.GetUserNameW(name, ctypes.byref(size)):
            return None
        buffer = ctypes.c_void_p()
        if netapi.NetUserGetInfo(None, name.value, 24, ctypes.byref(buffer)) != 0:
            return None
    except (AttributeError, OSError):
        return None
    try:
        info = ctypes.cast(buffer, ctypes.POINTER(_UserInfo24)).contents
        return bool(info.internet_identity), str(info.principal or ""), name.value
    finally:
        netapi.NetApiBufferFree(buffer)


@functools.lru_cache(maxsize=1)
def _current_user_sid() -> Optional[str]:
    if sys.platform != "win32":
        return None
    try:
        result = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    for part in result.stdout.replace('"', "").replace("\n", ",").split(","):
        if part.strip().startswith("S-1-"):
            return part.strip()
    return None


def microsoft_account() -> Optional[bool]:
    """当前 Windows 登录账号是否为 Microsoft 微软账户（None=无法判断）。"""
    if sys.platform != "win32":
        return None
    identity = _windows_identity()
    if identity is not None:
        return identity[0]
    try:
        import winreg
    except ImportError:
        return None
    sid = _current_user_sid()
    if sid:
        provider = _read_hklm(
            rf"SOFTWARE\Microsoft\IdentityStore\Cache\{sid}\IdentityCache\{sid}",
            "ProviderName",
        )
        if isinstance(provider, str) and provider:
            return "microsoftaccount" in provider.replace(" ", "").lower()
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\IdentityCRL\UserExtendedProperties",
        ) as key:
            return winreg.QueryInfoKey(key)[0] > 0
    except FileNotFoundError:
        return False
    except OSError:
        return None


def sign_in_account() -> Optional[str]:
    """返回分身登录框应预填的准确账号名（MicrosoftAccount\\邮箱 或 计算机名\\用户名）。"""
    identity = _windows_identity()
    if identity is None:
        return None
    linked, principal, user = identity
    if linked:
        return f"MicrosoftAccount\\{principal}" if "@" in principal else None
    machine = os.environ.get("COMPUTERNAME", "")
    return f"{machine}\\{user}" if machine and user else None


def hello_only() -> bool:
    """微软账户是否开启了「仅允许 Windows Hello 登录」（会阻挡分身密码登录）。"""
    if sys.platform != "win32":
        return False
    value = _read_hklm(HELLO_KEY, "DevicePasswordLessBuildVersion")
    return value == 2 and microsoft_account() is not False


def turn_off_hello_only(wait: float = 20.0) -> bool:
    """一键关闭「仅允许 Windows Hello 登录」（不关闭人脸与 PIN 本身）。"""
    if sys.platform != "win32":
        return False
    if is_admin():
        try:
            import winreg

            with winreg.CreateKeyEx(
                winreg.HKEY_LOCAL_MACHINE, HELLO_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(
                    key, "DevicePasswordLessBuildVersion", 0, winreg.REG_DWORD, 0
                )
        except (ImportError, OSError):
            return False
        return not hello_only()
    arguments = subprocess.list2cmdline(
        [
            "add",
            "HKLM\\" + HELLO_KEY,
            "/v",
            "DevicePasswordLessBuildVersion",
            "/t",
            "REG_DWORD",
            "/d",
            "0",
            "/f",
        ]
    )
    try:
        shell_execute = ctypes.windll.shell32.ShellExecuteW
        shell_execute.restype = ctypes.c_void_p
        result = shell_execute(None, "runas", "reg.exe", arguments, None, 0)
    except (AttributeError, OSError):
        return False
    if (result or 0) <= 32:
        return False
    return _wait_until(lambda: not hello_only(), wait)


def saved_sign_in() -> bool:
    """Windows 凭据管理器中是否已记住分身登录密码。"""
    if sys.platform != "win32":
        return False
    try:
        advapi = ctypes.windll.advapi32
        pointer = ctypes.c_void_p()
        if not advapi.CredReadW(SAVED_SIGN_IN_TARGET, 1, 0, ctypes.byref(pointer)):
            return False
        advapi.CredFree(pointer)
        return True
    except (AttributeError, OSError):
        return False


def password_text(microsoft: Optional[bool]) -> str:
    if microsoft:
        return "微软账号的密码（登录微软官网用的那组），不是 PIN"
    if microsoft is False:
        return "这台电脑的本地开机密码，不是 PIN"
    return "Windows 账户密码，不是 PIN"


def evaluate_pc_checks(
    *,
    is_supported: bool,
    is_removed: bool,
    is_ready: bool,
    service: str,
    microsoft: Optional[bool],
    account: Optional[str],
    is_hello_only: bool,
) -> list[CloneCheck]:
    """纯函数：根据检测值生成与 YES-BD2 完全一致的 6 行电脑状态诊断卡。"""
    if not is_supported:
        return [CloneCheck("Windows", BAD, "家庭版不支持子会话桌面分身，请改用主桌面后台模式")]

    rows = [CloneCheck("Windows", OK, "专业版/企业版，支持桌面分身")]
    if is_removed:
        rows.append(CloneCheck("分身程序", BAD, "CloneDesktop.exe 不见了（可能被杀毒软件误删）", "第一次设定"))
    elif not is_ready:
        rows.append(CloneCheck("第一次设定", WARN, "尚未完成设定", "第一次设定"))
    else:
        rows.append(CloneCheck("第一次设定", OK, "已设定"))

    if service == "missing":
        rows.append(CloneCheck("远程桌面服务", BAD, "本机缺少该服务（精简版 Windows），无法使用"))
    elif service == "disabled":
        rows.append(CloneCheck("远程桌面服务", WARN, "已被禁用", "帮我打开"))
    elif service == "replaced":
        rows.append(CloneCheck("远程桌面服务", WARN, "ServiceDll 被替换（如 RDP Wrapper），可能导致无法连接"))
    else:
        rows.append(CloneCheck("远程桌面服务", OK, "正常"))

    shown = (account or "").removeprefix("MicrosoftAccount\\")
    if microsoft:
        rows.append(CloneCheck("登录账户", OK, f"微软账户 {shown}".strip()))
    elif microsoft is False:
        rows.append(CloneCheck("登录账户", OK, f"本地账户 {shown}".strip()))
    else:
        rows.append(CloneCheck("登录账户", WARN, "未能识别账户类型"))

    rows.append(CloneCheck("要打的密码", OK, password_text(microsoft)))

    if is_hello_only:
        rows.append(CloneCheck("Windows Hello", WARN, "仅允许 Windows Hello 登录（会挡住分身）", "帮我关掉"))
    else:
        rows.append(CloneCheck("Windows Hello", OK, "允许使用密码登录"))

    return rows


def check_this_pc() -> list[CloneCheck]:
    """实时检查当前电脑的桌面分身就绪状态。"""
    is_sup = supported()
    if not is_sup:
        return evaluate_pc_checks(
            is_supported=False,
            is_removed=False,
            is_ready=False,
            service="ok",
            microsoft=None,
            account=None,
            is_hello_only=False,
        )
    return evaluate_pc_checks(
        is_supported=True,
        is_removed=viewer_removed(),
        is_ready=ready(),
        service=remote_desktop_service(),
        microsoft=microsoft_account(),
        account=sign_in_account(),
        is_hello_only=hello_only(),
    )


def _session_of(pid: int) -> Optional[int]:
    if sys.platform != "win32":
        return None
    try:
        session = ctypes.c_ulong(0)
        if not ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(session)):
            return None
        return int(session.value)
    except (AttributeError, OSError):
        return None


def _console_session() -> Optional[int]:
    if sys.platform != "win32":
        return None
    try:
        return int(ctypes.windll.kernel32.WTSGetActiveConsoleSessionId())
    except (AttributeError, OSError):
        return None


def _viewer_processes() -> list[Any]:
    try:
        import psutil

        return [
            p
            for p in psutil.process_iter(["pid", "name"])
            if (p.info.get("name") or "").lower() == "clonedesktop.exe"
        ]
    except Exception:
        return []


def viewer_running() -> bool:
    return bool(_viewer_processes())


def _viewer_in_other_session(own: int) -> bool:
    for proc in _viewer_processes():
        session = _session_of(proc.info["pid"])
        if session is None or session != own:
            return True
    return False


@functools.lru_cache(maxsize=1)
def in_clone() -> bool:
    """判断当前 YES-NK 进程是否正运行在桌面分身子会话内部。"""
    own = _session_of(os.getpid())
    console = _console_session()
    if own is None or console is None or own == console:
        return False
    return _viewer_in_other_session(own)


def child_session_id() -> Optional[int]:
    if sys.platform != "win32":
        return None
    try:
        session = ctypes.c_ulong(0)
        if not ctypes.windll.wtsapi32.WTSGetChildSessionId(ctypes.byref(session)):
            return None
        val = int(session.value)
        return val if val not in (0, 0xFFFFFFFF) else None
    except (AttributeError, OSError):
        return None


def _tool_names() -> set[str]:
    return {os.path.basename(sys.executable).lower(), "python.exe", "pythonw.exe", "yes-nk.exe"}


def _in_clone_session(names: set[str]) -> bool:
    child = child_session_id()
    if child is None or in_clone():
        return False
    try:
        import psutil
    except ImportError:
        return False
    for proc in psutil.process_iter(["pid", "name"]):
        if (proc.info.get("name") or "").lower() not in names:
            continue
        if _session_of(proc.info["pid"]) == child:
            return True
    return False


def tool_running_in_clone() -> bool:
    return _in_clone_session(_tool_names())


def clone_open() -> bool:
    return _in_clone_session(_tool_names() | GAME_NAMES)


def run_setup(undo: bool = False, allow_rdp: bool = False) -> bool:
    """在独立 PowerShell 窗口中运行 setup.ps1（第一次设定或一键还原桌面分身）。"""
    if sys.platform != "win32" or not SETUP_SCRIPT.exists():
        return False
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SETUP_SCRIPT),
    ]
    if undo:
        command.append("-Undo")
    if allow_rdp:
        command.append("-AllowRdp")
    subprocess.Popen(
        command,
        cwd=str(APP_ROOT),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )
    return True


def update_viewer() -> None:
    """当 CloneDesktop.cs 更新时自动用系统自带 csc.exe 重编 CloneDesktop.exe（无需管理员）。"""
    if sys.platform != "win32":
        return
    try:
        if (
            not VIEWER.exists()
            or not VIEWER_SOURCE.exists()
            or VIEWER.stat().st_mtime >= VIEWER_SOURCE.stat().st_mtime
        ):
            return
    except OSError:
        return
    if viewer_running():
        return

    windir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    csc = windir / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
    if not csc.exists():
        csc = windir / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe"
    if not csc.exists():
        return

    built = VIEWER.with_suffix(".new.exe")
    command = [
        str(csc),
        "/nologo",
        "/codepage:65001",
        "/target:winexe",
        f"/out:{built}",
        "/r:System.Windows.Forms.dll",
        "/r:System.Drawing.dll",
        "/r:Microsoft.CSharp.dll",
        "/r:System.Core.dll",
        "/r:System.Management.dll",
        str(VIEWER_SOURCE),
    ]
    try:
        subprocess.run(
            command,
            capture_output=True,
            timeout=120,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        os.replace(built, VIEWER)
    except (OSError, subprocess.SubprocessError):
        try:
            built.unlink()
        except OSError:
            pass


def _exe_of_command(command: str) -> Optional[str]:
    command = os.path.expandvars(command.strip())
    if command.startswith('"'):
        return command[1:].split('"', 1)[0]
    lowered = command.lower()
    end = lowered.find(".exe")
    return command[: end + 4] if end >= 0 else command.split(" ", 1)[0]


def startup_programs() -> set[str]:
    paths: set[str] = set()
    if sys.platform != "win32":
        return paths
    try:
        import winreg
    except ImportError:
        return paths
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for key_path in _RUN_KEYS:
            try:
                with winreg.OpenKey(root, key_path) as key:
                    index = 0
                    while True:
                        try:
                            _name, value, _kind = winreg.EnumValue(key, index)
                        except OSError:
                            break
                        index += 1
                        exe = _exe_of_command(str(value))
                        if exe:
                            paths.add(os.path.normcase(exe))
            except OSError:
                continue
    return paths


def sign_in_task_programs() -> set[str]:
    paths: set[str] = set()
    if sys.platform != "win32":
        return paths
    try:
        import win32com.client

        service = win32com.client.Dispatch("Schedule.Service")
        service.Connect()
    except Exception:
        return paths
    folders = [service.GetFolder("\\")]
    while folders:
        folder = folders.pop()
        try:
            folders.extend(folder.GetFolders(0))
            tasks = list(folder.GetTasks(0))
        except Exception:
            continue
        for task in tasks:
            try:
                if not task.Enabled:
                    continue
                definition = task.Definition
                if not any(trigger.Type in (9, 11) for trigger in definition.Triggers):
                    continue
                for action in definition.Actions:
                    if action.Type == 0 and action.Path:
                        path = os.path.expandvars(str(action.Path).strip('"'))
                        paths.add(os.path.normcase(path))
            except Exception:
                continue
    return paths


def _closable(path: str) -> bool:
    windows_dir = os.path.normcase(os.environ.get("SystemRoot", r"C:\Windows"))
    return not path.startswith(windows_dir) and os.path.basename(path).lower() not in KEEP_NAMES


def write_startup_list() -> None:
    """将用户开机自启清单写入分身数据目录，供 CloneDesktop.exe 在分身登录后自动清理杂项程序。"""
    try:
        paths = sorted(p for p in startup_programs() if _closable(p))
        tasks = sorted(p for p in sign_in_task_programs() if _closable(p))
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STARTUP_LIST.write_text("\n".join(paths), encoding="utf-8")
        STARTUP_TASK_LIST.write_text("\n".join(tasks), encoding="utf-8")
    except OSError:
        pass


def build_clone_tool_command(debug: bool = False) -> tuple[str, str]:
    """返回供 CloneDesktop.exe -launch/-args 在分身内启动 YES-NK ok-script 引擎的命令。"""
    if getattr(sys, "frozen", False):
        args = ["--ok-core", "--in-clone"]
        if debug:
            args.append("--debug")
        return sys.executable, subprocess.list2cmdline(args)
    args = [str(APP_ROOT / "main.py"), "--in-clone"]
    if debug:
        args.append("--debug")
    return sys.executable, subprocess.list2cmdline(args)


def open_viewer(
    launch_tool: bool = True,
    debug: bool = False,
    move_uri: Optional[str] = None,
) -> bool:
    """打开与 YES-BD2 一致的桌面分身窗口 (CloneDesktop.exe)，并在登录后自动在分身内拉起 YES-NK。"""
    open_failure["why"] = ""
    if sys.platform != "win32":
        open_failure["why"] = "unsupported"
        return False

    for stale in (LAUNCH_RESULT, END_REQUEST):
        try:
            stale.unlink()
        except OSError:
            pass

    update_viewer()
    write_startup_list()

    args: list[str] = []
    account = None if saved_sign_in() else sign_in_account()
    if account:
        args += ["-user", account]
    if launch_tool:
        exe, arguments = build_clone_tool_command(debug=debug)
        args += ["-launch", exe, "-args", arguments, "-cwd", str(APP_ROOT)]
    if move_uri:
        args += ["-move", move_uri]

    if is_admin():
        try:
            subprocess.Popen([str(VIEWER), *args], cwd=str(DATA_DIR))
            return True
        except OSError:
            open_failure["why"] = "blocked"
            return False

    try:
        shell_execute = ctypes.windll.shell32.ShellExecuteW
        shell_execute.restype = ctypes.c_void_p
        result = shell_execute(
            None, "runas", str(VIEWER), subprocess.list2cmdline(args), str(DATA_DIR), 1
        )
    except (AttributeError, OSError):
        open_failure["why"] = "blocked"
        return False
    if (result or 0) > 32:
        return True
    open_failure["why"] = "declined" if result == 5 else "blocked"
    return False


def launch_result() -> Optional[str]:
    try:
        return LAUNCH_RESULT.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def end_clone(timeout: float = LOGOFF_WAIT_SECONDS) -> bool:
    """从主桌面安全关闭分身窗口并注销子会话（与点分身窗口 X 一致）。"""
    child = child_session_id()
    if child is None or in_clone():
        for proc in _viewer_processes():
            try:
                proc.terminate()
                proc.wait(5)
            except Exception:
                pass
        return True

    for proc in _viewer_processes():
        try:
            proc.terminate()
            proc.wait(5)
        except Exception:
            pass

    try:
        subprocess.run(
            ["logoff", str(child)],
            capture_output=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return _wait_until(lambda: not clone_open(), timeout)


def end_from_inside(how: str = END_JUST_CLOSE, wait: float = END_REQUEST_WAIT_SECONDS) -> bool:
    """从分身内部请求主桌面的 CloneDesktop.exe 结束分身（支持 'end' 直接关掉 / 'move' 搬回桌面）。"""
    if not in_clone():
        return False
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        END_REQUEST.write_text(how, encoding="utf-8")
        asked = True
    except OSError:
        asked = False

    if asked and _wait_until(lambda: not END_REQUEST.exists(), wait):
        time.sleep(min(10.0, LOGOFF_WAIT_SECONDS))
        return True

    for proc in _viewer_processes():
        try:
            proc.terminate()
            proc.wait(5)
        except Exception:
            pass
    if _viewer_processes():
        try:
            END_REQUEST.unlink()
        except OSError:
            pass
        return False
    try:
        subprocess.run(
            ["logoff"],
            capture_output=True,
            timeout=LOGOFF_WAIT_SECONDS,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def write_atomic(path: Path, payload: bytes) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(payload)
    os.replace(temp, path)


def request_job(task: str, run_mode: Optional[str] = None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    job = {"task": task, "run_mode": run_mode, "at": time.time()}
    write_atomic(JOB_FILE, json.dumps(job, ensure_ascii=False).encode("utf-8"))


def take_job(max_age: float = 120.0) -> Optional[dict[str, Any]]:
    try:
        job = json.loads(JOB_FILE.read_text(encoding="utf-8"))
        JOB_FILE.unlink()
    except (OSError, ValueError):
        return None
    if not isinstance(job, dict) or time.time() - float(job.get("at", 0)) > max_age:
        return None
    return job


def send_control(command: str) -> None:
    write_atomic(CONTROL_FILE, command.encode("utf-8"))


def take_control() -> Optional[str]:
    try:
        cmd = CONTROL_FILE.read_text(encoding="utf-8").strip()
        CONTROL_FILE.unlink()
        return cmd or None
    except OSError:
        return None


def open_clone_folder() -> bool:
    """打开 %LOCALAPPDATA%\\yes-nk\\clone-desktop 文件夹（查看 viewer.log / 加杀毒白名单）。"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(DATA_DIR))  # type: ignore[attr-defined]
            return True
    except OSError:
        pass
    return False


def read_log_tail(log_path: Path = VIEWER_LOG, max_chars: int = 2000) -> str:
    if not log_path.exists():
        return ""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace").strip()
        return text if len(text) <= max_chars else "...\n" + text[-max_chars:]
    except OSError:
        return ""


class WindowsDesktopCloneManager:
    """面向旧调用方的轻量兼容包装，内部已全面切换为 YES-BD2 同款 Child Session 桌面分身。"""

    def __init__(self, config: Optional[DesktopCloneConfig] = None) -> None:
        self.config = config or DesktopCloneConfig()

    @property
    def desktop_name(self) -> str:
        return self.config.sanitized_desktop_name()

    @property
    def is_supported_os(self) -> bool:
        return sys.platform == "win32"

    def is_ready(self) -> bool:
        return ready()

    def open_clone(self, launch_tool: bool = True, debug: bool = False) -> bool:
        move_uri = self.config.game_exe_path or None
        return open_viewer(launch_tool=launch_tool, debug=debug, move_uri=move_uri)

    def end_clone(self) -> bool:
        return end_clone()
