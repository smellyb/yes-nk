"""YES-NK 桌面客户端视觉主题系统（完全对齐 YES-BD2 `淡紫 / 深色` oink-ui 规范）。

包含两套官方色板：
- LIGHT ("淡紫"): #F4F3F9 画布 / #EEECF6 圆角侧边栏 / #FFFFFF 浮起卡片 / #7467C4 淡紫主色
- DARK  ("深色"): #16151D 紫黑画布 / #2B2A37 圆角侧边栏 / #23222E 浮起卡片 / #7467C4 主色
"""

from __future__ import annotations

LIGHT_TOKENS: dict[str, str] = {
    "bg": "#F4F3F9",
    "side": "#EEECF6",
    "card": "#FFFFFF",
    "card_line": "#FFFFFF",
    "inset": "#F6F5FA",
    "line": "#EEECF6",
    "line2": "#DEDBEA",
    "well": "#ECEAF3",
    "well2": "#DCD9E8",
    "raised": "#FFFFFF",
    "fill": "#ECEAF3",
    "fill_hover": "#DCD9E8",
    "ink": "#1F1D29",
    "ink2": "#4A4759",
    "ink3": "#5C596B",
    "primary": "#7467C4",
    "primary_hover": "#675AB5",
    "on_primary": "#FFFFFF",
    "accent_soft": "#EFEDF6",
    "ghost_ink": "#5B4FB0",
    "ok": "#2E7A70",
    "ok_soft": "#E4F1EF",
    "warn": "#B98012",
    "warn_soft": "#FAF0D7",
    "bad": "#D4788C",
    "bad_soft": "#FAEBEF",
    "skip": "#C9C5D8",
    "shot": "#1B1A26",
    "shadow": "#4A3F8C",
    "nav_icon": "#4F4B60",
    "nav_on": "#FFFFFF",
    "nav_on_ink": "#1F1D29",
    "nav_on_icon": "#FFFFFF",
    "nav_on_circle": "#7467C4",
    "ring": "#DEDBEA",
    "badge": "#EFEDF6",
    "badge_ink": "#5C596B",
    "badge_on": "#EFEDF6",
    "badge_on_ink": "#5B4FB0",
    "badge_ok": "#E4F1EF",
    "row_on": "#EFEDF6",
}

DARK_TOKENS: dict[str, str] = {
    "bg": "#16151D",
    "side": "#2B2A37",
    "card": "#23222E",
    "card_line": "#23222E",
    "inset": "#1E1D27",
    "line": "#2B2A37",
    "line2": "#383646",
    "well": "#1A1922",
    "well2": "#3A3849",
    "raised": "#3A3849",
    "fill": "#33313F",
    "fill_hover": "#3F3D4D",
    "ink": "#ECEAF4",
    "ink2": "#B5B2C4",
    "ink3": "#9B98AD",
    "primary": "#7467C4",
    "primary_hover": "#8A80D8",
    "on_primary": "#FFFFFF",
    "accent_soft": "#2C2A3B",
    "ghost_ink": "#B4ABF6",
    "ok": "#93CFC5",
    "ok_soft": "#1F3534",
    "warn": "#E3B04B",
    "warn_soft": "#3A3123",
    "bad": "#D4788C",
    "bad_soft": "#3B2832",
    "skip": "#4C4A5B",
    "shot": "#0E0D13",
    "shadow": "#000000",
    "nav_icon": "#C6C3D5",
    "nav_on": "#23222E",
    "nav_on_ink": "#ECEAF4",
    "nav_on_icon": "#FFFFFF",
    "nav_on_circle": "#7467C4",
    "ring": "#383646",
    "badge": "#2C2A3B",
    "badge_ink": "#9B98AD",
    "badge_on": "#2C2A3B",
    "badge_on_ink": "#B4ABF6",
    "badge_ok": "#1F3534",
    "row_on": "#2C2A3B",
}

SHAPES: dict[str, int | float | bool] = {
    "card": 20,
    "inset": 14,
    "side_inset": 10,
    "side_width": 208,
    "control_sm": 28,
    "control_md": 34,
    "control_lg": 40,
}


def get_tokens(mode: str = "light") -> dict[str, str]:
    """返回指定主题（light=淡紫, dark=深色）的色板字典。"""
    return DARK_TOKENS if mode == "dark" else LIGHT_TOKENS


