"""前哨基地公告栏派遣任务一键收取与重派。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class DispatchTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "公告栏派遣收取与重派"
        self.description = "进入前哨基地公告栏，一键收取已完成派遣并自动全部重新派遣。"

    def run(self) -> bool:
        self.log_info("开始执行：公告栏派遣收取与重派")
        if not self.ensure_in_lobby():
            self.log_error("无法回到大厅，跳过派遣任务")
            return False

        # 进入前哨基地或直接点击公告栏快捷图标
        entered = self.click_feature_or_ocr(
            "outpost_bulletin_icon",
            ["公告栏", "派遣"],
            NikkeROI.LOBBY_OUTPOST_ENTRY,
            wait_after=1.4,
        )
        if not entered:
            self.log_info("未定位到公告栏入口，尝试通过前哨基地主入口进入")
            if not self.click_feature_or_ocr(
                "lobby_outpost_entry",
                ["前哨基地"],
                NikkeROI.LOBBY_OUTPOST_ENTRY,
                wait_after=2.0,
            ):
                return False
            self.click_feature_or_ocr(
                "outpost_bulletin_icon",
                ["公告栏", "派遣"],
                NikkeROI.LOBBY_TOP_RIGHT,
                wait_after=1.2,
            )

        self.nikke_scene.mark("dispatch")

        if self.click_feature_or_ocr(
            "dispatch_claim_all_btn",
            ["全部领取", "全部收取"],
            NikkeROI.DISPATCH_ACTIONS,
            wait_after=1.0,
        ):
            self.log_info("已收取已完成派遣奖励")
            self.handle_common_popups()

        if self.click_feature_or_ocr(
            "dispatch_send_all_btn",
            ["全部派遣", "一键派遣"],
            NikkeROI.DISPATCH_ACTIONS,
            wait_after=1.0,
        ):
            self.click_ocr(
                ["派遣", "确认"],
                NikkeROI.POPUP_CENTER_DIALOG,
                wait_after=1.0,
                name="dispatch_confirm",
            )
            self.log_info("已完成全部重新派遣")

        self.back_to_lobby()
        return True
