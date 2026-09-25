"""Build tray-only PAA poses from the existing catheter artwork.

Arma's ctrlSetAngle can distort pictures under custom FOV (BI T136844).
Bake the five fixed tray poses in source-pixel space instead. The held and
inserted catheter textures are never modified. Requires Pillow >= 11.2 and numpy.
"""
from io import BytesIO
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from paa import read_paa

ROOT = Path(__file__).resolve().parents[1]
CANVAS = 512
LENGTH = 448
TIP = (32, 256)
ANGLES = (0, 4, 8, 12, 16)


def tray_poses(gauge):
    source = ROOT / f"ui/iv/{gauge}g/base/iv_catheter_{gauge}g_base_frame_00_ready_ca.paa"
    rgb, alpha = read_paa(source)
    image = Image.fromarray(np.dstack((rgb, alpha)))
    # Cut only transparent margins. A quarter turn preserves every source pixel.
    image = image.crop(image.getbbox()).transpose(Image.Transpose.ROTATE_90)
    height = round(image.height * LENGTH / image.width)
    image = image.resize((LENGTH, height), Image.Resampling.LANCZOS)
    base = Image.new("RGBA", (CANVAS, CANVAS))
    base.alpha_composite(image, (TIP[0], TIP[1] - height // 2))
    # Left tip stays fixed; every positive angle raises the handle. No pose is
    # rotated around its center, which would drop one end below the baseline.
    return [base if angle == 0 else base.rotate(
        angle, Image.Resampling.BICUBIC, center=TIP
    ) for angle in ANGLES]


def write_paa(path, image):
    """Store standard DXT5 mipmaps in a PAA container, without optional LZO."""
    data = bytearray(struct.pack("<H", 0xFF05))
    # Flag alpha blending; optional OFFS/average tags are not needed by PAA.
    data += b"GGATGALF" + struct.pack("<II", 4, 1)
    data += struct.pack("<H", 0)  # no palette
    while image.width >= 4 and image.height >= 4:
        buffer = BytesIO()
        image.save(buffer, format="DDS", pixel_format="DXT5")
        dds = buffer.getvalue()
        assert dds[84:88] == b"DXT5"
        blocks = dds[128:]
        assert len(blocks) == image.width * image.height
        data += struct.pack("<HH", *image.size)
        data += len(blocks).to_bytes(3, "little") + blocks
        image = image.resize((image.width // 2, image.height // 2), Image.Resampling.LANCZOS)
    data += bytes(6)
    path.write_bytes(data)


def main():
    target = ROOT / "ui/iv/tray"
    target.mkdir(exist_ok=True)
    for gauge in (14, 16, 18, 20):
        for index, image in enumerate(tray_poses(gauge)):
            write_paa(target / f"iv_tray_{gauge}g_{index}_ca.paa", image)
    print("Built 20 tray poses from the original catheter PAAs.")


if __name__ == "__main__":
    main()
