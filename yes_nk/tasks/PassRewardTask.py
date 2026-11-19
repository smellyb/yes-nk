"""PASS（通行证）每日/赛季奖励领取任务（对应 MaaNikke Pass 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class PassRewardTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "通行证 (PASS) 奖励领取"
        self.description = "从大厅活动横幅进入 Mission Pass，一键领取通行证任务积分与已解锁阶梯奖励。"

    def run(self) -> bool:
        self.log_info("开始执行：通行证 (PASS) 奖励领取")
        if not self.ensure_in_lobby():
            return False

        opened = self.click_feature_or_ocr(
            "lobby_pass_banner",
            ["PASS", "通行证", "任务通行证"],
            NikkeROI.LOBBY_LEFT_BANNERS,
            wait_after=1.4,
        )
        if not opened:
            self.log_info("大厅左侧未检测到通行证入口（可能当前无活跃通行证）")
            return True

        self.nikke_scene.mark("pass")
        # 1. 先领任务积分
        if self.click_ocr(["任务", "每日任务"], NikkeROI.MISSION_TABS, wait_after=0.8):
            if self.click_ocr(["全部领取", "一键领取"], NikkeROI.BOTTOM_ACTION_BAR, wait_after=1.0):
                self.log_info("已领取通行证任务积分")
                self.handle_common_popups()

        # 2. 切回奖励页一键领取
        if self.click_ocr(["奖励", "通行证奖励"], NikkeROI.MISSION_TABS, wait_after=0.8):
            if self.click_ocr(["全部领取", "一键领取"], NikkeROI.BOTTOM_ACTION_BAR, wait_after=1.0):
                self.log_info("已领取通行证阶梯奖励")
                self.handle_common_popups()

        self.back_to_lobby()
        return True
