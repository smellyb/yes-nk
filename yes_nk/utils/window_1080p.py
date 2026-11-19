"""1080P 物理显示器与 16:9 客户区几何校验工具。

专门解决 1920x1080 显示器下运行 PC 自动化常见的两大问题：
1. 窗口化运行时标题栏与 Windows 任务栏挤压客户区高度（如 1920x1009），破坏 16:9 比例；
2. 125% / 150% 系统 DPI 缩放导致逻辑坐标与物理截图坐标错位。
"""

from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Optional

BASE_WIDTH = 1920
BASE_HEIGHT = 1080
TARGET_RATIO = 16.0 / 9.0
MIN_CLIENT_WIDTH = 1280
MIN_CLIENT_HEIGHT = 720
RATIO_TOLERANCE = 0.015  # 允许 ±1.5% 的极小边框误差


@dataclass(frozen=True)
class WindowGeometryReport:
    client_width: int
    client_height: int
    dpi_scale_percent: int
    aspect_ratio: float
    ratio_error: float
    scale_x: float
    scale_y: float
    status: str  # "optimal_1080p" | "valid_scaled_16_9" | "non_16_9" | "too_small"
    is_valid: bool
    recommendation: str


def evaluate_client_geometry(
    client_width: int,
    client_height: int,
    dpi_scale_percent: int = 100,
) -> WindowGeometryReport:
    """评估游戏窗口客户区（Client Area）是否满足 YES-NK 16:9 识别标准。"""
    if client_width <= 0 or client_height <= 0:
        return WindowGeometryReport(
            client_width=client_width,
            client_height=client_height,
            dpi_scale_percent=dpi_scale_percent,
            aspect_ratio=0.0,
            ratio_error=1.0,
            scale_x=0.0,
            scale_y=0.0,
            status="too_small",
            is_valid=False,
            recommendation="未检测到有效客户区尺寸，请确认游戏窗口未最小化。",
        )

    aspect_ratio = client_width / client_height
    ratio_error = abs(aspect_ratio - TARGET_RATIO) / TARGET_RATIO
    scale_x = client_width / BASE_WIDTH
    scale_y = client_height / BASE_HEIGHT

    dpi_hint = (
        f" 当前系统 DPI 为 {dpi_scale_percent}%，已启用 Per-Monitor DPI v2 感知，建议同时在 nikke.exe 属性中勾选“替代高 DPI 缩放行为（应用程序）”。"
        if dpi_scale_percent > 100
        else ""
    )

    if client_width < MIN_CLIENT_WIDTH or client_height < MIN_CLIENT_HEIGHT:
        return WindowGeometryReport(
            client_width=client_width,
            client_height=client_height,
            dpi_scale_percent=dpi_scale_percent,
            aspect_ratio=round(aspect_ratio, 4),
            ratio_error=round(ratio_error, 4),
            scale_x=round(scale_x, 4),
            scale_y=round(scale_y, 4),
            status="too_small",
            is_valid=False,
            recommendation=(
                f"当前客户区 {client_width}x{client_height} 小于最低 1280x720 要求，"
                "请将游戏调整为 1600x900 窗口化或在桌面分身内设为 1920x1080 无边框全屏。"
                + dpi_hint
            ),
        )

    if ratio_error > RATIO_TOLERANCE:
        return WindowGeometryReport(
            client_width=client_width,
            client_height=client_height,
            dpi_scale_percent=dpi_scale_percent,
            aspect_ratio=round(aspect_ratio, 4),
            ratio_error=round(ratio_error, 4),
            scale_x=round(scale_x, 4),
            scale_y=round(scale_y, 4),
            status="non_16_9",
            is_valid=False,
            recommendation=(
                f"当前客户区 {client_width}x{client_height} 非标准 16:9（偏差 {ratio_error * 100:.1f}%），"
                "常见于 1080P 屏幕上窗口化被任务栏与标题栏挤压。建议切换为桌面分身内 1920x1080 无边框，"
                "或在主桌面校准为 1600x900 / 1280x720 窗口。"
                + dpi_hint
            ),
        )

    if client_width == BASE_WIDTH and client_height == BASE_HEIGHT:
        return WindowGeometryReport(
            client_width=client_width,
            client_height=client_height,
            dpi_scale_percent=dpi_scale_percent,
            aspect_ratio=round(aspect_ratio, 4),
            ratio_error=round(ratio_error, 4),
            scale_x=1.0,
            scale_y=1.0,
            status="optimal_1080p",
            is_valid=True,
            recommendation="客户区为标准 1920x1080 (16:9) 基准分辨率，COCO 模板 1:1 零缩放匹配。"
            + dpi_hint,
        )

    return WindowGeometryReport(
        client_width=client_width,
        client_height=client_height,
        dpi_scale_percent=dpi_scale_percent,
        aspect_ratio=round(aspect_ratio, 4),
        ratio_error=round(ratio_error, 4),
        scale_x=round(scale_x, 4),
        scale_y=round(scale_y, 4),
        status="valid_scaled_16_9",
        is_valid=True,
        recommendation=(
            f"客户区 {client_width}x{client_height} 满足 16:9 比例（缩放系数 {scale_x:.2f}x），"
            "适合 1080P 主桌面窗口化运行，所有 ROI 与模板将自动等比缩放。"
            + dpi_hint
        ),
    )


def enable_per_monitor_dpi_awareness() -> bool:
    """在 Windows 下主动声明 Per-Monitor DPI v2 感知，避免高分屏坐标漂移。"""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        user32 = ctypes.windll.user32
        result = user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        if result:
            return True
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return True
    except Exception:
        return False


def get_window_client_size(hwnd: int) -> Optional[tuple[int, int]]:
    """读取 Windows 窗口客户区物理像素尺寸（不含标题栏与外边框）。"""
    if sys.platform != "win32" or hwnd <= 0:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return (rect.right - rect.left, rect.bottom - rect.top)
    except Exception:
        return None
    return None


def resize_client_to_16_9(hwnd: int, target_width: int = 1600, target_height: int = 900) -> bool:
    """将带边框的游戏窗口校准为精确的 16:9 客户区尺寸（默认 1600x900，适配 1080P 主桌面）。"""
    if sys.platform != "win32" or hwnd <= 0:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        win_rect = wintypes.RECT()
        cli_rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(win_rect)):
            return False
        if not user32.GetClientRect(hwnd, ctypes.byref(cli_rect)):
            return False

        border_w = (win_rect.right - win_rect.left) - (cli_rect.right - cli_rect.left)
        border_h = (win_rect.bottom - win_rect.top) - (cli_rect.bottom - cli_rect.top)
        new_w = target_width + max(0, border_w)
        new_h = target_height + max(0, border_h)

        # SWP_NOMOVE (0x0002) | SWP_NOZORDER (0x0004)
        return bool(user32.SetWindowPos(hwnd, 0, 0, 0, new_w, new_h, 0x0002 | 0x0004))
    except Exception:
        return False
