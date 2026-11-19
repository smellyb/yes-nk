"""YES-NK 应用组合根配置（完全对齐 YES-BD2 的 ok-script config 规范）。

支持自动加载从 Web 配套工作台导出的 `yes_nk_config.json` 覆盖项，
并针对 1080P 物理显示器与 Windows 桌面分身模式预设了最佳分辨率与截图后端。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yes_nk import __version__
from yes_nk.utils.desktop_clone import (
    DesktopCloneConfig,
    resolve_ok_interaction_class,
    validate_run_mode,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
USER_OVERRIDE_CONFIG = PROJECT_ROOT / "yes_nk_config.json"


def load_user_overrides(config_path: Path = USER_OVERRIDE_CONFIG) -> dict[str, Any]:
    """加载 Web 工作台导出的 yes_nk_config.json（若不存在则返回空字典）。"""
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_desktop_clone_config(overrides: dict[str, Any]) -> DesktopCloneConfig:
    dc = overrides.get("desktop_clone", {})
    return DesktopCloneConfig(
        run_mode=validate_run_mode(str(dc.get("run_mode", "desktop_clone"))),
        desktop_name=str(dc.get("desktop_name", "YES_NK_Desktop")),
        switch_hotkey=str(dc.get("switch_hotkey", "Ctrl+Alt+F12")),
        auto_close_desktop_on_exit=bool(dc.get("auto_close_desktop_on_exit", True)),
        prefer_borderless_1080p=bool(dc.get("prefer_borderless_1080p", True)),
    )


_overrides = load_user_overrides()
desktop_clone_config = build_desktop_clone_config(_overrides)
_client_overrides = _overrides.get("client", {})

config: dict[str, Any] = {
    "debug": False,
    "use_gui": True,
    "config_folder": "configs",
    "gui_icon": "assets/icon.png",
    "gui_title": "YES-NK — 胜利女神：新的希望 日常自动化",
    "version": __version__,
    "ocr": {
        "lib": "rapidocr",
        "params": {
            "use_openvino": False,
        },
    },
    # 针对 1080P 显示器双轨适配：
    # - 桌面分身内推荐使用 1920x1080 无边框全屏 (1:1 零缩放)
    # - 1080P 主桌面窗口化推荐使用 1600x900 或 1280x720 (严格 16:9 等比缩放)
    "supported_resolution": {
        "ratio": "16:9",
        "min_size": (1280, 720),
        "resize_to": [(1920, 1080), (1600, 900), (1280, 720)],
    },
    "coco_feature_json": str((PROJECT_ROOT / "assets" / "result.json").as_posix()),
    "windows": {
        "exe": ["nikke.exe", "NIKKE.exe"],
        "title": str(_client_overrides.get("windowTitle", "NIKKE")),
        "calculate_pc_exe_path": True,
        "hwnd_class": "UnityWndClass",
        "interaction": resolve_ok_interaction_class(desktop_clone_config.run_mode),
        "capture_method": ["WGC", "BitBlt_RenderFull"],
        "can_bit_blt_flip": False,
        "check_hdr": True,
        "force_no_dpi_scaling": True,
    },
    "start_timeout": 120,
    "window_size": {
        "width": 1200,
        "height": 760,
        "min_width": 960,
        "min_height": 640,
    },
    "analytics": {
        "report_url": "",
    },
    "onetime_tasks": [
        ["yes_nk.tasks.DailyTask", "DailyTask"],
        ["yes_nk.tasks.MailTask", "MailTask"],
        ["yes_nk.tasks.FriendPointTask", "FriendPointTask"],
        ["yes_nk.tasks.OutpostDefenseTask", "OutpostDefenseTask"],
        ["yes_nk.tasks.DispatchTask", "DispatchTask"],
        ["yes_nk.tasks.ShopTask", "ShopTask"],
        ["yes_nk.tasks.DailyMissionTask", "DailyMissionTask"],
    ],
    "trigger_tasks": [
        ["yes_nk.tasks.PopupGuardTrigger", "PopupGuardTrigger"],
    ],
}
