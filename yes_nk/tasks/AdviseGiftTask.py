"""妮姬每日咨询与送礼任务（对应 MaaNikke Advise & Gift 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class AdviseGiftTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "妮姬咨询与好感送礼"
        self.description = "优先对已解锁快速咨询的妮姬一键完成每日咨询，并可选赠送 1 次好感礼物以完成每日任务。"
        self.default_config.update(
            {
                "优先使用快速咨询": True,
                "每日咨询最大处理人数": 5,
                "顺带赠送 1 次好感礼物": False,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：妮姬咨询与好感送礼")
        if not self.ensure_in_lobby():
            return False

        if not self.click_feature_or_ocr(
            "lobby_nikke_nav",
            ["妮姬"],
            NikkeROI.LOBBY_BOTTOM_NAV,
            wait_after=1.4,
        ):
            return False

        if not self.click_feature_or_ocr(
            "nikke_advise_entry",
            ["咨询"],
            NikkeROI.LOBBY_TOP_RIGHT,
            wait_after=1.4,
        ):
            self.log_info("未定位到咨询入口")
            self.back_to_lobby()
            return False

        self.nikke_scene.mark("advise")
        max_count = int(self.config.get("每日咨询最大处理人数", 5))
        completed = 0

        for idx in range(max_count):
            # 1. 优先匹配“快速咨询”按钮
            if self.config.get("优先使用快速咨询", True) and self.click_ocr(
                ["快速咨询"],
                NikkeROI.ADVISE_ACTION_BAR,
                wait_after=1.0,
                name="quick_advise",
            ):
                self.click_ocr(["确认", "确定"], NikkeROI.POPUP_CENTER_DIALOG, wait_after=1.0)
                self.handle_common_popups()
                completed += 1
                self.log_info(f"完成第 {completed} 位妮姬快速咨询")
                continue

            # 2. 常规咨询流程（点击咨询 -> 推进对话 -> 选择首个友好回复）
            if self.click_ocr(["咨询"], NikkeROI.ADVISE_ACTION_BAR, wait_after=1.0, name="normal_advise"):
                self.click_ocr(["确认", "确定"], NikkeROI.POPUP_CENTER_DIALOG, wait_after=1.0)
                for _ in range(4):
                    if self.click_ocr(["SKIP", "跳过"], NikkeROI.POPUP_TOP_RIGHT_CLOSE, wait_after=0.6):
                        break
                    self.click_relative(0.50, 0.68)
                    self._wait_step(0.5)
                self.handle_common_popups()
                completed += 1
                self.log_info(f"完成第 {completed} 位妮姬常规咨询")
            else:
                self.log_info(f"第 {idx + 1} 轮未检测到剩余可咨询次数，结束咨询流程")
                break

        if self.config.get("顺带赠送 1 次好感礼物", False):
            if self.click_ocr(["赠送礼物", "送礼"], NikkeROI.ADVISE_ACTION_BAR, wait_after=0.9):
                self.click_ocr(["赠送", "确认"], NikkeROI.POPUP_CENTER_DIALOG, wait_after=0.9)
                self.handle_common_popups()
                self.log_info("已完成日常好感送礼")

        self.back_to_lobby()
        return True
