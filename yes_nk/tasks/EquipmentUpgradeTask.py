"""装备升级日常任务（对应 MaaNikke EquipmentUpgrade 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class EquipmentUpgradeTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "装备升级（日常 1 次）"
        self.description = "进入首位已养成妮姬的装备详情页，使用最低阶强化素材升级 1 次装备以完成每日活跃任务。"

    def run(self) -> bool:
        self.log_info("开始执行：装备升级（日常 1 次）")
        if not self.ensure_in_lobby():
            return False

        if not self.click_feature_or_ocr(
            "lobby_nikke_nav",
            ["妮姬"],
            NikkeROI.LOBBY_BOTTOM_NAV,
            wait_after=1.4,
        ):
            return False

        self.nikke_scene.mark("equipment_upgrade")
        # 点击列表中首位妮姬卡片进入详情
        self.click_relative(0.24, 0.34)
        self._wait_step(1.2)

        # 点击左侧第一件装备槽位
        if not self.click_feature_or_ocr(
            "equip_slot_head",
            ["头盔", "胸甲", "手套", "靴子", "强化"],
            NikkeROI.EQUIP_SLOT_AREA,
            wait_after=1.0,
        ):
            self.click_relative(0.16, 0.44)
            self._wait_step(1.0)

        if self.click_ocr(["强化", "升级"], NikkeROI.EQUIP_UPGRADE_ACTIONS, wait_after=1.0):
            # 仅勾选单个低阶素材（自动选择/单个强化模组）并点击强化
            self.click_ocr(["自动选择", "模组"], NikkeROI.EQUIP_UPGRADE_ACTIONS, wait_after=0.6)
            if self.click_ocr(["强化", "升级"], NikkeROI.EQUIP_UPGRADE_ACTIONS, wait_after=1.2):
                self.log_info("已完成 1 次日常装备升级")
                self.handle_common_popups()

        self.back_to_lobby()
        return True
