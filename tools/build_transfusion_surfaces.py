#!/usr/bin/env python3
"""Build deterministic code-native rounded transfusion surfaces (no medical artwork).

Run with --hemtt to regenerate the committed PAA files. PNG intermediates belong in
the selected temporary output directory; only the compact native textures ship.
"""
from argparse import ArgumentParser
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "addons/circulation/ui/transfusionmenu/surfaces"
SPECS = {
    "window": ((1024, 512), 10, 17, 52),
    "list": ((512, 256), 10, 19, 47),
    "row": ((512, 64), 8, 24, 46),
    "row_selected": ((512, 64), 8, 48, 145),
    "button": ((512, 64), 8, 32, 54),
    "button_hover": ((512, 64), 8, 43, 103),
    "button_disabled": ((512, 64), 8, 23, 40),
    "button_wide": ((512, 32), 6, 32, 54),
    "button_hover_wide": ((512, 32), 6, 43, 103),
    "button_disabled_wide": ((512, 32), 6, 23, 40),
}


def surface(size, radius, fill, border):
    scale = 4
    w, h = size
    im = Image.new("RGBA", (w * scale, h * scale))
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((scale, scale, (w - 1) * scale, (h - 1) * scale),
                           radius=radius * scale,
                           fill=(fill, fill, fill, 255),
                           outline=(border, border, border, 255), width=scale)
    return im.resize(size, Image.Resampling.LANCZOS)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--hemtt", required=True)
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="acme-transfusion-surfaces-") as tmp:
        for name, (size, radius, fill, border) in SPECS.items():
            png = Path(tmp) / f"{name}_ca.png"
            surface(size, radius, fill, border).save(png)
            subprocess.run([args.hemtt, "utils", "paa", "convert", str(png),
                            str(DEST / f"{name}_ca.paa")], check=True,
                           stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
