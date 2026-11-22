#!/usr/bin/env python3
"""Laminated inventory sheets on the lids of the Hardigg chests: DA Form 3234, filled in by hand.

Each chest that has one lists what fn_medicalChestStock.sqf really puts in it (12 of a consumable and 4 of a
device in a specialty chest; 24, 8 and 4 in the full stock chest). Only the top panel of the folded sheet
shows, six or seven lines; the rest of the list is on the pages folded under it. Every sheet is in another
hand, folded a little differently, and taped down another way. All of them sit in the same place: the lower
third of the lid, between the third and fourth rib.

sheet(index) returns the picture (RGBA), normal map, specular map, size in lid pixels and the fold of the mesh.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS = Path(__file__).with_name("assets")
FORM = ASSETS / "da_form_3234.png"                           # 1700 x 2200, a letter page
SCALE = 3                                                    # texels for each lid design pixel
SIZE = (410, 207)                                            # the laminated sheet on the lid, in lid pixels
PAPER = 382 * SCALE                                          # width of the page in texels: a letter page at 0.93
ROWS = (394, 66.7)                                           # first line of the list on the form, and its pitch
BLACK, SILVER = (47, 49, 46), (118, 119, 104)

# finish: where (centre on the lid face, turn), hand, what the header says, the lines that show, how it was
# folded (line of the fold on the form, its slant, a second crease along the page or None, how far the page
# under it sticks out, turn of the page in the laminate, a dog ear: size, right + or left -) and the tape that holds it
SHEETS = {
    2: dict(place=((520, 1136), 1.0), font=("QEPhilipBean", 1.0), ink=(38, 46, 88),
            org="MED PLT HHC - CHEST 02 GEN RESUPPLY", month="MAR", year="2035", pages=("1", "4"),
            rows=(("TOURNIQUET, CAT", "EA", "24"), ("GAUZE, COMBAT HEMOSTATIC", "EA", "24"),
                  ("DRESSING, EMERG TRAUMA 6IN", "EA", "24"), ("CHEST SEAL, VENTED", "EA", "24"),
                  ("IV START KIT 18G", "EA", "24"), ("NPA 28FR W/LUBE", "EA", "8"), ("SALINE 0.9% 500ML", "BG", "8")),
            fold=(868, 0.5, None, 5, 0.6, 0), tape=("frame", SILVER)),
    3: dict(place=((470, 1132), -1.5), font=("QEDSFont", 0.86), ink=(26, 26, 30),
            org="FST - CHEST 03 SURG / OR", month="JAN", year="2035", pages=("1", "5"),
            rows=(("THORACOSTOMY KIT", "EA", "12"), ("CHEST TUBE KIT 28FR", "EA", "12"), ("NCD KIT 14ga 3.25in", "EA", "12"),
                  ("KETAMINE 500mg VIAL", "VL", "12"), ("PROPOFOL 1% 50ML", "VL", "12"), ("ROCURONIUM 50mg VIAL", "VL", "12"),
                  ("TXA 1 gram VIAL", "VL", "12")),
            fold=(842, -0.9, 0.52, 9, -1.1, 0), tape=("top_bottom", BLACK)),
    5: dict(place=((395, 1130), 0.8), font=("QESamRoberts", 0.80), ink=(30, 34, 60),
            org="MED PLT - CHEST 05 DRESSINGS", month="FEB", year="2035", pages=("1", "2"),
            rows=(("GAUZE, COMBAT", "EA", "12"), ("DRESSING, EMERG TRAUMA", "EA", "12"), ("BANDAGE, PRESSURE", "EA", "12"),
                  ("WRAP, ELASTIC 6IN", "EA", "12"), ("CHEST SEAL, VENTED", "EA", "12"), ("SPLINT, SAM 36IN", "EA", "12"),
                  ("HPMK HYPOTHERMIA KIT", "EA", "4")),
            fold=(872, 1.2, 0.34, 3, 1.3, 20), tape=("corners", SILVER)),
    6: dict(place=((560, 1134), -0.6), font=("QEPhillips", 1.30), ink=(34, 42, 96),
            org="MED PLT - CHEST 06 IV FLUIDS", month="MAR", year="2035", pages=("1", "3"),
            rows=(("PLASMA-LYTE A 500ML", "BG", "12"), ("PLASMA-LYTE A 250ML", "BG", "12"), ("SALINE 0.9% 100ML", "BG", "12"),
                  ("IV START KIT 18G", "EA", "12"), ("IV ADMIN SET", "EA", "12"), ("SALINE LOCK", "EA", "12"),
                  ("PRESSURE INFUSER", "EA", "4")),
            fold=(818, 0.2, 0.66, 12, 0.3, 0), tape=("top_tabs", SILVER), moved={1: (360, 1436)}),
    7: dict(place=((500, 1134), 1.4), font=("QEPhilipBean", 0.98), ink=(24, 24, 28),
            org="MED PLT - CHEST 07 AIRWAY", month="FEB", year="2035", pages=("1", "3"),
            rows=(("NPA 28FR W/LUBE", "EA", "12"), ("OPA, ASSORTED", "EA", "12"), ("I-GEL SGA SZ 4", "EA", "12"),
                  ("ET TUBE 7.5 CUFFED", "EA", "12"), ("CRIC KIT", "EA", "12"), ("LARYNGOSCOPE", "EA", "4"),
                  ("BVM, ADULT", "EA", "4")),
            fold=(858, -0.4, None, 7, -0.8, -15), tape=("frame", BLACK)),
    8: dict(place=((540, 1132), -1.0), font=("QEDSFont", 0.84), ink=(120, 28, 30),
            org="FST - CHEST 08 BLOOD / KEEP COLD", month="MAR", year="2035", pages=("1", "2"),
            rows=(("BLOOD, WHOLE O 500ML", "UN", "12"), ("BLOOD, WHOLE O 250ML", "UN", "12"), ("TRANSFUSION KIT, FIELD", "EA", "12"),
                  ("IV START KIT 16ga", "EA", "12"), ("BLOOD COOLER 4 UNIT", "EA", "4"), ("BLOOD WARMER", "EA", "4"),
                  ("PRESSURE INFUSER", "EA", "4")),
            fold=(830, 0.8, 0.45, 6, 0.9, 0), tape=("sides_bottom", SILVER), moved={0: (575, 1436)}),
}
SHEETS[5]["moved"] = {0: (640, 1436)}
# Markings that would lie under a sheet go up one valley of the lid: finish, new centre of the first line.
STENCIL_MOVED = {6: (641, 449), 7: (514, 430)}


def strips(index):
    """Tape that holds the sheet: (offset from its centre, length, width, turn, damage, colour), in lid pixels."""
    style, colour = SHEETS[index]["tape"]
    w, h = SIZE
    top, bottom = ((0, -h / 2 + 4), w + 26, 23, 0), ((0, h / 2 - 4), w + 26, 23, 0)
    left, right = ((-w / 2 + 4, 0), h - 28, 26, 90), ((w / 2 - 4, 0), h - 28, 26, -90)
    layout = {"frame": (top + ("fold",), bottom + ("split",), left + ("lift",), right + ("fold",)),
              "top_bottom": (((6, -h / 2 + 6), w + 60, 26, 1.5, "lift"), ((-8, h / 2 - 5), w + 40, 26, -1.0, "fold")),
              "corners": tuple(((sx * (w / 2 - 14), sy * (h / 2 - 12)), 118, 30, 40 * sx * sy + 4 * sx, damage)
                               for sx, sy, damage in ((-1, -1, "fold"), (1, -1, "lift"), (-1, 1, "split"), (1, 1, "fold"))),
              "top_tabs": (((0, -h / 2 + 5), w + 34, 28, -0.8, "fold"), ((-w / 2 + 6, 34), 96, 26, 86, "lift"),
                           ((w / 2 - 6, 30), 88, 26, -93, "fold")),
              "sides_bottom": (((-w / 2 + 5, -4), h + 22, 27, 91, "fold"), ((w / 2 - 5, 3), h + 14, 27, -88, "lift"),
                               ((4, h / 2 - 5), w - 40, 24, 0.7, "split"))}[style]
    return [(*strip, colour) for strip in layout]


def _noise(rng, shape, cell):
    small = rng.random((max(2, shape[0] // cell + 2), max(2, shape[1] // cell + 2))).astype(np.float32)
    image = Image.fromarray((small * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.Resampling.BICUBIC)
    return np.asarray(image, np.float32) / 255.0


def _write(layer, rng, text, font, where, ink, anchor="lm", turn=1.2):
    """One entry in the hand of the sheet: never quite on the line, never quite level, the pen running dry."""
    box = font.getbbox(text, anchor="ls")
    pad = 24
    word = Image.new("L", (box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad), 0)
    ImageDraw.Draw(word).text((pad - box[0], pad - box[1]), text, font=font, fill=255, anchor="ls")
    word = word.rotate(rng.normal(0, turn), resample=Image.Resampling.BICUBIC, expand=True)
    press = np.clip(0.72 + 0.5 * _noise(rng, (word.height, word.width), 26), 0, 1)
    word = Image.fromarray((np.asarray(word, np.float32) * press).astype(np.uint8))
    x, y = where
    x = x - word.width / 2 if anchor == "mm" else x - pad
    y = y - word.height / 2 + rng.normal(0, 3.0)
    layer.paste(Image.new("RGB", word.size, ink), (int(x + rng.normal(0, 4)), int(y)), word)


def page(index):
    """The form of one chest, filled in. A greyscale-like RGB image the size of the form."""
    spec = SHEETS[index]
    rng = np.random.default_rng(8800 + index)
    with Image.open(FORM) as form:
        sheet = Image.merge("RGB", [form.convert("L")] * 3)
    name, size = spec["font"]
    font = lambda points: ImageFont.truetype(str(ASSETS / "fonts" / (name + ".ttf")), round(points * size))
    ink = spec["ink"]
    _write(sheet, rng, spec["org"], font(46), (112, 250), ink)
    _write(sheet, rng, spec["month"], font(50), (1276, 252), ink, "mm")
    _write(sheet, rng, spec["year"], font(50), (1497, 252), ink, "mm")
    _write(sheet, rng, spec["pages"][0], font(46), (1325, 138), ink, "mm")
    _write(sheet, rng, spec["pages"][1], font(46), (1487, 138), ink, "mm")
    for row, (item, unit, count) in enumerate(spec["rows"]):
        y = ROWS[0] + ROWS[1] * (row + 0.56)
        _write(sheet, rng, item, font(48), (110, y), ink)
        _write(sheet, rng, unit, font(46), (869, y), ink, "mm")
        _write(sheet, rng, count, font(52), (1269, y), ink, "mm")
    return sheet


def sheet(index):
    """The laminated, folded sheet of one chest: dict(image RGBA, normal RGB, smdi RGB, size, fold)."""
    from build_hardigg_surface import blur, normal_map
    spec = SHEETS[index]
    rng = np.random.default_rng(9900 + index)
    line, slant, crease, peek, turn, ear = spec["fold"]
    w, h = SIZE[0] * SCALE, SIZE[1] * SCALE
    shape = (h, w)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # ---- the panel that shows: the top of the page down to the fold, never folded quite square
    full = page(index)
    factor = PAPER / full.width
    top = 34
    panel = full.crop((0, top, full.width, line + 40)).resize((PAPER, round((line + 40 - top) * factor)), Image.Resampling.LANCZOS)
    grey = np.asarray(panel.convert("L"), np.float32) / 255.0
    paper = np.array([228.0, 224, 205]) * (0.90 + 0.10 * _noise(rng, grey.shape, 80))[..., None]
    inked = np.asarray(panel, np.float32)
    written = (inked.max(-1) - inked.min(-1)) > 18                                      # coloured ink, not print
    colour = paper * grey[..., None] + np.array([44.0, 46, 44]) * (1 - grey[..., None]) * 0.6
    colour = np.where(written[..., None], inked * 0.92 + paper * 0.08 * grey[..., None], colour)
    ph, pw = grey.shape
    py, px = np.mgrid[0:ph, 0:pw].astype(np.float32)
    fold_y = (line - top) * factor + (px - pw / 2) * math.tan(math.radians(slant))       # the fold, on the panel
    relief = np.zeros((ph, pw), np.float32)                                             # millimetres
    relief += 0.5 * np.exp(-((py - fold_y) / 5.0) ** 2)                                 # the roll of the fold itself
    if crease is not None:                                                               # folded along the page before
        d = px - (crease * pw + 5 * np.sin(py / 120))
        relief += 0.22 * np.exp(-(d / 2.2) ** 2) - 0.10 * np.exp(-((d - 6) / 6.0) ** 2)
        colour *= (1 - 0.10 * np.exp(-((d - 5) / 7.0) ** 2) + 0.05 * np.exp(-(d / 2.0) ** 2))[..., None]
    crumple = _noise(rng, (ph, pw), 44) - 0.5
    relief += 0.10 * crumple
    colour *= (1 + 0.05 * crumple)[..., None]
    stain = np.clip(_noise(rng, (ph, pw), 150) * 2.2 - 1.45, 0, 1)                       # damp got in at one time
    colour += (np.array([170.0, 150, 110]) - colour) * (stain * 0.30)[..., None]
    mask = (py < fold_y).astype(np.float32)
    if ear:                                                                              # a corner turned over
        across = (pw - px) if ear > 0 else px               # which top corner, and how far it is turned
        cut = across + py * 1.1 < abs(ear) * SCALE
        back = (across + py * 1.1 < 2 * abs(ear) * SCALE) & ~cut
        mask *= 1 - cut
        colour = np.where(back[..., None], paper * 0.93, colour)
        relief += 0.25 * back
    # the pages folded under stick out below the fold, a little askew
    under = ((py >= fold_y) & (py < fold_y + peek * SCALE + (px - pw / 2) * 0.012)).astype(np.float32)
    colour = np.where(under[..., None] > 0, paper * (0.86 + 0.06 * np.sin(py / 2.0))[..., None], colour)
    relief -= 0.18 * under
    shade = np.clip(1 - np.abs(py - fold_y) / 9.0, 0, 1)
    colour *= (1 - 0.16 * shade * (py > fold_y - 2))[..., None]
    mask = np.maximum(mask, under)

    # ---- into the laminate: the page lies a little crooked in it
    def placed(array, fill=0):
        image = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
        canvas = Image.new(image.mode, (w, h), fill)
        canvas.paste(image, ((w - pw) // 2, 10 * SCALE))
        return canvas.rotate(turn, resample=Image.Resampling.BICUBIC, center=(w / 2, h / 2))

    on = np.asarray(placed(mask * 255), np.float32) / 255.0
    sheet_rgb = np.asarray(placed(colour), np.float32)
    bump = np.asarray(placed((relief + 0.4) * 255), np.float32) / 255.0 - 0.4 * on
    film = Image.new("L", (w, h), 0)
    ImageDraw.Draw(film).rounded_rectangle((3, 3, w - 4, h - 4), radius=7 * SCALE, fill=255)
    film = np.asarray(film, np.float32) / 255.0
    haze = _noise(rng, shape, 120)
    scratch = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(scratch)
    for _ in range(70):
        x, y, a, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, math.pi), float(np.exp(rng.normal(3.3, 0.8)))
        draw.line([(x - math.cos(a) * r, y - math.sin(a) * r), (x + math.cos(a) * r, y + math.sin(a) * r)],
                  fill=int(rng.uniform(40, 150)), width=1)
    scratch = np.asarray(scratch, np.float32) / 255.0
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    seal = np.exp(-((edge - 5 * SCALE) / 2.5) ** 2)                                      # the heat seal round the film
    # The film round the paper is drawn, not see-through: a half transparent face shimmers in the game. It is
    # the colour of the case seen through milky plastic.
    clear = (np.array([77.0, 83, 59]) * 0.62 + np.array([196.0, 201, 190]) * 0.38) * (0.94 + 0.08 * haze)[..., None]
    rgb = np.where(on[..., None] > 0.5, sheet_rgb * (0.955 + 0.03 * haze)[..., None] + 6, clear)
    rgb += (np.array([240.0, 242, 236]) - rgb) * np.clip(0.10 * scratch + 0.16 * seal, 0, 1)[..., None]
    rgb += (np.array([96.0, 90, 74]) - rgb) * (np.exp(-edge / (2.0 * SCALE)) * 0.35)[..., None]      # dirt under the edge
    alpha = film
    height = (0.00016 * on + 0.001 * bump * 0.22 + 0.00006 * (haze - 0.5) + 0.00004 * seal).astype(np.float32)
    height = blur(height, 3.0)
    normal = normal_map(height / (0.000526 / SCALE) / 2)
    # An even, soft sheen. Scratches and haze in the specular map sparkle as the eye moves, so they stay out.
    spec_map = 0.30 * film + 0.05 * (1 - film)
    gloss = np.full(shape, 0.58, np.float32)
    smdi = np.stack([np.ones(shape), spec_map, gloss], -1) * 255
    image = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")
    return dict(image=image, normal=Image.fromarray(np.clip(normal, 0, 255).astype(np.uint8), "RGB"),
                smdi=Image.fromarray(smdi.astype(np.uint8), "RGB"), size=SIZE,
                fold=((10 * SCALE + (line - top) * factor) / h, 0.04 * slant, 0.0006))
