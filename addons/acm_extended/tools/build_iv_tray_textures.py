"""Build tray-only PAA poses from the existing catheter artwork.

Arma's ctrlSetAngle can distort pictures under custom FOV (BI T136844).
Bake the five fixed tray poses in source-pixel space instead. The held and
inserted catheter textures are never modified. Requires Pillow, numpy and HEMTT.

Use HEMTT's converter for the PAA container, mipmap index and compression. The
former handwritten container lacked OFFS, so HEMTT and Arma saw no mipmaps even
though a sequential custom decoder could find and display its DXT pixel data.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

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


def write_paa(path, image, hemtt):
    """Convert and independently reopen the completed asset before replacing it."""
    def run(*args):
        return subprocess.run(
            [hemtt, "utils", "paa", *map(str, args)],
            check=True, capture_output=True, text=True,
        ).stdout

    with TemporaryDirectory(prefix="acme_iv_tray_") as directory:
        directory = Path(directory)
        source = directory / f"{path.stem}.png"
        candidate = directory / path.name
        decoded = directory / "decoded.png"
        image.save(source)
        run("convert", source, candidate)
        inspection = run("inspect", candidate)
        if "Maps: 8" not in inspection or "SFFO =" not in inspection:
            raise RuntimeError(f"HEMTT could not read all 8 indexed mipmaps: {path}")
        run("convert", candidate, decoded)
        with Image.open(decoded) as verified:
            if verified.size != image.size or verified.convert("RGBA").getchannel("A").getextrema()[1] < 128:
                raise RuntimeError(f"HEMTT decoded an empty or incorrectly sized texture: {path}")
        path.write_bytes(candidate.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hemtt", default=shutil.which("hemtt"), help="Path to the HEMTT executable")
    args = parser.parse_args()
    if not args.hemtt:
        parser.error("HEMTT is required; install it or pass --hemtt /path/to/hemtt")
    target = ROOT / "ui/iv/tray"
    target.mkdir(exist_ok=True)
    for gauge in (14, 16, 18, 20):
        for index, image in enumerate(tray_poses(gauge)):
            write_paa(target / f"iv_tray_{gauge}g_{index}_ca.paa", image, args.hemtt)
    print("Built 20 tray poses; HEMTT independently reopened 8 indexed mipmaps and decoded each asset.")


if __name__ == "__main__":
    main()
