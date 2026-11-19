"""纯 Python 生成 YES-NK 桌面客户端图标 (assets/icon.png 与 assets/icon.ico)。

无需安装 Pillow 或外部画图软件即可生成 64x64 锐利 Fluent 蓝底白字几何徽章图标。
"""

from __future__ import annotations

from pathlib import Path
import struct
import zlib

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def _build_rgba_pixels(size: int = 64) -> bytes:
    """绘制圆角 Fluent 蓝 (#0067C0) 徽章与简洁白色对角折线徽标。"""
    rows = bytearray()
    radius = size * 0.22
    for y in range(size):
        rows.append(0)  # PNG filter type 0
        for x in range(size):
            # 判断是否在圆角矩形内
            dx = max(radius - x, 0.0, x - (size - 1 - radius))
            dy = max(radius - y, 0.0, y - (size - 1 - radius))
            inside = (dx * dx + dy * dy) <= (radius * radius + 0.5)
            if not inside:
                rows.extend((0, 0, 0, 0))
                continue

            nx = x / size
            ny = y / size

            # 简洁现代的白色 "N" 折线标志
            in_left_bar = 0.24 <= nx <= 0.34 and 0.24 <= ny <= 0.76
            in_right_bar = 0.66 <= nx <= 0.76 and 0.24 <= ny <= 0.76
            diag_dist = abs((ny - 0.26) - (nx - 0.29) * 1.12)
            in_diag = 0.28 <= nx <= 0.72 and 0.24 <= ny <= 0.76 and diag_dist <= 0.065

            if in_left_bar or in_right_bar or in_diag:
                rows.extend((255, 255, 255, 255))
            else:
                # 微妙深浅渐变 Fluent 蓝 (#0067C0 -> #004E96)
                t = ny
                r = int(0 + 10 * (1 - t))
                g = int(103 - 25 * t)
                b = int(192 - 38 * t)
                rows.extend((r, g, b, 255))
    return bytes(rows)


def _encode_png_rgba(width: int, height: int, raw_rows: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw_rows, level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def _wrap_png_as_ico(png_bytes: bytes, size: int = 64) -> bytes:
    """使用 Vista+ 标准 PNG-in-ICO 封装格式生成合法 .ico 文件。"""
    ico_header = struct.pack("<HHH", 0, 1, 1)  # reserved=0, type=1 (ICO), count=1
    dim = 0 if size >= 256 else size
    entry = struct.pack(
        "<BBBBHHII",
        dim,  # width
        dim,  # height
        0,  # color count
        0,  # reserved
        1,  # planes
        32,  # bpp
        len(png_bytes),
        6 + 16,  # image data offset
    )
    return ico_header + entry + png_bytes


def generate_icons(output_dir: Path = ASSETS_DIR, size: int = 64) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    png_bytes = _encode_png_rgba(size, size, _build_rgba_pixels(size))
    ico_bytes = _wrap_png_as_ico(png_bytes, size=size)

    png_path = output_dir / "icon.png"
    ico_path = output_dir / "icon.ico"
    png_path.write_bytes(png_bytes)
    ico_path.write_bytes(ico_bytes)
    return png_path, ico_path


if __name__ == "__main__":
    png, ico = generate_icons()
    print(f"已生成图标: {png} / {ico}")
