#!/usr/bin/env python3
"""Build the paint textures and fitted visual models for the ten medical chests.

The mesh dumps contain model-space vertices and face indices for each stock
model. Each finish follows its own model's surfaces. Stock models still supply
the case, moving drawers and collision.
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
    "white": ((230, 228, 211), (170, 170, 151)),
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


# Rectangle bounds are measured on the model-space atlas projections.
FRONT_RIBS = ((.13,.141,.865,.201), (.13,.337,.865,.396),
              (.13,.602,.865,.662), (.13,.797,.865,.856))
REAR_RIBS = ((.13,.119,.865,.179), (.13,.315,.865,.375),
             (.13,.58,.865,.64), (.13,.775,.865,.835))
SIDE_HANDLES = ((.41,.226,.955,.391), (.41,.623,.955,.787))
END_HANDLE = ((.353,.417,.647,.957),)
END_WHEELS = ((.056,.87,.125,.997), (.875,.87,.944,.997))
MISMATCHED_FINISH = 8
GHOST_STENCILS = {
    2: ("FTH", (575, 1162), 137, -5, "black"),
    5: ("EVAC", (328, 797), 105, 3, "black"),
    7: ("M2", (266, 414), 135, -3, "yellow"),
}


def contact_masks(region, size, rng):
    width, height = size
    x = (np.arange(width, dtype=np.float32)+.5)/width
    y = ((np.arange(height, dtype=np.float32)+.5)/height)[:, None]
    abrasion = np.zeros(size[::-1], dtype=np.float32)
    dust = np.zeros_like(abrasion)

    def patch(field, cx, cy, sx, sy, strength):
        blob = np.exp(-.5*((x-cx)/sx)**2-.5*((y-cy)/sy)**2)
        np.maximum(field, blob*strength, out=field)

    end = region in ("top", "bottom")
    side = region in ("left", "right")
    # Worn bevels wrap around each end of the case. Their edges taper into
    # the panels, with more spread at the corners used to set the case down.
    for dx in (x, 1-x):
        for dy, lower in ((y, False), (1-y, not end)):
            corner = np.exp(-.5*((dx/.096)**2 + (dy/.069)**2))
            bevel = np.minimum(np.minimum(dx*width, dy*height), (dx*width+dy*height-23)*.71)
            rim = np.exp(-.5*((bevel-rng.uniform(15,26))/rng.uniform(12,20))**2)
            np.maximum(abrasion, corner*(rim*.81+.19)*rng.uniform(.87,1.1)*(1.30 if lower else 1), out=abrasion)
    if not end:
        lower_edge = np.exp(-.5*((y-.973)/.023)**2)
        np.maximum(abrasion, lower_edge*(.20+.19*np.cos(x*math.pi*3)**2), out=abrasion)
        patch(dust,.53,.96,.42,.090,.70)
    else:
        patch(dust,.50,.54,.54,.38,.72 if region == "bottom" else .37)

    if side or end:
        for x0,y0,x1,y1 in (SIDE_HANDLES if side else END_HANDLE):
            # Knuckles polish the rim. Dust survives toward the recess corners.
            patch(abrasion,x0,(y0+y1)*.48,.023,(y1-y0)*.32,.38)
            for edge in (y0,y1):
                patch(abrasion,x0+.16*(x1-x0),edge,(x1-x0)*.21,.015,.36)
                patch(dust,x0+.24*(x1-x0),edge+(y1-y0)*.09,(x1-x0)*.29,.025,.66)
    else:
        for x0,y0,x1,y1 in (FRONT_RIBS if region == "lid" else REAR_RIBS):
            span = np.clip((x-x0)/.030,0,1)*np.clip((x1-x)/.030,0,1)
            lip = np.exp(-.5*((y-(y0+.017))/.010)**2)
            np.maximum(abrasion, lip*span*rng.uniform(.26,.38), out=abrasion)
            for cx in (x0+.027,x1-.027):
                patch(abrasion,cx,y0+.023,.027,.016,rng.uniform(.40,.59))
            for cx in (x0+.070,rng.uniform(.36,.65),x1-.070):
                patch(dust,cx,y1+.005,rng.uniform(.049,.113),.010,rng.uniform(.30,.52))

    if region == "bottom":
        # Wheels and the rear skid points take the weight during loading.
        for x0,y0,x1,y1 in END_WHEELS:
            patch(abrasion,(x0+x1)*.5,(y0+y1)*.5,.043,.077,1.10)
        for cx in (.19,.32,.68,.81):
            patch(abrasion,cx,rng.uniform(.69,.85),.035,.099,rng.uniform(.48,.78))
    return abrasion, dust


def scrape(mask, start, end, width, strength, rng):
    # Vary the pressure along a single path so each scrape feathers at both ends.
    draw = ImageDraw.Draw(mask)
    x0,y0 = start
    dx,dy = end[0]-x0,end[1]-y0
    wobble = rng.uniform(-3,3)
    steps = 12
    for index in range(steps):
        a,b = index/steps,(index+1)/steps
        pressure = math.sin(math.pi*(a+b)*.5)**.7
        points = [(x0+dx*t,y0+dy*t+wobble*math.sin(t*math.pi)) for t in (a,b)]
        draw.line(points, fill=round(strength*pressure*rng.uniform(.68,1)),
                  width=max(1,round(width*(.38+.62*pressure))))


def contact_wear(region, size, rng):
    contact, dust = contact_masks(region,size,rng)
    width,height = size

    def grain(scale):
        return np.asarray(noise(size,scale,rng),dtype=np.float32)/255

    cloud, speck, fine = grain(61),grain(13),grain(3)
    texture = .46*speck+.34*fine+.20*cloud
    dust_opacity = (dust*(.26+.74*cloud)+cloud*.12)*np.clip((texture-.27)*2.5,0,1)
    dust_alpha = Image.fromarray((dust_opacity*46).astype(np.uint8))
    layer = color_layer(size,(137,122,96),dust_alpha)

    # Diffuse burnishing at the bevels, broken up by fine stress whitening.
    polish = contact*(.27+.62*cloud)*np.clip((texture-.22)*2.3,0,1)
    fibers = np.clip((speck*.52+fine*.48-.54)*3.8,0,1)*contact**1.4
    abrasion_alpha = Image.fromarray(np.clip(polish*143+fibers*49,0,154).astype(np.uint8))
    dull = Image.new("RGB",size,(104,110,94))
    chalk = Image.new("RGB",size,(153,154,136))
    rub = Image.composite(chalk,dull,Image.fromarray((texture*255).astype(np.uint8)))
    rub.putalpha(abrasion_alpha)
    layer.alpha_composite(rub)

    hairlines = Image.new("L",size)
    # Upright panels mostly get glancing marks from sliding in and out of stacks.
    for _ in range(17 if region in ("lid","back") else 11):
        cx = rng.uniform(.055,.945)
        cy = rng.uniform(.045,.955)
        if region in ("lid","back","left","right") and rng.random() < .44:
            cx = rng.choice((.10,.90))+rng.uniform(-.038,.038)
        x,y = cx*width,cy*height
        angle = rng.uniform(-.37,.41) if region in ("lid","back") else rng.uniform(.68,1.48)
        length = rng.uniform(13,57)
        scrape(hairlines,(x,y),(x+math.cos(angle)*length,y+math.sin(angle)*length),
               rng.choice((1,2,2)),rng.uniform(16,48),rng)
    layer.alpha_composite(color_layer(size,(130,130,109),hairlines.filter(ImageFilter.GaussianBlur(.25))))

    if region == "bottom":
        # Drag lines follow the wheel travel across the underside. Keep the
        # wheel hubs and recessed central handle clear of the deepest cuts.
        gouges = Image.new("L",size)
        for _ in range(9):
            x = rng.choice((.17,.27,.72,.83))*width+rng.uniform(-24,24)
            y = rng.uniform(.31,.86)*height
            end = (x+rng.uniform(-24,24),y-rng.uniform(39,125))
            scrape(gouges,(x,y),end,rng.uniform(2.6,5.6),rng.uniform(112,195),rng)
        lip = Image.new("L",size)
        lip.paste(gouges,(2,0))
        lip = ImageChops.subtract(lip,gouges).point(lambda p: p*48//100)
        layer.alpha_composite(color_layer(size,(147,143,123),lip))
        layer.alpha_composite(color_layer(size,(22,25,19),gouges))
    alpha = layer.getchannel("A").point(lambda value: value if value >= 5 else 0)
    layer.putalpha(alpha)
    return Image.composite(layer, Image.new("RGBA",size), alpha.point(lambda value: 255 if value else 0))


def ghost_stencil(text, height, color, rng, glyphs):
    mask = label_mask((text,), height, 11, rng, glyphs)
    paint = aerosol(mask, color, rng, False, 1.05)
    patches = noise(paint.size, 22, rng).point(lambda p: min(194,max(0,p-98)*3))
    grain = noise(paint.size, 4, rng).point(lambda p: min(239,max(0,p-47)*2))
    erosion = ImageChops.multiply(patches,grain)
    drag = ImageDraw.Draw(erosion)
    for _ in range(21):
        x,y = rng.randrange(paint.width),rng.randrange(45,paint.height-30)
        drag.line((x,y,x+rng.randrange(15,97),y+rng.randrange(-9,13)),
                  fill=rng.randrange(0,45),width=rng.randrange(1,5))
    paint.putalpha(ImageChops.multiply(paint.getchannel("A"),erosion))
    return paint


def artwork(number, glyphs):
    lines, color, center, height, angle, halo, residue_pos, residue_style, tape = DESIGNS[number-1]
    rng = random.Random(32540 + number*193)
    wear_rng = random.Random(32840 + number*173)
    lid = contact_wear("lid", FRONT, wear_rng)
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

    if number in GHOST_STENCILS:
        text, pos, height, rotation, pigment = GHOST_STENCILS[number]
        stamp(lid, ghost_stencil(text,height,pigment,rng,glyphs), pos, rotation)

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
    return {"lid": lid, **shell_artwork(number, rng, wear_rng)}


def shell_artwork(number, rng, wear_rng):
    layers = {}
    for region, size in (("back", FRONT), ("right", SIDE), ("left", SIDE), ("top", TOP), ("bottom", TOP)):
        layers[region] = contact_wear(region, size, wear_rng)

    for side_index, region in enumerate(("right","left")):
        side = layers[region]
        side.alpha_composite(tape_residue(SIDE, [((455, 257), 120, 26, 3-number, .43)], number*149+side_index))
        cross = cross_mask(380+number+side_index, 125, 128, number in (5, 7, 9, 10))
        stamp(side, aerosol(cross, "black" if number != 10 else "red", rng, False, 1.1), (452, 793), rng.uniform(-11, 11))

    if number != 10:
        small = cross_mask(411+number, 108, 111, number % 2 == 0)
        stamp(layers["top"], aerosol(small, "black", rng, False, 1.08), (803, 458), rng.uniform(-8,8))

    layers["back"].alpha_composite(residue(FRONT, (rng.randint(385,615), rng.randint(710,860)), number%6, rng))
    return layers


def mesh_dump(path):
    source = json.loads(path.read_text())
    points = np.array([[point[axis] for axis in "XYZ"] for point in source["vertices"]])
    faces = []
    for face in source["faces"]:
        corners = face["VertexIndices"]
        faces.extend((corners[0], corners[i], corners[i+1]) for i in range(1, len(corners)-1))
    return points, np.array(faces)


def paint_projections(positions, normals, surface):
    # U and V are projected in model space so the paint reads in the same
    # direction across the molded ribs and the removable cover.
    x, y, z = positions.transpose(2, 0, 1)
    projection_normals = normals
    if surface == "cabinet":
        # The open stock models have their top on -Y and their drawers on -Z.
        # Transform only the artwork coordinates. The mesh stays in native space.
        x, y, z = -y, -z + .05, x
        projection_normals = normals[:, [1, 2, 0]] * (-1, -1, 1)
    front = .082 if surface == "closed" else .005
    dominant = np.argmax(abs(projection_normals), axis=1)
    front_faces = (y.min(axis=1) > front) & (dominant == 1) & (projection_normals[:, 1] > 0)
    # In Arma's upright placement, -model Z is the viewer's right.
    # Use this for both meshes so lettering and tape keep their orientation.
    lid_coords = ((.266 - z)/.532, (.421 - x)/.844)
    projections = [] if surface == "cabinet" else [(front_faces, "lid", lid_coords, (0, 1, 0))]
    if surface in ("closed", "cabinet"):
        nx, ny, nz = projection_normals.T
        rear_faces = (y.max(axis=1) < -.083) & (dominant == 1) & (ny < 0)
        top_faces = (x.min(axis=1) > .377) & (dominant == 0) & (nx > 0)
        bottom_faces = (x.max(axis=1) < -.377) & (dominant == 0) & (nx < 0)
        right_faces = (z.min(axis=1) > .216) & (dominant == 2) & (nz > 0)
        left_faces = (z.max(axis=1) < -.216) & (dominant == 2) & (nz < 0)
        side_coords = ((.164 - y)/.334, (.421 - x)/.844)
        top_coords = ((.266 + z)/.532, (.164 - y)/.334)
        projections.extend([
            (rear_faces, "back", ((.266+z)/.532, (.421-x)/.844), (0,-1,0)),
            (right_faces, "right", side_coords, (0, 0, 1)),
            (left_faces, "left", side_coords, (0, 0, -1)),
            (top_faces, "top", top_coords, (1, 0, 0)),
            (bottom_faces, "bottom", top_coords, (-1, 0, 0)),
        ])

    return projections


def fitted_faces(path, surface, regions=None):
    points, faces = mesh_dump(path)
    positions = points[faces]
    edges = positions[:, 1:] - positions[:, :1]
    normals = np.cross(edges[:, 0], edges[:, 1])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals /= np.maximum(lengths, 1e-12)

    for selected, region, (u, v), offset in paint_projections(positions, normals, surface):
        if regions is not None and region not in regions:
            continue
        if surface == "cabinet":
            # Paint only exterior triangles behind the front opening. None
            # of the moving drawer geometry belongs in the finish.
            selected = selected & ((.05 - positions[:, :, 2]).max(axis=1) < .053)
        atlas_x, atlas_y, width, height = ATLAS_REGIONS[region]
        uv = np.stack(((atlas_x + u.clip(0, 1)*width)/ATLAS_SIZE[0],
                       (atlas_y + v.clip(0, 1)*height)/ATLAS_SIZE[1]), axis=2)
        # MLOD expects clockwise faces with explicit outward normals.
        for index in np.flatnonzero(selected):
            outward = normals[index] if surface in ("cabinet", "lid") else offset
            vertices = (positions[index] + .0012 * np.asarray(outward))[::-1]
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



def native_shell_albedo(olive_path, sand_path, lid_uv, cabinet4_uv, cabinet7_uv):
    """Tint the molded body in native UV space and keep the olive lid islands."""
    with Image.open(olive_path) as image:
        olive = image.convert("RGB")
    with Image.open(sand_path) as image:
        sand = image.convert("RGB")
    if olive.size != sand.size:
        raise ValueError("Native cabinet albedos must share the same texture layout")

    def uv_mask(*paths):
        mask = Image.new("L", olive.size)
        draw = ImageDraw.Draw(mask)
        for path in paths:
            for lod in json.loads(path.read_text()):
                uv = np.asarray(lod["UV"]) * (olive.width - 1, olive.height - 1)
                for face in lod["Faces"]:
                    draw.polygon([tuple(uv[index]) for index in face], fill=255)
        return mask

    # Extend the color outside the UV islands to avoid dark borders in filtered mipmaps.
    lid_mask = uv_mask(lid_uv).filter(ImageFilter.MaxFilter(9))
    body_mask = uv_mask(cabinet4_uv, cabinet7_uv).filter(ImageFilter.MaxFilter(17))
    paint_mask = ImageChops.subtract(body_mask, lid_mask)
    olive_rgb = np.asarray(olive, dtype=np.float32)
    sand_rgb = np.asarray(sand, dtype=np.float32)
    # Use the stock sand finish's luminance change so the native wear and dark hardware survive.
    luminance_change = (sand_rgb - olive_rgb) @ np.array((.2126, .7152, .0722), dtype=np.float32)
    green_tint = luminance_change[:, :, None] * np.array((.91, 1.19, .90), dtype=np.float32)
    painted = Image.fromarray(np.uint8(np.clip(olive_rgb + green_tint, 0, 255).round()))
    return Image.composite(painted, olive, paint_mask)

def generic_open_atlas(base_paint, png_dir, hemtt):
    """Put the original chest's markings on the same fitted surfaces as the wear."""
    def decode(paa):
        png = png_dir / paa.with_suffix(".png").name
        png.unlink(missing_ok=True)
        subprocess.run([hemtt, "utils", "paa", "convert", str(paa), str(png)], check=True)
        with Image.open(png) as image:
            return image.convert("RGBA")

    image = decode(base_paint)
    stamps = {}
    placements = [
        ("lid", "chest_title", (500, 800), (752, 303)),
        ("lid", "chest_serial", (675, 1168), (335, 78)),
        ("lid", "chest_tape_lid", (451, 425), (462, 190)),
        ("right", "chest_cross", (327, 790), (199, 197)),
        ("left", "chest_cross", (327, 790), (199, 197)),
        ("left", "chest_tape_side", (327, 280), (195, 63)),
        ("top", "chest_cross", (780, 465), (195, 199)),
        ("back", "chest_tape_back", (500, 827), (481, 298)),
    ]
    for region, mark, (cx, cy), (width, height) in placements:
        if mark not in stamps:
            stamps[mark] = decode(DATA / f"{mark}_ca.paa")
        left, top, _, _ = ATLAS_REGIONS[region]
        patch = stamps[mark].resize((width, height), Image.Resampling.LANCZOS)
        image.alpha_composite(patch, (left + cx - width // 2, top + cy - height // 2))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--closed-mesh", type=Path)
    parser.add_argument("--cabinet4-mesh", type=Path, required=True)
    parser.add_argument("--cabinet7-mesh", type=Path, required=True)
    parser.add_argument("--lid-mesh", type=Path, required=True)
    parser.add_argument("--png-dir", type=Path, required=True)
    parser.add_argument("--hemtt", required=True)
    parser.add_argument("--native-shell", nargs=5, type=Path,
                        metavar=("OLIVE_PNG", "SAND_PNG", "LID_UV", "CABINET4_UV", "CABINET7_UV"),
                        help="Rebuild the two-tone body albedo from native textures and visual LOD UV dumps")
    parser.add_argument("--open-only", action="store_true", help="Reuse existing paint atlases and update only open parts")
    args = parser.parse_args()
    if not args.open_only and (args.reference is None or args.closed_mesh is None):
        parser.error("--reference and --closed-mesh are required for a full rebuild")

    destination = DATA / "variants"
    destination.mkdir(parents=True, exist_ok=True)
    args.png_dir.mkdir(parents=True, exist_ok=True)
    surfaces = {
        "cabinet4": tuple(fitted_faces(args.cabinet4_mesh, "cabinet")),
        "cabinet7": tuple(fitted_faces(args.cabinet7_mesh, "cabinet")),
        "lid": tuple(fitted_faces(args.lid_mesh, "lid")),
    }
    if not args.open_only:
        surfaces["closed"] = tuple(fitted_faces(args.closed_mesh, "closed"))
        glyphs = stencil_glyphs(args.reference)
    if any(not faces for faces in surfaces.values()):
        parser.error("At least one source mesh has no paintable exterior faces")

    def write_texture(png, paa):
        temp = args.png_dir / paa.name
        temp.unlink(missing_ok=True)
        subprocess.run([args.hemtt, "utils", "paa", "convert", str(png), str(temp)], check=True)
        paa.write_bytes(temp.read_bytes())
        temp.unlink()

    if args.native_shell:
        body = args.png_dir / f"chest_{MISMATCHED_FINISH}_shell_co.png"
        native_shell_albedo(*args.native_shell).save(body)
        write_texture(body, destination / body.with_suffix(".paa").name)

    for number in range(11):
        paint = f"chest_{number}_ca.paa"
        if not args.open_only:
            png = args.png_dir / Path(paint).with_suffix(".png")
            if number:
                layers = artwork(number, glyphs)
            else:
                rng = random.Random(32840)
                layers = {region: contact_wear(region, (width, height), rng)
                          for region, (_, _, width, height) in ATLAS_REGIONS.items()}
            atlas(layers).save(png)
            write_texture(png, destination / paint)
        if number == 0:
            open_png = args.png_dir / "chest_0_open_ca.png"
            generic_open_atlas(destination / paint, args.png_dir, args.hemtt).save(open_png)
            write_texture(open_png, destination / open_png.with_suffix(".paa").name)
        for surface, faces in surfaces.items():
            surface_paint = "chest_0_open_ca.paa" if number == 0 and surface != "closed" else paint
            texture = f"acm_extended\\data\\medical_chest\\variants\\{surface_paint}"
            (destination / f"chest_{number}_{surface}.p3d").write_bytes(visual_model(faces, texture))

    if args.open_only:
        return

    rng = random.Random(32610)
    red_cross = cross_mask(421, 125, 128, True)
    png = args.png_dir / "chest_cross_red_ca.png"
    aerosol(red_cross, "red", rng, False, 1.08).resize((256, 256), Image.Resampling.LANCZOS).save(png)
    write_texture(png, DATA / png.with_suffix(".paa").name)
    plane("chest_cross_red", .104, .104)


if __name__ == "__main__":
    main()
