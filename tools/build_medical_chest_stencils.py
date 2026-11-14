#!/usr/bin/env python3
"""Build the original transparent chest decals and their flat P3D planes."""
import argparse
import math
import random
import struct
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

DATA = Path(__file__).resolve().parents[1] / "addons/acm_extended/data/medical_chest"

# Pixel bounds of the six rows on the supplied military stencil sheet.
STENCIL_ROWS = (
    ("ABCDEFG", 36, 77, 60, 110),
    ("HIJKLMN", 36, 77, 132, 183),
    ("OPQRSTU", 36, 77, 204, 256),
    ("VWXYZ", 113, 77, 276, 328),
    ("123456", 76, 77, 350, 400),
    ("7890", 152, 77, 422, 473),
)


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

    # Dirt tones down the pigment and the chips reveal the shell beneath it.
    dirt = ImageChops.multiply(noise(size, 28, rng), noise(size, 8, rng))
    grit = noise(size, 1, rng).point(lambda p: 22 if p > 224 else 0)
    dirt = ImageChops.add(dirt.point(lambda p: min(129, max(0, p - 30) * 2)), grit)
    dusty_paint = Image.composite(Image.new("RGB", size, (59, 49, 33)), paint.convert("RGB"), dirt)
    dusty_paint.putalpha(ImageChops.multiply(paint.getchannel("A"), wear))
    return dusty_paint


def stencil_glyphs(reference):
    source = ImageOps.invert(Image.open(reference).convert("L").resize((540, 540)))
    source = source.point(lambda p: max(0, min(255, (p - 48) * 255 // 185)))
    glyphs = {}
    for letters, first, step, top, bottom in STENCIL_ROWS:
        for index, letter in enumerate(letters):
            center = first + index * step
            tile = source.crop((center - 29, top, center + 29, bottom))
            glyphs[letter] = tile.crop(tile.getbbox())
    return glyphs


def stencil_line(mask, label, y, height, gap, glyphs):
    tiles = []
    for letter in label:
        if letter == "-":
            tiles.append(Image.new("L", (round(height * 0.27), round(height * 0.11)), 255))
            continue
        glyph = glyphs[letter]
        tiles.append(glyph.resize((round(glyph.width * height / glyph.height), height), Image.Resampling.LANCZOS))
    x = (mask.width - sum(tile.width for tile in tiles) - gap * (len(tiles) - 1)) // 2
    for index, tile in enumerate(tiles):
        nudge = (-1, 1, 0, -1, 0, 1, 0)[index % 7]
        mask.paste(tile, (x, y - tile.height // 2 + nudge))
        x += tile.width + gap


def tape_residue(size, strips, seed):
    """Faded adhesive, torn scrim and dirt along old tape edges."""
    rng = random.Random(seed)
    layer = Image.new("RGBA", size)
    for (cx, cy), length, width, angle, remnant in strips:
        pad = 8
        patch_size = length + 2 * pad, width + 2 * pad
        silhouette = Image.new("L", patch_size)
        rim = [
            (pad + x, pad + rng.randint(-2, 2)) for x in range(0, length + 1, 4)
        ] + [
            (pad + x, pad + width + rng.randint(-2, 2)) for x in range(length, -1, -4)
        ]
        ImageDraw.Draw(silhouette).polygon(rim, fill=255)

        wear = noise(patch_size, 12, rng)
        grain = noise(patch_size, 2, rng)
        strength = ImageChops.multiply(wear, grain)
        film = strength.point(lambda p: min(126, max(0, (p - 18) * 2)))
        outline = ImageChops.subtract(silhouette, silhouette.filter(ImageFilter.MinFilter(5)))
        dirt = ImageChops.multiply(outline, strength.point(lambda p: min(150, p * 2)))
        thread = Image.new("L", patch_size)
        draw = ImageDraw.Draw(thread)
        for x in range(pad + 1, pad + length, rng.choice((3, 4))):
            if rng.random() < remnant:
                y = rng.randint(pad, pad + width // 2)
                draw.line((x, y, x, min(pad + width, y + rng.randint(2, width))), fill=rng.randint(44, 136))
        for _ in range(max(2, length // 17)):
            x = rng.randrange(pad, pad + length)
            y = rng.randint(pad, pad + width)
            draw.line((x, y, min(x + rng.randint(2, 9), pad + length), y), fill=rng.randint(30, 95))
        glue = Image.composite(Image.new("RGB", patch_size, (152, 138, 107)),
                               Image.new("RGB", patch_size, (67, 64, 50)), wear)
        glue.putalpha(ImageChops.multiply(silhouette, ImageChops.add(film, thread)))
        edge = Image.new("RGBA", patch_size, (31, 28, 23, 0))
        edge.putalpha(dirt)
        glue.alpha_composite(edge)
        glue = glue.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        layer.alpha_composite(glue, (cx - glue.width // 2, cy - glue.height // 2))
    return layer


def stencils(reference):
    glyphs = stencil_glyphs(reference)
    title = Image.new("L", (512, 256))
    stencil_line(title, "MEDICAL", 76, 65, 12, glyphs)
    stencil_line(title, "CHEST", 172, 65, 12, glyphs)

    serial = Image.new("L", (256, 64))
    stencil_line(serial, "MED-01", 33, 38, 8, glyphs)

    cross = Image.new("L", (256, 256))
    ImageDraw.Draw(cross).polygon(
        [(89, 35), (168, 37), (168, 90), (220, 89), (222, 166), (168, 167),
         (166, 219), (90, 221), (88, 167), (36, 167), (35, 89), (89, 88)],
        fill=255,
    )
    title_rng = random.Random(324)
    serial_rng = random.Random(325)
    cross_rng = random.Random(326)
    return (
        ("chest_title", weather(spray(title, (227, 174, 49), (161, 117, 29), title_rng),
                                title, title_rng, 183), 0.40, 0.16),
        ("chest_serial", weather(spray(serial, (210, 158, 46), (142, 109, 36), serial_rng),
                                 serial, serial_rng, 53), 0.178, 0.041),
        ("chest_cross", weather(spray(cross, (15, 15, 13), (40, 38, 31), cross_rng),
                                cross, cross_rng, 222), 0.104, 0.104),
        ("chest_tape_lid", tape_residue((512, 256), [
            ((244, 49), 354, 25, 1.6, 0.25), ((247, 207), 330, 23, 0.6, 0.19),
            ((72, 123), 190, 25, 90.5, 0.58), ((416, 126), 177, 24, 89.6, 0.33),
            ((437, 211), 47, 16, -7, 0.70),
        ], 327), 0.246, 0.100),
        ("chest_tape_side", tape_residue((256, 64), [
            ((114, 34), 184, 29, -2, 0.61), ((211, 28), 43, 14, 8, 0.39),
        ], 328), 0.102, 0.033),
        ("chest_tape_back", tape_residue((512, 256), [
            ((248, 31), 342, 23, -1.5, 0.40), ((251, 223), 353, 27, -1.1, 0.45),
            ((86, 113), 205, 22, 90, 0.44), ((418, 127), 199, 24, 88, 0.38),
            ((72, 224), 56, 17, 6, 0.73),
        ], 329), 0.256, 0.157),
    )


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
    parser.add_argument("--reference", required=True, type=Path, help="Supplied military stencil sheet")
    parser.add_argument("--png-dir", required=True, type=Path)
    args = parser.parse_args()
    args.png_dir.mkdir(parents=True, exist_ok=True)
    for name, image, width, height in stencils(args.reference):
        image.save(args.png_dir / f"{name}_ca.png")
        plane(name, width, height)
