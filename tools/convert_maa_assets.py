"""MaaNikke 模板资源 -> YES-NK (ok-script) COCO result.json 转换工具。

用法示例：
  python tools/convert_maa_assets.py --maa-dir D:\\MaaNikke\\resource\\base\\image

说明：
- 扫描 MaaNikke 图像目录中的 PNG 模板文件；
- 按 assets/coco_manifest.json 中的候选关键词自动匹配对应 YES-NK 特征名；
- 复制匹配图片至 assets/images/，并生成 ok-script 可直接加载的 assets/result.json；
- 输出“已自动导入”与“需本地截图补充（已内置 OCR 兜底）”两类明细报告。
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


@dataclass(frozen=True)
class ConversionReport:
    matched_features: list[str]
    missing_features: list[str]
    output_json_path: Path


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
        p for p in maa_image_dir.rglob("*") if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg")
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
            "version": "0.1.0",
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
        description="将 Shinarin/MaaNikke 模板图像批量转换为 YES-NK ok-script COCO 特征包"
    )
    parser.add_argument(
        "--maa-dir",
        required=True,
        help="MaaNikke 的图片目录路径，例如 D:\\MaaNikke\\resource\\base\\image",
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

    print(f"转换完成：{report.output_json_path}")
    print(f"  已自动导入特征 ({len(report.matched_features)}): {', '.join(report.matched_features) or '无'}")
    print(f"  待本地补截特征 ({len(report.missing_features)}): {', '.join(report.missing_features) or '无'}")
    print("提示：未补截的文字按钮在运行时会自动使用局部 ROI OCR 兜底识别。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
