"""前哨基地防御收菜与每日免费一举歼灭任务。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class OutpostDefenseTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "前哨基地收菜与一举歼灭"
        self.description = "收取前哨基地累积防御奖励，并按配置执行每日免费 1 次一举歼灭。"
        self.default_config.update(
            {
                "执行每日免费一举歼灭": True,
            }
        )
        self.config.setdefault("执行每日免费一举歼灭", True)

    def run(self) -> bool:
        self.log_info("开始执行：前哨基地收菜与一举歼灭")
        if not self.ensure_in_lobby():
            self.log_error("无法回到大厅，跳过前哨基地收菜")
            return False

        opened = self.click_feature_or_ocr(
            "lobby_outpost_defense_btn",
            ["前哨基地防御", "前哨基地"],
            NikkeROI.LOBBY_OUTPOST_ENTRY,
            wait_after=1.2,
        )
        if not opened:
            self.log_info("未定位到前哨基地防御入口")
            return False

        self.nikke_scene.mark("outpost_defense")

        # 1. 收取当前累计防御奖励
        if self.click_feature_or_ocr(
            "outpost_claim_reward_btn",
            ["领取奖励", "领取"],
            NikkeROI.OUTPOST_REWARD_ACTIONS,
            wait_after=1.2,
        ):
            self.log_info("已收取前哨基地防御奖励")
            self.handle_common_popups()

        # 2. 每日免费一举歼灭（严禁消耗珠宝二次歼灭：必须确认出现“免费”字样）
        if self.config.get("执行每日免费一举歼灭", True):
            if self.click_feature_or_ocr(
                "outpost_wipe_out_btn",
                ["一举歼灭"],
                NikkeROI.OUTPOST_REWARD_ACTIONS,
                wait_after=1.0,
            ):
                free_confirm = self.ocr_in_roi(
                    NikkeROI.POPUP_CENTER_DIALOG,
                    match=["免费"],
                    name="wipe_out_free_check",
                )
                if free_confirm:
                    self.click_ocr(
                        ["进行一举歼灭", "确认", "免费"],
                        NikkeROI.POPUP_CENTER_DIALOG,
                        wait_after=1.2,
                        name="wipe_out_confirm",
                    )
                    self.log_info("已完成每日免费一举歼灭")
                    self.handle_common_popups()
                else:
                    self.log_info("未检测到免费一举歼灭标识，为防止误花珠宝已自动取消")
                    self.handle_common_popups()

        self.back_to_lobby()
        return True
