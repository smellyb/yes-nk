"""普通商店免费与安全折扣采购任务。

严格接入 shop_guard 安全护栏：任何命中钻石/珠宝图标或付费文案的货架均强制跳过，
仅购买明确命中“免费”的商品（及用户显式开启且达标的信用点折扣商品）。
"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask
from yes_nk.utils.shop_guard import ShopSlotObservation, evaluate_shop_slot


class ShopTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "道具商店每日采购"
        self.description = (
            "购买普通商店每日免费商品（支持免费刷新后二次扫货）及可选竞技场商店技能书，内置钻石防误买护栏。"
        )
        self.default_config.update(
            {
                "使用每日免费刷新": True,
                "购买高折扣信用点商品": False,
                "信用点最低折扣(%)": 50,
                "购买竞技场商店技能书": False,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def _scan_and_buy_current_shelf(self) -> int:
        bought = 0
        allow_credit = bool(self.config.get("购买高折扣信用点商品", False))
        min_discount = int(self.config.get("信用点最低折扣(%)", 50))

        for idx, slot_box in enumerate(NikkeROI.SHOP_SHELF_SLOTS):
            ocr_hits = self.ocr_in_roi(slot_box, name=f"shop_slot_{idx}")
            joined_text = " ".join(
                getattr(item, "name", str(item)) for item in ocr_hits
            )
            has_diamond = (
                self.find_feature_in_roi("shop_diamond_icon", box=slot_box) is not None
            )
            has_credit = (
                self.find_feature_in_roi("shop_credit_icon", box=slot_box) is not None
            )

            decision = evaluate_shop_slot(
                ShopSlotObservation(
                    slot_index=idx,
                    price_text=joined_text,
                    discount_text=joined_text,
                    has_diamond_icon=has_diamond,
                    has_credit_icon=has_credit,
                ),
                allow_credit_discount=allow_credit,
                min_credit_discount_percent=min_discount,
            )

            if not decision.should_buy:
                self.log_info(f"货架 #{idx + 1} 跳过：{decision.reason}")
                continue

            self.log_info(f"货架 #{idx + 1} 批准购买：{decision.reason}")
            x1, y1, x2, y2 = slot_box
            self.click_relative((x1 + x2) / 2, (y1 + y2) / 2)
            self._wait_step(0.8)

            if self.click_ocr(
                ["购买", "确认"],
                NikkeROI.POPUP_CENTER_DIALOG,
                wait_after=1.0,
                name="shop_buy_confirm",
            ):
                bought += 1
                self.handle_common_popups()

        return bought

    def _scan_arena_shop(self) -> int:
        """可选：切换至竞技场商店，使用竞技场兑换券购买技能手册（绝不点击钻石商品）。"""
        switched = self.click_feature_or_ocr(
            "shop_arena_tab",
            ["竞技场商店", "竞技场"],
            NikkeROI.SHOP_SIDE_TABS,
            wait_after=1.0,
        )
        if not switched:
            self.log_info("未检测到竞技场商店页签，跳过竞技场商店采购")
            return 0

        bought = 0
        for idx, slot_box in enumerate(NikkeROI.SHOP_SHELF_SLOTS):
            ocr_hits = self.ocr_in_roi(slot_box, name=f"arena_shop_slot_{idx}")
            joined = " ".join(getattr(item, "name", str(item)) for item in ocr_hits)
            has_diamond = (
                self.find_feature_in_roi("shop_diamond_icon", box=slot_box) is not None
            )
            if has_diamond or any(k in joined for k in ("珠宝", "钻石", "已售罄", "售罄")):
                continue
            if any(k in joined for k in ("技能", "爆裂", "手册", "元素")):
                x1, y1, x2, y2 = slot_box
                self.click_relative((x1 + x2) / 2, (y1 + y2) / 2)
                self._wait_step(0.8)
                if self.click_ocr(
                    ["购买", "确认"],
                    NikkeROI.POPUP_CENTER_DIALOG,
                    wait_after=0.9,
                    name="arena_shop_buy_confirm",
                ):
                    bought += 1
                    self.handle_common_popups()
        return bought

    def run(self) -> bool:
        self.log_info("开始执行：道具商店每日采购")
        if not self.ensure_in_lobby():
            self.log_error("无法回到大厅，跳过商店采购")
            return False

        opened = self.click_feature_or_ocr(
            "lobby_shop_icon",
            ["商店"],
            NikkeROI.LOBBY_RIGHT_SHORTCUTS,
            wait_after=1.5,
        )
        if not opened:
            self.log_info("未定位到商店入口")
            return False

        self.nikke_scene.mark("shop")
        total_bought = self._scan_and_buy_current_shelf()

        if self.config.get("使用每日免费刷新", True):
            if self.click_feature_or_ocr(
                "shop_refresh_btn",
                ["刷新"],
                NikkeROI.SHOP_REFRESH_BTN,
                wait_after=0.9,
            ):
                # 严防消耗钻石刷新：仅当弹窗明确出现“免费”时才确认刷新
                free_refresh = self.ocr_in_roi(
                    NikkeROI.POPUP_CENTER_DIALOG,
                    match=["免费"],
                    name="shop_free_refresh_check",
                )
                if free_refresh:
                    self.click_ocr(
                        ["确认", "刷新"],
                        NikkeROI.POPUP_CENTER_DIALOG,
                        wait_after=1.2,
                        name="shop_refresh_confirm",
                    )
                    self.log_info("已完成普通商店免费刷新，执行第二轮扫描")
                    total_bought += self._scan_and_buy_current_shelf()
                else:
                    self.log_info("今日免费刷新已用完，跳过付费刷新")
                    self.handle_common_popups()

        if self.config.get("购买竞技场商店技能书", False):
            total_bought += self._scan_arena_shop()

        self.log_info(f"道具商店采购结束，本次共购入 {total_bought} 项商品")
        self.back_to_lobby()
        return True
