#!/usr/bin/env python3
"""Build the original transparent chest decals and their flat P3D planes."""
import argparse
import math
import random
import struct
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

DATA = Path(__file__).resolve().parents[1] / "addons/acm_extended/data/medical_chest"


def noise(size, cell, rng):
    grid = Image.new("L", tuple(max(2, side // cell) for side in size))
    grid.putdata([rng.randrange(256) for _ in range(grid.width * grid.height)])
    return grid.resize(size, Image.Resampling.BICUBIC)


def spray(mask, pigment, fade, rng):
    # Broad uneven coverage plus speckled overspray outside the stencil edge.
    density = noise(mask.size, 21, rng).point(lambda p: 155 + int(p * 0.39))
    haze = mask.filter(ImageFilter.GaussianBlur(5.2))
    overspray = ImageChops.subtract(haze, mask)
    flecks = noise(mask.size, 1, rng).point(lambda p: int((p - 182) * 1.18) if p > 182 else 0)
    alpha = ImageChops.add(ImageChops.multiply(mask, density), ImageChops.multiply(overspray, flecks))
    pigment_mix = noise(mask.size, 17, rng).point(lambda p: int(p * 0.64))
    layer = Image.composite(Image.new("RGB", mask.size, fade), Image.new("RGB", mask.size, pigment), pigment_mix)
    layer.putalpha(alpha)
    return layer


def weather(paint, footprint, rng, chip_count):
    size = paint.size
    left, top, right, bottom = footprint.getbbox()
    wear = Image.new("L", size, 255)
    cuts = ImageDraw.Draw(wear)
    for _ in range(chip_count):
        x, y = rng.randrange(left, right), rng.randrange(top, bottom)
        radius = rng.choices((1, 2, 4, 7, 11), weights=(37, 29, 23, 9, 2))[0]
        depth = rng.choice((0, 12, 48, 92, 145))
        corners = rng.randrange(4, 9)
        rotation = rng.uniform(0, math.tau)
        contour = []
        for corner in range(corners):
            angle = rotation + math.tau * corner / corners
            distance = radius * rng.uniform(0.35, 1.4)
            contour.append((round(x + distance * math.cos(angle)), round(y + distance * math.sin(angle) * 0.7)))
        cuts.polygon(contour, fill=depth)
    for y_fraction, length in ((0.18, 31), (0.57, 47), (0.81, 24)):
        x = rng.randrange(left, max(left + 1, right - length))
        y = top + int((bottom - top) * y_fraction)
        cuts.line([(x, y), (x + length // 2, y + 4), (x + length, y + 7)], fill=45, width=2)
        cuts.line([(x + 4, y + 4), (x + length // 3, y + 6)], fill=116, width=1)

    # Dirt darkens both colors equally, while cuts in either pigment show the shell.
    dirt = ImageChops.multiply(noise(size, 28, rng), noise(size, 8, rng))
    grit = noise(size, 1, rng).point(lambda p: 22 if p > 224 else 0)
    dirt = ImageChops.add(dirt.point(lambda p: min(129, max(0, p - 30) * 2)), grit)
    dusty_paint = Image.composite(Image.new("RGB", size, (59, 49, 33)), paint.convert("RGB"), dirt)
    dusty_paint.putalpha(ImageChops.multiply(paint.getchannel("A"), wear))
    return dusty_paint


def stencils(font_path):
    title = Image.new("L", (1024, 256))
    font = ImageFont.truetype(font_path, 92)
    draw = ImageDraw.Draw(title)
    for word, y in (("MEDICAL", 75), ("CHEST", 180)):
        advance = font.getlength(word)
        start = (1024 - advance) / 2
        offsets = ((-2, 1), (0, -2), (1, 2), (0, 0), (2, -1), (0, 1), (-1, 0))
        for index, letter in enumerate(word):
            x = start + font.getlength(word[:index])
            dx, dy = offsets[index]
            draw.text((x + dx, y + dy), letter, font=font, anchor="lm", fill=255)
            if letter in "ADC":
                bridge = x + dx + font.getlength(letter) * 0.46
                draw.rectangle((bridge, y - 52, bridge + 5, y + 52), fill=0)
    title = title.crop((160, 0, 864, 256)).resize((512, 256), Image.Resampling.LANCZOS)
    cross = Image.new("L", (256, 256))
    ImageDraw.Draw(cross).polygon(
        [(89, 34), (167, 34), (167, 89), (222, 89), (222, 167), (167, 167),
         (167, 222), (89, 222), (89, 167), (34, 167), (34, 89), (89, 89)],
        fill=255,
    )
    red = Image.new("L", (256, 256))
    ImageDraw.Draw(red).rounded_rectangle((17, 17, 239, 239), radius=14, fill=255)
    title_rng = random.Random(324)
    badge_rng = random.Random(325)
    lettering = spray(title, (224, 173, 43), (166, 126, 30), title_rng)
    badge = spray(red, (147, 41, 34), (108, 47, 33), badge_rng)
    badge.alpha_composite(spray(cross, (223, 219, 191), (176, 167, 138), badge_rng))
    return weather(lettering, title, title_rng, 132), weather(badge, red, badge_rng, 171)


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
        ("chest_title", "chest_cross"), stencils(args.font), (0.40, 0.092), (0.15, 0.092)
    ):
        image.save(args.png_dir / f"{name}_ca.png")
        plane(name, width, height)
