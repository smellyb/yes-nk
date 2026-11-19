"""方舟无限之塔（主塔与四大企业塔）每日推进任务（对应 MaaNikke TribeTower 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class TribeTowerTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "无限之塔（企业塔每日推进）"
        self.description = "扫描当日开放的企业无限之塔，自动进入最高层推进，支持战败 1 次即停以节省时间。"
        self.default_config.update(
            {
                "目标企业塔顺序": "极乐净土,米西利斯,泰特拉,朝圣者",
                "单塔最大尝试次数": 3,
                "战败 1 次即切换下一座塔": True,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：无限之塔（企业塔每日推进）")
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
            "ark_tribe_tower_entry",
            ["无限之塔"],
            NikkeROI.ARK_MODE_GRID,
            wait_after=1.5,
        ):
            self.back_to_lobby()
            return False

        self.nikke_scene.mark("tribe_tower")
        towers = [
            t.strip()
            for t in str(self.config.get("目标企业塔顺序", "极乐净土,米西利斯,泰特拉,朝圣者")).split(",")
            if t.strip()
        ]
        max_runs = int(self.config.get("单塔最大尝试次数", 3))

        for tower_name in towers:
            if not self.click_ocr([tower_name], NikkeROI.TOWER_LIST_AREA, wait_after=1.2):
                continue

            self.log_info(f"已进入企业塔：{tower_name}")
            for idx in range(max_runs):
                if not self.click_ocr(["进入战斗", "开始战斗"], NikkeROI.BATTLE_START_BTN, wait_after=2.0):
                    break

                defeat = self.ocr_in_roi(NikkeROI.BATTLE_RESULT_AREA, match=["失败", "FAILED"], name="tower_defeat")
                self.click_ocr(["下一关", "点击继续", "返回"], NikkeROI.BATTLE_RESULT_AREA, wait_after=1.2)
                self.handle_common_popups()

                if defeat and self.config.get("战败 1 次即切换下一座塔", True):
                    self.log_info(f"{tower_name} 战败，停止当前企业塔")
                    break
                self.log_info(f"{tower_name} 完成第 {idx + 1} 层挑战")

            self.click_feature_or_ocr("nav_back_btn", ["返回"], NikkeROI.TOP_LEFT_BACK, wait_after=1.0)

        self.back_to_lobby()
        return True
