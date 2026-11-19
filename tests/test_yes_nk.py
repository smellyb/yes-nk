"""YES-NK Python 自动化核心单测（无游戏窗口环境下覆盖全部 21 条 MaaNikke 转换流水线）。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.convert_maa_assets import (
    analyze_maa_pipeline_directory,
    convert_maa_directory_to_coco,
)
from yes_nk.config import build_desktop_clone_config, config
from yes_nk.tasks.CashShopFreeTask import is_safe_free_cash_shop_text
from yes_nk.tasks.DailyTask import ALL_PIPELINE_SPECS, DailyTask
from yes_nk.tasks.PopupGuardTrigger import PopupGuardTrigger
from yes_nk.tasks.SocialRecruitTask import is_social_recruit_banner
from yes_nk.utils.desktop_clone import (
    DesktopCloneConfig,
    WindowsDesktopCloneManager,
    resolve_ok_interaction_class,
)
from yes_nk.utils.shop_guard import ShopSlotObservation, evaluate_shop_slot
from yes_nk.utils.window_1080p import evaluate_client_geometry


@dataclass
class FakeHit:
    name: str


def _write_minimal_png(path: Path, width: int = 32, height: int = 24) -> None:
    """写入合法的最小 1-bit PNG 文件供转换器单测使用。"""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


class FakeDailyTaskHarness(DailyTask):
    """覆盖底层截屏/点击 IO，验证全部 21 条 MaaNikke 转换流水线串联执行。"""

    def __init__(self, enable_all: bool = True) -> None:
        super().__init__()
        if enable_all:
            for key, _cat, _default, _cls in ALL_PIPELINE_SPECS:
                self.config[key] = True
        self.events: list[str] = []

    def _build_subtask(self, task_cls):
        parent = self

        class InstrumentedSubtask(task_cls):
            def __init__(self_inner) -> None:
                super().__init__()
                self_inner._sim_steps = 0

            def sleep(self_inner, seconds: float) -> None:
                _ = seconds

            def ocr(self_inner, *args, **kwargs):
                match = kwargs.get("match")
                box = kwargs.get("box")
                box_name = box[4] if isinstance(box, tuple) and len(box) >= 5 else ""

                if box_name == "lobby_nav":
                    return [FakeHit("大厅"), FakeHit("妮姬")]
                if box_name.startswith("shop_slot_"):
                    if box_name.endswith("_0"):
                        return [FakeHit("免费")]
                    if box_name.endswith("_1"):
                        return [FakeHit("300 珠宝")]
                    if box_name.endswith("_2"):
                        return [FakeHit("已售罄")]
                    return [FakeHit("免费")]
                if box_name in ("wipe_out_free_check", "shop_free_refresh_check", "arena_free_check"):
                    return [FakeHit("免费")]
                if box_name == "cash_shop_free_scan":
                    return [FakeHit("每日免费礼包 免费")]
                if box_name == "recruit_banner_title":
                    return [FakeHit("社交点招募")]
                if box_name == "sim_room_state":
                    self_inner._sim_steps += 1
                    if self_inner._sim_steps == 1:
                        return [FakeHit("快速战斗")]
                    if self_inner._sim_steps == 2:
                        return [FakeHit("不选择")]
                    return [FakeHit("结束模拟")]
                if isinstance(match, list) and match:
                    if "战斗失败" in match:
                        return []
                    return [FakeHit(match[0])]
                return []

            def find_one(self_inner, feature_name: str, *args, **kwargs):
                if feature_name == "shop_diamond_icon":
                    box = kwargs.get("box")
                    if isinstance(box, tuple) and box[0] == 0.35:
                        return FakeHit("shop_diamond_icon")
                    return None
                if feature_name in ("popup_dont_show_today", "popup_close_x"):
                    return None
                return FakeHit(feature_name)

            def click_box(self_inner, box, *args, **kwargs):
                parent.events.append(f"{task_cls.__name__}:click:{getattr(box, 'name', box)}")

            def click_relative(self_inner, x: float, y: float, *args, **kwargs):
                parent.events.append(f"{task_cls.__name__}:click_rel:{x:.2f},{y:.2f}")

        return InstrumentedSubtask()

    def sleep(self, seconds: float) -> None:
        _ = seconds

    def ocr(self, *args, **kwargs):
        return [FakeHit("大厅"), FakeHit("妮姬")]


class YesNkCoreTests(unittest.TestCase):
    def test_1080p_geometry_validation(self) -> None:
        optimal = evaluate_client_geometry(1920, 1080, dpi_scale_percent=100)
        self.assertTrue(optimal.is_valid)
        self.assertEqual(optimal.status, "optimal_1080p")
        self.assertEqual(optimal.scale_x, 1.0)

        scaled_900p = evaluate_client_geometry(1600, 900, dpi_scale_percent=125)
        self.assertTrue(scaled_900p.is_valid)
        self.assertEqual(scaled_900p.status, "valid_scaled_16_9")
        self.assertIn("125%", scaled_900p.recommendation)

        squished = evaluate_client_geometry(1920, 1009, dpi_scale_percent=100)
        self.assertFalse(squished.is_valid)
        self.assertEqual(squished.status, "non_16_9")

        too_small = evaluate_client_geometry(960, 540)
        self.assertFalse(too_small.is_valid)
        self.assertEqual(too_small.status, "too_small")

    def test_desktop_clone_config_and_interactions(self) -> None:
        import os
        from yes_nk.gui.clone_host import build_in_clone_ok_argv
        from yes_nk.utils.desktop_clone import (
            MOD_ALT,
            MOD_CONTROL,
            MOD_NOREPEAT,
            MOD_SHIFT,
            build_command_line,
            parse_hotkey_spec,
        )

        dc = DesktopCloneConfig(desktop_name="YES NK 桌面#1")
        self.assertEqual(dc.sanitized_desktop_name(), "YES_NK____1")

        mgr = WindowsDesktopCloneManager(dc)
        self.assertEqual(mgr.build_process_desktop_attr(), "WinSta0\\YES_NK____1")

        # 热键解析验证（Ctrl+Alt+F12 / Ctrl+Shift+H）
        mods_f12, vk_f12 = parse_hotkey_spec("Ctrl+Alt+F12")
        self.assertEqual(mods_f12, MOD_NOREPEAT | MOD_CONTROL | MOD_ALT)
        self.assertEqual(vk_f12, 0x7B)

        mods_h, vk_h = parse_hotkey_spec("Ctrl+Shift+H")
        self.assertEqual(mods_h, MOD_NOREPEAT | MOD_CONTROL | MOD_SHIFT)
        self.assertEqual(vk_h, ord("H"))

        # 带空格路径的命令行安全转义
        cmd = build_command_line([r"C:\Program Files\Python311\python.exe", r"D:\YES NK\main.py", "--clone-host"])
        self.assertIn('"C:\\Program Files\\Python311\\python.exe"', cmd)
        self.assertIn("--clone-host", cmd)

        # 验证已存活 Clone Host 复用检测（避免重复创建）
        with tempfile.TemporaryDirectory() as tmp:
            ready_file = Path(tmp) / "clone_host_ready.json"
            ready_file.write_text(
                json.dumps({"pid": os.getpid(), "desktop": mgr.desktop_name, "ts": 12345.0}),
                encoding="utf-8",
            )
            self.assertEqual(mgr.check_existing_clone_host(ready_file), os.getpid())

            # 不同桌面名称不误复用
            ready_file.write_text(
                json.dumps({"pid": os.getpid(), "desktop": "Other_Desktop", "ts": 12345.0}),
                encoding="utf-8",
            )
            self.assertIsNone(mgr.check_existing_clone_host(ready_file))

        ok_argv = build_in_clone_ok_argv(debug=True)
        self.assertIn("--in-clone", ok_argv)
        self.assertIn("--debug", ok_argv)

        self.assertEqual(resolve_ok_interaction_class("desktop_clone"), "ForegroundPostMessage")
        self.assertEqual(resolve_ok_interaction_class("background_post_message"), "PostMessage")
        self.assertEqual(resolve_ok_interaction_class("foreground_compat"), "Pynput")

        parsed = build_desktop_clone_config(
            {
                "desktop_clone": {
                    "run_mode": "background_post_message",
                    "game_exe_path": r"D:\Games\NIKKE\nikke.exe",
                }
            }
        )
        self.assertEqual(parsed.run_mode, "background_post_message")
        self.assertEqual(parsed.game_exe_path, r"D:\Games\NIKKE\nikke.exe")

    def test_safety_guards_shop_cash_and_recruit(self) -> None:
        # 1. 普通商店钻石防误买护栏
        diamond_slot = ShopSlotObservation(0, "免费 300 珠宝", has_diamond_icon=True)
        self.assertFalse(evaluate_shop_slot(diamond_slot, allow_credit_discount=True).should_buy)

        free_slot = ShopSlotObservation(1, "免费")
        self.assertTrue(evaluate_shop_slot(free_slot).should_buy)

        credit_low = ShopSlotObservation(2, "5000", discount_text="-30%", has_credit_icon=True)
        self.assertFalse(
            evaluate_shop_slot(
                credit_low, allow_credit_discount=True, min_credit_discount_percent=50
            ).should_buy
        )

        credit_high = ShopSlotObservation(3, "2500", discount_text="-60%", has_credit_icon=True)
        self.assertTrue(
            evaluate_shop_slot(
                credit_high, allow_credit_discount=True, min_credit_discount_percent=50
            ).should_buy
        )

        # 2. 付费商店免费礼包护栏（严禁触碰 RMB/￥/¥/珠宝）
        self.assertTrue(is_safe_free_cash_shop_text("每日免费礼包 免费"))
        self.assertFalse(is_safe_free_cash_shop_text("￥6 每日特惠礼包"))
        self.assertFalse(is_safe_free_cash_shop_text("免费赠品 ¥30 组合包"))
        self.assertFalse(is_safe_free_cash_shop_text("6元 首充礼包"))
        self.assertFalse(is_safe_free_cash_shop_text("免费 300 珠宝"))
        self.assertFalse(is_safe_free_cash_shop_text("已售罄 免费"))

        # 3. 社交点招募卡池护栏（严禁误抽珠宝卡池）
        self.assertTrue(is_social_recruit_banner("社交点招募"))
        self.assertTrue(is_social_recruit_banner("友情点招募"))
        self.assertFalse(is_social_recruit_banner("特殊招募 概率UP"))
        self.assertFalse(is_social_recruit_banner("普通招募"))
        self.assertFalse(is_social_recruit_banner("限定招募 社交点"))

    def test_maa_to_coco_converter_and_pipeline_analyzer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            maa_dir = tmp_path / "maa_images"
            maa_dir.mkdir()
            _write_minimal_png(maa_dir / "mailbox_entry.png", 48, 36)
            _write_minimal_png(maa_dir / "shop_refresh.png", 64, 28)
            _write_minimal_png(maa_dir / "interception_boss.png", 96, 48)

            out_json = tmp_path / "out" / "result.json"
            out_imgs = tmp_path / "out" / "images"

            report = convert_maa_directory_to_coco(
                maa_image_dir=maa_dir,
                output_json_path=out_json,
                output_images_dir=out_imgs,
            )

            self.assertIn("lobby_mail_icon", report.matched_features)
            self.assertIn("shop_refresh_btn", report.matched_features)
            self.assertIn("ark_interception_entry", report.matched_features)
            self.assertTrue(out_json.exists())

            coco = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(len(coco["categories"]), 44)
            self.assertEqual(len(coco["images"]), len(report.matched_features))
            # 验证合成出的 ok-script 画布为 1280x720，且 bbox 为原始模板宽高
            self.assertEqual(coco["images"][0]["width"], 1280)
            self.assertEqual(coco["images"][0]["height"], 720)
            self.assertEqual(coco["annotations"][0]["bbox"][2:], [48, 36])

            # 测试 MaaNikke pipeline JSON 解析与覆盖映射
            pipe_dir = tmp_path / "maa_pipeline"
            pipe_dir.mkdir()
            (pipe_dir / "interception.json").write_text(
                json.dumps(
                    {
                        "EnterInterception": {"template": "ark/interception.png"},
                        "QuickBattle": {"template": ["ark/quick.png", "ark/confirm.png"]},
                    }
                ),
                encoding="utf-8",
            )
            (pipe_dir / "simulation_room.json").write_text(
                json.dumps({"StartSim": {"template": "sim/start.png"}}),
                encoding="utf-8",
            )
            (pipe_dir / "arena.json").write_text(
                json.dumps({"RookieArena": {"template": "arena/rookie.png"}}),
                encoding="utf-8",
            )

            p_report = analyze_maa_pipeline_directory(pipe_dir)
            self.assertEqual(p_report.scanned_files, 3)
            self.assertEqual(p_report.total_nodes, 4)
            self.assertIn("yes_nk.tasks.InterceptionTask.InterceptionTask", p_report.mapped_tasks)
            self.assertIn("yes_nk.tasks.SimulationRoomTask.SimulationRoomTask", p_report.mapped_tasks)
            self.assertIn("yes_nk.tasks.ArenaTask.ArenaTask", p_report.mapped_tasks)
            self.assertEqual(len(p_report.referenced_templates), 5)

    def test_preconverted_real_maa_coco_assets(self) -> None:
        """验证仓库已内置从 Shinarin/MaaNikke 直接转换好的 40 项 1280x720 ok-script 模板。"""
        from tools.convert_maa_assets import decode_png_rgb

        root = Path(__file__).resolve().parent.parent
        result_json = root / "assets" / "result.json"
        self.assertTrue(result_json.exists())
        coco = json.loads(result_json.read_text(encoding="utf-8"))
        self.assertEqual(len(coco["categories"]), 44)
        self.assertGreaterEqual(len(coco["images"]), 40)
        self.assertEqual(len(coco["images"]), len(coco["annotations"]))

        for img_meta, ann in zip(coco["images"], coco["annotations"]):
            img_path = root / "assets" / img_meta["file_name"]
            self.assertTrue(img_path.exists(), f"缺少特征图: {img_path}")
            self.assertEqual(img_meta["width"], 1280)
            self.assertEqual(img_meta["height"], 720)
            bx, by, bw, bh = ann["bbox"]
            self.assertGreater(bw, 0)
            self.assertGreater(bh, 0)
            self.assertLessEqual(bx + bw, 1280)
            self.assertLessEqual(by + bh, 720)

        # 抽检一张真实转换后的模板可无损解码且包含非零像素
        sample_w, sample_h, sample_rgb = decode_png_rgb(root / "assets" / "images" / "lobby_ark_icon.png")
        self.assertEqual((sample_w, sample_h), (1280, 720))
        self.assertTrue(any(b != 0 for b in sample_rgb))

    def test_all_22_pipelines_in_daily_task_and_config(self) -> None:
        self.assertEqual(len(ALL_PIPELINE_SPECS), 22)
        # config.py 包含 DailyTask + 全部 22 个独立任务 = 23
        self.assertEqual(len(config["onetime_tasks"]), 23)

        harness = FakeDailyTaskHarness(enable_all=True)
        summary = harness.run()

        for key, _cat, _default, _cls in ALL_PIPELINE_SPECS:
            self.assertEqual(summary.get(key), "ok", f"流水线 {key} 执行未返回 ok: {summary}")

        # 确认普通商店绝对没有点击位于 x=0.35..0.50 (中心 0.42) 的钻石货架
        self.assertFalse(any("ShopTask:click_rel:0.42" in e for e in harness.events))
        # 确认普通商店购买了 0 号免费格 (中心 0.26)
        self.assertTrue(any("ShopTask:click_rel:0.26" in e for e in harness.events))

        # 验证配置结构符合 ok-script 规范
        self.assertEqual(config["supported_resolution"]["ratio"], "16:9")
        self.assertEqual(config["supported_resolution"]["min_size"], (1280, 720))

        # 验证触发守护任务可响应断线重连弹窗
        trigger = PopupGuardTrigger()
        clicked: list[str] = []
        trigger.ocr = lambda *a, **kw: [FakeHit("重新连接")]  # type: ignore[method-assign]
        trigger.click_box = lambda box, *a, **kw: clicked.append(box.name)  # type: ignore[method-assign]
        trigger.sleep = lambda s: None  # type: ignore[method-assign]
        self.assertTrue(trigger.run())
        self.assertEqual(clicked, ["重新连接"])

    def test_desktop_client_controller_and_icons(self) -> None:
        from tools.generate_icon import generate_icons
        from yes_nk.gui.controller import (
            DEFAULT_DAILY_TOGGLES,
            DesktopClientController,
            get_grouped_pipelines,
        )

        self.assertEqual(len(DEFAULT_DAILY_TOGGLES), 22)
        grouped = get_grouped_pipelines()
        self.assertEqual(sum(len(v) for v in grouped.values()), 22)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg_path = tmp_path / "yes_nk_config.json"
            ctrl = DesktopClientController(config_path=cfg_path)
            ctrl.state.run_mode = "desktop_clone"
            ctrl.state.desktop_name = "YES NK 桌面"
            ctrl.state.daily_toggles["邮箱一键领取"] = False
            ctrl.state.daily_toggles["大型活动刷取与签到"] = True
            ctrl.save_state()

            reloaded = DesktopClientController(config_path=cfg_path)
            self.assertEqual(reloaded.state.run_mode, "desktop_clone")
            self.assertEqual(reloaded.state.desktop_name, "YES_NK")
            self.assertFalse(reloaded.state.daily_toggles["邮箱一键领取"])
            self.assertTrue(reloaded.state.daily_toggles["大型活动刷取与签到"])

            argv = reloaded.build_ok_launch_argv(debug=True)
            self.assertIn("--desktop-clone", argv)
            self.assertIn("--debug", argv)

            png_path, ico_path = generate_icons(output_dir=tmp_path / "icons")
            self.assertTrue(png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertTrue(ico_path.read_bytes().startswith(b"\x00\x00\x01\x00"))

        root = Path(__file__).resolve().parent.parent
        self.assertTrue((root / "desktop_launcher.py").exists())
        self.assertTrue((root / "yes_nk.spec").exists())
        self.assertTrue((root / "scripts" / "start_yes_nk.bat").exists())
        self.assertTrue((root / ".github" / "workflows" / "build-windows-release.yml").exists())


if __name__ == "__main__":
    unittest.main()
