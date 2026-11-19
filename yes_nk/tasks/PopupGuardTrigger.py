"""后台触发守护任务：突发弹窗清理与网络波动断线重连（仿 YES-BD2 TriggerTask）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTriggerTask


class PopupGuardTrigger(BaseNikkeTriggerTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "突发弹窗与断线重连守护"
        self.description = "低频巡检限时礼包弹窗、每日签到、网络断线重试与点击继续遮罩。"
        self.default_config.update(
            {
                "自动处理网络重连弹窗": True,
                "自动关闭限时礼包公告": True,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        # 1. 网络波动重试守护
        if self.config.get("自动处理网络重连弹窗", True):
            reconnect_box = self.box_of_screen(*NikkeROI.POPUP_CENTER_DIALOG, name="reconnect")
            hits = self.ocr(box=reconnect_box, match=["重新连接", "网络异常", "连接中断"]) or []
            if hits:
                self.log_info("检测到网络波动弹窗，尝试点击确认重连")
                confirm_hits = self.ocr(box=reconnect_box, match=["确认", "重试", "确定"]) or []
                if confirm_hits:
                    self.click_box(confirm_hits[0])
                else:
                    self.click_box(hits[0])
                self.sleep(1.5)
                return True

        # 2. 限时公告与关闭按钮守护
        if self.config.get("自动关闭限时礼包公告", True):
            close_box = self.box_of_screen(*NikkeROI.POPUP_TOP_RIGHT_CLOSE, name="popup_close")
            close_btn = self.find_one("popup_close_x", box=close_box)
            if close_btn is not None:
                self.log_info("触发守护：关闭突发活动/礼包弹窗")
                self.click_box(close_btn)
                self.sleep(0.8)
                return True

        return False
