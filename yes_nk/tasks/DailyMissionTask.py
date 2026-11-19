"""日常收尾：每日任务与通行证一键领取活跃度奖励。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class DailyMissionTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "每日任务与活跃奖励领取"
        self.description = "在基础日常收尾阶段进入任务面板，一键领取每日/每周活跃度与积分奖励。"
        self.default_config.update(
            {
                "同时领取每周任务奖励": True,
            }
        )
        self.config.setdefault("同时领取每周任务奖励", True)

    def run(self) -> bool:
        self.log_info("开始执行：每日任务与活跃奖励领取")
        if not self.ensure_in_lobby():
            self.log_error("无法回到大厅，跳过任务奖励领取")
            return False

        opened = self.click_feature_or_ocr(
            "lobby_mission_icon",
            ["任务"],
            NikkeROI.LOBBY_RIGHT_SHORTCUTS,
            wait_after=1.3,
        )
        if not opened:
            self.log_info("未定位到大厅任务图标")
            return False

        self.nikke_scene.mark("mission")

        if self.click_feature_or_ocr(
            "mission_claim_all_btn",
            ["全部领取", "一键领取"],
            NikkeROI.MISSION_CLAIM_ALL,
            wait_after=1.0,
        ):
            self.log_info("已领取每日任务奖励")
            self.handle_common_popups()

        if self.config.get("同时领取每周任务奖励", True):
            if self.click_ocr(["每周任务", "每周"], NikkeROI.MISSION_TABS, wait_after=0.9):
                if self.click_feature_or_ocr(
                    "mission_claim_all_btn",
                    ["全部领取", "一键领取"],
                    NikkeROI.MISSION_CLAIM_ALL,
                    wait_after=1.0,
                ):
                    self.log_info("已领取每周任务奖励")
                    self.handle_common_popups()

        self.back_to_lobby()
        return True
