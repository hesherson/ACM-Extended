#!/usr/bin/env python3
"""Rebuild ACME's code-drawn native rounded transfusion panel textures.

Requires Pillow and HEMTT. These are UI primitives, not replacement medical art.
Run: python tools/generate_transfusion_chrome.py --hemtt /path/to/hemtt
All native output is power-of-two PAA; temporary PNGs are never shipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "addons/acm_extended/ui/transfusion"
SIZE = 64
BORDER = 8
SUPERSAMPLE = 4
PARTS = ("tl", "top", "tr", "left", "center", "right", "bl", "bottom", "br")
PROFILES = {
    "window": ("#111214", "#34363c"),
    "panel": ("#18191c", "#292b30"),
    "button": ("#202125", "#34363c"),
    "selected": ("#303239", "#9498a2"),
    "popup": ("#24262b", "#50545e"),
    "piggyback": ("#28252e", "#a392bd"),
    "piggyback_selected": ("#302a3a", "#d2c2ec"),
}


def render_parts(fill: str, stroke: str) -> dict[str, Image.Image]:
    """Quarter-circle corners and flat strips with identical seam colors.

    The middle strips stretch only parallel to their border. The source border
    is 1/8 the corner radius; at radius 7px it renders about 0.875px. Corner width
    and height must represent the same physical pixels in the native helper.
    """
    side = SIZE * SUPERSAMPLE
    full = side * 2
    width = BORDER * SUPERSAMPLE
    image = Image.new("RGBA", (full, full), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, full - 1, full - 1), fill=stroke)
    draw.ellipse((width, width, full - width - 1, full - width - 1), fill=fill)
    corners = {
        "tl": image.crop((0, 0, side, side)),
        "tr": image.crop((side, 0, full, side)),
        "bl": image.crop((0, side, side, full)),
        "br": image.crop((side, side, full, full)),
    }
    parts = {key: value.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
             for key, value in corners.items()}
    for part in ("top", "bottom", "left", "right"):
        edge = Image.new("RGBA", (side, side), fill)
        edge_draw = ImageDraw.Draw(edge)
        rect = {
            "top": (0, 0, side - 1, width - 1),
            "bottom": (0, side - width, side - 1, side - 1),
            "left": (0, 0, width - 1, side - 1),
            "right": (side - width, 0, side - 1, side - 1),
        }[part]
        edge_draw.rectangle(rect, fill=stroke)
        parts[part] = edge.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    parts["center"] = Image.new("RGBA", (SIZE, SIZE), fill)
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hemtt", default=shutil.which("hemtt"), help="HEMTT executable")
    parser.add_argument("--png-output", type=Path, help="Optional PNG inspection directory")
    args = parser.parse_args()
    if not args.hemtt:
        parser.error("HEMTT is required; supply --hemtt")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.png_output:
        args.png_output.mkdir(parents=True, exist_ok=True)
    assets = []
    with tempfile.TemporaryDirectory(prefix="acme-transfusion-chrome-") as temporary:
        for profile, (fill, stroke) in PROFILES.items():
            parts = render_parts(fill, stroke)
            for part in PARTS:
                name = f"{profile}_{part}_ca"
                png = Path(temporary) / f"{name}.png"
                paa = OUTPUT / f"{name}.paa"
                parts[part].save(png)
                if args.png_output:
                    parts[part].save(args.png_output / png.name)
                subprocess.run([args.hemtt, "utils", "paa", "convert", "--no-color", str(png), str(paa)],
                               check=True, capture_output=True, text=True)
                assets.append({"file": paa.name, "profile": profile, "part": part,
                               "sha256": hashlib.sha256(paa.read_bytes()).hexdigest()})
    manifest = {
        "schema": 1,
        "generator": "tools/generate_transfusion_chrome.py",
        "size": [SIZE, SIZE],
        "sourceCornerRadius": SIZE,
        "sourceBorderWidth": BORDER,
        "parts": PARTS,
        "profiles": {key: {"fill": fill, "border": stroke}
                     for key, (fill, stroke) in PROFILES.items()},
        "assets": assets,
    }
    (OUTPUT / "chrome_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(assets)} native rounded UI textures in {OUTPUT}")


if __name__ == "__main__":
    main()
