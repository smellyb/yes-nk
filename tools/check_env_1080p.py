"""1080P 屏幕与 nikke.exe 窗口 16:9 客户区自检/校准工具。

用法：
  python tools/check_env_1080p.py
  python tools/check_env_1080p.py --width 1920 --height 1009 --dpi 125
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from yes_nk.utils.window_1080p import (
    enable_per_monitor_dpi_awareness,
    evaluate_client_geometry,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查游戏窗口客户区是否符合 YES-NK 1080P / 16:9 标准")
    parser.add_argument("--width", type=int, default=1920, help="游戏客户区宽度（像素）")
    parser.add_argument("--height", type=int, default=1080, help="游戏客户区高度（像素）")
    parser.add_argument("--dpi", type=int, default=100, help="Windows 缩放百分比（100/125/150）")
    args = parser.parse_args(argv)

    enable_per_monitor_dpi_awareness()
    report = evaluate_client_geometry(args.width, args.height, args.dpi)

    print(f"客户区尺寸 : {report.client_width} x {report.client_height}")
    print(f"DPI 缩放   : {report.dpi_scale_percent}%")
    print(f"纵横比     : {report.aspect_ratio} (相对 16:9 偏差 {report.ratio_error * 100:.2f}%)")
    print(f"缩放系数   : {report.scale_x}x / {report.scale_y}x")
    print(f"检测结论   : {'通过' if report.is_valid else '需要校准'} [{report.status}]")
    print(f"建议       : {report.recommendation}")
    return 0 if report.is_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
