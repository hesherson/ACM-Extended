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
ATLAS_SIZE = (2048, 4096)
ATLAS_REGIONS = {
    "lid": (8, 8, *FRONT),
    "back": (1032, 8, *FRONT),
    "right": (8, 1632, *SIDE),
    "left": (664, 1632, *SIDE),
    "top": (8, 3256, *TOP),
    "bottom": (1032, 3256, *TOP),
}
WHITE_TAPE = {
    3: ((697, 410), 263, 63, -4, "C3"),
    6: ((360, 1216), 344, 59, 5, "IV"),
    8: ((679, 432), 233, 65, -8, ""),
}
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
    ((), "black", (0, 0), 0, 0, False, (384, 1194), 1, (((630, 1430), 232, 77, -14),)),
    (("OR",), "red", (365, 788), 208, -8.5, False, (636, 1156), 2, (((769, 444), 160, 62, 14),)),
    (("MED",), "black", (594, 1142), 156, 8, True, (347, 421), 3, (((362, 828), 150, 60, -26),)),
    (("PAD",), "yellow", (308, 404), 124, -4, False, (666, 830), 4, (((625, 1192), 291, 72, 8),)),
    (("IV", "FLUIDS"), "blue", (641, 799), 93, 4.5, True, (350, 433), 2, (((765, 1425), 152, 66, -34),)),
    (("AIRWAY",), "yellow", (514, 1106), 103, -9, True, (612, 424), 5, (((248, 768), 170, 55, -17),)),
    (("BLOOD",), "red", (578, 838), 118, 4, False, (384, 414), 1, (((575, 1250), 204, 69, -7),)),
    ((), "black", (553, 725), 0, -7, False, (357, 1157), 4, (((630, 424), 277, 83, 3),)),
    ((), "red", (0, 0), 0, 0, False, (0, 0), 0, ()),
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


# Paint marker strokes are drawn independently to keep the writing uneven.
MARKER_STROKES = {
    "F": [[(.12,.98),(.21,.68),(.22,.31),(.29,.07),(.89,.13)],[(.24,.46),(.69,.49)]],
    "8": [[(.49,.49),(.22,.39),(.12,.22),(.28,.08),(.61,.06),(.80,.15),(.77,.28),
           (.60,.43),(.31,.61),(.16,.80),(.22,.93),(.42,.99),(.70,.92),(.86,.78),
           (.81,.65),(.63,.54),(.49,.49)]],
    "1": [[(.34,.24),(.59,.07),(.58,.47),(.52,.98)]],
    "0": [[(.52,.08),(.28,.12),(.11,.32),(.13,.67),(.27,.89),(.51,.93),(.77,.79),
           (.87,.54),(.81,.26),(.65,.11),(.52,.08)]],
    "5": [[(.85,.08),(.26,.11),(.17,.46),(.36,.39),(.64,.44),(.82,.61),(.78,.80),
           (.61,.93),(.35,.97),(.11,.83)]],
    "C": [[(.86,.18),(.60,.08),(.36,.14),(.18,.36),(.15,.63),(.29,.85),(.55,.92),(.85,.81)]],
    "3": [[(.17,.19),(.39,.10),(.69,.09),(.79,.22),(.57,.41),(.44,.50),(.70,.56),
           (.83,.71),(.71,.91),(.45,.96),(.18,.88)]],
    "I": [[(.43,.08),(.42,.57),(.37,.93)]],
    "V": [[(.10,.08),(.23,.49),(.45,.93),(.63,.58),(.86,.10)]],
}


