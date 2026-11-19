"""《胜利女神：新的希望》国服全量 16:9 归一化 ROI 区域与场景状态模型。

覆盖 MaaNikke 全部 20+ 条流水线涉及的界面区域（大厅、邮箱、好友、前哨基地、公告栏、
普通/付费商店、招募、咨询、装备、更生馆、方舟、拦截战、模拟室、竞技场、无限之塔、
协同作战、单人突击、联盟突袭、大型活动与通行证 PASS）。
所有坐标以 1920x1080 (16:9) 客户区为基准归一化到 [0.0, 1.0]。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

NormalizedBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class NikkeROI:
    # --- 大厅与通用导航（已按 MaaNikke 1280x720 实测 ROI 校准） ---
    LOBBY_BOTTOM_NAV: NormalizedBox = (0.24, 0.85, 0.76, 0.995)
    LOBBY_TOP_LEFT: NormalizedBox = (0.00, 0.00, 0.30, 0.24)
    LOBBY_TOP_RIGHT: NormalizedBox = (0.76, 0.00, 0.995, 0.66)
    LOBBY_LEFT_BANNERS: NormalizedBox = (0.00, 0.14, 0.36, 0.68)
    LOBBY_OUTPOST_ENTRY: NormalizedBox = (0.02, 0.66, 0.42, 0.94)
    LOBBY_RIGHT_SHORTCUTS: NormalizedBox = (0.58, 0.12, 0.995, 0.90)
    TOP_LEFT_BACK: NormalizedBox = (0.00, 0.00, 0.20, 0.995)
    FULL_CENTER: NormalizedBox = (0.15, 0.18, 0.85, 0.86)

    # --- 弹窗与战斗通用 ---
    POPUP_TOP_RIGHT_CLOSE: NormalizedBox = (0.55, 0.02, 0.98, 0.26)
    POPUP_CENTER_DIALOG: NormalizedBox = (0.22, 0.24, 0.78, 0.82)
    POPUP_BOTTOM_DISMISS: NormalizedBox = (0.28, 0.78, 0.72, 0.97)
    BATTLE_START_BTN: NormalizedBox = (0.32, 0.74, 0.76, 0.94)
    BATTLE_RESULT_AREA: NormalizedBox = (0.25, 0.72, 0.75, 0.96)

    # --- 邮箱 / 好友 / 通行证 / 任务 ---
    BOTTOM_ACTION_BAR: NormalizedBox = (0.25, 0.76, 0.85, 0.97)
    MISSION_TABS: NormalizedBox = (0.18, 0.12, 0.82, 0.24)
    MISSION_CLAIM_ALL: NormalizedBox = (0.55, 0.80, 0.88, 0.95)
    PASS_REWARD_AREA: NormalizedBox = (0.18, 0.10, 0.96, 0.92)

    # --- 前哨基地、派遣与循环室/同步器 ---
    OUTPOST_REWARD_ACTIONS: NormalizedBox = (0.26, 0.66, 0.74, 0.86)
    DISPATCH_ACTIONS: NormalizedBox = (0.26, 0.76, 0.76, 0.94)
    OUTPOST_FACILITIES: NormalizedBox = (0.04, 0.14, 0.92, 0.92)

    # --- 商店（普通 / 竞技场 / 付费商店） ---
    SHOP_SIDE_TABS: NormalizedBox = (0.02, 0.14, 0.20, 0.86)
    SHOP_SHELF_SLOTS: Tuple[NormalizedBox, ...] = (
        (0.18, 0.42, 0.34, 0.78),
        (0.35, 0.42, 0.50, 0.78),
        (0.51, 0.42, 0.66, 0.78),
        (0.67, 0.42, 0.82, 0.78),
    )
    SHOP_REFRESH_BTN: NormalizedBox = (0.70, 0.24, 0.88, 0.36)
    CASH_SHOP_TOP_TABS: NormalizedBox = (0.14, 0.10, 0.88, 0.24)
    CASH_SHOP_FREE_GRID: NormalizedBox = (0.16, 0.24, 0.86, 0.82)

    # --- 招募 / 妮姬咨询 / 装备 / 更生馆 ---
    RECRUIT_BANNER_SWITCH: NormalizedBox = (0.04, 0.40, 0.96, 0.62)
    RECRUIT_PULL_AREA: NormalizedBox = (0.24, 0.74, 0.78, 0.92)
    NIKKE_ROSTER_GRID: NormalizedBox = (0.16, 0.22, 0.84, 0.86)
    ADVISE_DIALOG_CHOICES: NormalizedBox = (0.20, 0.58, 0.80, 0.88)
    ADVISE_ACTION_BAR: NormalizedBox = (0.24, 0.76, 0.82, 0.94)
    EQUIP_SLOT_AREA: NormalizedBox = (0.08, 0.34, 0.46, 0.84)
    EQUIP_UPGRADE_ACTIONS: NormalizedBox = (0.48, 0.68, 0.88, 0.92)
    LIBERATION_TASKS_AREA: NormalizedBox = (0.18, 0.34, 0.84, 0.86)

    # --- 方舟副本（拦截战 / 模拟室 / 竞技场 / 无限之塔 / 协同 / 单人突击） ---
    ARK_MODE_GRID: NormalizedBox = (0.12, 0.18, 0.88, 0.86)
    INTERCEPTION_BOSS_AREA: NormalizedBox = (0.16, 0.24, 0.84, 0.88)
    SIM_ROOM_DIFFICULTY: NormalizedBox = (0.16, 0.22, 0.84, 0.84)
    SIM_ROOM_STAGES: NormalizedBox = (0.14, 0.24, 0.86, 0.84)
    ARENA_MODE_SELECT: NormalizedBox = (0.16, 0.24, 0.84, 0.84)
    ARENA_OPPONENT_SLOTS: Tuple[NormalizedBox, ...] = (
        (0.64, 0.32, 0.88, 0.46),
        (0.64, 0.48, 0.88, 0.62),
        (0.64, 0.64, 0.88, 0.78),
    )
    TOWER_LIST_AREA: NormalizedBox = (0.14, 0.20, 0.86, 0.86)

    # --- 联盟突袭 & 大型活动 ---
    UNION_MENU_AREA: NormalizedBox = (0.16, 0.22, 0.86, 0.86)
    EVENT_MAIN_STAGE_AREA: NormalizedBox = (0.14, 0.20, 0.88, 0.88)


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
