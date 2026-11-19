"""大型限时活动关卡刷取与活动任务领取（对应 MaaNikke EventStory 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class EventStoryTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "大型活动刷取与签到"
        self.description = "从大厅左侧进入当前大型活动，领取活动签到与成就任务，并自动重复扫荡指定活动关卡（如 1-11）。"
        self.default_config.update(
            {
                "目标关卡编号": "1-11",
                "每日重复刷取次数": 5,
                "优先使用快速战斗": True,
                "顺带领取活动任务与签到": True,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：大型活动刷取与签到")
        if not self.ensure_in_lobby():
            return False

        opened = self.click_feature_or_ocr(
            "lobby_event_banner",
            ["EVENT", "活动", "剧情活动"],
            NikkeROI.LOBBY_LEFT_BANNERS,
            wait_after=1.6,
        )
        if not opened:
            self.log_info("未在大厅左侧检测到大型活动入口")
            return True

        self.nikke_scene.mark("event_story")

        if self.config.get("顺带领取活动任务与签到", True):
            if self.click_ocr(["任务", "成就", "签到"], NikkeROI.EVENT_MAIN_STAGE_AREA, wait_after=1.0):
                self.click_ocr(["全部领取", "一键领取"], NikkeROI.BOTTOM_ACTION_BAR, wait_after=1.0)
                self.handle_common_popups()
                self.click_feature_or_ocr("nav_back_btn", ["返回"], NikkeROI.TOP_LEFT_BACK, wait_after=0.9)

        # 进入剧情关卡列表并刷取目标关卡
        self.click_ocr(["STORY", "剧情", "NORMAL", "HARD"], NikkeROI.EVENT_MAIN_STAGE_AREA, wait_after=1.2)
        stage_code = str(self.config.get("目标关卡编号", "1-11"))
        self.click_ocr([stage_code], NikkeROI.EVENT_MAIN_STAGE_AREA, wait_after=1.0)

        runs = int(self.config.get("每日重复刷取次数", 5))
        for idx in range(runs):
            if self.config.get("优先使用快速战斗", True) and self.click_ocr(
                ["快速战斗"],
                NikkeROI.BATTLE_START_BTN,
                wait_after=1.2,
            ):
                self.handle_common_popups()
                self.log_info(f"活动关卡 {stage_code} 快速战斗完成 ({idx + 1}/{runs})")
                continue

            if self.click_ocr(["进入战斗", "再次挑战", "开始战斗"], NikkeROI.BATTLE_START_BTN, wait_after=2.0):
                self.click_ocr(["再次挑战", "点击继续", "返回"], NikkeROI.BATTLE_RESULT_AREA, wait_after=1.2)
                self.handle_common_popups()
                self.log_info(f"活动关卡 {stage_code} 挑战完成 ({idx + 1}/{runs})")
            else:
                break

        self.back_to_lobby()
        return True
