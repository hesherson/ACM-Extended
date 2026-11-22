#!/usr/bin/env python3
"""Duct tape for the lid of the Hardigg chest, three texels for each lid pixel (0.18 mm per texel).

Cloth tape with a glossy polyethylene face: black, silver, or white cloth tape that takes a marker. A strip
that was pressed on by hand is never flat. It puckers: a few sharp ridges fan out from where it was pinched,
wander, fork and die away, and the scrim under the coating shows as rows of small bumps. Both ends are torn
by hand. A tip that is ripped down the middle has a tear there, a narrow gap along the weave with threads in it.

tape_image() makes one strip from a height field: colour with alpha, normal map, specular map, and a coarse
relief that build_hardigg_lid_artwork.py lifts the mesh by, so the big wrinkles are really there.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SCALE = 3                                                    # texels for each lid design pixel
TEXEL = 0.000526 / SCALE                                     # metres
MM = 0.001 / TEXEL                                           # texels in a millimetre
MARGIN = 14                                                  # texels at each end left for the torn edge
WARP, WEFT = 6, 12                                           # texels between threads along and across the strip
KINDS = {  # face colour, crest and hollow tint, specular, gloss, how strongly the scrim shows
    # The face is polyethylene: a soft, wide sheen, never the glint of metal. Silver tape is grey plastic.
    "black": dict(base=(21, 21, 22), light=(74, 74, 76), dark=(8, 8, 9), spec=0.30, gloss=0.50, scrim=1.0),
    "silver": dict(base=(138, 141, 143), light=(186, 189, 191), dark=(84, 87, 90), spec=0.34, gloss=0.44, scrim=1.3),
    "white": dict(base=(203, 198, 177), light=(236, 233, 220), dark=(126, 121, 104), spec=0.20, gloss=0.30, scrim=0.6),
}
SLEEVE = (255, 80, 150)                                      # specular map of the card in its plastic sleeve


def kind_of(color):
    level = sum(color) / 3
    return "black" if level < 80 else "silver" if level < 170 else "white"


def _noise(rng, shape, cell):
    """Smooth noise 0..1 with features of about `cell` texels."""
    small = rng.random((max(2, shape[0] // cell + 2), max(2, shape[1] // cell + 2))).astype(np.float32)
    image = Image.fromarray((small * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.Resampling.BICUBIC)
    return np.asarray(image, np.float32) / 255.0


def _blurred(image, radius):
    layer = np.asarray(image.filter(ImageFilter.GaussianBlur(radius)), np.float32)
    return layer / max(float(layer.max()), 1e-6)


def _ridge(draw, rng, start, heading, reach, strength, fork=True):
    """One ridge of a pucker: it wanders, is highest in its middle and dies away at both ends."""
    x, y = start
    steps = max(4, int(reach / 4))
    bend = rng.normal(0, 0.012)
    for k in range(steps):
        t = (k + 0.5) / steps
        heading += bend + rng.normal(0, 0.07)
        nx, ny = x + 4 * math.cos(heading), y + 4 * math.sin(heading)
        level = strength * math.sin(math.pi * min(1, t * 1.15)) ** 0.7
        draw.line([(x, y), (nx, ny)], fill=int(255 * max(0, min(1, level))), width=2)
        if fork and 0.25 < t < 0.7 and rng.random() < 1.6 / steps:
            turn = rng.choice((-1, 1)) * rng.uniform(0.45, 0.95)
            _ridge(draw, rng, (nx, ny), heading + turn, reach * rng.uniform(0.3, 0.55), strength * 0.75, False)
        x, y = nx, ny


def wrinkles(rng, w, h, length, amount=1.0):
    """Height of the puckers of one strip, 0..1 on the highest crest, and its crests alone.
    amount: 1 a strip that went on badly, 0 one that was laid down flat and rubbed smooth."""
    crest = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(crest)
    for _ in range(int(round((max(1, round(length / 95)) + (rng.random() < 0.6)) * amount))):
        pinch = (rng.uniform(0.10, 0.90) * w, rng.uniform(0.15, 0.85) * h)
        base = rng.choice((0, math.pi)) + rng.choice((-1, 1)) * (rng.uniform(0.35, 1.15) if rng.random() < 0.7
                                                               else rng.uniform(0.0, 0.3))
        for _ in range(int(rng.integers(3, 6))):
            start = (pinch[0] + rng.normal(0, 3 * MM), pinch[1] + rng.normal(0, 2.5 * MM))
            reach = float(np.exp(rng.normal(math.log(24 * MM), 0.45)))
            _ridge(draw, rng, start, base + rng.normal(0, 0.28), reach, rng.uniform(0.55, 1.0))
        if rng.random() < 0.6:                               # and the long one that runs out of it along the strip
            _ridge(draw, rng, pinch, rng.choice((0, math.pi)) + rng.normal(0, 0.22), rng.uniform(30, 60) * MM, 0.7)
    for _ in range(int(round(rng.integers(0, 3) * amount))):  # a kink straight across, where it was bent back once
        x = rng.uniform(0.08, 0.92) * w
        lean = rng.uniform(-0.12, 0.12) * h
        draw.line([(x - lean, 0), (x + rng.normal(0, 2), h / 2), (x + lean, h)], fill=int(rng.uniform(90, 170)), width=2)
    for _ in range(int(round((4 + length / 40) * (0.15 + 0.85 * amount)))):    # small dents and short creases
        start = (rng.uniform(0, w), rng.uniform(0, h))
        _ridge(draw, rng, start, rng.uniform(0, 2 * math.pi), rng.uniform(3, 9) * MM, rng.uniform(0.15, 0.38), False)
    sharp = _blurred(crest, 1.4)
    height = 0.20 * sharp + 0.50 * _blurred(crest, 5.0) + 0.30 * _blurred(crest, 11)
    return height.astype(np.float32), sharp


def tape_image(length, width, rng, color, label="", glyphs=None, damage=""):
    """One strip, SCALE times its size in lid pixels: dict(image RGBA, normal RGB, smdi RGB, relief in metres).
    rng: random.Random of the caller; one number is drawn from it."""
    from build_hardigg_surface import normal_map
    rng = np.random.default_rng(rng.randrange(2 ** 31))
    kind = KINDS[kind_of(color)]
    w, h = length * SCALE, width * SCALE
    shape = (h, w)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base, light, dark = (np.array(kind[name], np.float32) for name in ("base", "light", "dark"))
    if kind_of(color) == "white":
        base = np.array(color, np.float32)

    # ---- the height field: puckers, a slow waviness, and the scrim under the coating
    # Four strips in ten lie flat with next to no creases, three have a few, the rest went on badly.
    calm = rng.random()
    amount = 0.0 if calm < 0.40 else 0.45 if calm < 0.70 else 1.0
    pucker, crest = wrinkles(rng, w, h, length, amount)
    wavy = _noise(rng, shape, 70) - 0.5
    drift = 3.0 * (_noise(rng, shape, 140) - 0.5)
    warp = np.clip(np.cos(2 * math.pi * (yy + drift) / WARP), 0, 1) ** 2
    weft = np.clip(np.cos(2 * math.pi * (xx + drift) / WEFT), 0, 1) ** 6
    scrim = (0.45 * warp + 0.9 * weft * (0.35 + 0.65 * warp)) * kind["scrim"]
    height = 0.0026 * pucker + 0.00030 * wavy + 0.000035 * scrim
    normal = normal_map(height / TEXEL / 2)

    # ---- colour: mostly the face colour. Light and shade come from the normal map; a little is painted in,
    # so that the strip still reads as creased in flat light and far away.
    tone = 1 + 0.08 * (_noise(rng, shape, 90) - 0.5) + 0.05 * (_noise(rng, shape, 12) - 0.5)
    rgb = base[None, None, :] * tone[..., None]
    hollow = np.clip(np.asarray(Image.fromarray((pucker * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)),
                                np.float32) / 255.0 - pucker, 0, 1)
    slope_x = np.gradient(height, axis=1) / TEXEL
    slope_y = np.gradient(height, axis=0) / TEXEL
    lit = np.clip(-(0.55 * slope_x + 0.83 * slope_y), -1.2, 1.2)                      # light from the top left
    rgb += (light - rgb) * np.clip(0.30 * crest + 0.14 * np.clip(lit, 0, 1), 0, 1)[..., None]
    rgb += (dark - rgb) * np.clip(1.0 * hollow + 0.18 * np.clip(-lit, 0, 1), 0, 0.7)[..., None]
    rgb += (light - rgb) * (0.10 * kind["scrim"] * weft * (0.4 + 0.6 * warp))[..., None]    # the tops of the threads
    rgb *= (1 - 0.05 * kind["scrim"] * (1 - warp))[..., None]
    edge = np.minimum(yy, h - 1 - yy)
    rgb += (np.array([104.0, 98, 84]) - rgb) * (np.exp(-edge / (1.2 * MM)) * 0.30)[..., None]    # dirt on the sticky edge
    dusty = np.clip(_noise(rng, shape, 46) * 1.7 - 0.95, 0, 1)
    rgb += (np.array([150.0, 142, 122]) - rgb) * (dusty * 0.22)[..., None]
    specks = (rng.random(shape) > 0.99965).astype(np.float32)                           # grit stuck in the face
    specks = np.asarray(Image.fromarray((specks * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 90
    rgb += (np.array([190.0, 185, 170]) - rgb) * np.clip(specks, 0, 0.6)[..., None]
    spec = kind["spec"] * (1 - 0.5 * dusty) * (1 - 0.35 * np.clip(specks, 0, 1))
    gloss = kind["gloss"] * (1 - 0.45 * dusty) * (1 - 0.10 * scrim / max(kind["scrim"], 1e-6))

    # ---- ink on a labelled strip
    if label and glyphs:
        from build_medical_chest_variants import label_mask, stamp
        import random
        mask = label_mask((label,), round(width * .45), 6, random.Random(int(rng.integers(2 ** 31))), glyphs)
        mask = mask.resize((mask.width * SCALE, mask.height * SCALE), Image.Resampling.LANCZOS)
        ink = Image.new("RGBA", mask.size, (59, 55, 48, 0))
        worn = np.asarray(mask, np.float32) * np.clip(0.55 + 0.6 * _noise(rng, (mask.height, mask.width), 9), 0, 1)
        ink.putalpha(Image.fromarray(worn.astype(np.uint8)))
        layer = Image.new("RGBA", (w, h))
        stamp(layer, ink, (w * .47, h * .52), 2)
        layer = np.asarray(layer, np.float32)
        rgb += (layer[..., :3] - rgb) * (layer[..., 3:] / 255.0 * 0.92)

    # ---- outline: long edges almost straight, both ends torn by hand
    fibre = np.array([196.0, 192, 178]) if kind_of(color) != "white" else np.array([236.0, 233, 220])
    alpha = np.ones(shape, np.float32)
    rows = np.arange(h)
    waver = np.cumsum(rng.normal(0, 0.10, w))
    waver -= np.linspace(waver[0], waver[-1], w)
    alpha *= np.clip(yy - (1.2 + waver[None, :]) + 0.5, 0, 1) * np.clip((h - 2.2 + waver[None, :]) - yy + 0.5, 0, 1)
    threads = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(threads)
    for end in (0, 1):
        # a tear across cloth tape runs along one thread, then jumps to the next; now and then it takes a bite
        block = int(rng.integers(7, 15))
        steps = np.repeat(rng.normal(0, 1.8, h // block + 2), block)[:h] + rng.normal(0, 0.6, h)
        bite = np.clip(_noise(rng, (h, 2), 16)[:, 0] * 2.4 - 1.5, 0, 1) * rng.uniform(1.5, 4.5) * MM
        slant = (rows - h / 2) * rng.uniform(-0.09, 0.09)
        inset = MARGIN + steps + slant + bite if end == 0 else w - MARGIN + steps + slant - bite
        gate = xx - inset[:, None] if end == 0 else inset[:, None] - xx
        alpha *= np.clip(gate + 0.5, 0, 1)
        for y in range(int(rng.integers(2, 9)), h - 2, int(rng.integers(7, 19))):      # a few threads left hanging
            reach = float(np.exp(rng.normal(math.log(4.0), 0.7)))
            sag = rng.normal(0, 0.5) * reach
            x0 = float(inset[y])
            x1 = x0 - reach if end == 0 else x0 + reach
            draw.line([(x0 + (2 if end == 0 else -2), y), ((x0 + x1) / 2, y + sag * 0.3), (x1, y + sag)],
                      fill=int(rng.uniform(110, 230)), width=1)

    # ---- a tip ripped down the middle: a narrow gap along the weave, frayed, with threads across it
    if damage == "split":
        tip = w * rng.uniform(0.32, 0.42)
        columns = np.arange(w, dtype=np.float32)
        run = int(9 * MM)
        jumps = np.repeat(np.cumsum(rng.choice((-1.0, 0.0, 0.0, 0.0, 1.0), w // run + 2) * WARP * 0.5), run)[:w]
        path = h * rng.uniform(0.44, 0.56) + jumps + rng.normal(0, 0.25, w)
        gape = np.clip(1 - (columns - MARGIN) / (tip - MARGIN), 0, 1) ** 0.75 * (0.62 * MM)
        half = np.clip(gape * (1 + 0.35 * rng.normal(0, 1, w)), 0, None)
        gap = np.clip(half[None, :] - np.abs(yy - path[None, :]) + 0.5, 0, 1) * (columns[None, :] < tip)
        alpha *= 1 - gap
        fray = np.clip(1 - (np.abs(yy - path[None, :]) - half[None, :]) / (0.45 * MM), 0, 1) * (columns[None, :] < tip + 4 * MM)
        rgb += (fibre - rgb) * (fray * 0.5)[..., None]                                 # the scrim is bare along a tear
        spec, gloss = spec * (1 - 0.7 * fray), gloss * (1 - 0.7 * fray)
        for x in range(MARGIN + 2, int(tip + 3 * MM), 4):
            if rng.random() < 0.45:
                side = 1 if rng.random() < 0.5 else -1
                y0 = float(path[x]) + side * (float(half[x]) + 1.5)
                reach = float(np.exp(rng.normal(math.log(4.0), 0.55)))
                draw.line([(x, y0), (x + rng.normal(0, 1.4), y0 - side * reach * 0.5), (x + rng.normal(0, 2.4), y0 - side * reach)],
                          fill=int(rng.uniform(110, 240)), width=1)

    thread = np.asarray(threads, np.float32) / 255.0
    rgb = np.where((alpha > 0.02)[..., None], rgb, base[None, None, :])                # no fringe in the mip maps
    rgb += (fibre - rgb) * (thread * 0.85)[..., None]
    alpha = np.maximum(alpha, thread * 0.9)
    image = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")
    smdi = np.stack([np.ones(shape), np.clip(spec, 0.02, 1), np.clip(gloss, 0.03, 1)], -1) * 255
    # the mesh has a point every 5 mm: it gets the swell under each pucker, the normal map keeps the sharp crest
    broad = np.asarray(Image.fromarray((pucker * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18)), np.float32) / 255
    relief = Image.fromarray((np.clip(broad * 2.4, 0, 1) * 255).astype(np.uint8)).resize(
        (max(2, w // 8), max(2, h // 8)), Image.Resampling.BILINEAR)
    return dict(image=image, normal=Image.fromarray(np.clip(normal, 0, 255).astype(np.uint8), "RGB"),
                smdi=Image.fromarray(smdi.astype(np.uint8), "RGB"),
                relief=np.asarray(relief, np.float32) / 255.0 * 0.0021)


def lift(relief, u, v):
    """Height of the broad wrinkles (metres) at a place on the strip, both 0..1."""
    rows, columns = relief.shape
    x, y = min(max(u, 0), 1) * (columns - 1), min(max(v, 0), 1) * (rows - 1)
    x0, y0 = min(int(x), columns - 2), min(int(y), rows - 2)
    fx, fy = x - x0, y - y0
    top = relief[y0, x0] * (1 - fx) + relief[y0, x0 + 1] * fx
    low = relief[y0 + 1, x0] * (1 - fx) + relief[y0 + 1, x0 + 1] * fx
    return float(top * (1 - fy) + low * fy)


def export(pieces, index, output, work, hemtt, colour):
    """Textures and material of the lid artwork of one finish. colour: its colour atlas, an RGBA image."""
    import subprocess
    import build_hardigg_fittings as fittings
    work.mkdir(parents=True, exist_ok=True)
    normal, smdi = atlas_maps(pieces, colour.width)
    for name, image in (("ca", colour), ("nohq", normal), ("smdi", smdi)):
        png = work / f"lid_artwork_{index}_{name}.png"
        image.save(png)
        paa = output / png.with_suffix(".paa").name
        paa.unlink(missing_ok=True)
        subprocess.run([hemtt, "utils", "paa", "convert", str(png), str(paa)], check=True, stdout=subprocess.DEVNULL)
    fittings.material(output, "detail.rvmat", f"lid_artwork_{index}.rvmat",
                      {1: f"lid_artwork_{index}_nohq.paa", 5: f"lid_artwork_{index}_smdi.paa"}, 0.55, 42, (1.45, 0.3))


def atlas_maps(pieces, size):
    """Normal map and specular map of one finish, laid out as its colour atlas is."""
    normal = Image.new("RGB", (size, size), (128, 128, 255))
    smdi = Image.new("RGB", (size, size), (255, 40, 60))
    for piece in pieces:
        x, y, width, height = piece.tile
        if piece.maps:
            normal.paste(piece.maps["normal"].resize((width, height), Image.Resampling.LANCZOS), (x, y))
            smdi.paste(piece.maps["smdi"].resize((width, height), Image.Resampling.LANCZOS), (x, y))
        else:
            smdi.paste(SLEEVE, (x, y, x + width, y + height))
    return normal, smdi
