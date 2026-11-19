"""启动游戏与登录奖励领取任务（对应 MaaNikke StartGame + LoginReward 流水线）。"""

from __future__ import annotations

from yes_nk.scene.NikkeScene import NikkeROI
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask


class AutoLoginTask(BaseNikkeTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = "启动登录与签到奖励"
        self.description = "检测国服客户端进入界面，处理“点击继续”、每日签到与版本公告弹窗直至稳定到达大厅。"
        self.default_config.update(
            {
                "最大等待进入大厅次数": 12,
                "清理每日签到与限时礼包弹窗": True,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def run(self) -> bool:
        self.log_info("开始执行：启动登录与签到奖励")
        max_rounds = int(self.config.get("最大等待进入大厅次数", 12))

        for idx in range(max_rounds):
            if self.in_lobby():
                self.log_info("已稳定进入国服主大厅")
                return True

            # 处理标题页“点击继续 / 进入游戏”
            if self.click_ocr(
                ["点击继续", "进入游戏", "开始游戏", "TOUCH TO CONTINUE"],
                NikkeROI.POPUP_BOTTOM_DISMISS,
                wait_after=1.5,
                name="login_touch_continue",
            ):
                self.log_info("已点击登录引导进入游戏")
                continue

            # 领取每日签到奖励弹窗
            if self.click_ocr(
                ["领取", "全部领取", "签到"],
                NikkeROI.POPUP_CENTER_DIALOG,
                wait_after=1.0,
                name="login_checkin_claim",
            ):
                self.log_info("已领取登录签到奖励")
                continue

            if self.config.get("清理每日签到与限时礼包弹窗", True) and self.handle_common_popups():
                continue

            self.log_info(f"等待加载主大厅 ({idx + 1}/{max_rounds})...")
            self._wait_step(1.2)

        return self.ensure_in_lobby()
