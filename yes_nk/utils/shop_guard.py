"""普通商店防误花钻石/珠宝安全护栏（纯逻辑层，可独立单测）。"""

from __future__ import annotations

from dataclasses import dataclass
import re


FREE_KEYWORDS = ("免费", "FREE", "0")
SOLD_OUT_KEYWORDS = ("已售罄", "售罄", "SOLD OUT", "已购买")
FORBIDDEN_CURRENCY_KEYWORDS = ("珠宝", "钻石", "付费", "GEM", "CHARGE")


@dataclass(frozen=True)
class ShopSlotObservation:
    slot_index: int
    price_text: str
    discount_text: str = ""
    has_diamond_icon: bool = False
    has_credit_icon: bool = False


@dataclass(frozen=True)
class ShopPurchaseDecision:
    should_buy: bool
    reason: str


def parse_discount_percent(discount_text: str) -> int:
    """从 OCR 文本解析折扣百分比，如 '-90%' / '90% OFF' -> 90。"""
    if not discount_text:
        return 0
    match = re.search(r"(\d{1,2})\s*%", discount_text)
    if not match:
        return 0
    return int(match.group(1))


def evaluate_shop_slot(
    slot: ShopSlotObservation,
    allow_credit_discount: bool = False,
    min_credit_discount_percent: int = 50,
) -> ShopPurchaseDecision:
    """严格判定某个商店格子是否允许自动购买。

    安全铁律：
    1. 已售罄 -> 禁止购买；
    2. 检测到钻石/珠宝图标或付费关键词 -> 绝对禁止购买；
    3. 价格明确命中“免费” -> 放行购买；
    4. 仅在明确开启信用点折扣采购、命中信用点图标、且折扣达到阈值时放行。
    """
    normalized_price = slot.price_text.strip().upper()
    normalized_discount = slot.discount_text.strip().upper()

    if any(k in normalized_price for k in SOLD_OUT_KEYWORDS):
        return ShopPurchaseDecision(False, "商品已售罄")

    if slot.has_diamond_icon or any(
        k in normalized_price for k in FORBIDDEN_CURRENCY_KEYWORDS
    ):
        return ShopPurchaseDecision(False, "安全拦截：检测到钻石/珠宝付费项")

    if normalized_price in ("免费", "FREE") or "免费" in normalized_price:
        return ShopPurchaseDecision(True, "命中免费商品")

    if allow_credit_discount and slot.has_credit_icon:
        discount = parse_discount_percent(normalized_discount)
        if discount >= min_credit_discount_percent:
            return ShopPurchaseDecision(
                True, f"命中信用点折扣商品 (-{discount}% >= -{min_credit_discount_percent}%)"
            )
        return ShopPurchaseDecision(
            False, f"信用点商品折扣不足 (-{discount}% < -{min_credit_discount_percent}%)"
        )

    return ShopPurchaseDecision(False, "未命中免费或允许的信用点折扣条件，保守跳过")
