#!/usr/bin/env python3
"""Build the original transparent chest decals and their flat P3D planes."""
import argparse
import random
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

DATA = Path(__file__).resolve().parents[1] / "addons/acm_extended/data/medical_chest"


def painted(mask, pigment, seed):
    rng = random.Random(seed)
    soft = mask.filter(ImageFilter.GaussianBlur(1.8))
    rgba = []
    for visible, overspray in zip(mask.getdata(), soft.getdata()):
        alpha = int(visible * rng.uniform(0.75, 1) + max(0, overspray - visible) * 0.28)
        if rng.random() < 0.09:
            alpha = alpha // 3
        tint = rng.randrange(-14, 9)
        rgba.append(tuple(max(0, min(255, c + tint)) for c in pigment) + (min(255, alpha),))
    layer = Image.new("RGBA", mask.size)
    layer.putdata(rgba)
    return layer


def stencils(font_path):
    title = Image.new("L", (1024, 256))
    font = ImageFont.truetype(font_path, 92)
    draw = ImageDraw.Draw(title)
    for word, y in (("MEDICAL", 75), ("CHEST", 180)):
        advance = font.getlength(word)
        start = (1024 - advance) / 2
        draw.text((start, y), word, font=font, anchor="lm", fill=255)
        for index, letter in enumerate(word):
            if letter in "ADC":
                x = start + font.getlength(word[:index]) + font.getlength(letter) * 0.46
                draw.rectangle((x, y - 52, x + 5, y + 52), fill=0)
    title = title.crop((160, 0, 864, 256)).resize((512, 256), Image.Resampling.LANCZOS)
    cross = Image.new("L", (256, 256))
    ImageDraw.Draw(cross).polygon(
        [(89, 34), (167, 34), (167, 89), (222, 89), (222, 167), (167, 167),
         (167, 222), (89, 222), (89, 167), (34, 167), (34, 89), (89, 89)],
        fill=255,
    )
    red = Image.new("L", (256, 256))
    ImageDraw.Draw(red).rounded_rectangle((17, 17, 239, 239), radius=14, fill=255)
    badge = painted(red, (177, 37, 30), 2)
    badge.alpha_composite(painted(cross, (233, 232, 217), 3))
    return painted(title, (230, 187, 45), 1), badge


def plane(name, width, height):
    points = [(-width/2, 0, -height/2), (width/2, 0, -height/2),
              (width/2, 0, height/2), (-width/2, 0, height/2)]
    # Clockwise face order as seen from model-forward (+Y).
    uv = [(1, 1), (0, 1), (0, 0), (1, 0)]
    mesh = bytearray(b"MLOD" + struct.pack("<II", 257, 1))
    mesh += b"P3DM" + struct.pack("<6I", 28, 256, 4, 1, 1, 0)
    for point in points:
        mesh += struct.pack("<3fI", *point, 0)
    mesh += struct.pack("<3fI", 0, 1, 0, 4)
    for index in range(4):
        mesh += struct.pack("<IIff", index, 0, *uv[index])
    mesh += struct.pack("<I", 0) + f"acm_extended\\data\\medical_chest\\{name}_ca.paa".encode() + b"\0\0"
    mesh += b"TAGG\x01#Property#\0" + struct.pack("<I", 128)
    mesh += b"autocenter".ljust(64, b"\0") + b"0".ljust(64, b"\0")
    mesh += b"\x01#UVSet#\0" + struct.pack("<II", 36, 0)
    for point in uv:
        mesh += struct.pack("<2f", *point)
    mesh += b"\x01#EndOfFile#\0" + struct.pack("<If", 0, 0)
    (DATA / f"{name}.p3d").write_bytes(mesh)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", required=True, type=Path)
    parser.add_argument("--png-dir", required=True, type=Path)
    args = parser.parse_args()
    args.png_dir.mkdir(parents=True, exist_ok=True)
    for name, image, width, height in zip(
        ("chest_title", "chest_cross"), stencils(args.font), (0.34, 0.12), (0.15, 0.12)
    ):
        image.save(args.png_dir / f"{name}_ca.png")
        plane(name, width, height)
