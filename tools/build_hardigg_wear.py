"""Author the Hardigg lid markings and the material art for modeled tape."""
from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from build_medical_chest_stencils import noise, tape_residue
from build_medical_chest_variants import (
    DESIGNS, WHITE_TAPE, aerosol, contact_wear, paint_marker, residue, stamp,
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


def tape_material(length, width, rng, color, label):
    """The fabric coloring. The outline, folds and tears are built into the mesh."""
    size = length, width
    yy, xx = np.indices((width, length))
    cloth = (np.asarray(noise(size, 12, rng), dtype=np.float32) - 128) * .16
    cloth += (np.asarray(noise(size, 2, rng), dtype=np.float32) - 128) * .09
    cloth += (xx % 5 == 1) * 3.8 + (yy % 4 == 0) * 2.4
    dirty_edges = np.exp(-np.minimum(yy, width - 1 - yy) / 5) * 12
    rgb = np.clip(np.asarray(color) + (cloth - dirty_edges)[:, :, None], 0, 255)
    tape = Image.fromarray(rgb.astype(np.uint8)).convert("RGBA")
    if label:
        stamp(tape, paint_marker(label, round(width * .48), (59, 55, 48), rng),
              (length * .47, width * .52), 2)
    return tape


def inventory_card():
    """A printed field inventory folded into a sleeve."""
    width, height = 490, 415
    sheet = Image.new("RGBA", (width + 76, height + 70))
    # The visible half shows the actual supplied form header and its first few inventory rows.
    with Image.open(FORM) as ref:
        x, y = ref.size
        form = ImageOps.grayscale(ref.crop((round(.049*x), round(.039*y), round(.951*x), round(.432*y))))
    form = form.resize((width-30, height-32), Image.Resampling.LANCZOS)
    print_colors = ImageOps.colorize(form, (38, 43, 37), (212, 211, 188)).convert("RGBA")

    draw = ImageDraw.Draw(sheet)
    draw.rounded_rectangle((27,25,27+width+12,25+height+10), radius=8, fill=(178,183,164,248),
                           outline=(231,232,212,240), width=3)
    draw.polygon([(42,46),(width+25,42),(width+28,height+25),(47,height+28)], fill=(202,198,175,255))
    draw.line((52,height+20,width+19,height+15), fill=(103,102,80,190), width=3)
    sheet.alpha_composite(print_colors, (43, 38))
    draw = ImageDraw.Draw(sheet)
    pen = ImageFont.truetype("C:/Windows/Fonts/segoepr.ttf", 17)
    for position, note in (((52, 100), "MED 02 / AID DET"), ((59, 192), "GAUZE"),
                           ((61, 218), "IV SETS"), ((59, 244), "NPA"),
                           ((401, 191), "18"), ((402, 218), "12"), ((401, 243), "8")):
        draw.text(position, note, font=pen, fill=(53, 66, 77, 239))

    gloss = Image.new("RGBA", sheet.size)
    light = ImageDraw.Draw(gloss)
    light.polygon([(58,41),(109,39),(273,height+19),(250,height+18)], fill=(245,251,238,32))
    light.line([(44,252),(219,253),(324,249),(width+17,247)], fill=(250,248,231,99), width=2)
    light.line([(44,254),(219,255),(324,251),(width+17,249)], fill=(67,62,47,65), width=3)
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


def paint_underneath(lid, index):
    text, position, height, angle, opacity = PREVIOUS_PAINT[index]
    rng = random.Random(35913 + index)
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", height)
    left, top, right, bottom = font.getbbox(text)
    mask = Image.new("L", (right - left + 4, bottom - top + 4))
    draw = ImageDraw.Draw(mask)
    draw.text((2-left, 2-top), text, font=font, fill=255)
    # Small bridges and patchy erasure leave remnants of the previous field stencil.
    for y in (int(mask.height*.31), int(mask.height*.69)):
        draw.line((0, y, mask.width, y+rng.randint(-3, 2)), fill=0, width=max(2, height//19))
    paint = aerosol(mask, "black", rng, False, .95)
    cloud = np.asarray(noise(paint.size, 32, rng), dtype=np.float32)/255
    alpha = np.asarray(paint.getchannel("A"), dtype=np.float32)
    alpha *= opacity * (.29 + .71*cloud)
    paint.putalpha(Image.fromarray(alpha.astype(np.uint8)))
    coat = Image.new("RGBA", lid.size)
    stamp(coat, paint, position, angle)
    coat.alpha_composite(lid)
    return coat


def paint_finish(overlay, index, lid_region):
    rng = random.Random(35600 + index * 31)
    lid_x, lid_y, width, height = lid_region
    lid_bounds = (lid_x, lid_y, lid_x+width, lid_y+height)
    lid = overlay.crop(lid_bounds)
    tapes = original_tape(index)
    if tapes:
        # Recover the existing wear under the old tape footprint before replacing it.
        restore = contact_wear("lid", lid.size, random.Random(32840 + index*173))
        mask = Image.new("RGBA", lid.size)
        for pos, length, depth, angle, _, _ in tapes:
            stamp(mask, Image.new("RGBA",(length+25,depth+24),(255,255,255,255)), pos, angle)
        lid.paste(restore, mask=mask.getchannel("A"))

    if index in PREVIOUS_PAINT:
        lid = paint_underneath(lid, index)

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

    overlay.paste(lid, lid_bounds[:2])
