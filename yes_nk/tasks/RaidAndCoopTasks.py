"""限时团队与突击副本任务集合（对应 MaaNikke 协同作战 / 单人突击 / 联盟突袭 Beta 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class CoopOperationTask(BaseNikkeTask):
    """协同作战自动匹配与每日 3 次挂机（对应 MaaNikke Coop 流水线）。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "协同作战自动匹配"
        self.description = "检测限时协同作战开放状态，自动匹配普通/挑战模式并消耗每日 3 次挑战次数。"
        self.default_config.update(
            {
                "目标难度": "普通",
                "每日匹配次数": 3,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：协同作战自动匹配")
        if not self.ensure_in_lobby():
            return False

        if not self.click_feature_or_ocr(
            "lobby_coop_banner",
            ["协同作战"],
            NikkeROI.LOBBY_LEFT_BANNERS,
            wait_after=1.5,
        ):
            self.log_info("当前未检测到开放中的协同作战活动，已自动跳过")
            return True

        self.nikke_scene.mark("coop")
        runs = int(self.config.get("每日匹配次数", 3))
        diff = str(self.config.get("目标难度", "普通"))

        for idx in range(runs):
            self.click_ocr([diff, "普通"], NikkeROI.FULL_CENTER, wait_after=0.7)
            if not self.click_ocr(["配对", "开始匹配", "匹配"], NikkeROI.BATTLE_START_BTN, wait_after=2.0):
                break
            self.click_ocr(["准备完成", "准备"], NikkeROI.BATTLE_START_BTN, wait_after=2.0)
            self.click_ocr(["点击画面继续", "点击继续", "确认"], NikkeROI.BATTLE_RESULT_AREA, wait_after=1.2)
            self.handle_common_popups()
            self.log_info(f"协同作战完成第 {idx + 1}/{runs} 场")

        self.back_to_lobby()
        return True


class SoloRaidTask(BaseNikkeTask):
    """单人突击每日扫荡任务（对应 MaaNikke SoloRaid 流水线）。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "单人突击每日快速战斗"
        self.description = "检测单人突击赛季入口，优先使用“快速战斗”耗尽每日 3 次挑战券。"
        self.default_config.update({"每日最大扫荡次数": 3})
        self.config.setdefault("每日最大扫荡次数", 3)

    def run(self) -> bool:
        self.log_info("开始执行：单人突击每日快速战斗")
        if not self.ensure_in_lobby():
            return False

        if not self.click_feature_or_ocr(
            "lobby_solo_raid_banner",
            ["单人突击"],
            NikkeROI.LOBBY_LEFT_BANNERS,
            wait_after=1.5,
        ):
            self.log_info("当前非单人突击开放期，已跳过")
            return True

        self.nikke_scene.mark("solo_raid")
        runs = int(self.config.get("每日最大扫荡次数", 3))
        for idx in range(runs):
            if self.click_ocr(["快速战斗"], NikkeROI.BATTLE_START_BTN, wait_after=1.2):
                self.click_ocr(["确认", "确定"], NikkeROI.POPUP_CENTER_DIALOG, wait_after=1.0)
                self.handle_common_popups()
                self.log_info(f"单人突击快速战斗完成 ({idx + 1}/{runs})")
            else:
                break

        self.back_to_lobby()
        return True


class UnionRaidTask(BaseNikkeTask):
    """联盟突袭 (Beta) 自动出刀任务（对应 MaaNikke UnionRaid 流水线）。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "联盟突袭 (Beta)"
        self.description = "进入联盟 -> 联盟突袭，按预设编队依次完成每日联盟突袭出刀。"
        self.default_config.update({"每日出刀次数": 3})
        self.config.setdefault("每日出刀次数", 3)

    def run(self) -> bool:
        self.log_info("开始执行：联盟突袭 (Beta)")
        if not self.ensure_in_lobby():
            return False

        if not self.click_feature_or_ocr(
            "lobby_union_icon",
            ["联盟"],
            NikkeROI.LOBBY_TOP_RIGHT,
            wait_after=1.5,
        ):
            self.log_info("未定位到联盟入口")
            return False

        if not self.click_ocr(["联盟突袭"], NikkeROI.UNION_MENU_AREA, wait_after=1.5):
            self.log_info("当前未处于联盟突袭开放期，已跳过")
            self.back_to_lobby()
            return True

        self.nikke_scene.mark("union_raid")
        runs = int(self.config.get("每日出刀次数", 3))
        for idx in range(runs):
            if not self.click_ocr(["进入战斗", "开始战斗", "挑战"], NikkeROI.BATTLE_START_BTN, wait_after=2.0):
                break
            self.click_ocr(["点击画面继续", "点击继续", "确认"], NikkeROI.BATTLE_RESULT_AREA, wait_after=1.2)
            self.handle_common_popups()
            self.log_info(f"联盟突袭出刀完成 ({idx + 1}/{runs})")

        self.back_to_lobby()
        return True
