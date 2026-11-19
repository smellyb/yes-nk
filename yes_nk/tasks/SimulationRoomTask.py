"""方舟模拟室自动快速通关任务（对应 MaaNikke SimulationRoom 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class SimulationRoomTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "模拟室每日快速通关"
        self.description = "进入方舟模拟室，选定目标难度 C 区，优先执行快速战斗并自动处理增益/事件直至领取全部奖励。"
        self.default_config.update(
            {
                "目标难度": "难度 5",
                "目标区域": "C",
                "满战力直接跳过增益选择": True,
                "最大节点步数": 16,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：模拟室每日快速通关")
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
            "ark_sim_room_entry",
            ["模拟室"],
            NikkeROI.ARK_MODE_GRID,
            wait_after=1.5,
        ):
            self.back_to_lobby()
            return False

        self.nikke_scene.mark("simulation_room")

        # 开始模拟并选定目标难度与区域
        self.click_ocr(["开始模拟", "继续模拟"], NikkeROI.BATTLE_START_BTN, wait_after=1.0)
        diff = str(self.config.get("目标难度", "难度 5"))
        sector = str(self.config.get("目标区域", "C"))
        self.click_ocr([diff, "5", "难度5"], NikkeROI.SIM_ROOM_DIFFICULTY, wait_after=0.7)
        self.click_ocr([sector, f"{sector}区"], NikkeROI.SIM_ROOM_DIFFICULTY, wait_after=0.7)
        self.click_ocr(["开始模拟", "进入", "确认"], NikkeROI.BATTLE_START_BTN, wait_after=1.2)

        max_steps = int(self.config.get("最大节点步数", 16))
        for step in range(max_steps):
            # 检查是否已经到达结束模拟/通关结算
            if self.click_ocr(["结束模拟", "领取奖励"], NikkeROI.BOTTOM_ACTION_BAR, wait_after=1.0):
                self.click_ocr(["确认", "不选择", "完成"], NikkeROI.POPUP_CENTER_DIALOG, wait_after=1.0)
                self.handle_common_popups()
                self.log_info("模拟室本轮已通关并领取奖励")
                break

            # 跳过或默认选择增益
            if self.config.get("满战力直接跳过增益选择", True) and self.click_ocr(
                ["不选择", "跳过"],
                NikkeROI.BOTTOM_ACTION_BAR,
                wait_after=0.8,
            ):
                self.click_ocr(["确认"], NikkeROI.POPUP_CENTER_DIALOG, wait_after=0.7)
                continue

            # 优先普通战斗/快速战斗节点
            if self.click_ocr(
                ["普通", "困难", "BOSS", "强化"],
                NikkeROI.SIM_ROOM_STAGES,
                wait_after=1.0,
                name="sim_node_pick",
            ):
                if self.click_ocr(["快速战斗"], NikkeROI.BATTLE_START_BTN, wait_after=1.2):
                    self.handle_common_popups()
                elif self.click_ocr(["进入战斗", "开始战斗"], NikkeROI.BATTLE_START_BTN, wait_after=2.0):
                    self.click_ocr(["点击画面继续", "点击继续"], NikkeROI.BATTLE_RESULT_AREA, wait_after=1.0)
                continue

            self.log_info(f"模拟室状态推进中 ({step + 1}/{max_steps})")
            self.handle_common_popups()

        self.back_to_lobby()
        return True
