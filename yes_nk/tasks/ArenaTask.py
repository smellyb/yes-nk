"""方舟竞技场任务（对应 MaaNikke RookieArena + SpecialArena + ChampionArena 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class ArenaTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "竞技场（新人 + 特殊 + 冠军）"
        self.description = "自动收取特殊竞技场累计点数，并按配置对手位耗尽新人竞技场每日 5 次免费挑战。"
        self.default_config.update(
            {
                "收取特殊竞技场累积奖励": True,
                "执行新人竞技场免费挑战": True,
                "新人竞技场优先对手位(1-3)": 3,
                "新人竞技场最大免费次数": 5,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：竞技场（新人 + 特殊）")
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
            "ark_arena_entry",
            ["竞技场"],
            NikkeROI.ARK_MODE_GRID,
            wait_after=1.5,
        ):
            self.back_to_lobby()
            return False

        self.nikke_scene.mark("arena")

        # 1. 特殊竞技场收菜
        if self.config.get("收取特殊竞技场累积奖励", True):
            if self.click_ocr(["特殊竞技场"], NikkeROI.ARENA_MODE_SELECT, wait_after=1.4):
                if self.click_ocr(["领取", "收取", "触碰领取"], NikkeROI.FULL_CENTER, wait_after=1.0):
                    self.log_info("已收取特殊竞技场累积积分奖励")
                    self.handle_common_popups()
                self.click_feature_or_ocr("nav_back_btn", ["返回"], NikkeROI.TOP_LEFT_BACK, wait_after=1.0)

        # 2. 新人竞技场免费次数挑战（严禁花珠宝买次数）
        if self.config.get("执行新人竞技场免费挑战", True):
            if self.click_ocr(["新人竞技场"], NikkeROI.ARENA_MODE_SELECT, wait_after=1.4):
                slot_idx = max(1, min(3, int(self.config.get("新人竞技场优先对手位(1-3)", 3)))) - 1
                max_free = int(self.config.get("新人竞技场最大免费次数", 5))
                slot_box = NikkeROI.ARENA_OPPONENT_SLOTS[slot_idx]

                for attempt in range(max_free):
                    # 校验仍有“免费”标识，防止耗钻购买挑战券
                    free_hits = self.ocr_in_roi(slot_box, match=["免费", "进入战斗"], name="arena_slot")
                    if not free_hits:
                        self.log_info("未检测到免费挑战按钮，结束新人竞技场")
                        break

                    self.click_box(free_hits[0])
                    self._wait_step(1.0)
                    if self.click_ocr(["进入战斗", "开始战斗"], NikkeROI.BATTLE_START_BTN, wait_after=1.8):
                        self.click_ocr(["点击画面继续", "点击继续"], NikkeROI.BATTLE_RESULT_AREA, wait_after=1.0)
                        self.handle_common_popups()
                        self.log_info(f"新人竞技场第 {attempt + 1}/{max_free} 场完成")

        self.back_to_lobby()
        return True
