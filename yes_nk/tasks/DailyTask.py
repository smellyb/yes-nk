"""全量日常一条龙总控任务（完整承接 Shinarin/MaaNikke 全部 21 条流水线）。"""

from __future__ import annotations

from typing import Any

from yes_nk.config import load_user_overrides
from yes_nk.tasks.AdviseGiftTask import AdviseGiftTask
from yes_nk.tasks.ArenaTask import ArenaTask
from yes_nk.tasks.AutoLoginTask import AutoLoginTask
from yes_nk.tasks.BaseNikkeTask import BaseNikkeTask
from yes_nk.tasks.CashShopFreeTask import CashShopFreeTask
from yes_nk.tasks.DailyMissionTask import DailyMissionTask
from yes_nk.tasks.DispatchTask import DispatchTask
from yes_nk.tasks.EquipmentUpgradeTask import EquipmentUpgradeTask
from yes_nk.tasks.EventStoryTask import EventStoryTask
from yes_nk.tasks.FriendPointTask import FriendPointTask
from yes_nk.tasks.InterceptionTask import InterceptionTask
from yes_nk.tasks.LiberationTask import LiberationTask
from yes_nk.tasks.MailTask import MailTask
from yes_nk.tasks.OutpostDefenseTask import OutpostDefenseTask
from yes_nk.tasks.PassRewardTask import PassRewardTask
from yes_nk.tasks.RaidAndCoopTasks import (
    CoopOperationTask,
    SoloRaidTask,
    UnionRaidTask,
)
from yes_nk.tasks.ShopTask import ShopTask
from yes_nk.tasks.SimulationRoomTask import SimulationRoomTask
from yes_nk.tasks.SocialRecruitTask import SocialRecruitTask
from yes_nk.tasks.TribeTowerTask import TribeTowerTask


# (配置开关名, 所属分类, 默认是否启用, 任务类)
ALL_PIPELINE_SPECS: list[tuple[str, str, bool, type[BaseNikkeTask]]] = [
    ("启动登录与签到奖励", "启动与奖励", True, AutoLoginTask),
    ("邮箱一键领取", "启动与奖励", True, MailTask),
    ("好友友情点互赠", "日常养成", True, FriendPointTask),
    ("前哨基地收菜与一举歼灭", "日常养成", True, OutpostDefenseTask),
    ("公告栏派遣收取与重派", "日常养成", True, DispatchTask),
    ("付费商店免费礼包领取", "商店相关", True, CashShopFreeTask),
    ("道具商店每日采购", "商店相关", True, ShopTask),
    ("社交点招募（日常 1 抽）", "日常养成", True, SocialRecruitTask),
    ("妮姬咨询与好感送礼", "日常养成", True, AdviseGiftTask),
    ("装备升级（日常 1 次）", "日常养成", False, EquipmentUpgradeTask),
    ("更生馆每日进度领取", "日常养成", False, LiberationTask),
    ("拦截战挑战与快速扫荡", "副本挑战", True, InterceptionTask),
    ("模拟室每日快速通关", "副本挑战", True, SimulationRoomTask),
    ("竞技场（新人 + 特殊 + 冠军）", "副本挑战", True, ArenaTask),
    ("无限之塔（企业塔每日推进）", "副本挑战", False, TribeTowerTask),
    ("协同作战自动匹配", "联盟与活动", False, CoopOperationTask),
    ("单人突击每日快速战斗", "联盟与活动", False, SoloRaidTask),
    ("联盟突袭 (Beta)", "联盟与活动", False, UnionRaidTask),
    ("大型活动刷取与签到", "联盟与活动", False, EventStoryTask),
    ("每日任务与活跃奖励领取", "启动与奖励", True, DailyMissionTask),
    ("通行证 (PASS) 奖励领取", "启动与奖励", True, PassRewardTask),
]


class DailyTask(BaseNikkeTask):
    """按用户勾选顺序依次调度国服《胜利女神：新的希望》全部 21 条 MaaNikke 转换流水线。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.name = "全量日常一条龙"
        self.description = (
            "一键串联执行从 Shinarin/MaaNikke 完整转换的 21 条国服自动化流水线："
            "启动签到、邮箱、好友、前哨基地、派遣、付费免费礼包、道具商店、社交招募、"
            "咨询送礼、装备升级、更生馆、拦截战、模拟室、竞技场、无限之塔、协同/单突/盟突、大型活动、每日任务与 PASS。"
        )
        for key, _category, default_enabled, _cls in ALL_PIPELINE_SPECS:
            self.default_config[key] = default_enabled

        # 自动同步桌面客户端 / Web 工作台保存的 daily_toggles 覆盖项
        overrides = load_user_overrides()
        saved_toggles = overrides.get("daily_toggles", {})
        for k, v in self.default_config.items():
            if isinstance(saved_toggles, dict) and k in saved_toggles:
                self.config.setdefault(k, bool(saved_toggles[k]))
            else:
                self.config.setdefault(k, v)

        self._init_args = args
        self._init_kwargs = kwargs

    def _build_subtask(self, task_cls: type[BaseNikkeTask]) -> BaseNikkeTask:
        subtask = task_cls(*self._init_args, **self._init_kwargs)
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
        self.log_info("========== 开始执行 YES-NK 全量日常一条龙（21 条流水线） ==========")
        summary: dict[str, str] = {}

        # 若启用了启动登录任务，先于 ensure_in_lobby 运行以通过标题页与登录公告
        first_key, _, _, first_cls = ALL_PIPELINE_SPECS[0]
        if self.config.get(first_key, True):
            login_task = self._build_subtask(first_cls)
            try:
                ok = login_task.run()
                summary[first_key] = "ok" if ok else "incomplete"
            except Exception as exc:
                self.log_error(f"子任务 {first_key} 异常中断: {exc}", exception=exc)
                summary[first_key] = "error"
        else:
            summary[first_key] = "skipped"

        if not self.ensure_in_lobby():
            self.log_error("初始化未能确认大厅界面，请检查游戏是否已完成登录且保持 16:9 画面。")
            summary["init"] = "failed"
            return summary

        for config_key, _category, default_enabled, task_cls in ALL_PIPELINE_SPECS[1:]:
            if not self.config.get(config_key, default_enabled):
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

        self.log_info(f"========== 全量日常一条龙结束：{summary} ==========", notify=True)
        return summary
