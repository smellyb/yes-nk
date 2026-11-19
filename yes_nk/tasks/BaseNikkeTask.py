"""YES-NK 任务基类，完整对齐 YES-BD2 (ok-script) 的混合识别与状态机工作方式。

识别优先级（复刻 YES-BD2 实战经验）：
1. 局部 ROI 模板匹配（ok-script COCO 特征 `find_feature` / `wait_feature`）；
2. 局部 ROI OCR 文字识别（`box_of_screen` + `ocr`，抗动态 Live2D 背景与皮肤变化）；
3. 带重试与弹窗清理的状态机跳转（`ensure_in_lobby` / `handle_common_popups` / `back_to_lobby`）。
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional, Sequence

from yes_nk.scene.NikkeScene import NikkeROI, NikkeScene, NormalizedBox
from yes_nk.utils.window_1080p import evaluate_client_geometry

try:
    from ok import BaseTask as _OkBaseTask
    from ok import TriggerTask as _OkTriggerTask
except Exception:  # pragma: no cover - 非 Windows 或无 ok-script 环境下启用可测试基类

    class _OkBaseTask:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.name: str = self.__class__.__name__
            self.description: str = ""
            self.default_config: dict[str, Any] = {}
            self.config: dict[str, Any] = {}
            self.scene: Any = None

        def log_info(self, message: str, notify: bool = False) -> None:
            _ = (message, notify)

        def log_error(self, message: str, exception: Any = None, notify: bool = False) -> None:
            _ = (message, exception, notify)

        def sleep(self, seconds: float) -> None:
            _ = seconds

        def box_of_screen(self, x1: float, y1: float, x2: float, y2: float, name: str = "") -> Any:
            return (x1, y1, x2, y2, name)

        def ocr(self, *args: Any, **kwargs: Any) -> list[Any]:
            _ = (args, kwargs)
            return []

        def find_one(self, feature_name: str, *args: Any, **kwargs: Any) -> Any:
            _ = (feature_name, args, kwargs)
            return None

        def click(self, *args: Any, **kwargs: Any) -> None:
            _ = (args, kwargs)

        def click_box(self, box: Any, *args: Any, **kwargs: Any) -> None:
            _ = (box, args, kwargs)

        def click_relative(self, x: float, y: float, *args: Any, **kwargs: Any) -> None:
            _ = (x, y, args, kwargs)

        def send_key(self, key: str, *args: Any, **kwargs: Any) -> None:
            _ = (key, args, kwargs)

    class _OkTriggerTask(_OkBaseTask):  # type: ignore[no-redef]
        pass


class BaseNikkeTask(_OkBaseTask):
    """所有《胜利女神：新的希望》一次性日常任务的公共父类。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.nikke_scene: NikkeScene = NikkeScene()
        self.default_config.update(
            {
                "OCR 匹配阈值": 0.78,
                "模板匹配阈值": 0.82,
                "动作后基础等待(秒)": 0.8,
                "返回大厅最大重试次数": 8,
            }
        )
        # 确保单测或独立实例化时 config 具备默认值
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)

    def _wait_step(self, multiplier: float = 1.0) -> None:
        base = float(self.config.get("动作后基础等待(秒)", 0.8))
        self.sleep(max(0.1, base * multiplier))

    def roi(self, box: NormalizedBox, name: str = "") -> Any:
        x1, y1, x2, y2 = box
        return self.box_of_screen(x1, y1, x2, y2, name=name)

    def ocr_in_roi(
        self,
        box: NormalizedBox,
        match: Optional[str | re.Pattern[str] | Sequence[str]] = None,
        name: str = "",
    ) -> list[Any]:
        """在 16:9 归一化 ROI 内执行 OCR，缩小扫描范围提升帧率与准确率。"""
        threshold = float(self.config.get("OCR 匹配阈值", 0.78))
        target_box = self.roi(box, name=name)
        kwargs: dict[str, Any] = {"box": target_box, "threshold": threshold}
        if match is not None:
            kwargs["match"] = match
        return self.ocr(**kwargs) or []

    def find_feature_in_roi(
        self,
        feature_name: str,
        box: Optional[NormalizedBox] = None,
        threshold: Optional[float] = None,
    ) -> Any:
        """在指定归一化 ROI 中检索 COCO 特征模板。"""
        th = threshold if threshold is not None else float(self.config.get("模板匹配阈值", 0.82))
        kwargs: dict[str, Any] = {"threshold": th}
        if box is not None:
            kwargs["box"] = self.roi(box, name=feature_name)
        return self.find_one(feature_name, **kwargs)

    def click_ocr(
        self,
        keywords: str | Sequence[str],
        box: NormalizedBox,
        wait_after: float = 1.0,
        name: str = "",
    ) -> bool:
        """在局部 ROI 内按文字匹配并点击首个命中项。"""
        patterns = [keywords] if isinstance(keywords, str) else list(keywords)
        hits = self.ocr_in_roi(box, match=patterns, name=name)
        if not hits:
            return False
        self.click_box(hits[0])
        self._wait_step(wait_after)
        return True

    def click_feature_or_ocr(
        self,
        feature_name: str,
        ocr_keywords: str | Sequence[str],
        box: NormalizedBox,
        wait_after: float = 1.0,
    ) -> bool:
        """仿 YES-BD2 混合点击：优先匹配 COCO 图标特征，未命中时自动降级为局部 ROI OCR。"""
        feature_hit = self.find_feature_in_roi(feature_name, box=box)
        if feature_hit is not None:
            self.click_box(feature_hit)
            self._wait_step(wait_after)
            return True
        return self.click_ocr(ocr_keywords, box=box, wait_after=wait_after, name=feature_name)

    def in_lobby(self) -> bool:
        """通过底部固定菜单栏多关键词锚点判断是否处于游戏大厅。"""
        hits = self.ocr_in_roi(
            NikkeROI.LOBBY_BOTTOM_NAV,
            match=list(NikkeScene.LOBBY_ANCHOR_KEYWORDS),
            name="lobby_nav",
        )
        if len(hits) >= 2:
            self.nikke_scene.mark("lobby")
            return True
        if self.find_feature_in_roi("lobby_ark_icon", box=NikkeROI.LOBBY_RIGHT_SHORTCUTS):
            self.nikke_scene.mark("lobby")
            return True
        return False

    def handle_common_popups(self) -> bool:
        """清理国服高频登录公告、每日签到、奖励结算与限时礼包弹窗。"""
        # 1. 勾选“今日不再显示”后再关闭
        if self.click_feature_or_ocr(
            "popup_dont_show_today",
            ["今日不再显示", "今天不再显示"],
            NikkeROI.POPUP_CENTER_DIALOG,
            wait_after=0.4,
        ):
            self.log_info("已勾选弹窗“今日不再显示”")

        # 2. 匹配右上角关闭叉号或关闭文字
        if self.click_feature_or_ocr(
            "popup_close_x",
            ["关闭"],
            NikkeROI.POPUP_TOP_RIGHT_CLOSE,
            wait_after=0.7,
        ):
            self.nikke_scene.record_popup_dismissed()
            return True

        # 3. 匹配底部“点击继续 / 确认 / 领取”类通用结算遮罩
        if self.click_ocr(
            ["点击画面继续", "点击继续", "确认", "确定", "重新连接"],
            NikkeROI.POPUP_BOTTOM_DISMISS,
            wait_after=0.7,
            name="popup_dismiss",
        ):
            self.nikke_scene.record_popup_dismissed()
            return True

        return False

    def ensure_in_lobby(self) -> bool:
        """确保游戏稳定停留在国服主大厅界面，自动清理弹窗并逐级返回。"""
        max_attempts = int(self.config.get("返回大厅最大重试次数", 8))
        for attempt in range(max_attempts):
            if self.in_lobby():
                return True

            if self.handle_common_popups():
                continue

            # 尝试点击左上角“返回大厅”或“返回”按钮
            if self.click_feature_or_ocr(
                "nav_home_btn",
                ["大厅", "主界面"],
                NikkeROI.TOP_LEFT_BACK,
                wait_after=1.0,
            ):
                continue

            if self.click_feature_or_ocr(
                "nav_back_btn",
                ["返回"],
                NikkeROI.TOP_LEFT_BACK,
                wait_after=0.8,
            ):
                continue

            # 兜底：发送 ESC 或轻击底部安全空白处关闭无按钮奖励提示
            self.log_info(f"第 {attempt + 1}/{max_attempts} 次尝试回到大厅...")
            self.click_relative(0.50, 0.90)
            self._wait_step(0.8)

        return self.in_lobby()

    def back_to_lobby(self) -> bool:
        """语义别名：子任务结束后统一归位至大厅。"""
        return self.ensure_in_lobby()

    def verify_window_1080p_compatibility(
        self, client_width: int, client_height: int, dpi_scale_percent: int = 100
    ) -> bool:
        """在任务启动前记录 1080P/16:9 客户区校验结论。"""
        report = evaluate_client_geometry(client_width, client_height, dpi_scale_percent)
        if report.is_valid:
            self.log_info(f"窗口校验通过: {report.recommendation}")
            return True
        self.log_error(f"窗口校验异常: {report.recommendation}")
        return False

    def run_steps_with_recovery(self, steps: Iterable[tuple[str, Any]]) -> bool:
        """顺序执行子步骤并在异常时安全归位大厅。"""
        try:
            for step_name, fn in steps:
                self.log_info(f"[{self.name}] 执行步骤: {step_name}")
                fn()
            return True
        except Exception as exc:
            self.log_error(f"[{self.name}] 执行失败: {exc}", exception=exc)
            self.back_to_lobby()
            return False


class BaseNikkeTriggerTask(_OkTriggerTask):
    """后台触发守护任务基类（用于断线重连与突发弹窗拦截）。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.nikke_scene: NikkeScene = NikkeScene()
        self.default_config.update({"OCR 匹配阈值": 0.78})
        for k, v in self.default_config.items():
            self.config.setdefault(k, v)