def paint_marker(text, height, color, rng):
    step = round(height * .64)
    mask = Image.new("L", (step*len(text)+22, height+28))
    draw = ImageDraw.Draw(mask)
    for index, char in enumerate(text):
        base_x = 10 + index*step + rng.randint(-5, 5)
        base_y = 13 + rng.randint(-7, 7)
        width = step * rng.uniform(.86, 1.04)
        for stroke in MARKER_STROKES[char]:
            points = [(round(base_x+x*width+rng.uniform(-2,2)),
                       round(base_y+y*height+rng.uniform(-2,2))) for x,y in stroke]
            for start, end in zip(points, points[1:]):
                weight = max(2, round(height*rng.uniform(.043,.084)))
                draw.line([start,end], fill=rng.randrange(177,244), width=weight)
                x,y = start
                draw.ellipse((x-weight//2,y-weight//2,x+weight//2,y+weight//2), fill=199)
    mask = ImageChops.multiply(mask.filter(ImageFilter.GaussianBlur(.38)),
                               noise(mask.size, 3, rng).point(lambda p: 135+p*120//255))
    return color_layer(mask.size, color, mask)


def painters_tape(length, width, label, rng):
    size = (length+20, width+20)
    mask = Image.new("L", size)
    points = [(10+x,10+rng.randint(-1,2)) for x in range(0,length+1,8)]
    points += [(length+9+rng.randint(-6,4),y) for y in range(12,width+9,4)]
    points += [(10+x,width+10+rng.randint(-2,2)) for x in range(length,-1,-8)]
    points += [(10+rng.randint(-4,6),y) for y in range(width+8,9,-4)]
    ImageDraw.Draw(mask).polygon(points, fill=247)

    fibers = noise(size, 2, rng)
    dirt = noise(size, 22, rng)
    texture = ImageChops.add(dirt, fibers, scale=2)
    tape = Image.composite(Image.new("RGB",size,(221,220,206)), Image.new("RGB",size,(151,145,127)), texture)
    tape.putalpha(mask)
    crease = Image.new("RGBA",size)
    draw = ImageDraw.Draw(crease)
    for _ in range(7):
        x,y = rng.randrange(18,length), rng.randrange(16,width+6)
        points = [(x,y),(x+4,y+7),(x+2,y+13)]
        draw.line(points, fill=(92,86,71,rng.randrange(39,101)), width=2)
        draw.line([(px+2,py) for px,py in points], fill=(245,242,225,108), width=1)
    crease.putalpha(ImageChops.multiply(crease.getchannel("A"),mask))
    tape.alpha_composite(crease)
    if label:
        stamp(tape,paint_marker(label,round(width*.53),(47,46,38),rng),(length*.48,width*.55),3)
    return tape


def impact_wear(size, rng, density):
    width,height = size
    smear = Image.new("L", size)
    draw = ImageDraw.Draw(smear)
    # Abrasions collect at the corners and where a strap or another case rubbed.
    for _ in range(density):
        x = rng.choice((rng.randrange(13,width//7),rng.randrange(width-width//7,width-13),rng.randrange(24,width-24)))
        y = rng.choice((rng.randrange(16,height//7),rng.randrange(height-height//7,height-16),rng.randrange(24,height-24)))
        length = rng.randrange(29,123)
        angle = rng.uniform(-math.pi,math.pi)
        dx,dy = math.cos(angle)*length,math.sin(angle)*length
        for _ in range(rng.randint(6,16)):
            slide = rng.randrange(-23,24)
            start = (x+slide,y+rng.randint(-14,14))
            end = (start[0]+dx*rng.uniform(.28,1.06),start[1]+dy*rng.uniform(.41,1))
            draw.line((start,end),fill=rng.randint(18,82),width=rng.randint(1,7))
    roughness = noise(size, 3, rng).point(lambda p: 65+p*190//255)
    smear = ImageChops.multiply(smear.filter(ImageFilter.GaussianBlur(1.6)),roughness)
    layer = color_layer(size,(136,138,116),smear)

    cuts = Image.new("RGBA",size)
    draw = ImageDraw.Draw(cuts)
    for _ in range(density + 5):
        x,y = rng.randrange(28,width-28),rng.randrange(24,height-24)
        angle = rng.uniform(-math.pi,math.pi)
        length = rng.randrange(15,115)
        dx,dy = math.cos(angle)*length,math.sin(angle)*length
        points = [(x,y),(round(x+dx*.38),round(y+dy*.41+rng.randint(-4,4))),
                  (round(x+dx*.77),round(y+dy*.76)),(round(x+dx),round(y+dy))]
        radius = rng.randint(2,5)
        draw.line(points,fill=(23,25,19,rng.randint(99,164)),width=radius)
        draw.line([(px-1,py+max(1,radius//2)) for px,py in points[:-1]],
                  fill=(164,158,131,rng.randint(94,175)),width=2)
        draw.line(points[2:],fill=(142,141,117,rng.randint(80,142)),width=1)
    for _ in range(density):
        x,y = rng.randrange(18,width-18),rng.randrange(17,height-17)
        span = rng.randint(6,19)
        tip = [(x-span,y),(x-4,y-4),(x+span,y-2),(x+4,y+4),(x-6,y+5)]
        draw.polygon(tip,fill=(27,28,23,rng.randint(92,153)))
        draw.line(tip[2:]+tip[:1],fill=(152,146,123,rng.randint(92,164)),width=2)
    layer.alpha_composite(cuts)
    return layer


def artwork(number, glyphs):
    lines, color, center, height, angle, halo, residue_pos, residue_style, tape = DESIGNS[number-1]
    rng = random.Random(32540 + number*193)
    wear_rng = random.Random(32740 + number*173)
    lid = impact_wear(FRONT, wear_rng, 22)
    if lines:
        mask = label_mask(lines, height, 13, rng, glyphs)
        stamp(lid, aerosol(mask, color, rng, halo, 1.22 if color == "black" else 1.04), center, angle)
    elif number == 9:
        mask = cross_mask(334, 322, 346, True)
        stamp(lid, aerosol(mask, color, rng, False, 1.22), center, angle)
    elif number == 2:
        stamp(lid, paint_marker("F8105", 112, (230,228,211), rng), (449, 420), 4)
        stamp(lid, paint_marker("C3", 63, (192,189,172), rng), (631, 775), -9)
        swipe = tape_residue(FRONT, [((642,790),97,8,-13,.28)], 28105)
        lid.alpha_composite(swipe)

    # Finish 10's lid has handling wear only. Its red crosses are on the shell.
    if number != 10:
        lid.alpha_composite(residue(FRONT, residue_pos, residue_style, rng))
    fragments = {1:(748,1425),3:(552,160),6:(380,135),8:(661,188)}
    if number in fragments:
        pos = fragments[number]
        lid.alpha_composite(tape_residue(FRONT, [(pos, rng.randint(100,174), 24, rng.choice((-12, 8, 15)), .68)], number * 41))
    for pos, length, width, rotation in tape:
        stamp(lid, tape_patch(length, width, rng), pos, rotation)
    if number in WHITE_TAPE:
        pos,length,width,rotation,label = WHITE_TAPE[number]
        stamp(lid, painters_tape(length,width,label,rng), pos, rotation)
    lid.alpha_composite(abrasion(FRONT, rng, 35+number%5, lid=True))

    sides = []
    for side_index in range(2):
        side = impact_wear(SIDE, wear_rng, 16)
        side.alpha_composite(abrasion(SIDE, rng, 19))
        side.alpha_composite(tape_residue(SIDE, [((455, 257), 120, 26, 3-number, .43)], number*149+side_index))
        cross = cross_mask(380+number+side_index, 125, 128, number in (5, 7, 9, 10))
        stamp(side, aerosol(cross, "black" if number != 10 else "red", rng, False, 1.1), (452, 793), rng.uniform(-11, 11))
        sides.append(side)

    top = impact_wear(TOP, wear_rng, 17)
    top.alpha_composite(abrasion(TOP, rng, 15))
    if number != 10:
        small = cross_mask(411+number, 108, 111, number % 2 == 0)
        stamp(top, aerosol(small, "black", rng, False, 1.08), (803, 458), rng.uniform(-8,8))

    back = impact_wear(FRONT, wear_rng, 25)
    back.alpha_composite(abrasion(FRONT, rng, 25, lid=True))
    back.alpha_composite(residue(FRONT, (rng.randint(385,615), rng.randint(710,860)), number%6, rng))
    bottom = impact_wear(TOP, wear_rng, 21)
    bottom.alpha_composite(abrasion(TOP, rng, 23))
    return dict(zip(ATLAS_REGIONS, (lid, back, *sides, top, bottom)))


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
    dominant = np.argmax(abs(normals), axis=1)
    front_faces = (y.min(axis=1) > front) & (dominant == 1) & (normals[:, 1] > 0)
    lid_coords = ((.266 + z)/.532, (.421 - x)/.844)
    projections = [(front_faces, "lid", lid_coords, (0, 1, 0))]
    if surface == "closed":
        rear_faces = (y.max(axis=1) < -.083) & (dominant == 1) & (normals[:, 1] < 0)
        top_faces = (x.min(axis=1) > .377) & (dominant == 0) & (normals[:, 0] > 0)
        bottom_faces = (x.max(axis=1) < -.377) & (dominant == 0) & (normals[:, 0] < 0)
        right_faces = (z.min(axis=1) > .216) & (dominant == 2) & (normals[:, 2] > 0)
        left_faces = (z.max(axis=1) < -.216) & (dominant == 2) & (normals[:, 2] < 0)
        side_coords = ((.164 - y)/.334, (.421 - x)/.844)
        top_coords = ((.266 + z)/.532, (.164 - y)/.334)
        projections.extend([
            (rear_faces, "back", ((.266-z)/.532, (.421-x)/.844), (0,-1,0)),
            (right_faces, "right", side_coords, (0, 0, 1)),
            (left_faces, "left", side_coords, (0, 0, -1)),
            (top_faces, "top", top_coords, (1, 0, 0)),
            (bottom_faces, "bottom", top_coords, (-1, 0, 0)),
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
    for region, (x, y, width, height) in ATLAS_REGIONS.items():
        image.paste(layers[region].resize((width, height), Image.Resampling.LANCZOS), (x, y))
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
