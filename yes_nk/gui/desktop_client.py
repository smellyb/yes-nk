"""YES-NK 原生 Windows 桌面客户端（仿 YES-BD2 的 PySide6 Fluent 风格窗口）。

提供图形化的一站式操作界面，彻底免除命令行操作：
1. 基础日常一条龙勾选与一键启动 ok-script 自动化引擎；
2. 桌面分身一键创建/切屏/切回主桌面，与 1080P 窗口一键校准为 1600x900 / 1280x720；
3. MaaNikke 图像素材目录图形化选择与一键转换为 COCO 特征包；
4. 所有参数自动保存至 yes_nk_config.json，与 ok-script 运行时及 Web 工作台完全互通。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Any

from yes_nk import __version__
from yes_nk.config import PROJECT_ROOT
from yes_nk.gui.controller import (
    BASIC_DAILY_KEYS,
    DEFAULT_DAILY_TOGGLES,
    DesktopClientController,
    get_grouped_pipelines,
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
            QSpinBox,
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

    class YesNkDesktopWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.controller = DesktopClientController()
            self.setWindowTitle(f"YES-NK 桌面客户端 v{__version__} — 胜利女神：新的希望")
            self.resize(1040, 680)
            self.setMinimumSize(900, 600)

            icon_path = PROJECT_ROOT / "assets" / "icon.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))

            self.daily_checkboxes: dict[str, QCheckBox] = {}
            self.log_box = QTextEdit()
            self.log_box.setReadOnly(True)

            self._build_ui()
            self._append_log("YES-NK 桌面客户端已就绪（国服 PC 端 / 仿 YES-BD2 架构）。")

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

            # 左侧 Fluent 导航栏
            sidebar_wrap = QWidget()
            sidebar_wrap.setFixedWidth(220)
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
                    "桌面分身与 1080P 校准",
                    "MaaNikke 素材导入",
                    "运行日志与排障",
                ]
            )
            self.nav_list.setCurrentRow(0)
            sb_layout.addWidget(self.nav_list)
            root_layout.addWidget(sidebar_wrap)

            # 右侧主内容区
            right_wrap = QWidget()
            right_layout = QVBoxLayout(right_wrap)
            right_layout.setContentsMargins(20, 16, 20, 16)
            right_layout.setSpacing(14)

            # 顶部操作栏
            header = QHBoxLayout()
            self.page_title = QLabel("国服基础日常一条龙")
            self.page_title.setStyleSheet("font-size:16px; font-weight:700;")
            header.addWidget(self.page_title)
            header.addStretch(1)

            btn_save = QPushButton("保存配置")
            btn_save.clicked.connect(self._on_save_config)
            header.addWidget(btn_save)

            btn_start_ok = QPushButton("启动 ok-script 自动化")
            btn_start_ok.setObjectName("PrimaryButton")
            btn_start_ok.clicked.connect(lambda: self._on_launch_ok(debug=False))
            header.addWidget(btn_start_ok)
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
                "仿 YES-BD2 桌面分身与 1080P 适配",
                "MaaNikke 素材与 Pipeline 导入转换",
                "桌面客户端运行日志",
            ]
            if 0 <= idx < len(titles):
                self.page_title.setText(titles[idx])
                self.pages.setCurrentIndex(idx)

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
                "勾选需要执行的项目，然后点击启动："
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
            btn_clone_start = QPushButton("在桌面分身内一键启动 (仿 YES-BD2)")
            btn_clone_start.setObjectName("PrimaryButton")
            btn_clone_start.clicked.connect(self._on_launch_in_clone)
            action_row.addWidget(btn_clone_start)

            btn_debug = QPushButton("调试模式启动 (main_debug)")
            btn_debug.clicked.connect(lambda: self._on_launch_ok(debug=True))
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
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(14)

            # 1. 桌面分身控制卡
            clone_card = self._make_card()
            clone_grid = QGridLayout(clone_card)
            clone_grid.setContentsMargins(18, 16, 18, 16)
            clone_grid.setSpacing(10)

            clone_grid.addWidget(QLabel("运行隔离模式"), 0, 0)
            self.mode_combo = QComboBox()
            self.mode_combo.addItem("桌面分身模式（CreateDesktopW · 首选）", "desktop_clone")
            self.mode_combo.addItem("后台窗口消息模式（PostMessage）", "background_post_message")
            self.mode_combo.addItem("前台兼容兜底模式（Pynput）", "foreground_compat")
            idx = self.mode_combo.findData(self.controller.state.run_mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            clone_grid.addWidget(self.mode_combo, 0, 1)

            clone_grid.addWidget(QLabel("分身桌面名称"), 1, 0)
            self.desktop_name_input = QLineEdit(self.controller.state.desktop_name)
            clone_grid.addWidget(self.desktop_name_input, 1, 1)

            clone_grid.addWidget(QLabel("游戏窗口标题"), 2, 0)
            self.window_title_input = QLineEdit(self.controller.state.window_title)
            clone_grid.addWidget(self.window_title_input, 2, 1)

            btn_row = QHBoxLayout()
            btn_enter_clone = QPushButton("创建并进入桌面分身")
            btn_enter_clone.setObjectName("PrimaryButton")
            btn_enter_clone.clicked.connect(self._on_launch_in_clone)
            btn_row.addWidget(btn_enter_clone)

            btn_back_default = QPushButton("切回 Windows 主桌面")
            btn_back_default.clicked.connect(self._on_switch_default)
            btn_row.addWidget(btn_back_default)
            btn_row.addStretch(1)
            clone_grid.addLayout(btn_row, 3, 0, 1, 2)
            layout.addWidget(clone_card)

            # 2. 1080P 窗口检测与一键校准卡
            win_card = self._make_card()
            win_layout = QVBoxLayout(win_card)
            win_layout.setContentsMargins(18, 16, 18, 16)
            win_layout.setSpacing(10)

            win_title = QLabel("1080P 屏幕窗口客户区检测与一键 16:9 校准")
            win_title.setStyleSheet("font-weight:600;")
            win_layout.addWidget(win_title)

            self.geometry_status_label = QLabel(
                "点击下方按钮实时检测正在运行的 nikke.exe 客户区尺寸，或直接一键校准为 1600×900 (16:9)。"
            )
            self.geometry_status_label.setWordWrap(True)
            self.geometry_status_label.setStyleSheet("color:#475569;")
            win_layout.addWidget(self.geometry_status_label)

            win_btn_row = QHBoxLayout()
            btn_check = QPushButton("检测当前游戏窗口尺寸")
            btn_check.clicked.connect(self._on_check_live_window)
            win_btn_row.addWidget(btn_check)

            btn_cal_900 = QPushButton("一键校准为 1600×900 (1080P 窗口推荐)")
            btn_cal_900.clicked.connect(lambda: self._on_calibrate_window(1600, 900))
            win_btn_row.addWidget(btn_cal_900)

            btn_cal_720 = QPushButton("校准为 1280×720")
            btn_cal_720.clicked.connect(lambda: self._on_calibrate_window(1280, 720))
            win_btn_row.addWidget(btn_cal_720)
            win_btn_row.addStretch(1)
            win_layout.addLayout(win_btn_row)

            layout.addWidget(win_card)
            layout.addStretch(1)
            return page

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
                "校验所有节点到 YES-NK 21 个原生状态机任务的映射覆盖率："
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
            layout.addWidget(self.log_box)
            return page

        def _sync_form_to_controller(self) -> None:
            st = self.controller.state
            st.run_mode = self.mode_combo.currentData()
            st.desktop_name = self.desktop_name_input.text().strip() or "YES_NK_Desktop"
            st.window_title = self.window_title_input.text().strip() or "NIKKE"
            st.daily_toggles = {
                name: cb.isChecked() for name, cb in self.daily_checkboxes.items()
            }

        def _on_save_config(self) -> None:
            self._sync_form_to_controller()
            saved = self.controller.save_state()
            self._append_log(f"已保存配置至 {saved}")
            QMessageBox.information(self, "配置已保存", f"已写入 {saved.name}，启动 ok-script 时将自动生效。")

        def _on_launch_ok(self, debug: bool = False) -> None:
            self._sync_form_to_controller()
            self.controller.save_state()
            argv = self.controller.build_ok_launch_argv(debug=debug)
            self._append_log(f"启动自动化引擎: {' '.join(argv)}")
            try:
                subprocess.Popen(argv, cwd=str(PROJECT_ROOT))
            except Exception as exc:
                self._append_log(f"启动失败: {exc}")
                QMessageBox.warning(self, "启动失败", str(exc))

        def _on_launch_in_clone(self) -> None:
            idx = self.mode_combo.findData("desktop_clone")
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            self._on_launch_ok(debug=False)

        def _on_switch_default(self) -> None:
            mgr = self.controller.create_desktop_clone_manager()
            ok = mgr.switch_to_default()
            self._append_log("已切回 Windows 主桌面" if ok else "切回主桌面失败（请确认在 Windows 下运行）")

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
