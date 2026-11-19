"""邮箱一键领取任务（借鉴 MaaNikke Mailbox 流程，改用 ok-script 混合识别）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class MailTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "邮箱一键领取"
        self.description = "从大厅进入邮箱界面并点击“全部领取”，随后清理奖励结算弹窗。"

    def run(self) -> bool:
        self.log_info("开始执行：邮箱一键领取")
        if not self.ensure_in_lobby():
            self.log_error("无法回到大厅，跳过邮箱领取")
            return False

        opened = self.click_feature_or_ocr(
            "lobby_mail_icon",
            ["邮箱", "邮件"],
            NikkeROI.LOBBY_TOP_RIGHT,
            wait_after=1.2,
        )
        if not opened:
            self.log_info("未在右上角定位到邮箱入口，请检查 COCO 模板 lobby_mail_icon")
            return False

        self.nikke_scene.mark("mail")
        claimed = self.click_feature_or_ocr(
            "mail_claim_all_btn",
            ["全部领取", "一键领取"],
            NikkeROI.BOTTOM_ACTION_BAR,
            wait_after=1.2,
        )
        if claimed:
            self.log_info("已点击邮箱“全部领取”")
            self.handle_common_popups()
        else:
            self.log_info("邮箱无可领取附件或按钮已置灰")

        self.back_to_lobby()
        return True
