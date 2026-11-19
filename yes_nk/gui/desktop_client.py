"""YES-NK 原生 Windows 桌面客户端（与 YES-BD2 一致的 PySide6 Fluent 风格窗口与桌面分身体验）。

功能：
1. 首页一键日常（22 条 MaaNikke 转换流水线）+「在桌面分身跑」智能引导启动；
2. 完整复刻 YES-BD2 桌面分身引导与控制页（这台电脑 6 项自动检查 + 一键第一次设定 / 帮我打开 / 帮我关掉 / 还原桌面分身 / 折叠排障）；
3. 1080P 游戏窗口客户区实时检测与一键 16:9 校准；
4. MaaNikke 图像素材与 Pipeline JSON 导入分析。
"""

from __future__ import annotations

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
from yes_nk.utils import desktop_clone as clone
from yes_nk.utils.desktop_clone import (
    BAD,
    CLONE_TROUBLESHOOT_QA,
    OK,
    WARN,
    CloneCheck,
)
from yes_nk.utils.window_1080p import (
    enable_per_monitor_dpi_awareness,
    evaluate_client_geometry,
)

FLUENT_QSS = """
QMainWindow, QWidget {
    background-color: #F3F4F6;
    color: #0F172A;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QListWidget#Sidebar {
    background-color: #F9FAFB;
    border: none;
    border-right: 1px solid #E2E8F0;
    padding: 8px;
    outline: none;
}
QListWidget#Sidebar::item {
    padding: 10px 12px;
    margin-bottom: 4px;
    border-radius: 6px;
    color: #334155;
}
QListWidget#Sidebar::item:selected {
    background-color: #FFFFFF;
    color: #0067C0;
    border: 1px solid #CBD5E1;
    font-weight: 600;
}
QFrame.Card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 14px;
    color: #0F172A;
}
QPushButton:hover {
    border-color: #0067C0;
    background-color: #F8FAFC;
}
QPushButton#PrimaryButton {
    background-color: #0067C0;
    border: 1px solid #0067C0;
    color: #FFFFFF;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover {
    background-color: #005A9E;
}
QPushButton#DangerButton {
    background-color: #FEF2F2;
    border: 1px solid #FCA5A5;
    color: #B91C1C;
}
QPushButton#DangerButton:hover {
    background-color: #FEE2E2;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 8px;
}
QScrollArea {
    border: none;
    background: transparent;
}
"""


