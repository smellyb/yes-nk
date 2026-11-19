"""社交点招募日常任务（对应 MaaNikke SocialPointRecruit 流水线）。

严格安全护栏：必须确认当前卡池标题命中“社交点数招募 / 友情点招募”才允许点击招募，
绝对禁止在普通/限定珠宝池执行抽卡！
"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


def is_social_recruit_banner(banner_text: str) -> bool:
    """安全校验：仅当卡池文案明确指向社交点/友情点招募时返回 True。"""
    normalized = banner_text.strip()
    return ("社交" in normalized or "友情" in normalized) and "限定" not in normalized


class SocialRecruitTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "社交点招募（日常 1 抽）"
        self.description = "切换到社交点数招募卡池执行 1 次招募以完成每日任务，内置珠宝卡池防误抽护栏。"
        self.default_config.update(
            {
                "仅执行单抽 (10 社交点)": True,
                "切换卡池最大翻页次数": 6,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：社交点招募")
        if not self.ensure_in_lobby():
            return False

        opened = self.click_feature_or_ocr(
            "lobby_recruit_icon",
            ["队员招募", "招募"],
            NikkeROI.LOBBY_BOTTOM_NAV,
            wait_after=1.5,
        )
        if not opened:
            self.log_info("未定位到队员招募入口")
            return False

        self.nikke_scene.mark("recruit")
        max_pages = int(self.config.get("切换卡池最大翻页次数", 6))
        found_social = False

        for _ in range(max_pages):
            banner_hits = self.ocr_in_roi(NikkeROI.FULL_CENTER, name="recruit_banner_title")
            joined = " ".join(getattr(h, "name", str(h)) for h in banner_hits)
            if is_social_recruit_banner(joined):
                found_social = True
                break
            # 向右切换卡池
            self.click_feature_or_ocr(
                "recruit_next_banner_btn",
                [">", "下一"],
                NikkeROI.RECRUIT_BANNER_SWITCH,
                wait_after=0.7,
            )

        if not found_social:
            self.log_info("未确认处于社交点数招募卡池，为防止误花珠宝已安全退出")
            self.back_to_lobby()
            return False

        target_keywords = ["招募1次", "单次招募"] if self.config.get("仅执行单抽 (10 社交点)", True) else ["招募10次", "招募1次"]
        if self.click_ocr(target_keywords, NikkeROI.RECRUIT_PULL_AREA, wait_after=1.5, name="social_pull"):
            self.log_info("已触发社交点招募，跳过演出动画")
            self.click_ocr(["SKIP", "跳过"], NikkeROI.POPUP_TOP_RIGHT_CLOSE, wait_after=1.2)
            self.handle_common_popups()

        self.back_to_lobby()
        return True
