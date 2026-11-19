"""前哨基地同步器与循环室升级任务（对应 MaaNikke looproomandsync 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class LoopRoomAndSyncTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "同步器与循环室升级"
        self.description = (
            "进入前哨基地升级循环室研究与同步器等级，默认不自动消耗时间资源箱，防止误耗囤积箱子。"
        )
        self.default_config.update(
            {
                "升级循环室": True,
                "升级同步器": True,
                "允许使用时间盒子道具": False,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：同步器与循环室升级")
        if not self.ensure_in_lobby():
            return False

        opened_outpost = self.click_feature_or_ocr(
            "lobby_outpost_entry",
            ["前哨基地"],
            NikkeROI.LOBBY_OUTPOST_ENTRY,
            wait_after=1.8,
        )
        if not opened_outpost:
            self.log_info("未定位到前哨基地入口，跳过同步器与循环室")
            return False

        self.nikke_scene.mark("outpost_facilities")

        if self.config.get("升级循环室", True):
            if self.click_feature_or_ocr(
                "outpost_loop_room_icon",
                ["循环室", "研究"],
                NikkeROI.OUTPOST_FACILITIES,
                wait_after=1.4,
            ):
                if self.click_ocr(
                    ["全部升级", "升级", "研究"],
                    NikkeROI.BOTTOM_ACTION_BAR,
                    wait_after=1.1,
                    name="loop_room_upgrade",
                ):
                    self.click_ocr(
                        ["确认", "确定"],
                        NikkeROI.POPUP_CENTER_DIALOG,
                        wait_after=0.9,
                        name="loop_room_confirm",
                    )
                    self.handle_common_popups()
                self.click_feature_or_ocr(
                    "nav_back_btn", ["返回"], NikkeROI.TOP_LEFT_BACK, wait_after=1.0
                )

        if self.config.get("升级同步器", True):
            if self.click_feature_or_ocr(
                "outpost_sync_device_icon",
                ["同步器", "同步"],
                NikkeROI.OUTPOST_FACILITIES,
                wait_after=1.4,
            ):
                if self.click_ocr(
                    ["升级", "强化"],
                    NikkeROI.BOTTOM_ACTION_BAR,
                    wait_after=1.0,
                    name="sync_upgrade",
                ):
                    if self.config.get("允许使用时间盒子道具", False):
                        self.click_ocr(
                            ["自动选择", "使用", "确认"],
                            NikkeROI.POPUP_CENTER_DIALOG,
                            wait_after=1.0,
                            name="sync_use_box",
                        )
                    self.click_ocr(
                        ["升级", "确认"],
                        NikkeROI.POPUP_CENTER_DIALOG,
                        wait_after=1.0,
                        name="sync_upgrade_confirm",
                    )
                    self.handle_common_popups()

        self.back_to_lobby()
        return True
