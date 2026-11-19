"""《胜利女神：新的希望》国服 16:9 归一化 ROI 区域与场景状态模型。

所有坐标均以 1920x1080 (16:9) 客户区为基准归一化到 [0.0, 1.0]，
配合 ok-script 的 box_of_screen(x1, y1, x2, y2) 可在 1920x1080 / 1600x900 / 1280x720 自动等比缩放。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

NormalizedBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class NikkeROI:
    # 大厅底部导航栏（用于稳定判定是否在大厅，不受动态立绘干扰）
    LOBBY_BOTTOM_NAV: NormalizedBox = (0.24, 0.88, 0.76, 0.99)
    # 大厅右上角系统图标区（邮箱、公告、菜单、好友）
    LOBBY_TOP_RIGHT: NormalizedBox = (0.76, 0.01, 0.99, 0.14)
    # 大厅左侧/左下角前哨基地与防御进度入口
    LOBBY_OUTPOST_ENTRY: NormalizedBox = (0.02, 0.68, 0.28, 0.90)
    # 大厅右侧快捷入口（商店、方舟、任务）
    LOBBY_RIGHT_SHORTCUTS: NormalizedBox = (0.72, 0.56, 0.98, 0.88)
    # 通用弹窗关闭区域与“今日不再显示”复选区
    POPUP_TOP_RIGHT_CLOSE: NormalizedBox = (0.72, 0.04, 0.97, 0.24)
    POPUP_CENTER_DIALOG: NormalizedBox = (0.22, 0.24, 0.78, 0.82)
    POPUP_BOTTOM_DISMISS: NormalizedBox = (0.28, 0.78, 0.72, 0.97)
    # 邮箱与好友底部批量操作栏
    BOTTOM_ACTION_BAR: NormalizedBox = (0.25, 0.78, 0.85, 0.96)
    # 前哨基地防御弹窗操作区（领取奖励 / 一举歼灭）
    OUTPOST_REWARD_ACTIONS: NormalizedBox = (0.26, 0.66, 0.74, 0.86)
    # 公告栏派遣操作区（全部领取 / 全部派遣）
    DISPATCH_ACTIONS: NormalizedBox = (0.26, 0.76, 0.76, 0.94)
    # 普通商店 4 格商品货架区域（支持逐格切分，严控价格与货币图标 ROI）
    SHOP_SHELF_SLOTS: Tuple[NormalizedBox, ...] = (
        (0.18, 0.42, 0.34, 0.78),
        (0.35, 0.42, 0.50, 0.78),
        (0.51, 0.42, 0.66, 0.78),
        (0.67, 0.42, 0.82, 0.78),
    )
    SHOP_REFRESH_BTN: NormalizedBox = (0.70, 0.24, 0.88, 0.36)
    # 顶部返回大厅 / 返回上一级区域
    TOP_LEFT_BACK: NormalizedBox = (0.01, 0.01, 0.16, 0.12)
    # 日常任务与通行证页面
    MISSION_TABS: NormalizedBox = (0.18, 0.12, 0.82, 0.24)
    MISSION_CLAIM_ALL: NormalizedBox = (0.55, 0.80, 0.88, 0.95)


class NikkeScene:
    """仿 YES-BD2 的场景状态缓存，避免子任务重复编写大厅与弹窗判定。"""

    LOBBY_ANCHOR_KEYWORDS = ("大厅", "妮姬", "部队", "背包", "商店", "前哨基地")
    POPUP_DISMISS_KEYWORDS = ("点击继续", "点击画面继续", "确认", "确定", "今日不再显示", "重新连接")

    def __init__(self) -> None:
        self.last_scene: str = "unknown"
        self.popup_dismissed_count: int = 0

    def mark(self, scene_name: str) -> str:
        self.last_scene = scene_name
        return scene_name

    def record_popup_dismissed(self) -> int:
        self.popup_dismissed_count += 1
        return self.popup_dismissed_count

    def reset(self) -> None:
        self.last_scene = "unknown"
        self.popup_dismissed_count = 0
