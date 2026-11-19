# -*- mode: python ; coding: utf-8 -*-
"""YES-NK PyInstaller 打包配置：生成便携式 Windows 桌面客户端 dist/YES-NK/YES-NK.exe。"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve()

hidden_imports = [
    "yes_nk.config",
    "yes_nk.tasks.DailyTask",
    "yes_nk.tasks.AutoLoginTask",
    "yes_nk.tasks.MailTask",
    "yes_nk.tasks.FriendPointTask",
    "yes_nk.tasks.OutpostDefenseTask",
    "yes_nk.tasks.DispatchTask",
    "yes_nk.tasks.CashShopFreeTask",
    "yes_nk.tasks.ShopTask",
    "yes_nk.tasks.SocialRecruitTask",
    "yes_nk.tasks.AdviseGiftTask",
    "yes_nk.tasks.EquipmentUpgradeTask",
    "yes_nk.tasks.LoopRoomAndSyncTask",
    "yes_nk.tasks.LiberationTask",
    "yes_nk.tasks.InterceptionTask",
    "yes_nk.tasks.SimulationRoomTask",
    "yes_nk.tasks.ArenaTask",
    "yes_nk.tasks.TribeTowerTask",
    "yes_nk.tasks.RaidAndCoopTasks",
    "yes_nk.tasks.EventStoryTask",
    "yes_nk.tasks.DailyMissionTask",
    "yes_nk.tasks.PassRewardTask",
    "yes_nk.tasks.PopupGuardTrigger",
    "yes_nk.gui.clone_host",
    "yes_nk.gui.desktop_client",
    "yes_nk.gui.controller",
    "tools.convert_maa_assets",
]

try:
    hidden_imports += collect_submodules("ok")
except Exception:
    pass

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "README.md"), "."),
]

icon_file = ROOT / "assets" / "icon.ico"

a = Analysis(
    [str(ROOT / "desktop_launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YES-NK",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_file) if icon_file.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="YES-NK",
)
