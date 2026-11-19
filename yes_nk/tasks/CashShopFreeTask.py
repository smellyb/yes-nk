"""付费商店每日/每周/每月免费奖励领取任务（对应 MaaNikke CashShop 流水线）。

严格安全护栏：仅点击明确 OCR 命中“免费”的礼包项，凡包含人民币符号（￥/¥/元/购买）
的项目绝对禁止点击，杜绝误触发充值弹窗。
"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask

FORBIDDEN_PAY_TOKENS = ("￥", "¥", "元", "RMB", "$", "USD", "珠宝", "钻石", "GEM", "DIAMOND", "售罄", "已购买")


def is_safe_free_cash_shop_text(text: str) -> bool:
    """纯函数校验：付费商店目标文本必须命中“免费”且不包含任何法币价格、珠宝或售罄字样。"""
    cleaned = text.strip().upper()
    if any(tok in cleaned for tok in FORBIDDEN_PAY_TOKENS):
        return False
    return "免费" in cleaned or cleaned == "FREE"


class CashShopFreeTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "付费商店免费礼包领取"
        self.description = "进入付费商店依次检查每日、每周与每月页签，仅安全领取明确标注“免费”的珠宝礼包。"
        self.default_config.update(
            {
                "检查每日免费礼包": True,
                "检查每周免费礼包": True,
                "检查每月免费礼包": True,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def _claim_free_in_current_tab(self, tab_label: str) -> int:
        claimed = 0
        hits = self.ocr_in_roi(
            NikkeROI.CASH_SHOP_FREE_GRID,
            match=["免费", "FREE"],
            name=f"cash_shop_{tab_label}",
        )
        for hit in hits:
            text = getattr(hit, "name", str(hit))
            if not is_safe_free_cash_shop_text(text):
                self.log_info(f"安全拦截付费项：{text}")
                continue
            self.click_box(hit)
            self._wait_step(0.9)
            self.handle_common_popups()
            claimed += 1
        return claimed

    def run(self) -> bool:
        self.log_info("开始执行：付费商店免费礼包领取")
        if not self.ensure_in_lobby():
            return False

        opened = self.click_feature_or_ocr(
            "lobby_cash_shop_icon",
            ["付费商店", "商城"],
            NikkeROI.LOBBY_RIGHT_SHORTCUTS,
            wait_after=1.5,
        )
        if not opened:
            self.log_info("未定位到付费商店入口")
            return False

        self.nikke_scene.mark("cash_shop")
        tabs: list[tuple[str, str]] = []
        if self.config.get("检查每日免费礼包", True):
            tabs.append(("每日", "每日"))
        if self.config.get("检查每周免费礼包", True):
            tabs.append(("每周", "每周"))
        if self.config.get("检查每月免费礼包", True):
            tabs.append(("每月", "每月"))

        total = 0
        for tab_name, keyword in tabs:
            if self.click_ocr([keyword, f"{keyword}礼包"], NikkeROI.CASH_SHOP_TOP_TABS, wait_after=0.9):
                count = self._claim_free_in_current_tab(tab_name)
                if count > 0:
                    self.log_info(f"已在付费商店[{tab_name}]领取 {count} 个免费礼包")
                total += count

        self.log_info(f"付费商店免费礼包检查完成，共领取 {total} 项")
        self.back_to_lobby()
        return True
