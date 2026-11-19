"""MaaNikke 模板与流水线 JSON -> YES-NK (ok-script) 转换与分析工具。

用法示例：
  python tools/convert_maa_assets.py --maa-dir D:\\MaaNikke\\resource\\base\\image
  python tools/convert_maa_assets.py --maa-dir D:\\MaaNikke\\resource\\base\\image --maa-pipeline-dir D:\\MaaNikke\\resource\\base\\pipeline

说明：
1. 图像转换：扫描 MaaNikke 图像目录，按 assets/coco_manifest.json 自动匹配 38 项 YES-NK 特征，
   复制到 assets/images/ 并生成 ok-script 可直接加载的 assets/result.json；
2. 流水线分析：扫描 MaaNikke pipeline/*.json 节点，提取其中引用的模板与 OCR 文案，并自动映射
   到 YES-NK 全部 21 个原生 Python 状态机任务类，输出转换覆盖率报告。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import struct
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "assets" / "coco_manifest.json"
DEFAULT_OUTPUT_JSON = PROJECT_ROOT / "assets" / "result.json"
DEFAULT_OUTPUT_IMAGES = PROJECT_ROOT / "assets" / "images"


MAA_PIPELINE_TO_YES_NK: list[tuple[tuple[str, ...], str, str]] = [
    (("startup", "start_game", "login", "launch", "启动", "登录"), "yes_nk.tasks.AutoLoginTask", "AutoLoginTask"),
    (("mail", "mailbox", "邮件", "邮箱"), "yes_nk.tasks.MailTask", "MailTask"),
    (("friend", "social_point", "好友"), "yes_nk.tasks.FriendPointTask", "FriendPointTask"),
    (("outpost", "defense", "wipe", "前哨", "防御", "歼灭"), "yes_nk.tasks.OutpostDefenseTask", "OutpostDefenseTask"),
    (("dispatch", "bulletin", "派遣", "公告栏"), "yes_nk.tasks.DispatchTask", "DispatchTask"),
    (("cash", "charge", "付费商店", "礼包"), "yes_nk.tasks.CashShopFreeTask", "CashShopFreeTask"),
    (("shop", "store", "商店"), "yes_nk.tasks.ShopTask", "ShopTask"),
    (("recruit", "gacha", "招募"), "yes_nk.tasks.SocialRecruitTask", "SocialRecruitTask"),
    (("advise", "counsel", "gift", "咨询", "送礼"), "yes_nk.tasks.AdviseGiftTask", "AdviseGiftTask"),
    (("equip", "upgrade", "装备"), "yes_nk.tasks.EquipmentUpgradeTask", "EquipmentUpgradeTask"),
    (("liberation", "rehab", "更生", "解放"), "yes_nk.tasks.LiberationTask", "LiberationTask"),
    (("interception", "boss", "拦截"), "yes_nk.tasks.InterceptionTask", "InterceptionTask"),
    (("simulation", "sim_room", "模拟室"), "yes_nk.tasks.SimulationRoomTask", "SimulationRoomTask"),
    (("arena", "rookie", "special_arena", "竞技场"), "yes_nk.tasks.ArenaTask", "ArenaTask"),
    (("tower", "tribe", "无限之塔", "企业塔"), "yes_nk.tasks.TribeTowerTask", "TribeTowerTask"),
    (("coop", "co_op", "协同"), "yes_nk.tasks.RaidAndCoopTasks", "CoopOperationTask"),
    (("solo_raid", "soloraid", "单人突击"), "yes_nk.tasks.RaidAndCoopTasks", "SoloRaidTask"),
    (("union", "union_raid", "联盟"), "yes_nk.tasks.RaidAndCoopTasks", "UnionRaidTask"),
    (("event", "story", "活动"), "yes_nk.tasks.EventStoryTask", "EventStoryTask"),
    (("mission", "daily", "weekly", "每日", "任务"), "yes_nk.tasks.DailyMissionTask", "DailyMissionTask"),
    (("pass", "通行证"), "yes_nk.tasks.PassRewardTask", "PassRewardTask"),
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


def read_png_dimensions(png_path: Path) -> tuple[int, int]:
    """零依赖读取 PNG IHDR 宽高，若遇非 PNG 则回退 Pillow。"""
    data = png_path.read_bytes()
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)
    try:
        from PIL import Image

        with Image.open(png_path) as img:
            return int(img.width), int(img.height)
    except Exception:
        return (64, 64)


def _find_best_maa_image(
    maa_images: list[Path], candidates: list[str]
) -> Path | None:
    lowered_candidates = [c.lower() for c in candidates]
    for img_path in maa_images:
        stem = img_path.stem.lower()
        rel = img_path.as_posix().lower()
        for cand in lowered_candidates:
            if cand == stem or cand in stem or cand in rel:
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

        node_names = list(payload.keys())
        total_nodes += len(node_names)

        for node_cfg in payload.values():
            if not isinstance(node_cfg, dict):
                continue
            tpl = node_cfg.get("template")
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
) -> ConversionReport:
    """将 MaaNikke 模板目录批量转换为标准 ok-script COCO result.json。"""
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    features: list[dict[str, Any]] = manifest.get("features", [])

    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    maa_images = sorted(
        p
        for p in maa_image_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg")
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

        src_img = _find_best_maa_image(maa_images, candidates)
        if src_img is None:
            missing.append(feat_name)
            continue

        dest_name = f"{feat_name}{src_img.suffix.lower()}"
        dest_path = output_images_dir / dest_name
        shutil.copy2(src_img, dest_path)

        width, height = read_png_dimensions(dest_path)
        coco_images.append(
            {
                "id": image_id,
                "file_name": f"images/{dest_name}",
                "width": width,
                "height": height,
            }
        )
        coco_annotations.append(
            {
                "id": annotation_id,
                "image_id": image_id,
                "category_id": idx,
                "bbox": [0, 0, width, height],
                "area": width * height,
                "iscrowd": 0,
            }
        )
        matched.append(feat_name)
        image_id += 1
        annotation_id += 1

    coco_payload = {
        "info": {
            "description": "YES-NK ok-script COCO dataset converted from MaaNikke templates",
            "version": "0.2.0",
            "source_dir": str(maa_image_dir),
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
        description="将 Shinarin/MaaNikke 模板图像与 pipeline 批量转换为 YES-NK ok-script 特征包"
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

    report = convert_maa_directory_to_coco(
        maa_image_dir=maa_dir,
        manifest_path=Path(args.manifest),
        output_json_path=Path(args.output),
    )

    print(f"图像特征转换完成：{report.output_json_path}")
    print(f"  已自动导入特征 ({len(report.matched_features)}): {', '.join(report.matched_features) or '无'}")
    print(f"  待本地补截特征 ({len(report.missing_features)}): {', '.join(report.missing_features) or '无'}")
    print("提示：未补截的文字按钮在运行时会自动使用局部 ROI OCR 兜底识别。")

    if args.maa_pipeline_dir:
        p_dir = Path(args.maa_pipeline_dir)
        if p_dir.exists():
            p_report = analyze_maa_pipeline_directory(p_dir)
            print(
                f"\nMaaNikke Pipeline 覆盖分析：扫描 {p_report.scanned_files} 个文件，"
                f"共 {p_report.total_nodes} 个节点，引用模板 {len(p_report.referenced_templates)} 项，"
                f"已映射到 {len(p_report.mapped_tasks)} 个 YES-NK 原生状态机任务。"
            )
            for task_path, files in sorted(p_report.mapped_tasks.items()):
                print(f"  - {task_path} <= {', '.join(files)}")
            if p_report.unmapped_files:
                print(f"  - 未归类文件: {', '.join(p_report.unmapped_files)}")
        else:
            print(f"[警告] 未找到 pipeline 目录：{p_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
