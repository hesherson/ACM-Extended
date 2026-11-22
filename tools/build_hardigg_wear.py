"""Author the Hardigg lid markings and the material art for modeled tape."""
from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from build_hardigg_sheet import STENCIL_MOVED
from build_medical_chest_stencils import noise, tape_residue
from build_medical_chest_variants import (
    DESIGNS, GHOST_STENCILS, WHITE_TAPE, aerosol, contact_wear, cross_mask, label_mask, residue, stamp,
)

FORM = Path(__file__).with_name("assets") / "hardigg_inventory_record.webp"
# Lid-face center, length, width, rotation and opacity.
LONG_RESIDUE = {
    1: ((824, 793), 1060, 62, 89, .96),
    4: ((165, 873), 842, 51, 94, .72),
    7: ((547, 479), 612, 45, 120, .51),
    11: ((499, 1373), 733, 55, -2, .84),
}
SHORT_RESIDUE = {
    0: ((710, 393), 222, 33, -7),
    10: ((379, 472), 207, 48, 8),
    11: ((353, 393), 244, 42, -6),
}
EXTRA_TAPE = {
    0: ((372, 1248), 216, 64, -9, (56, 58, 53)),
    1: ((640, 1276), 237, 70, 6, (58, 61, 53)),
    10: ((390, 1088), 262, 76, -11, (118, 119, 104)),
    11: ((562, 1170), 248, 65, -5, (117, 119, 111)),
}
# Earlier markings, slightly misregistered beneath the current lid stencils.
PREVIOUS_PAINT = {
    3: ("SURG", (398, 803), 208, -3, .41),
    6: ("SALINE", (600, 791), 138, -2, .36),
    8: ("PLASMA", (557, 856), 148, -5, .34),
}


def make_adhesive_visible(layer, opacity=1.0):
    grain = layer.getchannel("A")
    warmed = Image.blend(layer.convert("RGB"), Image.new("RGB", layer.size, (155, 144, 111)), .36)
    warmed.putalpha(grain.point(lambda p: round(min(192, p * 2.15) * opacity)))
    return warmed


def tape_material(length, width, rng, color, label, glyphs):
    """The fabric coloring. The outline, folds and tears are built into the mesh."""
    size = length, width
    yy = np.indices((width, length))[0]
    cloth = (np.asarray(noise(size, 18, rng), dtype=np.float32) - 128) * .09
    dirty_edges = np.exp(-np.minimum(yy, width - 1 - yy) / 5) * 12
    rgb = np.clip(np.asarray(color) + (cloth - dirty_edges)[:, :, None], 0, 255)
    tape = Image.fromarray(rgb.astype(np.uint8)).convert("RGBA")
    if label:
        mask = label_mask((label,), round(width * .45), 6, rng, glyphs)
        ink = Image.new("RGBA", mask.size, (59, 55, 48, 0))
        ink.putalpha(mask)
        stamp(tape, ink, (length * .47, width * .52), 2)
    return tape


def inventory_card(handwriting, quantity):
    """A printed field inventory folded into a sleeve."""
    width, height = 490, 197
    sheet = Image.new("RGBA", (width + 76, height + 70))
    # The visible half shows the actual supplied form header and its first few inventory rows.
    with Image.open(FORM) as ref:
        x, y = ref.size
        form = ImageOps.grayscale(ref.crop((round(.049*x), round(.039*y), round(.951*x), round(.282*y))))
    form = form.resize((width-30, height-23), Image.Resampling.LANCZOS)
    print_colors = ImageOps.colorize(form, (38, 43, 37), (212, 211, 188)).convert("RGBA")

    draw = ImageDraw.Draw(sheet)
    draw.rounded_rectangle((27,25,27+width+12,25+height+10), radius=8, fill=(178,183,164,255),
                           outline=(211,216,199,255), width=2)
    draw.polygon([(42,46),(width+25,42),(width+28,height+25),(47,height+28)], fill=(202,198,175,255))
    draw.line((52,height+20,width+19,height+15), fill=(103,102,80,190), width=3)
    sheet.alpha_composite(print_colors, (43, 38))
    draw = ImageDraw.Draw(sheet)
    pen = ImageFont.truetype(str(handwriting), 24)
    count_pen = ImageFont.truetype(str(quantity), 24)
    for position, note in (((53, 83), "MED 02 / AID DET"), ((59, 135), "GAUZE"),
                           ((61, 154), "IV SETS"), ((59, 174), "NPA"),
                           ((408, 135), "18"), ((409, 154), "12"), ((408, 174), "8")):
        draw.text(position, note, font=count_pen if note.isdecimal() else pen, fill=(52, 62, 71, 255))

    gloss = Image.new("RGBA", sheet.size)
    light = ImageDraw.Draw(gloss)
    light.polygon([(58,41),(78,40),(225,height+19),(206,height+18)], fill=(245,251,238,17))
    light.line([(44,137),(219,138),(324,136),(width+17,135)], fill=(246,246,226,34), width=2)
    light.line([(43,height+13),(width+23,height+13)], fill=(254,251,227,100), width=2)
    sheet.alpha_composite(gloss)

    return sheet.crop((27, 25, 27 + width + 12, 25 + height + 10))


def original_tape(index):
    black = DESIGNS[index - 1][8] if 0 < index <= len(DESIGNS) else ()
    tapes = [(*strip, (47, 49, 46), "") for strip in black]
    if index in WHITE_TAPE:
        pos, length, width, angle, label = WHITE_TAPE[index]
        tapes.append((pos, length, width, angle, (203, 198, 177), label))
    return tapes


