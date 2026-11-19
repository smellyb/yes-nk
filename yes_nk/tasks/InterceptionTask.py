"""方舟拦截战自动挑战与快速战斗任务（对应 MaaNikke Interception 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class InterceptionTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "拦截战挑战与快速扫荡"
        self.description = "进入方舟拦截战，优先使用“快速战斗”耗尽每日 3 次机会；未解锁快速战斗时自动完成首战。"
        self.default_config.update(
            {
                "目标拦截模式": "异常拦截战",
                "每日最大挑战次数": 3,
                "优先快速战斗": True,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def _wait_battle_finish(self, max_polls: int = 30) -> bool:
        for _ in range(max_polls):
            if self.click_ocr(
                ["点击画面继续", "点击继续", "返回", "确认"],
                NikkeROI.BATTLE_RESULT_AREA,
                wait_after=1.0,
                name="interception_result",
            ):
                return True
            self._wait_step(2.0)
        return False

    def run(self) -> bool:
        self.log_info("开始执行：拦截战挑战与快速扫荡")
        if not self.ensure_in_lobby():
            return False

        if not self.click_feature_or_ocr(
            "lobby_ark_icon",
            ["方舟"],
            NikkeROI.LOBBY_RIGHT_SHORTCUTS,
            wait_after=1.5,
        ):
            return False

        if not self.click_feature_or_ocr(
            "ark_interception_entry",
            ["拦截战"],
            NikkeROI.ARK_MODE_GRID,
            wait_after=1.5,
        ):
            self.back_to_lobby()
            return False

        self.nikke_scene.mark("interception")
        target_mode = str(self.config.get("目标拦截模式", "异常拦截战"))
        self.click_ocr([target_mode, "异常拦截战", "特殊拦截战"], NikkeROI.INTERCEPTION_BOSS_AREA, wait_after=1.0)
        self.click_ocr(["挑战", "进入"], NikkeROI.INTERCEPTION_BOSS_AREA, wait_after=1.0)

        max_runs = int(self.config.get("每日最大挑战次数", 3))
        done = 0

        for _ in range(max_runs):
            if self.config.get("优先快速战斗", True) and self.click_ocr(
                ["快速战斗"],
                NikkeROI.BATTLE_START_BTN,
                wait_after=1.2,
                name="interception_quick",
            ):
                self.click_ocr(["确认", "确定"], NikkeROI.POPUP_CENTER_DIALOG, wait_after=1.0)
                self.handle_common_popups()
                done += 1
                self.log_info(f"拦截战快速战斗完成 ({done}/{max_runs})")
                continue

            if self.click_ocr(
                ["进入战斗", "开始战斗"],
                NikkeROI.BATTLE_START_BTN,
                wait_after=2.0,
                name="interception_battle",
            ):
                self._wait_battle_finish()
                self.handle_common_popups()
                done += 1
                self.log_info(f"拦截战首战/常规战斗完成 ({done}/{max_runs})")
            else:
                self.log_info("未检测到剩余拦截战次数，结束挑战")
                break

        self.back_to_lobby()
        return True
