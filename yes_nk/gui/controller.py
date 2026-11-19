"""Windows 桌面客户端纯逻辑控制器（与 PySide6 解耦，便于跨平台单测）。

负责：
- 读写根目录 yes_nk_config.json（与 Web 工作台、DailyTask 和 yes_nk/config.py 100% 互通）；
- 同步全部 21 条 MaaNikke 转换流水线的开关与分组元数据；
- 组装桌面分身 / 常规 ok-script 启动命令；
- 校验 1080P 窗口客户区并触发 16:9 校准；
- 调度 MaaNikke 图像模板转换与 pipeline JSON 覆盖分析。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any

from tools.convert_maa_assets import (
    ConversionReport,
    PipelineMigrationReport,
    analyze_maa_pipeline_directory,
    convert_maa_directory_to_coco,
)
from yes_nk.config import PROJECT_ROOT, USER_OVERRIDE_CONFIG
from yes_nk.tasks.DailyTask import ALL_PIPELINE_SPECS
from yes_nk.utils.desktop_clone import (
    DesktopCloneConfig,
    RunMode,
    WindowsDesktopCloneManager,
    resolve_ok_interaction_class,
    validate_run_mode,
)
from yes_nk.utils.window_1080p import (
    WindowGeometryReport,
    evaluate_client_geometry,
    get_window_client_size,
    resize_client_to_16_9,
)


PIPELINE_CATEGORIES: tuple[str, ...] = (
    "启动与奖励",
    "商店相关",
    "日常养成",
    "副本挑战",
    "联盟与活动",
)

DEFAULT_DAILY_TOGGLES: dict[str, bool] = {
    key: default_enabled for key, _cat, default_enabled, _cls in ALL_PIPELINE_SPECS
}

BASIC_DAILY_KEYS: set[str] = {
    "邮箱一键领取",
    "好友友情点互赠",
    "前哨基地收菜与一举歼灭",
    "公告栏派遣收取与重派",
    "付费商店免费礼包领取",
    "道具商店每日采购",
    "每日任务与活跃奖励领取",
    "通行证 (PASS) 奖励领取",
}


def get_grouped_pipelines() -> dict[str, list[tuple[str, bool]]]:
    """按 5 大类别返回全部 21 条流水线供桌面客户端分组渲染。"""
    grouped: dict[str, list[tuple[str, bool]]] = {cat: [] for cat in PIPELINE_CATEGORIES}
    for key, cat, default_enabled, _cls in ALL_PIPELINE_SPECS:
        grouped.setdefault(cat, []).append((key, default_enabled))
    return grouped


@dataclass
class DesktopLauncherState:
    run_mode: RunMode = "desktop_clone"
    desktop_name: str = "YES_NK_Desktop"
    switch_hotkey: str = "Ctrl+Alt+F12"
    window_title: str = "NIKKE"
    resolution: str = "1920x1080"
    prefer_borderless_1080p: bool = True
    auto_close_desktop_on_exit: bool = True
    ocr_confidence: float = 0.78
    template_threshold: float = 0.82
    daily_toggles: dict[str, bool] | None = None

    def __post_init__(self) -> None:
        if self.daily_toggles is None:
            self.daily_toggles = dict(DEFAULT_DAILY_TOGGLES)


class DesktopClientController:
    """桌面客户端业务状态与文件持久化控制器。"""

    def __init__(self, config_path: Path = USER_OVERRIDE_CONFIG) -> None:
        self.config_path = config_path
        self.state = self.load_state()

    def load_state(self) -> DesktopLauncherState:
        state = DesktopLauncherState()
        if not self.config_path.exists():
            return state
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return state

        dc = data.get("desktop_clone", {})
        client = data.get("client", {})
        state.run_mode = validate_run_mode(str(dc.get("run_mode", state.run_mode)))
        state.desktop_name = str(dc.get("desktop_name", state.desktop_name))
        state.switch_hotkey = str(dc.get("switch_hotkey", state.switch_hotkey))
        state.prefer_borderless_1080p = bool(
            dc.get("prefer_borderless_1080p", state.prefer_borderless_1080p)
        )
        state.auto_close_desktop_on_exit = bool(
            dc.get("auto_close_desktop_on_exit", state.auto_close_desktop_on_exit)
        )
        state.window_title = str(client.get("windowTitle", state.window_title))
        state.resolution = str(client.get("resolution", state.resolution))
        state.ocr_confidence = float(client.get("ocrConfidence", state.ocr_confidence))
        state.template_threshold = float(
            client.get("templateThreshold", state.template_threshold)
        )

        saved_daily = data.get("daily_toggles", {})
        if isinstance(saved_daily, dict):
            for key in DEFAULT_DAILY_TOGGLES:
                if key in saved_daily:
                    state.daily_toggles[key] = bool(saved_daily[key])  # type: ignore[index]
        return state

    def save_state(self) -> Path:
        """将当前桌面客户端配置写回 yes_nk_config.json 供 ok-script 运行时读取。"""
        dc_cfg = DesktopCloneConfig(
            run_mode=self.state.run_mode,
            desktop_name=self.state.desktop_name,
            switch_hotkey=self.state.switch_hotkey,
            auto_close_desktop_on_exit=self.state.auto_close_desktop_on_exit,
            prefer_borderless_1080p=self.state.prefer_borderless_1080p,
        )
        payload: dict[str, Any] = {
            "project": "YES-NK",
            "framework": "ok-script",
            "target_game": "胜利女神：新的希望 (国服 PC / WeGame)",
            "desktop_clone": {
                "run_mode": dc_cfg.run_mode,
                "desktop_name": dc_cfg.sanitized_desktop_name(),
                "switch_hotkey": dc_cfg.switch_hotkey,
                "auto_close_desktop_on_exit": dc_cfg.auto_close_desktop_on_exit,
                "prefer_borderless_1080p": dc_cfg.prefer_borderless_1080p,
                "resolved_interaction": resolve_ok_interaction_class(dc_cfg.run_mode),
            },
            "client": {
                "exe": "nikke.exe",
                "windowTitle": self.state.window_title,
                "resolution": self.state.resolution,
                "captureMethod": "WGC + BitBlt_RenderFull",
                "ocrEngine": "RapidOCR (ok-script 内置)",
                "ocrConfidence": self.state.ocr_confidence,
                "templateThreshold": self.state.template_threshold,
                "autoReturnLobby": True,
            },
            "daily_toggles": dict(self.state.daily_toggles or DEFAULT_DAILY_TOGGLES),
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.config_path

    def build_ok_launch_argv(self, debug: bool = False) -> list[str]:
        """构造拉起 main.py (ok-script 核心) 的命令行参数。"""
        if getattr(sys, "frozen", False):
            base = [sys.executable, "--ok-core"]
        else:
            base = [sys.executable, str(PROJECT_ROOT / "main.py")]

        if self.state.run_mode == "desktop_clone":
            base.append("--desktop-clone")
        if debug:
            base.append("--debug")
        return base

    def find_nikke_window_hwnd(self) -> int:
        """在 Windows 下按标题查找国服 NIKKE 游戏窗口句柄。"""
        if sys.platform != "win32":
            return 0
        try:
            import ctypes

            user32 = ctypes.windll.user32
            for title in (self.state.window_title, "NIKKE", "胜利女神：新的希望"):
                if not title:
                    continue
                hwnd = int(user32.FindWindowW(None, title))
                if hwnd > 0:
                    return hwnd
        except Exception:
            return 0
        return 0

    def inspect_live_window(self, dpi_scale_percent: int = 100) -> WindowGeometryReport:
        """检测当前运行中的 nikke.exe 客户区尺寸并返回 1080P 诊断结果。"""
        hwnd = self.find_nikke_window_hwnd()
        if hwnd <= 0:
            return evaluate_client_geometry(0, 0, dpi_scale_percent)
        size = get_window_client_size(hwnd)
        if not size:
            return evaluate_client_geometry(0, 0, dpi_scale_percent)
        return evaluate_client_geometry(size[0], size[1], dpi_scale_percent)

    def calibrate_live_window_16_9(self, width: int = 1600, height: int = 900) -> bool:
        """一键将运行中的游戏窗口校准为严格 16:9 客户区（默认 1600x900 适配 1080P 主桌面）。"""
        hwnd = self.find_nikke_window_hwnd()
        if hwnd <= 0:
            return False
        return resize_client_to_16_9(hwnd, target_width=width, target_height=height)

    def create_desktop_clone_manager(self) -> WindowsDesktopCloneManager:
        return WindowsDesktopCloneManager(
            DesktopCloneConfig(
                run_mode=self.state.run_mode,
                desktop_name=self.state.desktop_name,
                switch_hotkey=self.state.switch_hotkey,
                auto_close_desktop_on_exit=self.state.auto_close_desktop_on_exit,
                prefer_borderless_1080p=self.state.prefer_borderless_1080p,
            )
        )

    def import_maa_assets(self, maa_dir: Path) -> ConversionReport:
        """图形界面调用：将用户选定的 MaaNikke 图像目录转换为 COCO 特征包。"""
        return convert_maa_directory_to_coco(maa_image_dir=maa_dir)

    def analyze_maa_pipelines(self, pipeline_dir: Path) -> PipelineMigrationReport:
        """图形界面调用：分析本地 MaaNikke pipeline JSON 目录并核对覆盖率。"""
        return analyze_maa_pipeline_directory(pipeline_dir)