def lid_tape(index):
    tapes = original_tape(index)
    if index in EXTRA_TAPE:
        tapes.append((*EXTRA_TAPE[index], ""))
    return [(*tape, ("fold", "lift", "split")[(index + i) % 3])
            for i, tape in enumerate(tapes)]


def worn_paint(mask, color, rng, overspray, coverage):
    paint = aerosol(mask, color, rng, False, coverage)
    padded = Image.new("L", paint.size)
    padded.paste(mask, (64, 53))
    if color == "black":
        inner = padded.filter(ImageFilter.MinFilter(15))
        edge = ImageChops.subtract(padded, inner).filter(ImageFilter.GaussianBlur(1.5))
        loss = ImageChops.multiply(edge, noise(paint.size, 12, rng).point(lambda value: min(245, 50 + value)))
        paint.putalpha(ImageChops.subtract(paint.getchannel("A"), loss))
    haze = ImageChops.subtract(padded.filter(ImageFilter.GaussianBlur(8 + overspray * 8)), padded)
    haze = ImageChops.multiply(haze, noise(paint.size, 5, rng))
    diffuse = Image.new("RGBA", paint.size, paint.convert("RGB").getpixel((64, 53)))
    diffuse.putalpha(haze.point(lambda value: min(130, value * overspray)))
    diffuse.alpha_composite(paint)
    return diffuse


def stencil_in_valley(lid, lines, center, height, angle, color, rng, glyphs, haze, strength):
    # Four molded ribs centered at z=.700, .517, .333 and .150 m, each 48 mm wide.
    valleys = ((107, 198), (306, 551), (659, 904), (1012, 1257), (1365, 1510))
    lo, hi = min(valleys, key=lambda band: abs(sum(band)/2 - center[1]))
    mask = label_mask(lines, height, 11, rng, glyphs)
    paint = worn_paint(mask, color, rng, haze, strength)
    paint = paint.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    box = paint.getbbox()
    paint = paint.crop(box)
    scale = min(1, (hi-lo) / paint.height, 772 / paint.width)
    if scale < 1:
        paint = paint.resize((round(paint.width*scale), round(paint.height*scale)), Image.Resampling.LANCZOS)
    x = max(110, min(890-paint.width, round(center[0]-paint.width/2)))
    y = max(lo, min(hi-paint.height, round(center[1]-paint.height/2)))
    lid.alpha_composite(paint, (x, y))


def paint_finish(overlay, index, regions, glyphs):
    rng = random.Random(35600 + index * 31)
    for region in ("lid", "back", "right", "left", "top", "bottom"):
        x, y, width, height = regions[region]
        layer = contact_wear(region, (width, height), rng)
        if region in ("right", "left") or (region == "top" and index != 10):
            size = 118 if region != "top" else 103
            pos = (452, 793) if region != "top" else (803, 458)
            cross = cross_mask(411+index, size, size, True)
            stamp(layer, worn_paint(cross, "red" if index == 10 else "black", rng, .15, 1.04),
                  pos, rng.uniform(-10, 9))
        overlay.alpha_composite(layer, (x, y))
    lid_x, lid_y, width, height = regions["lid"]
    lid = Image.new("RGBA", (width, height))

    if 0 < index < 10:
        layout = DESIGNS[index-1]
        lid.alpha_composite(make_adhesive_visible(residue(lid.size, layout[6], layout[7], rng)))
    if index in SHORT_RESIDUE:
        short = tape_residue(lid.size, [(*SHORT_RESIDUE[index], .81)], 35690+index)
        lid.alpha_composite(make_adhesive_visible(short))
    if index in LONG_RESIDUE:
        center, length, depth, angle, opacity = LONG_RESIDUE[index]
        band = tape_residue(lid.size, [(center, length, depth, angle, .81)], 35690+index)
        lid.alpha_composite(make_adhesive_visible(band, opacity))

    if index in PREVIOUS_PAINT:
        text, pos, height, angle, opacity = PREVIOUS_PAINT[index]
        stencil_in_valley(lid, (text,), pos, height, angle, "black", rng, glyphs, .22, opacity)
    if index in GHOST_STENCILS:
        text, pos, height, angle, color = GHOST_STENCILS[index]
        if index == 2:
            pos = (575, 1148)
        stencil_in_valley(lid, (text,), pos, height, angle, color, rng, glyphs, .32, .32)
    if index == 2:
        stencil_in_valley(lid, ("F8105",), (460, 430), 103, 3, "white", rng, glyphs, .25, .90)
    elif index in (0, 11):
        stencil_in_valley(lid, ("MED CHEST",), (500, 780), 122, -3, "yellow", rng, glyphs,
                          .33 if index == 0 else .84, 1.15)
    else:
        lines, color, center, height, angle, *_ = DESIGNS[index-1]
        center = STENCIL_MOVED.get(index, center)            # out from under the inventory sheet
        for row, line in enumerate(lines):
            pos = (center[0], center[1]+row*350)
            stencil_in_valley(lid, (line,), pos, height, angle, color, rng, glyphs,
                              (.18, .43, .78, .29)[index % 4], 1.10)
        if index == 9:
            cross = cross_mask(334, 280, 296, True)
            stamp(lid, worn_paint(cross, "black", rng, .27, 1.14), (527, 788), -7)
    overlay.alpha_composite(lid, (lid_x, lid_y))
