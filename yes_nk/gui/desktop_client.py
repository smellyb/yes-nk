"""YES-NK 原生 Windows 桌面客户端（完整对齐 YES-BD2 `淡紫 / 深色` oink-ui 界面设计）。

完全复刻 YES-BD2 视觉与交互架构：
1. 左侧浮动圆角侧边栏（#EEECF6 / #2B2A37）：品牌头 + 圆形图标胶囊导航 + 右侧进度徽章 + 侧边栏「淡紫 / 深色」主题切换 + 底部游戏连接状态卡；
2. 首页（今天）：118px 圆形进度 Ring + 「今日日常」主卡（一键完成日常 / 在桌面分身跑 / 打开就自动跑日常）+ 3 列统计卡 + 今日任务 & 本周与活动任务 BoardTile 瓷砖网格；
3. 今日报表：按游戏日（05:00 刷新）展示执行记录；
4. 任务设定：Master-Detail 左右分栏卡片（左 312px 一键运行顺序清单 + 右任务详情与预设）；
5. 桌面分身：完整复刻 YES-BD2 CloneGuidePage（这台电脑 6 项自动检查 + 一键设定/修复 + 3 步圆形编号引导卡 + 折叠排障 + 1080P 校准）；
6. 素材导入 / 运行日志 / 设置（HubRow 分组行卡片）。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
import sys

from yes_nk import __version__
from yes_nk.config import PROJECT_ROOT, RESOURCE_ROOT
from yes_nk.gui.controller import (
    BASIC_DAILY_KEYS,
    DEFAULT_DAILY_TOGGLES,
    DesktopClientController,
    get_grouped_pipelines,
)
from yes_nk.gui.theme import build_shell_qss, get_tokens
from yes_nk.utils import desktop_clone as clone
from yes_nk.utils.desktop_clone import (
    BAD,
    CLONE_TROUBLESHOOT_QA,
    OK,
    WARN,
)
from yes_nk.utils.window_1080p import (
    enable_per_monitor_dpi_awareness,
    evaluate_client_geometry,
)

WEEKLY_OR_EVENT_CATEGORIES = {"联盟与活动"}
WEEKDAY_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def launch_desktop_client() -> int:
    """启动与 YES-BD2 同款视觉架构的 PySide6 原生 Windows 桌面客户端。"""
    enable_per_monitor_dpi_awareness()

    try:
        from PySide6.QtCore import QRectF, QSize, Qt, QTimer
        from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
        from PySide6.QtWidgets import (
            QAbstractButton,
            QApplication,
            QButtonGroup,
            QCheckBox,
            QComboBox,
            QFileDialog,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QScrollArea,
            QSizePolicy,
            QStackedWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print(
            "[YES-NK] 未检测到 PySide6，请先在 Windows 下安装依赖：\n"
            "  pip install -r requirements.txt\n"
            "  python desktop_launcher.py"
        )
        return 1

    theme_state = {"mode": "light"}

    def tk(name: str) -> str:
        return get_tokens(theme_state["mode"])[name]

    def qc(name: str, alpha: float = 1.0) -> QColor:
        c = QColor(tk(name))
        c.setAlphaF(max(0.0, min(1.0, alpha)))
        return c

    def make_label(text: str, role: str | None = None, wrap: bool = False) -> QLabel:
        lbl = QLabel(text)
        if role:
            lbl.setProperty("role", role)
        lbl.setWordWrap(wrap)
        return lbl

    def make_button(
        text: str,
        kind: str = "secondary",
        size: str | None = None,
        on_click=None,
    ) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("kind", kind)
        if size:
            btn.setProperty("size", size)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if on_click is not None:
            btn.clicked.connect(on_click)
        return btn

    def make_card() -> QFrame:
        card = QFrame()
        card.setProperty("card", True)
        return card

    def make_sep() -> QFrame:
        sep = QFrame()
        sep.setProperty("sep", True)
        return sep

    class ProgressRing(QWidget):
        """复刻 YES-BD2 首页 118px 淡紫环形进度指示器。"""

        def __init__(self, diameter: int = 118, stroke: int = 11, parent=None) -> None:
            super().__init__(parent)
            self._diameter = diameter
            self._stroke = stroke
            self._done = 0
            self._total = 1
            self.setFixedSize(diameter, diameter)

        def set_progress(self, done: int, total: int) -> None:
            self._done = max(0, done)
            self._total = max(1, total)
            self.update()

        def paintEvent(self, _event) -> None:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pad = self._stroke / 2 + 2
            rect = QRectF(pad, pad, self.width() - pad * 2, self.height() - pad * 2)

            track_pen = QPen(qc("well"), self._stroke)
            track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(track_pen)
            p.drawArc(rect, 0, 360 * 16)

            ratio = min(1.0, self._done / max(1, self._total))
            if ratio > 0:
                arc_pen = QPen(qc("primary"), self._stroke)
                arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(arc_pen)
                p.drawArc(rect, 90 * 16, -round(ratio * 360 * 16))

            big_font = QFont(self.font())
            big_font.setPixelSize(24)
            big_font.setBold(True)
            p.setFont(big_font)
            p.setPen(qc("ink"))
            p.drawText(
                QRectF(0, 0, self.width(), self.height() * 0.62),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                str(self._done),
            )

            sub_font = QFont(self.font())
            sub_font.setPixelSize(12)
            p.setFont(sub_font)
            p.setPen(qc("ink3"))
            p.drawText(
                QRectF(0, self.height() * 0.56, self.width(), self.height() * 0.34),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                f"/ {self._total} 项",
            )

    class NavPillItem(QAbstractButton):
        """复刻 YES-BD2 左侧导航行：圆形图标底 + 选中白色胶囊 + 填充紫圆 + 右侧计数徽章。"""

        def __init__(self, key: str, label: str, glyph: str, parent=None) -> None:
            super().__init__(parent)
            self.key = key
            self._label = label
            self._glyph = glyph
            self._selected = False
            self._hovered = False
            self._badge = ""
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFixedHeight(38)

        def set_selected(self, selected: bool) -> None:
            self._selected = selected
            self.update()

        def set_badge(self, text: str) -> None:
            self._badge = text
            self.update()

        def enterEvent(self, event) -> None:
            self._hovered = True
            self.update()
            super().enterEvent(event)

        def leaveEvent(self, event) -> None:
            self._hovered = False
            self.update()
            super().leaveEvent(event)

        def paintEvent(self, _event) -> None:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
            radius = rect.height() / 2

            if self._selected:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qc("nav_on"))
                p.drawRoundedRect(rect, radius, radius)
            elif self._hovered:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qc("ink", 0.05))
                p.drawRoundedRect(rect, radius, radius)

            circle = QRectF(6, (self.height() - 26) / 2, 26, 26)
            if self._selected:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qc("nav_on_circle"))
                p.drawEllipse(circle)
                glyph_color = qc("nav_on_icon")
            else:
                p.setPen(QPen(qc("ring"), 1.2))
                p.setBrush(qc("card"))
                p.drawEllipse(circle)
                glyph_color = qc("nav_icon")

            g_font = QFont(self.font())
            g_font.setPixelSize(12)
            g_font.setBold(True)
            p.setFont(g_font)
            p.setPen(glyph_color)
            p.drawText(circle, Qt.AlignmentFlag.AlignCenter, self._glyph)

            t_font = QFont(self.font())
            t_font.setPixelSize(13)
            p.setFont(t_font)
            p.setPen(qc("nav_on_ink") if self._selected else qc("ink"))
            p.drawText(
                QRectF(40, 0, self.width() - 92, self.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._label,
            )

            if self._badge:
                b_font = QFont(self.font())
                b_font.setPixelSize(11)
                p.setFont(b_font)
                bw = max(28, p.fontMetrics().horizontalAdvance(self._badge) + 12)
                brect = QRectF(self.width() - bw - 8, (self.height() - 20) / 2, bw, 20)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qc("badge_on" if self._selected else "badge"))
                p.drawRoundedRect(brect, 10, 10)
                p.setPen(qc("badge_on_ink" if self._selected else "badge_ink"))
                p.drawText(brect, Qt.AlignmentFlag.AlignCenter, self._badge)

    class StepCircle(QLabel):
        """复刻 YES-BD2 桌面分身页 1 / 2 / 3 圆形步骤号。"""

        def __init__(self, num: int, parent=None) -> None:
            super().__init__(str(num), parent)
            self.setFixedSize(26, 26)
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def refresh_theme(self) -> None:
            self.setStyleSheet(
                f"background:{tk('accent_soft')}; color:{tk('primary')};"
                "border-radius:13px; font-weight:700; font-size:12px;"
            )

    class CollapsibleQA(QWidget):
        """复刻 YES-BD2 CloneGuidePage 可折叠常见问题排障项。"""

        def __init__(
            self, question: str, steps: tuple[str, ...], show_folder_btn: bool, on_open_folder
        ) -> None:
            super().__init__()
            col = QVBoxLayout(self)
            col.setContentsMargins(0, 2, 0, 2)
            col.setSpacing(4)

            self.toggle_btn = QPushButton(f"▸  {question}")
            self.toggle_btn.setProperty("kind", "flat")
            self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle_btn.setStyleSheet("text-align:left; font-size:14px;")
            self.toggle_btn.clicked.connect(self._toggle)
            col.addWidget(self.toggle_btn)

            self.body = QFrame()
            self.body.setProperty("inset", True)
            body_layout = QVBoxLayout(self.body)
            body_layout.setContentsMargins(16, 10, 14, 10)
            body_layout.setSpacing(4)
            for idx, step in enumerate(steps, 1):
                body_layout.addWidget(make_label(f"{idx}. {step}", "sub", wrap=True))
            if show_folder_btn:
                btn = make_button("打开分身文件夹", "secondary", "sm", on_open_folder)
                body_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
            self.body.hide()
            col.addWidget(self.body)
            self._question = question

        def _toggle(self) -> None:
            shown = not self.body.isVisible()
            self.body.setVisible(shown)
            self.toggle_btn.setText(("▾  " if shown else "▸  ") + self._question)

    class YesNkDesktopWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.controller = DesktopClientController()
            theme_state["mode"] = self.controller.state.theme_mode
            self.setWindowTitle(f"YES-NK v{__version__} — 胜利女神：新的希望")
            self.resize(1120, 740)
            self.setMinimumSize(940, 640)

            icon_path = RESOURCE_ROOT / "assets" / "icon.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))

            self.nav_items: dict[str, NavPillItem] = {}
            self.page_map: dict[str, int] = {}
            self.tile_checkboxes: dict[str, QCheckBox] = {}
            self.task_row_buttons: dict[str, QPushButton] = {}
            self.step_circles: list[StepCircle] = []
            self.selected_task_key: str = next(iter(DEFAULT_DAILY_TOGGLES))
            self.run_records: list[tuple[str, str, str]] = []
            self._setup_poll_ticks = 0
            self._setup_poll_timer = QTimer(self)
            self._setup_poll_timer.setInterval(1500)
            self._setup_poll_timer.timeout.connect(self._poll_clone_setup_status)

            self.log_box = QTextEdit()
            self.log_box.setReadOnly(True)

            self._build_ui()
            self._apply_theme(theme_state["mode"], save=False)
            self._refresh_home_metrics()
            self._refresh_clone_checks()
            self._append_log(
                "YES-NK 桌面客户端已就绪（对齐 YES-BD2 淡紫/深色界面与 Windows 子会话桌面分身）。"
            )

        def _append_log(self, msg: str) -> None:
            stamp = datetime.now().strftime("%H:%M:%S")
            self.log_box.append(f"[{stamp}] {msg}")

        def _build_ui(self) -> None:
            root = QWidget()
            root.setObjectName("ShellRoot")
            root_layout = QHBoxLayout(root)
            root_layout.setContentsMargins(10, 10, 10, 10)
            root_layout.setSpacing(12)

            # 左侧浮动圆角侧边栏（完全对齐 YES-BD2 Sidebar）
            sidebar = QFrame()
            sidebar.setObjectName("ShellSidebar")
            sidebar.setFixedWidth(212)
            sb_layout = QVBoxLayout(sidebar)
            sb_layout.setContentsMargins(12, 16, 12, 12)
            sb_layout.setSpacing(4)

            brand_row = QHBoxLayout()
            brand_row.setContentsMargins(6, 0, 4, 8)
            brand_row.setSpacing(10)
            logo_lbl = QLabel()
            logo_lbl.setFixedSize(32, 32)
            icon_path = RESOURCE_ROOT / "assets" / "icon.png"
            if icon_path.exists():
                logo_lbl.setPixmap(
                    QPixmap(str(icon_path)).scaled(
                        32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                    )
                )
            else:
                logo_lbl.setText("NK")
                logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_lbl.setStyleSheet(
                    f"background:{tk('primary')}; color:#FFFFFF; border-radius:10px; font-weight:700;"
                )
            brand_row.addWidget(logo_lbl)
            brand_txt = QVBoxLayout()
            brand_txt.setContentsMargins(0, 0, 0, 0)
            brand_txt.setSpacing(0)
            brand_txt.addWidget(make_label("YES-NK", "h3"))
            brand_txt.addWidget(make_label("NIKKE 自动日常", "muted"))
            brand_row.addLayout(brand_txt, 1)
            sb_layout.addLayout(brand_row)

            top_nav = (
                ("home", "首页", "首"),
                ("report", "今日报表", "报"),
                ("tasks", "任务设定", "任"),
            )
            bottom_nav = (
                ("clone", "桌面分身", "分"),
                ("maa", "素材导入", "素"),
                ("logs", "运行日志", "志"),
                ("settings", "设置", "设"),
            )

            for key, label, glyph in top_nav:
                item = NavPillItem(key, label, glyph)
                item.clicked.connect(lambda _c=False, k=key: self._navigate(k))
                self.nav_items[key] = item
                sb_layout.addWidget(item)

            sb_layout.addStretch(1)

            for key, label, glyph in bottom_nav:
                item = NavPillItem(key, label, glyph)
                item.clicked.connect(lambda _c=False, k=key: self._navigate(k))
                self.nav_items[key] = item
                sb_layout.addWidget(item)

            sb_layout.addSpacing(8)

            # 侧边栏「淡紫 / 深色」主题分段切换（复刻 YES-BD2）
            seg_wrap = QFrame()
            seg_wrap.setProperty("segmented", True)
            seg_row = QHBoxLayout(seg_wrap)
            seg_row.setContentsMargins(3, 3, 3, 3)
            seg_row.setSpacing(2)
            self.theme_group = QButtonGroup(self)
            self.btn_theme_light = QPushButton("淡紫")
            self.btn_theme_light.setProperty("seg", True)
            self.btn_theme_light.setCheckable(True)
            self.btn_theme_light.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_theme_dark = QPushButton("深色")
            self.btn_theme_dark.setProperty("seg", True)
            self.btn_theme_dark.setCheckable(True)
            self.btn_theme_dark.setCursor(Qt.CursorShape.PointingHandCursor)
            self.theme_group.addButton(self.btn_theme_light)
            self.theme_group.addButton(self.btn_theme_dark)
            self.btn_theme_light.clicked.connect(lambda: self._apply_theme("light", save=True))
            self.btn_theme_dark.clicked.connect(lambda: self._apply_theme("dark", save=True))
            seg_row.addWidget(self.btn_theme_light, 1)
            seg_row.addWidget(self.btn_theme_dark, 1)
            sb_layout.addWidget(seg_wrap)

            sb_layout.addSpacing(8)

            # 底部游戏连接状态卡（复刻 YES-BD2 _StatusFooter）
            footer = QFrame()
            footer.setObjectName("StatusFooter")
            f_col = QVBoxLayout(footer)
            f_col.setContentsMargins(12, 10, 12, 10)
            f_col.setSpacing(2)
            self.footer_headline = make_label("未连接游戏", "h3")
            self.footer_line1 = make_label("开始时会自动连接 nikke.exe", "muted")
            self.footer_line2 = make_label(f"目标 {self.controller.state.resolution}", "muted")
            f_col.addWidget(self.footer_headline)
            f_col.addWidget(self.footer_line1)
            f_col.addWidget(self.footer_line2)
            sb_layout.addWidget(footer)

            root_layout.addWidget(sidebar)

            # 右侧页面容器
            self.pages = QStackedWidget()
            page_builders = (
                ("home", self._build_home_page()),
                ("report", self._build_report_page()),
                ("tasks", self._build_tasks_page()),
                ("clone", self._build_desktop_clone_page()),
                ("maa", self._build_maa_import_page()),
                ("logs", self._build_log_page()),
                ("settings", self._build_settings_page()),
            )
            for idx, (key, widget) in enumerate(page_builders):
                self.page_map[key] = idx
                self.pages.addWidget(widget)
            root_layout.addWidget(self.pages, 1)

            self.setCentralWidget(root)
            self._navigate("home")

        def _wrap_scroll_page(self, title: str, sub: str, action_widgets=None):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view = QWidget()
            body = QVBoxLayout(view)
            body.setContentsMargins(18, 12, 22, 24)
            body.setSpacing(16)

            header = QHBoxLayout()
            header.setSpacing(12)
            titles = QVBoxLayout()
            titles.setContentsMargins(0, 0, 0, 0)
            titles.setSpacing(2)
            t_lbl = make_label(title, "h1")
            s_lbl = make_label(sub, "sub")
            titles.addWidget(t_lbl)
            titles.addWidget(s_lbl)
            header.addLayout(titles, 1)
            if action_widgets:
                for w in action_widgets:
                    header.addWidget(w)
            body.addLayout(header)
            scroll.setWidget(view)
            return scroll, body, t_lbl, s_lbl

        def _build_home_page(self) -> QWidget:
            now = datetime.now()
            today_str = f"{now.month}月{now.day}日 {WEEKDAY_CN[now.weekday()]} · 下次刷新 明天 05:00"
            scroll, body, _t, _s = self._wrap_scroll_page("今天", today_str)

            # 1. Hero Card（Ring + 今日日常 + 一键完成日常 / 在桌面分身跑 + 自动运行勾选项）
            hero = make_card()
            hero_row = QHBoxLayout(hero)
            hero_row.setContentsMargins(24, 20, 24, 20)
            hero_row.setSpacing(24)

            self.home_ring = ProgressRing(118, 11)
            hero_row.addWidget(self.home_ring)

            mid = QVBoxLayout()
            mid.setSpacing(4)
            mid.addStretch(1)
            mid.addWidget(make_label("今日日常", "eyebrow"))
            self.hero_title = make_label("还剩 16 项", "huge")
            self.hero_sub = make_label("已接入全部 22 条 MaaNikke 转换流水线与 40 项 COCO 模板", "sub", wrap=True)
            mid.addWidget(self.hero_title)
            mid.addWidget(self.hero_sub)
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 8, 0, 0)
            btn_row.addWidget(make_button("看今日报表", "secondary", on_click=lambda: self._navigate("report")))
            btn_row.addStretch(1)
            mid.addLayout(btn_row)
            mid.addStretch(1)
            hero_row.addLayout(mid, 1)

            right = QVBoxLayout()
            right.setSpacing(8)
            right.addStretch(1)
            btn_start_all = make_button(
                "一键完成日常", "primary", "lg", on_click=lambda: self._on_launch_direct_ok(debug=False)
            )
            btn_start_clone = make_button(
                "在桌面分身跑", "secondary", on_click=lambda: self._on_run_in_clone(launch_tool=True, debug=False)
            )
            right.addWidget(btn_start_all)
            right.addWidget(btn_start_clone)

            self.cb_autorun = QCheckBox("打开就自动跑日常")
            self.cb_autorun.setChecked(self.controller.state.autorun_enabled)
            self.cb_autorun_clone = QCheckBox("在桌面分身跑")
            self.cb_autorun_clone.setChecked(self.controller.state.autorun_in_clone)
            self.cb_autorun_clone.setEnabled(self.controller.state.autorun_enabled)
            self.cb_autorun.toggled.connect(self._on_autorun_changed)
            self.cb_autorun_clone.toggled.connect(self._on_autorun_changed)
            right.addWidget(self.cb_autorun)
            right.addWidget(self.cb_autorun_clone)
            right.addStretch(1)
            hero_row.addLayout(right)
            body.addWidget(hero)

            # 2. 3-Column Stat Row（今日报表 / 桌面分身 / 1080P 窗口）
            stat_row = QHBoxLayout()
            stat_row.setSpacing(12)

            self.stat_report_val = make_label("0", "big")
            self.stat_report_foot = make_label("今天还没跑，跑完会记录在这里", "muted", wrap=True)
            stat_row.addWidget(
                self._make_stat_card("今日报表", self.stat_report_val, self.stat_report_foot, lambda: self._navigate("report")),
                1,
            )

            self.stat_clone_val = make_label("子会话", "big")
            self.stat_clone_foot = make_label("1920×1080 独立窗口 · 点这里检查与设定", "muted", wrap=True)
            stat_row.addWidget(
                self._make_stat_card("桌面分身", self.stat_clone_val, self.stat_clone_foot, lambda: self._navigate("clone")),
                1,
            )

            self.stat_res_val = make_label(self.controller.state.resolution, "big")
            self.stat_res_foot = make_label("16:9 客户区校验 · 支持 1080P 屏幕", "muted", wrap=True)
            stat_row.addWidget(
                self._make_stat_card("游戏窗口", self.stat_res_val, self.stat_res_foot, lambda: self._navigate("clone")),
                1,
            )
            body.addLayout(stat_row)

            # 3. 今日任务 BoardTile 瓷砖网格
            daily_head = QHBoxLayout()
            daily_head.addWidget(make_label("今日任务", "h2"))
            daily_head.addStretch(1)
            daily_head.addWidget(make_label("勾选即加入一键日常，点击卡片进任务设定", "muted"))
            body.addLayout(daily_head)

            daily_grid = QGridLayout()
            daily_grid.setSpacing(10)
            weekly_grid = QGridLayout()
            weekly_grid.setSpacing(10)

            toggles = self.controller.state.daily_toggles or DEFAULT_DAILY_TOGGLES
            grouped = get_grouped_pipelines()
            d_idx = 0
            w_idx = 0
            for cat, items in grouped.items():
                is_weekly = cat in WEEKLY_OR_EVENT_CATEGORIES
                for name, default_val in items:
                    enabled = bool(toggles.get(name, default_val))
                    tile = self._make_board_tile(name, cat, enabled)
                    if is_weekly:
                        weekly_grid.addWidget(tile, w_idx // 4, w_idx % 4)
                        w_idx += 1
                    else:
                        daily_grid.addWidget(tile, d_idx // 4, d_idx % 4)
                        d_idx += 1

            body.addLayout(daily_grid)

            # 4. 本周与活动任务
            week_head = QHBoxLayout()
            week_head.addWidget(make_label("本周与活动任务", "h2"))
            week_head.addStretch(1)
            week_head.addWidget(make_label("联盟突袭、大型活动与单人突袭按需勾选", "muted"))
            body.addLayout(week_head)
            body.addLayout(weekly_grid)

            body.addStretch(1)
            return scroll

        def _make_stat_card(self, title: str, val_label: QLabel, foot_label: QLabel, on_click) -> QFrame:
            card = make_card()
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            col = QVBoxLayout(card)
            col.setContentsMargins(16, 14, 16, 14)
            col.setSpacing(6)
            col.addWidget(make_label(title, "sub"))
            col.addWidget(val_label)
            col.addWidget(foot_label)
            card.mouseReleaseEvent = lambda _e: on_click()
            return card

        def _make_board_tile(self, task_name: str, category: str, enabled: bool) -> QFrame:
            tile = make_card()
            col = QVBoxLayout(tile)
            col.setContentsMargins(14, 12, 14, 12)
            col.setSpacing(8)

            top = QHBoxLayout()
            cat_tag = make_label(category, "muted")
            top.addWidget(cat_tag, 1)
            cb = QCheckBox()
            cb.setChecked(enabled)
            cb.toggled.connect(lambda _v, k=task_name: self._on_tile_toggled(k))
            self.tile_checkboxes[task_name] = cb
            top.addWidget(cb)
            col.addLayout(top)

            title_btn = QPushButton(task_name)
            title_btn.setProperty("kind", "flat")
            title_btn.setStyleSheet("text-align:left; padding:0px; min-height:22px; max-height:40px;")
            title_btn.clicked.connect(lambda _c=False, k=task_name: self._open_task_detail(k))
            col.addWidget(title_btn)

            status_lbl = make_label("已加入一键日常" if enabled else "不在一键日常里", "ok" if enabled else "muted")
            status_lbl.setObjectName(f"tile_status_{task_name}")
            col.addWidget(status_lbl)
            return tile

        def _on_tile_toggled(self, task_name: str) -> None:
            cb = self.tile_checkboxes[task_name]
            checked = cb.isChecked()
            if self.controller.state.daily_toggles is not None:
                self.controller.state.daily_toggles[task_name] = checked
            lbl = self.findChild(QLabel, f"tile_status_{task_name}")
            if lbl is not None:
                lbl.setText("已加入一键日常" if checked else "不在一键日常里")
                lbl.setProperty("role", "ok" if checked else "muted")
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
            self._refresh_home_metrics()
            self._refresh_task_detail_panel()

        def _on_autorun_changed(self) -> None:
            on = self.cb_autorun.isChecked()
            self.cb_autorun_clone.setEnabled(on)
            self.controller.state.autorun_enabled = on
            self.controller.state.autorun_in_clone = self.cb_autorun_clone.isChecked()

        def _refresh_home_metrics(self) -> None:
            toggles = self.controller.state.daily_toggles or DEFAULT_DAILY_TOGGLES
            enabled_count = sum(1 for v in toggles.values() if v)
            total_count = len(toggles)
            done_count = len([r for r in self.run_records if r[2] == "完成"])
            self.home_ring.set_progress(done_count, max(1, enabled_count))
            remaining = max(0, enabled_count - done_count)
            self.hero_title.setText(f"还剩 {remaining} 项" if remaining else "今天的日常都做完了")
            self.hero_sub.setText(
                f"已启用 {enabled_count} / {total_count} 项日常流水线 · 桌面分身固定 1920×1080 后台运行"
            )
            self.nav_items["tasks"].set_badge(f"{enabled_count}/{total_count}")
            self.stat_report_val.setText(f"{len(self.run_records)} 项")
            self.stat_report_foot.setText(
                "点击查看今日各任务执行时间线" if self.run_records else "今天还没跑，跑完会记录在这里"
            )

        def _build_report_page(self) -> QWidget:
            now = datetime.now()
            scroll, body, _t, _s = self._wrap_scroll_page(
                "今日报表",
                f"{now.month}月{now.day}日 {WEEKDAY_CN[now.weekday()]} · 游戏日从 05:00 开始",
            )
            card = make_card()
            self.report_list_layout = QVBoxLayout(card)
            self.report_list_layout.setContentsMargins(20, 18, 20, 18)
            self.report_list_layout.setSpacing(10)
            self.report_empty_lbl = make_label(
                "今天还没有运行记录。回到「首页」点击「一键完成日常」或「在桌面分身跑」即可开始。",
                "sub",
                wrap=True,
            )
            self.report_list_layout.addWidget(self.report_empty_lbl)
            body.addWidget(card)
            body.addStretch(1)
            return scroll

        def _build_tasks_page(self) -> QWidget:
            btn_run = make_button(
                "一键完成日常", "primary", on_click=lambda: self._on_launch_direct_ok(debug=False)
            )
            scroll, body, _t, _s = self._wrap_scroll_page(
                "任务设定",
                "一键运行会照左边的顺序跑已勾选项目；点击左侧任一项查看详情",
                action_widgets=[btn_run],
            )

            preset_row = QHBoxLayout()
            preset_row.setSpacing(8)
            preset_row.addWidget(make_button("仅基础日常 (8项)", "secondary", "sm", lambda: self._apply_daily_preset("basic")))
            preset_row.addWidget(make_button("推荐全日常默认", "secondary", "sm", lambda: self._apply_daily_preset("default")))
            preset_row.addWidget(make_button("全部启用 (22项)", "secondary", "sm", lambda: self._apply_daily_preset("all")))
            preset_row.addWidget(make_button("保存配置", "primary", "sm", self._on_save_config))
            preset_row.addStretch(1)
            body.addLayout(preset_row)

            columns = QHBoxLayout()
            columns.setSpacing(16)

            list_card = make_card()
            list_card.setFixedWidth(312)
            list_col = QVBoxLayout(list_card)
            list_col.setContentsMargins(12, 14, 12, 14)
            list_col.setSpacing(4)
            list_col.addWidget(make_label("一键运行的顺序", "eyebrow"))

            for name in DEFAULT_DAILY_TOGGLES:
                row_btn = QPushButton(name)
                row_btn.setProperty("kind", "flat")
                row_btn.setStyleSheet("text-align:left; padding:0px 10px;")
                row_btn.clicked.connect(lambda _c=False, k=name: self._select_task_in_page(k))
                self.task_row_buttons[name] = row_btn
                list_col.addWidget(row_btn)

            left_wrap = QVBoxLayout()
            left_wrap.addWidget(list_card)
            left_wrap.addStretch(1)
            columns.addLayout(left_wrap)

            detail_card = make_card()
            d_col = QVBoxLayout(detail_card)
            d_col.setContentsMargins(22, 20, 22, 20)
            d_col.setSpacing(14)
            self.detail_title = make_label("", "h1")
            self.detail_cat = make_label("", "sub")
            self.detail_toggle = QCheckBox("加入一键日常（勾选后会在一键完成日常与桌面分身中执行）")
            self.detail_toggle.toggled.connect(self._on_detail_toggle)
            d_col.addWidget(self.detail_title)
            d_col.addWidget(self.detail_cat)
            d_col.addWidget(make_sep())
            d_col.addWidget(self.detail_toggle)
            d_col.addWidget(
                make_label(
                    "本任务已完整转换为 ok-script 原生状态机，支持 16:9 归一化 ROI 与 40 项实测 COCO 模板 + RapidOCR 兜底。",
                    "muted",
                    wrap=True,
                )
            )
            d_actions = QHBoxLayout()
            d_actions.addWidget(
                make_button("在桌面分身跑", "primary", on_click=lambda: self._on_run_in_clone(launch_tool=True, debug=False))
            )
            d_actions.addWidget(
                make_button("调试模式启动", "secondary", on_click=lambda: self._on_launch_direct_ok(debug=True))
            )
            d_actions.addStretch(1)
            d_col.addLayout(d_actions)

            right_wrap = QVBoxLayout()
            right_wrap.addWidget(detail_card)
            right_wrap.addStretch(1)
            columns.addLayout(right_wrap, 1)

            body.addLayout(columns)
            body.addStretch(1)
            self._refresh_task_detail_panel()
            return scroll

        def _open_task_detail(self, key: str) -> None:
            self.selected_task_key = key
            self._refresh_task_detail_panel()
            self._navigate("tasks")

        def _select_task_in_page(self, key: str) -> None:
            self.selected_task_key = key
            self._refresh_task_detail_panel()

        def _refresh_task_detail_panel(self) -> None:
            key = self.selected_task_key
            toggles = self.controller.state.daily_toggles or DEFAULT_DAILY_TOGGLES
            enabled = bool(toggles.get(key, False))
            self.detail_title.setText(key)
            cat_found = "日常流水线"
            for cat, items in get_grouped_pipelines().items():
                if any(n == key for n, _d in items):
                    cat_found = cat
                    break
            self.detail_cat.setText(f"所属分类：{cat_found} · 当前状态：{'已加入一键日常' if enabled else '不跑'}")
            self.detail_toggle.blockSignals(True)
            self.detail_toggle.setChecked(enabled)
            self.detail_toggle.blockSignals(False)

            for name, btn in self.task_row_buttons.items():
                is_sel = name == key
                on_flag = bool(toggles.get(name, False))
                prefix = "● " if on_flag else "○ "
                btn.setText(f"{prefix}{name}")
                if is_sel:
                    btn.setStyleSheet(
                        f"text-align:left; padding:0px 10px; background:{tk('row_on')}; color:{tk('primary')}; border-radius:10px;"
                    )
                else:
                    btn.setStyleSheet(
                        f"text-align:left; padding:0px 10px; background:transparent; color:{tk('ink') if on_flag else tk('ink3')};"
                    )

        def _on_detail_toggle(self, checked: bool) -> None:
            key = self.selected_task_key
            if key in self.tile_checkboxes:
                self.tile_checkboxes[key].setChecked(checked)

        def _apply_daily_preset(self, mode: str) -> None:
            for name, cb in self.tile_checkboxes.items():
                if mode == "all":
                    cb.setChecked(True)
                elif mode == "basic":
                    cb.setChecked(name in BASIC_DAILY_KEYS)
                else:
                    cb.setChecked(bool(DEFAULT_DAILY_TOGGLES.get(name, False)))
            self._append_log(f"已切换日常预设模式：{mode}")

        def _build_desktop_clone_page(self) -> QWidget:
            btn_recheck = make_button("重新检查", "secondary", "sm", self._refresh_clone_checks)
            scroll, body, _t, _s = self._wrap_scroll_page(
                "桌面分身",
                "边跑边用电脑；进不去就照这页做",
                action_widgets=[btn_recheck],
            )

            # 1. 这台电脑（自动检查）
            body.addWidget(make_label("这台电脑（自动检查）", "h2"))
            check_card = make_card()
            check_col = QVBoxLayout(check_card)
            check_col.setContentsMargins(18, 14, 18, 14)
            check_col.setSpacing(6)
            self.clone_checks_layout = QVBoxLayout()
            self.clone_checks_layout.setSpacing(4)
            check_col.addLayout(self.clone_checks_layout)

            self.clone_note_label = make_label("", "sub", wrap=True)
            self.clone_note_label.hide()
            check_col.addWidget(self.clone_note_label)

            check_col.addWidget(make_sep())
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)
            btn_row.addWidget(
                make_button("在桌面分身跑", "primary", on_click=lambda: self._on_run_in_clone(launch_tool=True, debug=False))
            )
            btn_row.addWidget(
                make_button("仅打开分身窗口", "secondary", on_click=lambda: self._on_run_in_clone(launch_tool=False, debug=False))
            )
            btn_row.addWidget(make_button("结束桌面分身", "secondary", on_click=self._on_end_clone))
            btn_row.addWidget(make_button("打开分身文件夹", "secondary", on_click=self._on_open_clone_folder))
            btn_row.addWidget(make_button("还原桌面分身", "danger", on_click=self._on_undo_clone_setup))
            btn_row.addStretch(1)
            check_col.addLayout(btn_row)
            body.addWidget(check_card)

            # 2. 第一次怎么用（3 步卡片，对齐 YES-BD2 CloneGuidePage）
            body.addWidget(make_label("第一次怎么用", "h2"))
            steps_row = QHBoxLayout()
            steps_row.setSpacing(12)
            for num, text in enumerate(
                (
                    "首页按「在桌面分身跑」或上方「第一次设定」",
                    "Windows 确认按「是」",
                    "打上面写的密码（不是 PIN），勾「记住」",
                ),
                1,
            ):
                step_card = make_card()
                line = QHBoxLayout(step_card)
                line.setContentsMargins(14, 14, 14, 14)
                line.setSpacing(10)
                sc = StepCircle(num)
                self.step_circles.append(sc)
                line.addWidget(sc, 0, Qt.AlignmentFlag.AlignTop)
                line.addWidget(make_label(text, "h3", wrap=True), 1)
                steps_row.addWidget(step_card, 1)
            body.addLayout(steps_row)

            # 3. 遇到问题（点开看做法）
            body.addWidget(make_label("遇到问题（点开看做法）", "h2"))
            qa_card = make_card()
            qa_col = QVBoxLayout(qa_card)
            qa_col.setContentsMargins(18, 12, 18, 12)
            qa_col.setSpacing(4)
            for q_text, q_steps, has_folder in CLONE_TROUBLESHOOT_QA:
                qa_col.addWidget(
                    CollapsibleQA(q_text, q_steps, has_folder, self._on_open_clone_folder)
                )
            body.addWidget(qa_card)

            # 4. 1080P 窗口校准与搬回路径
            body.addWidget(make_label("1080P 窗口校准与运行模式", "h2"))
            cfg_card = make_card()
            cfg_grid = QGridLayout(cfg_card)
            cfg_grid.setContentsMargins(18, 16, 18, 16)
            cfg_grid.setSpacing(10)

            cfg_grid.addWidget(make_label("运行模式", "sub"), 0, 0)
            self.mode_combo = QComboBox()
            self.mode_combo.addItem("桌面分身窗口模式（Windows 子会话 · 首选）", "desktop_clone")
            self.mode_combo.addItem("主桌面后台消息模式（PostMessage · 家庭版可用）", "background_post_message")
            self.mode_combo.addItem("主桌面标准前台模式（Pynput 兜底）", "foreground_compat")
            idx = self.mode_combo.findData(self.controller.state.run_mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            cfg_grid.addWidget(self.mode_combo, 0, 1)

            cfg_grid.addWidget(make_label("游戏窗口标题", "sub"), 1, 0)
            self.window_title_input = QLineEdit(self.controller.state.window_title)
            cfg_grid.addWidget(self.window_title_input, 1, 1)

            cfg_grid.addWidget(make_label("「搬回桌面」路径", "sub"), 2, 0)
            move_row = QHBoxLayout()
            self.game_exe_input = QLineEdit(self.controller.state.game_exe_path)
            self.game_exe_input.setPlaceholderText("可选：关闭分身选「搬回桌面」时在主桌面打开的 nikke.exe")
            move_row.addWidget(self.game_exe_input, 1)
            move_row.addWidget(make_button("浏览...", "secondary", "sm", self._on_browse_game_exe))
            cfg_grid.addLayout(move_row, 2, 1)

            self.geometry_status_label = make_label(
                "1080P 校准：桌面分身内固定 1920×1080；主桌面窗口化推荐一键校准为 1600×900 (16:9)。",
                "muted",
                wrap=True,
            )
            cfg_grid.addWidget(self.geometry_status_label, 3, 0, 1, 2)

            win_row = QHBoxLayout()
            win_row.addWidget(make_button("检测当前游戏窗口尺寸", "secondary", "sm", self._on_check_live_window))
            win_row.addWidget(make_button("校准为 1600×900", "secondary", "sm", lambda: self._on_calibrate_window(1600, 900)))
            win_row.addWidget(make_button("校准为 1280×720", "secondary", "sm", lambda: self._on_calibrate_window(1280, 720)))
            win_row.addStretch(1)
            cfg_grid.addLayout(win_row, 4, 0, 1, 2)

            body.addWidget(cfg_card)
            body.addStretch(1)
            return scroll

        def _refresh_clone_checks(self) -> None:
            while self.clone_checks_layout.count():
                item = self.clone_checks_layout.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()

            checks = self.controller.check_clone_environment()
            tone_symbol = {OK: ("●", "ok"), WARN: ("▲", "warn"), BAD: ("✕", "bad")}
            for check in checks:
                row = QWidget()
                line = QHBoxLayout(row)
                line.setContentsMargins(0, 4, 0, 4)
                line.setSpacing(10)

                sym, role = tone_symbol.get(check.tone, ("●", "muted"))
                dot = make_label(sym, role)
                dot.setFixedWidth(18)
                line.addWidget(dot)

                lbl = make_label(check.label, "muted")
                lbl.setFixedWidth(110)
                line.addWidget(lbl)

                line.addWidget(make_label(check.text, "h3", wrap=True), 1)

                if check.action:
                    line.addWidget(
                        make_button(
                            check.action,
                            "primary",
                            "sm",
                            on_click=lambda _c=False, a=check.action: self._on_clone_fix_action(a),
                        )
                    )
                self.clone_checks_layout.addWidget(row)

            all_ok = all(c.tone == OK for c in checks)
            self.stat_clone_val.setText("已就绪" if all_ok else "待设定")

        def _build_maa_import_page(self) -> QWidget:
            scroll, body, _t, _s = self._wrap_scroll_page(
                "素材导入",
                "已内置 40 项 Shinarin/MaaNikke 转换模板，可随时刷新图像或校验 Pipeline JSON",
            )
            card = make_card()
            col = QVBoxLayout(card)
            col.setContentsMargins(20, 18, 20, 18)
            col.setSpacing(12)

            col.addWidget(make_label("1. 导入 MaaNikke 图像素材目录（更新 assets/result.json）", "h2"))
            r1 = QHBoxLayout()
            self.maa_dir_input = QLineEdit()
            self.maa_dir_input.setPlaceholderText(r"例如 D:\MaaNikke\resource\base\image")
            r1.addWidget(self.maa_dir_input, 1)
            r1.addWidget(make_button("浏览...", "secondary", "sm", self._on_browse_maa_dir))
            r1.addWidget(make_button("开始导入转换", "primary", "sm", self._on_convert_maa))
            col.addLayout(r1)

            col.addWidget(make_sep())
            col.addWidget(make_label("2. 分析 MaaNikke Pipeline JSON 目录覆盖率", "h2"))
            r2 = QHBoxLayout()
            self.maa_pipeline_input = QLineEdit()
            self.maa_pipeline_input.setPlaceholderText(r"例如 D:\MaaNikke\resource\base\pipeline")
            r2.addWidget(self.maa_pipeline_input, 1)
            r2.addWidget(make_button("浏览...", "secondary", "sm", self._on_browse_maa_pipeline_dir))
            r2.addWidget(make_button("分析流水线映射", "secondary", "sm", self._on_analyze_maa_pipelines))
            col.addLayout(r2)

            self.maa_result_label = make_label(
                "尚未执行导入。未补截的文字按钮运行时会自动启用局部 ROI OCR 兜底。",
                "muted",
                wrap=True,
            )
            col.addWidget(self.maa_result_label)
            body.addWidget(card)
            body.addStretch(1)
            return scroll

        def _build_log_page(self) -> QWidget:
            actions_list = [
                make_button("加载分身 viewer.log", "secondary", "sm", self._on_load_viewer_log),
                make_button("打开分身文件夹", "secondary", "sm", self._on_open_clone_folder),
            ]
            scroll, body, _t, _s = self._wrap_scroll_page(
                "运行日志", "查看桌面客户端、ok-script 与 CloneDesktop.exe 的实时日志", actions_list
            )
            card = make_card()
            col = QVBoxLayout(card)
            col.setContentsMargins(16, 16, 16, 16)
            self.log_box.setMinimumHeight(460)
            col.addWidget(self.log_box)
            body.addWidget(card, 1)
            return scroll

        def _build_settings_page(self) -> QWidget:
            scroll, body, _t, _s = self._wrap_scroll_page(
                "设置", "外观、配置保存与国服客户端路径", [make_button("保存配置", "primary", on_click=self._on_save_config)]
            )
            card = make_card()
            col = QVBoxLayout(card)
            col.setContentsMargins(20, 14, 20, 14)
            col.setSpacing(10)

            col.addWidget(make_label("外观与主题", "h2"))
            row_theme = QHBoxLayout()
            row_theme.addWidget(make_label("界面风格（与 YES-BD2 同步，也可在左下角随时切换）", "sub"), 1)
            row_theme.addWidget(make_button("淡紫", "secondary", "sm", lambda: self._apply_theme("light", save=True)))
            row_theme.addWidget(make_button("深色", "secondary", "sm", lambda: self._apply_theme("dark", save=True)))
            col.addLayout(row_theme)

            col.addWidget(make_sep())
            col.addWidget(make_label("目录与快捷操作", "h2"))
            row_dir = QHBoxLayout()
            row_dir.addWidget(make_label(f"桌面分身数据目录：{clone.DATA_DIR}", "muted", wrap=True), 1)
            row_dir.addWidget(make_button("打开分身文件夹", "secondary", "sm", self._on_open_clone_folder))
            col.addLayout(row_dir)

            body.addWidget(card)
            body.addStretch(1)
            return scroll

        def _navigate(self, key: str) -> None:
            if key not in self.page_map:
                return
            self.pages.setCurrentIndex(self.page_map[key])
            for k, item in self.nav_items.items():
                item.set_selected(k == key)
            if key == "clone":
                self._refresh_clone_checks()
            elif key == "home":
                self._refresh_home_metrics()
            elif key == "tasks":
                self._refresh_task_detail_panel()

        def _apply_theme(self, mode: str, save: bool = False) -> None:
            mode = "dark" if mode == "dark" else "light"
            theme_state["mode"] = mode
            self.controller.state.theme_mode = mode
            self.btn_theme_light.setChecked(mode == "light")
            self.btn_theme_dark.setChecked(mode == "dark")
            app_inst = QApplication.instance()
            if app_inst is not None:
                app_inst.setStyleSheet(build_shell_qss(mode))
            for sc in self.step_circles:
                sc.refresh_theme()
            for item in self.nav_items.values():
                item.update()
            self.home_ring.update()
            self._refresh_task_detail_panel()
            if save:
                self.controller.save_state()

        def _sync_form_to_controller(self) -> None:
            st = self.controller.state
            st.run_mode = self.mode_combo.currentData()
            st.window_title = self.window_title_input.text().strip() or "NIKKE"
            st.game_exe_path = self.game_exe_input.text().strip()
            st.autorun_enabled = self.cb_autorun.isChecked()
            st.autorun_in_clone = self.cb_autorun_clone.isChecked()
            st.daily_toggles = {
                name: cb.isChecked() for name, cb in self.tile_checkboxes.items()
            }

        def _poll_clone_setup_status(self) -> None:
            self._setup_poll_ticks += 1
            if clone.ready():
                self._setup_poll_timer.stop()
                self.clone_note_label.setText("桌面分身「第一次设定」已完成！现在可以直接点击「在桌面分身跑」。")
                self.clone_note_label.show()
                self._append_log("[桌面分身] 检测到 CloneDesktop.exe 与子会话均已就绪。")
                self._refresh_clone_checks()
                return
            if self._setup_poll_ticks >= 80:  # 约 2 分钟
                self._setup_poll_timer.stop()
                self._refresh_clone_checks()

        def _on_clone_fix_action(self, action: str) -> None:
            if action == "第一次设定":
                ok = self.controller.run_clone_setup(undo=False)
                if ok:
                    msg = (
                        "已打开设定窗口：编译完成后会弹出 Windows 管理员确认 (UAC)，请点击「是」。"
                        "设定完成后本页会自动刷新状态（也可手动点击右上角「重新检查」）。"
                    )
                    self._setup_poll_ticks = 0
                    self._setup_poll_timer.start()
                else:
                    detail = clone.setup_failure.get("detail") or "仅支持在 Windows 系统下运行 setup.ps1。"
                    msg = f"未能启动设定脚本：{detail}"
            elif action == "帮我打开":
                ok = self.controller.fix_remote_desktop_service()
                msg = (
                    "「远程桌面服务」已恢复为可用状态。"
                    if ok
                    else "未能打开远程桌面服务（可能取消了管理员确认）。"
                )
            else:
                ok = self.controller.fix_windows_hello()
                msg = (
                    "已关闭「仅允许 Windows Hello 登录」，现在可以用账户密码登录桌面分身。"
                    if ok
                    else "未能关闭该项（可能取消了管理员确认）。"
                )
            self._navigate("clone")
            self.clone_note_label.setText(msg)
            self.clone_note_label.show()
            self._append_log(f"[桌面分身] {action} -> {msg}")
            self._refresh_clone_checks()

        def _on_browse_game_exe(self) -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择 nikke.exe 或 wegame.exe", "", "可执行文件 (*.exe);;所有文件 (*.*)"
            )
            if file_path:
                self.game_exe_input.setText(file_path)

        def _on_save_config(self) -> None:
            self._sync_form_to_controller()
            saved = self.controller.save_state()
            self._append_log(f"已保存配置至 {saved}")
            QMessageBox.information(self, "配置已保存", f"已写入 {saved.name}，启动 ok-script 时将自动生效。")

        def _on_launch_direct_ok(self, debug: bool = False) -> None:
            self._sync_form_to_controller()
            if self.controller.state.run_mode == "desktop_clone":
                self.controller.state.run_mode = "background_post_message"
            self.controller.save_state()
            argv = self.controller.build_ok_launch_argv(debug=debug)
            self._append_log(f"主桌面启动自动化引擎: {' '.join(argv)}")
            try:
                subprocess.Popen(argv, cwd=str(PROJECT_ROOT))
            except Exception as exc:
                self._append_log(f"启动失败: {exc}")
                QMessageBox.warning(self, "启动失败", str(exc))

        def _on_run_in_clone(self, launch_tool: bool = True, debug: bool = False) -> None:
            self._sync_form_to_controller()
            outcome = self.controller.launch_in_clone_desktop(
                launch_tool=launch_tool, debug=debug
            )
            self._append_log(f"[桌面分身] ({outcome.status}) {outcome.message}")

            if outcome.ok:
                self.clone_note_label.setText(outcome.message)
                self.clone_note_label.show()
                return

            if outcome.status == "need_setup":
                reply = QMessageBox.question(
                    self,
                    "需要完成第一次设定",
                    outcome.message + "\n\n是否现在执行「第一次设定」？（会弹出一次管理员确认）",
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._on_clone_fix_action("第一次设定")
                return

            if outcome.status == "service_disabled":
                reply = QMessageBox.question(
                    self,
                    "远程桌面服务被禁用",
                    outcome.message + "\n\n是否让 YES-NK 帮你恢复为可用状态？",
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._on_clone_fix_action("帮我打开")
                return

            if outcome.status == "hello_only":
                reply = QMessageBox.question(
                    self,
                    "需要关闭仅限 Windows Hello 登录",
                    outcome.message + "\n\n是否让 YES-NK 一键帮我关掉？（人脸和 PIN 不会关闭）",
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._on_clone_fix_action("帮我关掉")
                return

            QMessageBox.warning(self, "桌面分身提示", outcome.message)
            self._navigate("clone")

        def _on_end_clone(self) -> None:
            ok = self.controller.end_clone_desktop()
            msg = "已关闭桌面分身窗口并注销子会话。" if ok else "当前没有运行中的桌面分身或注销超时。"
            self.clone_note_label.setText(msg)
            self.clone_note_label.show()
            self._append_log(f"[桌面分身] {msg}")

        def _on_undo_clone_setup(self) -> None:
            reply = QMessageBox.question(
                self,
                "还原桌面分身",
                "将关闭桌面分身功能、恢复系统注册表默认值并删除 CloneDesktop.exe。\n确定要还原吗？",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            ok = self.controller.run_clone_setup(undo=True)
            msg = (
                "已打开还原窗口，请在 UAC 提示点「是」，完成后点击「重新检查」。"
                if ok
                else "仅支持在 Windows 系统下运行还原脚本。"
            )
            self.clone_note_label.setText(msg)
            self.clone_note_label.show()
            self._append_log(f"[桌面分身] {msg}")

        def _on_open_clone_folder(self) -> None:
            if not self.controller.open_clone_folder():
                QMessageBox.information(self, "分身文件夹", f"路径：{clone.DATA_DIR}")

        def _on_load_viewer_log(self) -> None:
            tail = clone.read_log_tail(clone.VIEWER_LOG, max_chars=3000)
            if not tail:
                self._append_log(f"暂无分身日志（{clone.VIEWER_LOG}）。")
            else:
                self._append_log(f"--- viewer.log ({clone.VIEWER_LOG}) ---\n{tail}")

        def _on_check_live_window(self) -> None:
            self._sync_form_to_controller()
            report = self.controller.inspect_live_window()
            text = f"检测结果 [{report.status}]：{report.client_width}×{report.client_height} — {report.recommendation}"
            self.geometry_status_label.setText(text)
            if report.client_width > 0:
                self.stat_res_val.setText(f"{report.client_width}×{report.client_height}")
            self._append_log(text)

        def _on_calibrate_window(self, w: int, h: int) -> None:
            self._sync_form_to_controller()
            ok = self.controller.calibrate_live_window_16_9(w, h)
            if ok:
                rep = evaluate_client_geometry(w, h)
                msg = f"已将游戏窗口校准为 {w}×{h} ({rep.status})"
                self.geometry_status_label.setText(msg)
                self.stat_res_val.setText(f"{w}×{h}")
                self._append_log(msg)
            else:
                msg = "未找到正在运行的国服 NIKKE 窗口，请先启动游戏后再点击校准。"
                self.geometry_status_label.setText(msg)
                self._append_log(msg)

        def _on_browse_maa_dir(self) -> None:
            folder = QFileDialog.getExistingDirectory(self, "选择 MaaNikke 图像素材目录")
            if folder:
                self.maa_dir_input.setText(folder)

        def _on_browse_maa_pipeline_dir(self) -> None:
            folder = QFileDialog.getExistingDirectory(self, "选择 MaaNikke Pipeline JSON 目录")
            if folder:
                self.maa_pipeline_input.setText(folder)

        def _on_convert_maa(self) -> None:
            raw = self.maa_dir_input.text().strip()
            if not raw:
                QMessageBox.warning(self, "提示", "请先选择 MaaNikke 图像目录。")
                return
            maa_path = Path(raw)
            if not maa_path.exists():
                QMessageBox.warning(self, "目录不存在", f"未找到目录：{maa_path}")
                return
            report = self.controller.import_maa_assets(maa_path)
            summary = (
                f"导入完成！已匹配 {len(report.matched_features)} / 44 项特征，"
                f"剩余 {len(report.missing_features)} 项纯文字按钮将自动使用 ROI OCR 兜底。"
            )
            self.maa_result_label.setText(summary)
            self._append_log(summary)

        def _on_analyze_maa_pipelines(self) -> None:
            raw = self.maa_pipeline_input.text().strip()
            if not raw:
                QMessageBox.warning(self, "提示", "请先选择 MaaNikke Pipeline 目录。")
                return
            p_path = Path(raw)
            if not p_path.exists():
                QMessageBox.warning(self, "目录不存在", f"未找到目录：{p_path}")
                return
            report = self.controller.analyze_maa_pipelines(p_path)
            summary = (
                f"分析完成：扫描 {report.scanned_files} 个 JSON 文件（共 {report.total_nodes} 个节点，"
                f"引用模板 {len(report.referenced_templates)} 项），"
                f"已映射到 {len(report.mapped_tasks)} 个 YES-NK 原生状态机任务。"
            )
            self.maa_result_label.setText(summary)
            self._append_log(summary)

    app = QApplication(sys.argv)
    win = YesNkDesktopWindow()
    win.show()
    return app.exec()