def launch_desktop_client() -> int:
    """启动 PySide6 原生 Windows 桌面客户端窗口。"""
    enable_per_monitor_dpi_awareness()

    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QFileDialog,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QScrollArea,
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

    class CollapsibleQA(QWidget):
        """复刻 YES-BD2 CloneGuidePage 的可折叠常见问题排障项。"""

        def __init__(
            self, question: str, steps: tuple[str, ...], show_folder_btn: bool, on_open_folder
        ) -> None:
            super().__init__()
            col = QVBoxLayout(self)
            col.setContentsMargins(0, 2, 0, 2)
            col.setSpacing(4)

            self.toggle_btn = QPushButton(f"▸  {question}")
            self.toggle_btn.setStyleSheet(
                "text-align:left; border:none; background:transparent; font-weight:600; padding:6px 4px; color:#0F172A;"
            )
            self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle_btn.clicked.connect(self._toggle)
            col.addWidget(self.toggle_btn)

            self.body = QWidget()
            self.body.setStyleSheet("background:#F8FAFC; border-radius:6px;")
            body_layout = QVBoxLayout(self.body)
            body_layout.setContentsMargins(16, 8, 12, 10)
            body_layout.setSpacing(4)
            for idx, step in enumerate(steps, 1):
                lbl = QLabel(f"{idx}. {step}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet("color:#334155; background:transparent;")
                body_layout.addWidget(lbl)
            if show_folder_btn:
                btn = QPushButton("打开分身文件夹")
                btn.clicked.connect(on_open_folder)
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
            self.setWindowTitle(f"YES-NK 桌面客户端 v{__version__} — 胜利女神：新的希望")
            self.resize(1060, 700)
            self.setMinimumSize(920, 620)

            icon_path = RESOURCE_ROOT / "assets" / "icon.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))

            self.daily_checkboxes: dict[str, QCheckBox] = {}
            self.log_box = QTextEdit()
            self.log_box.setReadOnly(True)

            self._build_ui()
            self._refresh_clone_checks()
            self._append_log(
                "YES-NK 桌面客户端已就绪（国服 PC 端 / YES-BD2 同款 Windows 子会话桌面分身）。"
            )

        def _append_log(self, msg: str) -> None:
            self.log_box.append(msg)

        def _make_card(self) -> QFrame:
            card = QFrame()
            card.setProperty("class", "Card")
            return card

        def _build_ui(self) -> None:
            root = QWidget()
            root_layout = QHBoxLayout(root)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.setSpacing(0)

            sidebar_wrap = QWidget()
            sidebar_wrap.setFixedWidth(224)
            sb_layout = QVBoxLayout(sidebar_wrap)
            sb_layout.setContentsMargins(0, 0, 0, 0)
            sb_layout.setSpacing(0)

            brand = QLabel(f"  YES-NK   v{__version__}")
            brand.setFixedHeight(52)
            brand.setStyleSheet(
                "background:#F9FAFB; font-weight:700; font-size:15px; border-bottom:1px solid #E2E8F0; border-right:1px solid #E2E8F0;"
            )
            sb_layout.addWidget(brand)

            self.nav_list = QListWidget()
            self.nav_list.setObjectName("Sidebar")
            self.nav_list.addItems(
                [
                    "日常一条龙启动台",
                    "桌面分身（同款 YES-BD2）",
                    "MaaNikke 素材导入",
                    "运行日志与排障",
                ]
            )
            self.nav_list.setCurrentRow(0)
            sb_layout.addWidget(self.nav_list)
            root_layout.addWidget(sidebar_wrap)

            right_wrap = QWidget()
            right_layout = QVBoxLayout(right_wrap)
            right_layout.setContentsMargins(20, 16, 20, 16)
            right_layout.setSpacing(14)

            header = QHBoxLayout()
            self.page_title = QLabel("国服全量日常一条龙（22 条 MaaNikke 转换流水线）")
            self.page_title.setStyleSheet("font-size:16px; font-weight:700;")
            header.addWidget(self.page_title)
            header.addStretch(1)

            btn_save = QPushButton("保存配置")
            btn_save.clicked.connect(self._on_save_config)
            header.addWidget(btn_save)

            btn_clone_top = QPushButton("在桌面分身跑")
            btn_clone_top.setObjectName("PrimaryButton")
            btn_clone_top.clicked.connect(lambda: self._on_run_in_clone(launch_tool=True, debug=False))
            header.addWidget(btn_clone_top)
            right_layout.addLayout(header)

            self.pages = QStackedWidget()
            self.pages.addWidget(self._build_daily_page())
            self.pages.addWidget(self._build_desktop_clone_page())
            self.pages.addWidget(self._build_maa_import_page())
            self.pages.addWidget(self._build_log_page())
            right_layout.addWidget(self.pages)

            self.nav_list.currentRowChanged.connect(self._on_nav_changed)
            root_layout.addWidget(right_wrap)
            self.setCentralWidget(root)

        def _on_nav_changed(self, idx: int) -> None:
            titles = [
                "国服全量日常一条龙（22 条 MaaNikke 转换流水线）",
                "桌面分身 — 边跑边用电脑（与 YES-BD2 一致的 Windows 子会话窗口）",
                "MaaNikke 素材与 Pipeline 导入转换",
                "桌面客户端运行日志",
            ]
            if 0 <= idx < len(titles):
                self.page_title.setText(titles[idx])
                self.pages.setCurrentIndex(idx)
                if idx == 1:
                    self._refresh_clone_checks()

        def _build_daily_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)

            card = self._make_card()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 16, 18, 16)
            card_layout.setSpacing(10)

            tip = QLabel(
                "已完整接入 Shinarin/MaaNikke 全部 22 条流水线并预置 40 项 COCO 模板。"
                "勾选日常项后，点击「在桌面分身跑」即可在独立 1920×1080 窗口中后台运行，完全不抢占主桌面鼠标键盘："
            )
            tip.setWordWrap(True)
            tip.setStyleSheet("color:#475569;")
            card_layout.addWidget(tip)

            preset_row = QHBoxLayout()
            btn_preset_basic = QPushButton("仅勾选基础日常 (8项)")
            btn_preset_basic.clicked.connect(lambda: self._apply_daily_preset("basic"))
            preset_row.addWidget(btn_preset_basic)

            btn_preset_default = QPushButton("推荐全日常默认")
            btn_preset_default.clicked.connect(lambda: self._apply_daily_preset("default"))
            preset_row.addWidget(btn_preset_default)

            btn_preset_all = QPushButton("全部启用 (22项)")
            btn_preset_all.clicked.connect(lambda: self._apply_daily_preset("all"))
            preset_row.addWidget(btn_preset_all)
            preset_row.addStretch(1)
            card_layout.addLayout(preset_row)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_body = QWidget()
            scroll_body.setStyleSheet("background:#FFFFFF;")
            scroll_layout = QVBoxLayout(scroll_body)
            scroll_layout.setContentsMargins(2, 4, 8, 4)
            scroll_layout.setSpacing(12)

            toggles = self.controller.state.daily_toggles or DEFAULT_DAILY_TOGGLES
            grouped = get_grouped_pipelines()
            for category, items in grouped.items():
                cat_label = QLabel(f"{category}（{len(items)}）")
                cat_label.setStyleSheet(
                    "font-weight:700; color:#0067C0; padding-top:4px; border-bottom:1px solid #E2E8F0;"
                )
                scroll_layout.addWidget(cat_label)

                grid = QGridLayout()
                grid.setHorizontalSpacing(16)
                grid.setVerticalSpacing(6)
                for idx_item, (name, default_val) in enumerate(items):
                    cb = QCheckBox(name)
                    cb.setChecked(bool(toggles.get(name, default_val)))
                    self.daily_checkboxes[name] = cb
                    grid.addWidget(cb, idx_item // 2, idx_item % 2)
                scroll_layout.addLayout(grid)

            scroll_layout.addStretch(1)
            scroll.setWidget(scroll_body)
            card_layout.addWidget(scroll, stretch=1)

            action_row = QHBoxLayout()
            btn_clone_start = QPushButton("在桌面分身跑（独立窗口 · 不抢鼠标）")
            btn_clone_start.setObjectName("PrimaryButton")
            btn_clone_start.clicked.connect(lambda: self._on_run_in_clone(launch_tool=True, debug=False))
            action_row.addWidget(btn_clone_start)

            btn_direct = QPushButton("在主桌面直接启动")
            btn_direct.clicked.connect(lambda: self._on_launch_direct_ok(debug=False))
            action_row.addWidget(btn_direct)

            btn_debug = QPushButton("调试模式启动 (main_debug)")
            btn_debug.clicked.connect(lambda: self._on_launch_direct_ok(debug=True))
            action_row.addWidget(btn_debug)
            action_row.addStretch(1)
            card_layout.addLayout(action_row)

            layout.addWidget(card, stretch=1)
            return page

        def _apply_daily_preset(self, mode: str) -> None:
            for name, cb in self.daily_checkboxes.items():
                if mode == "all":
                    cb.setChecked(True)
                elif mode == "basic":
                    cb.setChecked(name in BASIC_DAILY_KEYS)
                else:
                    cb.setChecked(bool(DEFAULT_DAILY_TOGGLES.get(name, False)))
            self._append_log(f"已切换日常预设模式：{mode}")

        def _build_desktop_clone_page(self) -> QWidget:
            outer = QScrollArea()
            outer.setWidgetResizable(True)
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 8, 12)
            layout.setSpacing(14)

            # 1. 这台电脑（自动检查）卡片 — 复刻 YES-BD2 clone_guide_page.py
            check_card = self._make_card()
            check_layout = QVBoxLayout(check_card)
            check_layout.setContentsMargins(18, 16, 18, 16)
            check_layout.setSpacing(10)

            head_row = QHBoxLayout()
            sec_title = QLabel("这台电脑（自动检查）")
            sec_title.setStyleSheet("font-weight:700; font-size:14px;")
            head_row.addWidget(sec_title)
            head_row.addStretch(1)
            btn_recheck = QPushButton("重新检查")
            btn_recheck.clicked.connect(self._refresh_clone_checks)
            head_row.addWidget(btn_recheck)
            check_layout.addLayout(head_row)

            self.clone_checks_layout = QVBoxLayout()
            self.clone_checks_layout.setSpacing(6)
            check_layout.addLayout(self.clone_checks_layout)

            self.clone_note_label = QLabel("")
            self.clone_note_label.setWordWrap(True)
            self.clone_note_label.setStyleSheet("color:#0067C0; font-weight:600;")
            self.clone_note_label.hide()
            check_layout.addWidget(self.clone_note_label)

            btn_row = QHBoxLayout()
            btn_run_clone = QPushButton("在桌面分身跑")
            btn_run_clone.setObjectName("PrimaryButton")
            btn_run_clone.clicked.connect(lambda: self._on_run_in_clone(launch_tool=True, debug=False))
            btn_row.addWidget(btn_run_clone)

            btn_open_only = QPushButton("仅打开分身窗口")
            btn_open_only.clicked.connect(lambda: self._on_run_in_clone(launch_tool=False, debug=False))
            btn_row.addWidget(btn_open_only)

            btn_end_clone = QPushButton("结束桌面分身")
            btn_end_clone.clicked.connect(self._on_end_clone)
            btn_row.addWidget(btn_end_clone)

            btn_folder = QPushButton("打开分身文件夹")
            btn_folder.clicked.connect(self._on_open_clone_folder)
            btn_row.addWidget(btn_folder)

            btn_undo = QPushButton("还原桌面分身")
            btn_undo.setObjectName("DangerButton")
            btn_undo.clicked.connect(self._on_undo_clone_setup)
            btn_row.addWidget(btn_undo)
            btn_row.addStretch(1)
            check_layout.addLayout(btn_row)
            layout.addWidget(check_card)

            # 2. 第一次怎么用（3 步引导卡）
            guide_card = self._make_card()
            guide_layout = QVBoxLayout(guide_card)
            guide_layout.setContentsMargins(18, 14, 18, 14)
            guide_layout.setSpacing(10)
            g_title = QLabel("第一次怎么用（与 YES-BD2 完全一致）")
            g_title.setStyleSheet("font-weight:700; font-size:14px;")
            guide_layout.addWidget(g_title)

            steps_row = QHBoxLayout()
            for num, text in enumerate(
                (
                    "点击「第一次设定」（弹出管理员 UAC 选「是」），自动编译 CloneDesktop.exe 并开启子会话",
                    "点击「在桌面分身跑」，会弹出独立 1920×1080 桌面窗口（不是黑屏切桌面，最小化也会继续跑）",
                    "在 Windows 登录框输入账户密码（不是 PIN）并勾选「记住」，登录成功后自动在分身内启动 YES-NK",
                ),
                1,
            ):
                step_box = QFrame()
                step_box.setStyleSheet(
                    "background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px;"
                )
                sb = QVBoxLayout(step_box)
                sb.setContentsMargins(12, 10, 12, 10)
                n_lbl = QLabel(f"步骤 {num}")
                n_lbl.setStyleSheet("font-weight:700; color:#0067C0; border:none;")
                t_lbl = QLabel(text)
                t_lbl.setWordWrap(True)
                t_lbl.setStyleSheet("color:#334155; font-size:12px; border:none;")
                sb.addWidget(n_lbl)
                sb.addWidget(t_lbl)
                steps_row.addWidget(step_box, 1)
            guide_layout.addLayout(steps_row)
            layout.addWidget(guide_card)

            # 3. 遇到问题（点开看做法）
            qa_card = self._make_card()
            qa_layout = QVBoxLayout(qa_card)
            qa_layout.setContentsMargins(18, 14, 18, 14)
            qa_layout.setSpacing(4)
            qa_title = QLabel("遇到问题（点开看做法）")
            qa_title.setStyleSheet("font-weight:700; font-size:14px; padding-bottom:4px;")
            qa_layout.addWidget(qa_title)
            for q_text, q_steps, has_folder in CLONE_TROUBLESHOOT_QA:
                qa_layout.addWidget(
                    CollapsibleQA(q_text, q_steps, has_folder, self._on_open_clone_folder)
                )
            layout.addWidget(qa_card)

            # 4. 运行模式与 1080P 窗口校准卡
            cfg_card = self._make_card()
            cfg_grid = QGridLayout(cfg_card)
            cfg_grid.setContentsMargins(18, 16, 18, 16)
            cfg_grid.setSpacing(10)

            cfg_grid.addWidget(QLabel("运行模式"), 0, 0)
            self.mode_combo = QComboBox()
            self.mode_combo.addItem("桌面分身窗口模式（Windows Child Session · 首选）", "desktop_clone")
            self.mode_combo.addItem("主桌面后台消息模式（PostMessage · 家庭版可用）", "background_post_message")
            self.mode_combo.addItem("主桌面标准前台模式（Pynput 兜底）", "foreground_compat")
            idx = self.mode_combo.findData(self.controller.state.run_mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            cfg_grid.addWidget(self.mode_combo, 0, 1)

            cfg_grid.addWidget(QLabel("游戏窗口标题"), 1, 0)
            self.window_title_input = QLineEdit(self.controller.state.window_title)
            cfg_grid.addWidget(self.window_title_input, 1, 1)

            cfg_grid.addWidget(QLabel("「搬回桌面」游戏路径"), 2, 0)
            move_row = QHBoxLayout()
            self.game_exe_input = QLineEdit(self.controller.state.game_exe_path)
            self.game_exe_input.setPlaceholderText("可选：关闭分身选「搬回桌面」时在主桌面打开的 nikke.exe / wegame.exe")
            move_row.addWidget(self.game_exe_input, stretch=1)
            btn_browse_game = QPushButton("浏览...")
            btn_browse_game.clicked.connect(self._on_browse_game_exe)
            move_row.addWidget(btn_browse_game)
            cfg_grid.addLayout(move_row, 2, 1)

            self.geometry_status_label = QLabel(
                "1080P 校准：桌面分身内自动固定 1920×1080；若在主桌面窗口化运行，可一键校准为 1600×900 (16:9)。"
            )
            self.geometry_status_label.setWordWrap(True)
            self.geometry_status_label.setStyleSheet("color:#475569;")
            cfg_grid.addWidget(self.geometry_status_label, 3, 0, 1, 2)

            win_btn_row = QHBoxLayout()
            btn_check = QPushButton("检测当前游戏窗口尺寸")
            btn_check.clicked.connect(self._on_check_live_window)
            win_btn_row.addWidget(btn_check)

            btn_cal_900 = QPushButton("校准为 1600×900 (1080P 窗口推荐)")
            btn_cal_900.clicked.connect(lambda: self._on_calibrate_window(1600, 900))
            win_btn_row.addWidget(btn_cal_900)

            btn_cal_720 = QPushButton("校准为 1280×720")
            btn_cal_720.clicked.connect(lambda: self._on_calibrate_window(1280, 720))
            win_btn_row.addWidget(btn_cal_720)
            win_btn_row.addStretch(1)
            cfg_grid.addLayout(win_btn_row, 4, 0, 1, 2)

            layout.addWidget(cfg_card)
            layout.addStretch(1)
            outer.setWidget(container)
            return outer

        def _refresh_clone_checks(self) -> None:
            while self.clone_checks_layout.count():
                item = self.clone_checks_layout.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()

            checks = self.controller.check_clone_environment()
            tone_badge = {
                OK: ("●", "#16A34A"),
                WARN: ("▲", "#D97706"),
                BAD: ("✕", "#DC2626"),
            }
            for check in checks:
                row = QWidget()
                row.setStyleSheet("background:#FFFFFF;")
                line = QHBoxLayout(row)
                line.setContentsMargins(0, 4, 0, 4)
                line.setSpacing(10)

                sym, color = tone_badge.get(check.tone, ("●", "#64748B"))
                dot = QLabel(sym)
                dot.setFixedWidth(18)
                dot.setStyleSheet(f"color:{color}; font-weight:700;")
                line.addWidget(dot)

                lbl = QLabel(check.label)
                lbl.setFixedWidth(110)
                lbl.setStyleSheet("color:#64748B; font-weight:600;")
                line.addWidget(lbl)

                txt = QLabel(check.text)
                txt.setWordWrap(True)
                txt.setStyleSheet("color:#0F172A;")
                line.addWidget(txt, 1)

                if check.action:
                    act_btn = QPushButton(check.action)
                    act_btn.setObjectName("PrimaryButton")
                    act_btn.clicked.connect(lambda _c=False, a=check.action: self._on_clone_fix_action(a))
                    line.addWidget(act_btn)
                self.clone_checks_layout.addWidget(row)

        def _on_clone_fix_action(self, action: str) -> None:
            if action == "第一次设定":
                ok = self.controller.run_clone_setup(undo=False)
                msg = (
                    "已打开设定窗口（请在弹出 UAC 时点击「是」），完成后点击「重新检查」。"
                    if ok
                    else "仅支持在 Windows 系统下运行 setup.ps1。"
                )
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
            self.clone_note_label.setText(msg)
            self.clone_note_label.show()
            self._append_log(f"[桌面分身] {action} -> {msg}")
            self._refresh_clone_checks()

        def _build_maa_import_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(14)

            card = self._make_card()
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(18, 16, 18, 16)
            c_layout.setSpacing(10)

            desc = QLabel(
                "1. 仓库已预置从 Shinarin/MaaNikke 转换好的 40 项 1280×720 基准 COCO 模板；"
                "若日后 MaaNikke 更新素材，可重新选择图像目录刷新 44 项特征："
            )
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#475569;")
            c_layout.addWidget(desc)

            row = QHBoxLayout()
            self.maa_dir_input = QLineEdit()
            self.maa_dir_input.setPlaceholderText("例如 D:\\MaaNikke\\resource\\base\\image")
            row.addWidget(self.maa_dir_input)

            btn_browse = QPushButton("浏览图像目录...")
            btn_browse.clicked.connect(self._on_browse_maa_dir)
            row.addWidget(btn_browse)

            btn_convert = QPushButton("开始导入转换")
            btn_convert.setObjectName("PrimaryButton")
            btn_convert.clicked.connect(self._on_convert_maa)
            row.addWidget(btn_convert)
            c_layout.addLayout(row)

            pipe_desc = QLabel(
                "2. 可选：选择 MaaNikke 的 pipeline JSON 目录（如 MaaNikke\\resource\\base\\pipeline），"
                "校验所有节点到 YES-NK 22 个原生状态机任务的映射覆盖率："
            )
            pipe_desc.setWordWrap(True)
            pipe_desc.setStyleSheet("color:#475569; padding-top:6px;")
            c_layout.addWidget(pipe_desc)

            pipe_row = QHBoxLayout()
            self.maa_pipeline_input = QLineEdit()
            self.maa_pipeline_input.setPlaceholderText("例如 D:\\MaaNikke\\resource\\base\\pipeline")
            pipe_row.addWidget(self.maa_pipeline_input)

            btn_browse_pipe = QPushButton("浏览 Pipeline 目录...")
            btn_browse_pipe.clicked.connect(self._on_browse_maa_pipeline_dir)
            pipe_row.addWidget(btn_browse_pipe)

            btn_scan_pipe = QPushButton("分析流水线映射")
            btn_scan_pipe.clicked.connect(self._on_analyze_maa_pipelines)
            pipe_row.addWidget(btn_scan_pipe)
            c_layout.addLayout(pipe_row)

            self.maa_result_label = QLabel(
                "尚未执行导入。未补截的文字按钮运行时会自动启用局部 ROI OCR 兜底。"
            )
            self.maa_result_label.setWordWrap(True)
            c_layout.addWidget(self.maa_result_label)

            layout.addWidget(card)
            layout.addStretch(1)
            return page

        def _build_log_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            bar = QHBoxLayout()
            btn_load_viewer_log = QPushButton("加载分身 viewer.log")
            btn_load_viewer_log.clicked.connect(self._on_load_viewer_log)
            bar.addWidget(btn_load_viewer_log)
            btn_open_dir = QPushButton("打开分身日志文件夹")
            btn_open_dir.clicked.connect(self._on_open_clone_folder)
            bar.addWidget(btn_open_dir)
            bar.addStretch(1)
            layout.addLayout(bar)
            layout.addWidget(self.log_box)
            return page

        def _sync_form_to_controller(self) -> None:
            st = self.controller.state
            st.run_mode = self.mode_combo.currentData()
            st.window_title = self.window_title_input.text().strip() or "NIKKE"
            st.game_exe_path = self.game_exe_input.text().strip()
            st.daily_toggles = {
                name: cb.isChecked() for name, cb in self.daily_checkboxes.items()
            }

        def _on_browse_game_exe(self) -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择 nikke.exe 或 wegame.exe",
                "",
                "可执行文件 (*.exe);;所有文件 (*.*)",
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
            self.nav_list.setCurrentRow(1)

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
                QMessageBox.information(
                    self, "分身文件夹", f"路径：{clone.DATA_DIR}"
                )

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
            self._append_log(text)

        def _on_calibrate_window(self, w: int, h: int) -> None:
            self._sync_form_to_controller()
            ok = self.controller.calibrate_live_window_16_9(w, h)
            if ok:
                rep = evaluate_client_geometry(w, h)
                msg = f"已将游戏窗口校准为 {w}×{h} ({rep.status})"
                self.geometry_status_label.setText(msg)
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
    app.setStyleSheet(FLUENT_QSS)
    win = YesNkDesktopWindow()
    win.show()
    return app.exec()