def build_shell_qss(mode: str = "light") -> str:
    """生成与 YES-BD2 `theme.style_sheet()` 一致的 PySide6 全局样式表。"""
    t = get_tokens(mode)
    card_r = int(SHAPES["card"])
    inset_r = int(SHAPES["inset"])
    return f"""
QMainWindow, QWidget#ShellRoot {{
    background-color: {t["bg"]};
    color: {t["ink"]};
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QWidget {{
    color: {t["ink"]};
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QFrame#ShellSidebar {{
    background-color: {t["side"]};
    border: none;
    border-radius: {card_r}px;
}}
QFrame#StatusFooter {{
    background-color: {t["card"]};
    border: none;
    border-radius: {inset_r}px;
}}
QFrame[card="true"] {{
    background-color: {t["card"]};
    border: 1px solid {t["line"]};
    border-radius: {card_r}px;
}}
QFrame[inset="true"] {{
    background-color: {t["inset"]};
    border: none;
    border-radius: {inset_r}px;
}}
QFrame[sep="true"] {{
    background-color: {t["line"]};
    border: none;
    min-height: 1px;
    max-height: 1px;
}}
QFrame[segmented="true"] {{
    background-color: {t["well"]};
    border: none;
    border-radius: 17px;
}}
QLabel {{
    background: transparent;
    color: {t["ink"]};
}}
QLabel[role="h1"] {{
    font-size: 23px;
    font-weight: 700;
    color: {t["ink"]};
}}
QLabel[role="h2"] {{
    font-size: 15px;
    font-weight: 600;
    color: {t["ink"]};
}}
QLabel[role="h3"] {{
    font-size: 14px;
    color: {t["ink"]};
}}
QLabel[role="huge"] {{
    font-size: 28px;
    font-weight: 700;
    color: {t["ink"]};
}}
QLabel[role="big"] {{
    font-size: 24px;
    font-weight: 700;
    color: {t["ink"]};
}}
QLabel[role="sub"] {{
    font-size: 13px;
    color: {t["ink2"]};
}}
QLabel[role="muted"] {{
    font-size: 12px;
    color: {t["ink3"]};
}}
QLabel[role="eyebrow"] {{
    font-size: 12px;
    color: {t["ink3"]};
}}
QLabel[role="ok"] {{
    color: {t["ok"]};
}}
QLabel[role="warn"] {{
    color: {t["warn"]};
}}
QLabel[role="bad"] {{
    color: {t["bad"]};
}}
QPushButton {{
    background-color: {t["fill"]};
    color: {t["ink"]};
    border: none;
    border-radius: 17px;
    min-height: 34px;
    max-height: 34px;
    padding: 0px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {t["fill_hover"]};
}}
QPushButton:disabled {{
    color: {t["ink3"]};
}}
QPushButton[kind="primary"] {{
    background-color: {t["primary"]};
    color: {t["on_primary"]};
    border: none;
}}
QPushButton[kind="primary"]:hover {{
    background-color: {t["primary_hover"]};
}}
QPushButton[kind="primary"]:disabled {{
    background-color: {t["line2"]};
    color: {t["ink3"]};
}}
QPushButton[kind="danger"] {{
    background-color: {t["bad_soft"]};
    color: {t["bad"]};
    border: none;
}}
QPushButton[kind="danger"]:hover {{
    background-color: {t["bad"]};
    color: #FFFFFF;
}}
QPushButton[kind="flat"] {{
    background-color: transparent;
    color: {t["ink2"]};
    border: none;
    padding: 0px 8px;
}}
QPushButton[kind="flat"]:hover {{
    color: {t["ink"]};
}}
QPushButton[size="lg"] {{
    min-height: 40px;
    max-height: 40px;
    border-radius: 20px;
    padding: 0px 20px;
    font-size: 14px;
}}
QPushButton[size="sm"] {{
    min-height: 28px;
    max-height: 28px;
    border-radius: 14px;
    padding: 0px 12px;
    font-size: 12px;
}}
QPushButton[seg="true"] {{
    background-color: transparent;
    color: {t["ink2"]};
    border: none;
    border-radius: 14px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px 10px;
    font-size: 12px;
}}
QPushButton[seg="true"]:checked {{
    background-color: {t["raised"]};
    color: {t["ink"]};
}}
QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    background-color: {t["inset"]};
    color: {t["ink"]};
    border: 1px solid {t["line2"]};
    border-radius: 10px;
    padding: 6px 10px;
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {t["primary"]};
}}
QCheckBox {{
    spacing: 8px;
    color: {t["ink"]};
    background: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1.5px solid {t["line2"]};
    background: {t["card"]};
}}
QCheckBox::indicator:checked {{
    background-color: {t["primary"]};
    border-color: {t["primary"]};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    margin: 4px 0px;
}}
QScrollBar::handle:vertical {{
    background: {t["line2"]};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
