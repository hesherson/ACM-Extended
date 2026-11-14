#!/usr/bin/env python3
"""Build the paint textures and fitted visual models for the ten medical chests.

The mesh dumps contain model-space vertices and face indices for the closed
cabinet and loose lid. The original models still supply the case and collision.
"""
import argparse
import json
from pathlib import Path
import math
import random
import struct
import subprocess

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from build_medical_chest_stencils import DATA, noise, plane, stencil_glyphs, tape_residue, weather

FRONT = (1000, 1600)
SIDE = (640, 1600)
TOP = (1000, 640)
ATLAS_SIZE = (1024, 4096)
ATLAS_REGIONS = ((8, 8, 1008, 1600), (8, 1624, 640, 1600), (8, 3240, 1008, 640))
PIGMENTS = {
    "yellow": ((232, 182, 51), (161, 122, 36)),
    "blue": ((96, 155, 188), (51, 102, 139)),
    "red": ((190, 68, 53), (117, 43, 39)),
    "black": ((13, 14, 12), (27, 26, 21)),
}


def color_layer(size, rgb, alpha):
    layer = Image.new("RGBA", size, rgb + (0,))
    layer.putalpha(alpha)
    return layer


def label_mask(lines, height, gap, rng, glyphs):
    line_step = round(height * 1.21)
    mask = Image.new("L", (830, height + (len(lines) - 1) * line_step + 44))
    for row, line in enumerate(lines):
        tiles = []
        for char in line:
            if char == " ":
                tiles.append(Image.new("L", (height // 3, height)))
                continue
            source = glyphs[char]
            glyph = source.resize((round(height * source.width / source.height * rng.uniform(.90, 1.06)), height),
                                  Image.Resampling.LANCZOS)
            tiles.append(glyph.rotate(rng.uniform(-3.8, 3.8), resample=Image.Resampling.BICUBIC, expand=True))
        x = (mask.width - sum(g.width for g in tiles) - gap * (len(line) - 1)) // 2
        for glyph in tiles:
            y = 22 + row * line_step + (height - glyph.height) // 2 + rng.randint(-6, 6)
            mask.paste(glyph, (x, y))
            x += glyph.width + gap
    return mask.crop(mask.getbbox())


def cross_mask(seed, width, height, rough):
    rng = random.Random(seed)
    mask = Image.new("L", (width, height))
    x, y = width // 2, height // 2
    a = width * .15
    b = height * .15
    points = [
        (x-a, 12), (x+a, 12), (x+a, y-b), (width-12, y-b), (width-12, y+b),
        (x+a, y+b), (x+a, height-12), (x-a, height-12), (x-a, y+b),
        (12, y+b), (12, y-b), (x-a, y-b),
    ]
    if rough:
        points = [(round(px + rng.uniform(-13, 13)), round(py + rng.uniform(-13, 13))) for px, py in points]
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask


def aerosol(mask, color, rng, edge_spray, coverage):
    pigment, fade = PIGMENTS[color]
    plate = Image.new("L", (mask.width + 128, mask.height + 106))
    plate.paste(mask, (64, 53))
    size = plate.size
    fine = noise(size, 2, rng)
    clouds = noise(size, 38, rng)
    opacity = ImageChops.multiply(plate, clouds.point(lambda p: min(255, int(coverage * (128 + p * .61)))))
    opacity = ImageChops.multiply(opacity, fine.point(lambda p: 80 + p if p < 107 else 255))
    soft = ImageChops.subtract(plate.filter(ImageFilter.GaussianBlur(4.5)), plate)
    opacity = ImageChops.add(opacity, ImageChops.multiply(soft, fine.point(lambda p: min(145, max(0, (p - 62) * 2)))))
    if edge_spray:
        rim = Image.new("L", size)
        d = ImageDraw.Draw(rim)
        x1, y1, x2, y2 = 35, 33, size[0] - 29, size[1] - 27
        for bounds in ((x1, y1, x2, y1 + 9), (x1, y1, x1 + 11, y2),
                       (x1, y2 - 8, x2, y2), (x2 - 8, y1, x2, y2)):
            d.rectangle(bounds, fill=rng.randint(66, 132))
        broken = ImageChops.multiply(rim.filter(ImageFilter.GaussianBlur(5)), clouds.point(lambda p: max(0, min(255, (p-43)*2))))
        opacity = ImageChops.add(opacity, ImageChops.multiply(broken, fine))
    freckles = Image.new("L", size)
    d = ImageDraw.Draw(freckles)
    for _ in range(mask.width // 2):
        x, y = rng.randrange(10, size[0]-10), rng.randrange(10, size[1]-10)
        if rng.random() < .65 and not plate.getpixel((x, y)):
            radius = rng.choices([1, 2, 3], [8, 3, 1])[0]
            d.ellipse((x, y, x+radius, y+radius), fill=rng.randrange(16, 98))
    opacity = ImageChops.add(opacity, freckles)
    pigment_rgb = Image.composite(Image.new("RGB", size, fade), Image.new("RGB", size, pigment),
                                  clouds.point(lambda p: p * 3 // 4))
    pigment_rgb.putalpha(opacity)
    return weather(pigment_rgb, plate, rng, round(mask.width * .68))


def stamp(target, layer, center, angle):
    rotated = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    target.alpha_composite(rotated, (round(center[0] - rotated.width / 2), round(center[1] - rotated.height / 2)))


def tape_patch(length, width, rng):
    mask = Image.new("L", (length + 16, width + 16))
    d = ImageDraw.Draw(mask)
    ends = [(length + 5 + rng.randint(-5, 5), y) for y in range(9, width + 8, 4)]
    start = [(8 + rng.randint(-4, 4), y) for y in range(width + 6, 7, -3)]
    d.polygon([(8, 8), (length + 5, 6), *ends, (length + 9, width + 8), (7, width + 10), *start], fill=244)
    cloth = noise(mask.size, 11, rng)
    fine = noise(mask.size, 2, rng)
    values = np.asarray(ImageChops.add(cloth, fine, scale=2)).astype(float)
    yy, xx = np.indices(values.shape)
    weave = (xx % 5 == 1) * 2 + (yy % 4 == 0) * 2
    values = np.clip(11 + values * .092 + weave, 0, 65).astype(np.uint8)
    rgb = np.stack((values, values, (values.astype(float)*.93).astype(np.uint8)), axis=-1)
    tape = Image.fromarray(rgb)
    tape.putalpha(mask)
    d = ImageDraw.Draw(tape)
    for _ in range(9):
        x, y = rng.randrange(14, length + 2), rng.randrange(12, width + 3)
        d.line((x,y,min(x+rng.randrange(4,29),length+3),y+rng.choice((-2,0,1))), fill=(71,67,57,rng.randrange(60,116)), width=1)
    for x in (8, length+5):
        d.line((x, 12, x+rng.randrange(-2,4), width+5), fill=(80,77,63,125), width=2)
    return tape


def abrasion(size, rng, density, lid=False):
    w, h = size
    layer = Image.new("RGBA", size)
    d = ImageDraw.Draw(layer)
    for _ in range(density * 5):
        if rng.random() < .55:
            x = rng.choice((rng.randint(10, w//9), rng.randint(w-w//9, w-10)))
        else:
            x = rng.randint(22, w-22)
        y = rng.randint(22, h-22)
        length = rng.choices((rng.randint(3, 10), rng.randint(11, 29), rng.randint(31, 88)), (57, 33, 10))[0]
        turn = rng.uniform(-math.pi, math.pi)
        dx, dy = math.cos(turn)*length, math.sin(turn)*length
        end = (round(x+dx), round(y+dy))
        edge = (round(x+dx*.64), round(y+dy*.61+rng.uniform(-3,3)))
        if length > 28:
            d.line([(x,y), edge, end], fill=(24, 25, 21, rng.randint(76,148)), width=3)
        alpha = rng.randint(74,168)
        tint = rng.choice(((138,133,111), (111,116,98), (160,151,123), (112,104,88)))
        d.line([(x,y+1), (edge[0],edge[1]+1), (end[0],end[1]+1)], fill=tint+(alpha,), width=rng.choice((1,2,2,3)))
    for _ in range(density):
        x, y = rng.randint(22,w-22), rng.randint(28,h-28)
        if lid and rng.random() < .60:
            y = rng.choice((238, 286, 541, 576, 997, 1047, 1297, 1341, 1525)) + rng.randint(-15,15)
        r = rng.choice((4,5,6,8,11,13))
        d.polygon([(x-r,y+2),(x-2,y-3),(x+r,y-1),(x+r//2,y+2),(x-4,y+4)],
                  fill=(41, 39, 31, rng.randint(79,148)))
        d.line((x-r+2,y+2,x-4,y+4,x+r//2,y+2), fill=(149,139,113,rng.randint(105,179)), width=2)
    return layer


# The coordinates lie on the upright lid, with top-left as the origin.
DESIGNS = (
    (("MED CHEST", "1"), "yellow", (483, 766), 97, -3.5, True, (573, 416), 0, ()),
    (("SURG",), "blue", (541, 407), 150, 6.8, True, (384, 1194), 1, (((630, 1430), 232, 77, -14),)),
    (("OR",), "red", (365, 788), 208, -8.5, False, (636, 1156), 2, (((769, 444), 160, 62, 14),)),
    (("MED",), "black", (594, 1142), 156, 8, True, (347, 421), 3, (((362, 828), 150, 60, -26),)),
    (("PAD",), "yellow", (308, 404), 124, -4, False, (666, 830), 4, (((625, 1192), 291, 72, 8),)),
    (("IV", "FLUIDS"), "blue", (641, 799), 93, 4.5, True, (350, 433), 2, (((765, 1425), 152, 66, -34),)),
    (("AIRWAY",), "yellow", (514, 1106), 103, -9, True, (612, 424), 5, (((248, 768), 170, 55, -17),)),
    (("BLOOD",), "red", (578, 838), 118, 4, False, (384, 414), 1, (((575, 1250), 204, 69, -7),)),
    ((), "black", (553, 725), 0, -7, False, (357, 1157), 4, (((630, 424), 277, 83, 3),)),
    ((), "red", (386, 1152), 0, 12, True, (568, 410), 3, (((721, 805), 142, 78, 27), ((759, 859), 101, 49, -24))),
)


def residue(size, center, style, rng):
    x, y = center
    # Each outline has missing edges or displaced fragments where tape peeled.
    templates = (
        [(-5,-60,275,23,1,.57),(4,66,247,22,-2,.43),(-137,-1,160,20,91,.47),(133,9,138,20,89,.43)],
        [(-26,-46,221,24,3,.48),(-126,9,140,23,89,.53),(117,31,101,22,87,.45),(16,65,208,17,-5,.42)],
        [(-65,-30,140,30,8,.58),(99,-29,98,27,-11,.39),(-82,51,104,24,-9,.49)],
        [(-5,-68,230,18,-5,.57),(-115,1,154,18,86,.48),(112,-5,152,20,94,.37),(-9,64,172,18,-6,.38)],
        [(-111,3,129,29,68,.53),(84,19,112,28,70,.43),(-19,-48,120,20,1,.39)],
        [(-10,-51,243,20,2,.52),(-104,21,133,25,94,.53),(104,19,146,20,86,.43),(22,79,213,17,-1,.50)],
    )
    strips = [((x+dx,y+dy), length, width, angle, fragment)
              for dx,dy,length,width,angle,fragment in templates[style]]
    return tape_residue(size, strips, rng.randrange(2**31))


def artwork(number, glyphs):
    lines, color, center, height, angle, halo, residue_pos, residue_style, tape = DESIGNS[number-1]
    rng = random.Random(32540 + number*193)
    lid = Image.new("RGBA", FRONT)
    if lines:
        mask = label_mask(lines, height, 13, rng, glyphs)
    else:
        mask = cross_mask(325+number, 322 if number == 9 else 277, 346 if number == 9 else 290, True)
    layer = aerosol(mask, color, rng, halo, 1.22 if color == "black" else 1.04)
    stamp(lid, layer, center, angle)
    lid.alpha_composite(residue(FRONT, residue_pos, residue_style, rng))
    if number in (1, 3, 6, 8, 10):
        pos = ((748, 1425), (552, 160), (380, 135), (661, 188), (418, 744))[(1,3,6,8,10).index(number)]
        lid.alpha_composite(tape_residue(FRONT, [(pos, rng.randint(100,174), 24, rng.choice((-12, 8, 15)), .68)], number * 41))
    for pos, length, width, rotation in tape:
        stamp(lid, tape_patch(length, width, rng), pos, rotation)
    lid.alpha_composite(abrasion(FRONT, rng, 27+number%5, lid=True))

    side = abrasion(SIDE, rng, 15)
    side.alpha_composite(tape_residue(SIDE, [((455, 257), 120, 26, 3-number, .43)], number*149))
    cross = cross_mask(380+number, 125, 128, number in (5, 7, 9, 10))
    stamp(side, aerosol(cross, "black" if number != 10 else "red", rng, False, 1.1), (452, 793), rng.uniform(-11, 11))

    top = abrasion(TOP, rng, 12)
    small = cross_mask(411+number, 108, 111, number % 2 == 0)
    stamp(top, aerosol(small, "black" if number != 10 else "red", rng, False, 1.08), (803, 458), rng.uniform(-8,8))
    return lid, side, top



def mesh_dump(path):
    source = json.loads(path.read_text())
    points = np.array([[point[axis] for axis in "XYZ"] for point in source["vertices"]])
    faces = []
    for face in source["faces"]:
        corners = face["VertexIndices"]
        faces.extend((corners[0], corners[i], corners[i+1]) for i in range(1, len(corners)-1))
    return points, np.array(faces)


def fitted_faces(path, surface):
    points, faces = mesh_dump(path)
    positions = points[faces]
    edges = positions[:, 1:] - positions[:, :1]
    normals = np.cross(edges[:, 0], edges[:, 1])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals /= np.maximum(lengths, 1e-12)

    # U and V are projected in model space so the paint reads in the same
    # direction across the molded ribs and the removable cover.
    x, y, z = positions.transpose(2, 0, 1)
    front = .082 if surface == "closed" else .005
    front_faces = (y.min(axis=1) > front) & (normals[:, 1] > .15)
    lid_coords = ((.266 + z)/.532, (.421 - x)/.844)
    projections = [(front_faces, 0, lid_coords, (0, 1, 0))]
    if surface == "closed":
        top_faces = (x.min(axis=1) > .395) & (normals[:, 0] > .25)
        right_faces = (z.min(axis=1) > .229) & (normals[:, 2] > .22)
        left_faces = (z.max(axis=1) < -.229) & (normals[:, 2] < -.22)
        side_coords = ((.164 - y)/.334, (.421 - x)/.844)
        top_coords = ((.266 + z)/.532, (.164 - y)/.334)
        projections.extend([
            (right_faces, 1, side_coords, (0, 0, 1)),
            (left_faces, 1, side_coords, (0, 0, -1)),
            (top_faces, 2, top_coords, (1, 0, 0)),
        ])

    for selected, region, (u, v), offset in projections:
        atlas_x, atlas_y, width, height = ATLAS_REGIONS[region]
        uv = np.stack(((atlas_x + u.clip(0, 1)*width)/ATLAS_SIZE[0],
                       (atlas_y + v.clip(0, 1)*height)/ATLAS_SIZE[1]), axis=2)
        # MLOD expects clockwise faces with explicit outward normals.
        for index in np.flatnonzero(selected):
            vertices = (positions[index] + .0012 * np.array(offset))[::-1]
            yield vertices, normals[index], uv[index, ::-1]


def visual_model(faces, texture):
    points = []
    indices = {}
    corners = []
    for vertices, normal, uv in faces:
        face_indices = []
        for vertex in vertices:
            key = tuple(vertex)
            if key not in indices:
                indices[key] = len(points)
                points.append(key)
            face_indices.append(indices[key])
        corners.append((face_indices, normal, uv))

    mesh = bytearray(b"MLOD" + struct.pack("<II", 257, 1))
    mesh += b"P3DM" + struct.pack("<6I", 28, 256, len(points), len(corners), len(corners), 0)
    for point in points:
        mesh += struct.pack("<3fI", *point, 0)
    for _, normal, _ in corners:
        mesh += struct.pack("<3f", *normal)
    texture = (texture + "\0\0").encode()
    for index, (face_indices, _, uv) in enumerate(corners):
        mesh += struct.pack("<I", 3)
        for vertex, (u, v) in zip(face_indices, uv):
            mesh += struct.pack("<IIff", vertex, index, u, v)
        mesh += struct.pack("<IIffI", 0, 0, 0, 0, 0) + texture

    mesh += b"TAGG\x01#Property#\0" + struct.pack("<I", 128)
    mesh += b"autocenter".ljust(64, b"\0") + b"0".ljust(64, b"\0")
    mesh += b"\x01#UVSet#\0" + struct.pack("<II", 4+24*len(corners), 0)
    for _, _, uv in corners:
        for u, v in uv:
            mesh += struct.pack("<2f", u, v)
    mesh += b"\x01#EndOfFile#\0" + struct.pack("<If", 0, 0)
    return mesh


def atlas(layers):
    image = Image.new("RGBA", ATLAS_SIZE)
    for layer, (x, y, width, height) in zip(layers, ATLAS_REGIONS):
        image.paste(layer.resize((width, height), Image.Resampling.LANCZOS), (x, y))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--closed-mesh", type=Path, required=True)
    parser.add_argument("--lid-mesh", type=Path, required=True)
    parser.add_argument("--png-dir", type=Path, required=True)
    parser.add_argument("--hemtt", required=True)
    args = parser.parse_args()

    destination = DATA / "variants"
    destination.mkdir(parents=True, exist_ok=True)
    args.png_dir.mkdir(parents=True, exist_ok=True)
    glyphs = stencil_glyphs(args.reference)
    closed = tuple(fitted_faces(args.closed_mesh, "closed"))
    lid = tuple(fitted_faces(args.lid_mesh, "lid"))
    def write_texture(png, paa):
        temp = args.png_dir / paa.name
        temp.unlink(missing_ok=True)
        subprocess.run([args.hemtt, "utils", "paa", "convert", str(png), str(temp)], check=True)
        paa.write_bytes(temp.read_bytes())
        temp.unlink()

    for number in range(1, 11):
        png = args.png_dir / f"chest_{number}_ca.png"
        atlas(artwork(number, glyphs)).save(png)
        write_texture(png, destination / png.with_suffix(".paa").name)
        texture = f"acm_extended\\data\\medical_chest\\variants\\{png.with_suffix('.paa').name}"
        for surface, faces in (("closed", closed), ("lid", lid)):
            (destination / f"chest_{number}_{surface}.p3d").write_bytes(visual_model(faces, texture))

    rng = random.Random(32610)
    red_cross = cross_mask(421, 125, 128, True)
    png = args.png_dir / "chest_cross_red_ca.png"
    aerosol(red_cross, "red", rng, False, 1.08).resize((256, 256), Image.Resampling.LANCZOS).save(png)
    write_texture(png, DATA / png.with_suffix(".paa").name)
    plane("chest_cross_red", .104, .104)


if __name__ == "__main__":
    main()
