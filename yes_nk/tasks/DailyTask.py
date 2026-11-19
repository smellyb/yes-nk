"""基础日常一条龙总控任务（仿 YES-BD2 的 DailyTask 聚合调度风格）。"""

from __future__ import annotations

from typing import Any

from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask
from yes_nk.tasks.DailyMissionTask import DailyMissionTask
from yes_nk.tasks.DispatchTask import DispatchTask
from yes_nk.tasks.FriendPointTask import FriendPointTask
from yes_nk.tasks.MailTask import MailTask
from yes_nk.tasks.OutpostDefenseTask import OutpostDefenseTask
from yes_nk.tasks.ShopTask import ShopTask


class DailyTask(BaseNikkeTask):
    """按用户勾选顺序依次调度国服《胜利女神：新的希望》基础日常子任务。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.name = "基础日常一条龙"
        self.description = (
            "一键串联执行：大厅初始化 -> 邮箱领取 -> 好友友情点 -> 前哨基地收菜/一举歼灭 -> "
            "公告栏派遣 -> 普通商店免费采购 -> 每日任务活跃奖励领取。"
        )
        self.default_config.update(
            {
                "邮箱一键领取": True,
                "好友友情点互赠": True,
                "前哨基地收菜与一举歼灭": True,
                "公告栏派遣收取与重派": True,
                "普通商店免费与折扣采购": True,
                "每日任务与活跃奖励领取": True,
            }
        )
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

        self._init_args = args
        self._init_kwargs = kwargs

    def _build_subtask(self, task_cls: type[BaseNikkeTask]) -> BaseNikkeTask:
        subtask = task_cls(*self._init_args, **self._init_kwargs)
        # 透传公共识别参数
        for shared_key in (
            "OCR 匹配阈值",
            "模板匹配阈值",
            "动作后基础等待(秒)",
            "返回大厅最大重试次数",
        ):
            if shared_key in self.config:
                subtask.config[shared_key] = self.config[shared_key]
        return subtask

    def run(self) -> dict[str, str]:
        self.log_info("========== 开始执行 YES-NK 基础日常一条龙 ==========")
        if not self.ensure_in_lobby():
            self.log_error("初始化未能确认大厅界面，请检查游戏是否已完成登录且保持 16:9 画面。")
            return {"init": "failed"}

        pipeline: list[tuple[str, type[BaseNikkeTask]]] = [
            ("邮箱一键领取", MailTask),
            ("好友友情点互赠", FriendPointTask),
            ("前哨基地收菜与一举歼灭", OutpostDefenseTask),
            ("公告栏派遣收取与重派", DispatchTask),
            ("普通商店免费与折扣采购", ShopTask),
            ("每日任务与活跃奖励领取", DailyMissionTask),
        ]

        summary: dict[str, str] = {}
        for config_key, task_cls in pipeline:
            if not self.config.get(config_key, True):
                summary[config_key] = "skipped"
                self.log_info(f"跳过未启用子任务：{config_key}")
                continue

            subtask = self._build_subtask(task_cls)
            try:
                ok = subtask.run()
                summary[config_key] = "ok" if ok else "incomplete"
            except Exception as exc:
                self.log_error(f"子任务 {config_key} 异常中断: {exc}", exception=exc)
                summary[config_key] = "error"
                self.back_to_lobby()

        self.log_info(f"========== 基础日常一条龙结束：{summary} ==========", notify=True)
        return summary
