"""更生馆（解放任务）每日点数收取任务（对应 MaaNikke Liberation 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class LiberationTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "更生馆每日进度领取"
        self.description = "从大厅或前哨基地进入更生馆，收取已完成的解放任务点数，严禁消耗珠宝刷新任务。"

    def run(self) -> bool:
        self.log_info("开始执行：更生馆每日进度领取")
        if not self.ensure_in_lobby():
            return False

        opened = self.click_feature_or_ocr(
            "lobby_liberation_icon",
            ["更生馆", "解放"],
            NikkeROI.LOBBY_TOP_LEFT,
            wait_after=1.4,
        )
        if not opened:
            self.log_info("大厅左上角未检测到更生馆入口（可能已全部解放或未解锁）")
            return True

        self.nikke_scene.mark("liberation")
        claimed = 0
        for _ in range(3):
            if self.click_ocr(
                ["完成", "领取"],
                NikkeROI.LIBERATION_TASKS_AREA,
                wait_after=1.0,
                name="liberation_claim",
            ):
                self.handle_common_popups()
                claimed += 1
            else:
                break

        self.log_info(f"更生馆检查完毕，本次领取 {claimed} 项解放任务进度")
        self.back_to_lobby()
        return True
