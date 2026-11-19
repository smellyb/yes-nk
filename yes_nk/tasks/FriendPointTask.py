"""好友友情点赠送与收取任务。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class FriendPointTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "好友友情点互赠"
        self.description = "进入好友列表一键赠送并收取每日友情点。"

    def run(self) -> bool:
        self.log_info("开始执行：好友友情点互赠")
        if not self.ensure_in_lobby():
            self.log_error("无法回到大厅，跳过好友友情点")
            return False

        opened = self.click_feature_or_ocr(
            "lobby_friend_icon",
            ["好友"],
            NikkeROI.LOBBY_TOP_RIGHT,
            wait_after=1.2,
        )
        if not opened:
            self.log_info("未定位到好友图标，请检查 COCO 模板 lobby_friend_icon")
            return False

        self.nikke_scene.mark("friend")
        sent = self.click_feature_or_ocr(
            "friend_send_all_btn",
            ["赠送", "一键赠送", "全部赠送"],
            NikkeROI.BOTTOM_ACTION_BAR,
            wait_after=1.0,
        )
        if sent:
            self.log_info("已完成每日友情点赠送与收取")
            self.handle_common_popups()
        else:
            self.log_info("今日友情点已赠送或未检测到可点击按钮")

        self.back_to_lobby()
        return True
