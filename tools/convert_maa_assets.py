"""MaaNikke 模板与流水线 JSON -> YES-NK (ok-script) 原生 COCO 特征包转换工具。

用法示例：
  python tools/convert_maa_assets.py --maa-dir D:\\MaaNikke\\resource\\base\\image --maa-pipeline-dir D:\\MaaNikke\\resource\\base\\pipeline

核心原理（对齐 ok-script FeatureSet.read_from_json）：
- Shinarin/MaaNikke 的官方模板素材均截取自 1280×720 (16:9) 基准画面；
- ok-script 读取 assets/result.json 时，会将对应 PNG 图片的宽高视为基准屏幕分辨率，再按 bbox
  裁切模板并等比缩放至目标游戏窗口（1920×1080 自动 1.5x、1600×900 自动 1.25x、1280×720 1.0x）；
- 因此本工具内置零依赖纯 Python 无损 PNG 编解码器，将每个匹配到的 MaaNikke 模板精准合成到
  1280×720 基准画布的对应 ROI 位置，输出标准 assets/images/<feature>.png 与 assets/result.json。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import struct
from typing import Any
import zlib


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "assets" / "coco_manifest.json"
DEFAULT_OUTPUT_JSON = PROJECT_ROOT / "assets" / "result.json"
DEFAULT_OUTPUT_IMAGES = PROJECT_ROOT / "assets" / "images"

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


MAA_PIPELINE_TO_YES_NK: list[tuple[tuple[str, ...], str, str]] = [
    (("startgame", "startup", "start_game", "loginrewards", "login", "launch", "启动", "登录"), "yes_nk.tasks.AutoLoginTask", "AutoLoginTask"),
    (("claimmail", "mail", "mailbox", "邮件", "邮箱"), "yes_nk.tasks.MailTask", "MailTask"),
    (("friendpoints", "friend", "social_point", "好友"), "yes_nk.tasks.FriendPointTask", "FriendPointTask"),
    (("outpostdefense", "outpost", "defense", "wipe", "前哨", "防御", "歼灭"), "yes_nk.tasks.OutpostDefenseTask", "OutpostDefenseTask"),
    (("dispatchboard", "dispatch", "bulletin", "派遣", "公告栏"), "yes_nk.tasks.DispatchTask", "DispatchTask"),
    (("payshop", "cash", "charge", "付费商店", "礼包"), "yes_nk.tasks.CashShopFreeTask", "CashShopFreeTask"),
    (("freeshopdaily", "shop", "store", "商店"), "yes_nk.tasks.ShopTask", "ShopTask"),
    (("teamrecruit", "recruit", "gacha", "招募"), "yes_nk.tasks.SocialRecruitTask", "SocialRecruitTask"),
    (("inquiryandgift", "advise", "counsel", "gift", "咨询", "送礼"), "yes_nk.tasks.AdviseGiftTask", "AdviseGiftTask"),
    (("gearup", "equip", "upgrade", "装备"), "yes_nk.tasks.EquipmentUpgradeTask", "EquipmentUpgradeTask"),
    (("looproomandsync", "looproom", "sync", "循环室", "同步器"), "yes_nk.tasks.LoopRoomAndSyncTask", "LoopRoomAndSyncTask"),
    (("gengshengguan", "liberation", "rehab", "更生", "解放"), "yes_nk.tasks.LiberationTask", "LiberationTask"),
    (("interception", "boss", "拦截"), "yes_nk.tasks.InterceptionTask", "InterceptionTask"),
    (("simroom", "simulation", "sim_room", "模拟室"), "yes_nk.tasks.SimulationRoomTask", "SimulationRoomTask"),
    (("arena", "rookie", "special_arena", "竞技场"), "yes_nk.tasks.ArenaTask", "ArenaTask"),
    (("climbtower", "tower", "tribe", "无限之塔", "企业塔", "爬塔"), "yes_nk.tasks.TribeTowerTask", "TribeTowerTask"),
    (("teambattle", "coop", "co_op", "协同"), "yes_nk.tasks.RaidAndCoopTasks", "CoopOperationTask"),
    (("soloraid", "solo_raid", "单人突击"), "yes_nk.tasks.RaidAndCoopTasks", "SoloRaidTask"),
    (("lianmengtuxi", "lianmeng", "union", "union_raid", "联盟"), "yes_nk.tasks.RaidAndCoopTasks", "UnionRaidTask"),
    (("limitedevent", "goddessfall", "liecauserecoil", "newflavor", "event", "story", "活动"), "yes_nk.tasks.EventStoryTask", "EventStoryTask"),
    (("dailyrewards", "mission", "daily", "weekly", "每日", "任务"), "yes_nk.tasks.DailyMissionTask", "DailyMissionTask"),
    (("claimpassreward", "pass", "通行证"), "yes_nk.tasks.PassRewardTask", "PassRewardTask"),
    (("backtohomepage", "default_pipeline"), "yes_nk.tasks.BaseNikkeTask", "BaseNikkeTask"),
]


@dataclass(frozen=True)
class ConversionReport:
    matched_features: list[str]
    missing_features: list[str]
    output_json_path: Path


@dataclass(frozen=True)
class PipelineMigrationReport:
    scanned_files: int
    total_nodes: int
    mapped_tasks: dict[str, list[str]]
    referenced_templates: list[str]
    unmapped_files: list[str]


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png_rgb(png_path: Path) -> tuple[int, int, bytes]:
    """零依赖纯 Python 解码非交错 8-bit RGB/RGBA PNG，返回 (width, height, rgb_bytes)。"""
    raw = png_path.read_bytes()
    if len(raw) < 33 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"非标准 PNG 文件: {png_path}")

    pos = 8
    width = height = bit_depth = color_type = interlace = 0
    idat_chunks: list[bytes] = []
    while pos < len(raw):
        length = struct.unpack(">I", raw[pos : pos + 4])[0]
        ctype = raw[pos + 4 : pos + 8]
        cdata = raw[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bit_depth, color_type, _comp, _flt, interlace = struct.unpack(
                ">IIBBBBB", cdata
            )
        elif ctype == b"IDAT":
            idat_chunks.append(cdata)
        elif ctype == b"IEND":
            break

    if bit_depth != 8 or interlace != 0 or color_type not in (2, 6):
        # 回退尝试 Pillow
        from PIL import Image

        with Image.open(png_path) as img:
            rgb_img = img.convert("RGB")
            return rgb_img.width, rgb_img.height, rgb_img.tobytes()

    bpp = 3 if color_type == 2 else 4
    stride = width * bpp
    inflated = zlib.decompress(b"".join(idat_chunks))

    prev_row = bytearray(stride)
    out_rgb = bytearray(width * height * 3)
    in_pos = 0
    out_pos = 0

    for _y in range(height):
        flt = inflated[in_pos]
        in_pos += 1
        row = bytearray(inflated[in_pos : in_pos + stride])
        in_pos += stride

        if flt == 1:  # Sub
            for i in range(bpp, stride):
                row[i] = (row[i] + row[i - bpp]) & 0xFF
        elif flt == 2:  # Up
            for i in range(stride):
                row[i] = (row[i] + prev_row[i]) & 0xFF
        elif flt == 3:  # Average
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((left + prev_row[i]) >> 1)) & 0xFF
        elif flt == 4:  # Paeth
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                up = prev_row[i]
                up_left = prev_row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + _paeth(left, up, up_left)) & 0xFF

        if bpp == 3:
            out_rgb[out_pos : out_pos + stride] = row
            out_pos += stride
        else:
            for px in range(0, stride, 4):
                out_rgb[out_pos] = row[px]
                out_rgb[out_pos + 1] = row[px + 1]
                out_rgb[out_pos + 2] = row[px + 2]
                out_pos += 3

        prev_row = row

    return width, height, bytes(out_rgb)


def encode_png_rgb(width: int, height: int, rgb_bytes: bytes) -> bytes:
    """零依赖纯 Python 编码 8-bit RGB 无损 PNG（含最优压缩）。"""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    stride = width * 3
    scanlines = bytearray((stride + 1) * height)
    for y in range(height):
        dst_off = y * (stride + 1)
        src_off = y * stride
        scanlines[dst_off] = 0
        scanlines[dst_off + 1 : dst_off + 1 + stride] = rgb_bytes[src_off : src_off + stride]

    compressed = zlib.compress(bytes(scanlines), level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def compose_template_on_canvas(
    src_png: Path,
    dest_png: Path,
    place_x: int,
    place_y: int,
    canvas_w: int = CANVAS_WIDTH,
    canvas_h: int = CANVAS_HEIGHT,
) -> tuple[int, int, int, int]:
    """将模板无损贴到 1280×720 基准画布上，返回实际 bbox (x, y, w, h)。"""
    tpl_w, tpl_h, tpl_rgb = decode_png_rgb(src_png)

    # 若模板本身已是整图尺寸则直接按实际宽高贴图
    cw = max(canvas_w, tpl_w)
    ch = max(canvas_h, tpl_h)
    x = max(0, min(place_x, cw - tpl_w))
    y = max(0, min(place_y, ch - tpl_h))

    canvas = bytearray(cw * ch * 3)
    tpl_stride = tpl_w * 3
    canvas_stride = cw * 3
    for row_idx in range(tpl_h):
        c_off = (y + row_idx) * canvas_stride + x * 3
        t_off = row_idx * tpl_stride
        canvas[c_off : c_off + tpl_stride] = tpl_rgb[t_off : t_off + tpl_stride]

    dest_png.parent.mkdir(parents=True, exist_ok=True)
    dest_png.write_bytes(encode_png_rgb(cw, ch, bytes(canvas)))
    return x, y, tpl_w, tpl_h


def read_png_dimensions(png_path: Path) -> tuple[int, int]:
    """零依赖读取 PNG IHDR 宽高。"""
    data = png_path.read_bytes()
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)
    return (64, 64)


def extract_maa_pipeline_rois(pipeline_dir: Path | None) -> dict[str, list[int]]:
    """从 MaaNikke pipeline JSON 中提取每个模板路径在 1280×720 下的真实 ROI [x, y, w, h]。"""
    if pipeline_dir is None or not pipeline_dir.exists():
        return {}
    roi_map: dict[str, list[int]] = {}
    for jf in sorted(pipeline_dir.rglob("*.json")):
        try:
            payload = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        for node in payload.values():
            if not isinstance(node, dict):
                continue
            rec = node.get("recognition", {})
            param = rec.get("param", {}) if isinstance(rec, dict) else {}
            tpls = param.get("template") or node.get("template")
            roi = param.get("roi") or node.get("roi")
            if isinstance(tpls, str):
                tpls = [tpls]
            if isinstance(tpls, list) and isinstance(roi, list) and len(roi) == 4:
                for t in tpls:
                    if isinstance(t, str):
                        key = t.replace("\\", "/").lower()
                        if key not in roi_map:
                            roi_map[key] = [int(v) for v in roi]
    return roi_map


def _find_best_maa_image(
    maa_root: Path, maa_images: list[Path], candidates: list[str]
) -> Path | None:
    """按候选列表优先精确相对路径匹配，其次文件名精确匹配，最后模糊子串匹配。"""
    rel_map = {p.relative_to(maa_root).as_posix().lower(): p for p in maa_images}
    name_map = {p.name.lower(): p for p in maa_images}

    for cand in candidates:
        c = cand.replace("\\", "/").lower()
        if c in rel_map:
            return rel_map[c]
        if c in name_map:
            return name_map[c]

    for cand in candidates:
        c = cand.replace("\\", "/").lower()
        for rel_str, img_path in rel_map.items():
            stem = img_path.stem.lower()
            if c == stem or c in stem or c in rel_str:
                return img_path
    return None


def _match_yes_nk_task(file_stem: str, node_names: list[str]) -> str | None:
    stem_lower = file_stem.lower()
    for keywords, module_name, class_name in MAA_PIPELINE_TO_YES_NK:
        if any(kw in stem_lower for kw in keywords):
            return f"{module_name}.{class_name}"
    nodes_lower = " ".join(node_names).lower()
    for keywords, module_name, class_name in MAA_PIPELINE_TO_YES_NK:
        if any(kw in nodes_lower for kw in keywords):
            return f"{module_name}.{class_name}"
    return None


def analyze_maa_pipeline_directory(pipeline_dir: Path) -> PipelineMigrationReport:
    """解析 MaaNikke pipeline/*.json 目录并输出与 YES-NK 原生任务的映射覆盖报告。"""
    json_files = sorted(p for p in pipeline_dir.rglob("*.json") if p.is_file())
    total_nodes = 0
    mapped_tasks: dict[str, list[str]] = {}
    referenced_templates: set[str] = set()
    unmapped_files: list[str] = []

    for json_file in json_files:
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            unmapped_files.append(json_file.name)
            continue

        if not isinstance(payload, dict):
            continue

        node_names = [k for k in payload.keys() if not k.startswith("$__")]
        total_nodes += len(node_names)

        for node_cfg in payload.values():
            if not isinstance(node_cfg, dict):
                continue
            rec = node_cfg.get("recognition", {})
            param = rec.get("param", {}) if isinstance(rec, dict) else {}
            tpl = param.get("template") or node_cfg.get("template")
            if isinstance(tpl, str):
                referenced_templates.add(tpl)
            elif isinstance(tpl, list):
                for item in tpl:
                    if isinstance(item, str):
                        referenced_templates.add(item)

        target_task = _match_yes_nk_task(json_file.stem, node_names)
        if target_task:
            mapped_tasks.setdefault(target_task, []).append(json_file.name)
        else:
            unmapped_files.append(json_file.name)

    return PipelineMigrationReport(
        scanned_files=len(json_files),
        total_nodes=total_nodes,
        mapped_tasks=mapped_tasks,
        referenced_templates=sorted(referenced_templates),
        unmapped_files=unmapped_files,
    )


def convert_maa_directory_to_coco(
    maa_image_dir: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_images_dir: Path = DEFAULT_OUTPUT_IMAGES,
    maa_pipeline_dir: Path | None = None,
) -> ConversionReport:
    """将 MaaNikke 模板目录批量转换为 ok-script 原生 1280×720 基准 COCO result.json。"""
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    features: list[dict[str, Any]] = manifest.get("features", [])
    base_res = manifest.get("base_resolution", [CANVAS_WIDTH, CANVAS_HEIGHT])
    canvas_w, canvas_h = int(base_res[0]), int(base_res[1])

    # 若未显式传入 pipeline 目录，自动探测同级 ../pipeline
    if maa_pipeline_dir is None:
        sibling_pipeline = maa_image_dir.parent / "pipeline"
        if sibling_pipeline.exists():
            maa_pipeline_dir = sibling_pipeline

    pipeline_rois = extract_maa_pipeline_rois(maa_pipeline_dir)

    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    maa_images = sorted(
        p
        for p in maa_image_dir.rglob("*")
        if p.is_file() and p.suffix.lower() == ".png"
    )

    coco_images: list[dict[str, Any]] = []
    coco_categories: list[dict[str, Any]] = []
    coco_annotations: list[dict[str, Any]] = []

    matched: list[str] = []
    missing: list[str] = []

    image_id = 1
    annotation_id = 1

    for idx, feat in enumerate(features, start=1):
        feat_name = str(feat["name"])
        coco_categories.append({"id": idx, "name": feat_name})
        candidates = [str(c) for c in feat.get("maa_candidates", [])]

        src_img = _find_best_maa_image(maa_image_dir, maa_images, candidates)
        if src_img is None:
            missing.append(feat_name)
            continue

        rel_key = src_img.relative_to(maa_image_dir).as_posix().lower()
        tpl_w, tpl_h = read_png_dimensions(src_img)

        # 确定模板在 1280×720 基准画布中的坐标（优先采用 MaaNikke 实测 ROI 中心）
        if rel_key in pipeline_rois:
            rx, ry, rw, rh = pipeline_rois[rel_key]
            place_x = rx + max(0, (rw - tpl_w) // 2)
            place_y = ry + max(0, (rh - tpl_h) // 2)
        else:
            x1, y1, x2, y2 = feat.get("roi_norm", [0.4, 0.4, 0.6, 0.6])
            cx = int(round(((x1 + x2) / 2) * canvas_w))
            cy = int(round(((y1 + y2) / 2) * canvas_h))
            place_x = max(0, cx - tpl_w // 2)
            place_y = max(0, cy - tpl_h // 2)

        dest_name = f"{feat_name}.png"
        dest_path = output_images_dir / dest_name
        bx, by, bw, bh = compose_template_on_canvas(
            src_png=src_img,
            dest_png=dest_path,
            place_x=place_x,
            place_y=place_y,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        )

        final_w, final_h = read_png_dimensions(dest_path)
        coco_images.append(
            {
                "id": image_id,
                "file_name": f"images/{dest_name}",
                "width": final_w,
                "height": final_h,
                "source_template": rel_key,
            }
        )
        coco_annotations.append(
            {
                "id": annotation_id,
                "image_id": image_id,
                "category_id": idx,
                "bbox": [bx, by, bw, bh],
                "area": bw * bh,
                "iscrowd": 0,
            }
        )
        matched.append(feat_name)
        image_id += 1
        annotation_id += 1

    coco_payload = {
        "info": {
            "description": "YES-NK ok-script COCO dataset (1280x720 16:9 baseline) directly converted from Shinarin/MaaNikke",
            "version": "0.3.0",
            "source_repo": "https://github.com/Shinarin/MaaNikke",
            "base_resolution": [canvas_w, canvas_h],
        },
        "images": coco_images,
        "categories": coco_categories,
        "annotations": coco_annotations,
    }

    output_json_path.write_text(
        json.dumps(coco_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ConversionReport(
        matched_features=matched,
        missing_features=missing,
        output_json_path=output_json_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="将 Shinarin/MaaNikke 模板图像与 pipeline 批量转换为 YES-NK ok-script 原生 COCO 特征包"
    )
    parser.add_argument(
        "--maa-dir",
        required=True,
        help="MaaNikke 的图片目录路径，例如 D:\\MaaNikke\\resource\\base\\image",
    )
    parser.add_argument(
        "--maa-pipeline-dir",
        default="",
        help="可选：MaaNikke 的 pipeline JSON 目录路径，例如 D:\\MaaNikke\\resource\\base\\pipeline",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="YES-NK 特征清单文件路径",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_JSON),
        help="生成的 COCO result.json 输出路径",
    )
    args = parser.parse_args(argv)

    maa_dir = Path(args.maa_dir)
    if not maa_dir.exists():
        print(f"[错误] 未找到目录：{maa_dir}")
        return 1

    p_dir = Path(args.maa_pipeline_dir) if args.maa_pipeline_dir else None
    report = convert_maa_directory_to_coco(
        maa_image_dir=maa_dir,
        manifest_path=Path(args.manifest),
        output_json_path=Path(args.output),
        maa_pipeline_dir=p_dir,
    )

    print(f"图像特征转换完成：{report.output_json_path}")
    print(f"  已自动导入特征 ({len(report.matched_features)}): {', '.join(report.matched_features) or '无'}")
    print(f"  纯文字 OCR 兜底特征 ({len(report.missing_features)}): {', '.join(report.missing_features) or '无'}")

    if p_dir and p_dir.exists():
        p_report = analyze_maa_pipeline_directory(p_dir)
        print(
            f"\nMaaNikke Pipeline 覆盖分析：扫描 {p_report.scanned_files} 个文件，"
            f"共 {p_report.total_nodes} 个节点，引用模板 {len(p_report.referenced_templates)} 项，"
            f"已映射到 {len(p_report.mapped_tasks)} 个 YES-NK 原生状态机任务。"
        )
        for task_path, files in sorted(p_report.mapped_tasks.items()):
            print(f"  - {task_path} <= {', '.join(files)}")
        if p_report.unmapped_files:
            print(f"  - 忽略/调试文件: {', '.join(p_report.unmapped_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
