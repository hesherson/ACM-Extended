"""Map contact wear and subdued plastic sheen onto the Hardigg shell UVs."""

import math
import random

import numpy as np
from PIL import Image, ImageFilter

from build_medical_chest_stencils import noise
from build_medical_chest_variants import scrape


def wear_tile(region, size):
    """Dragged corners, rib crowns and the top shoulder pick up chalky abrasion."""
    rng = random.Random(82017 + sum(map(ord, region)))
    width, height = size
    v, u = np.ogrid[:1:height*1j, :1:width*1j]
    deposits = np.zeros((height, width), dtype=np.float32)
    scratches = Image.new("L", size)

    def contact(x, y, sx, sy, weight, count, heading):
        patch = weight * np.exp(-.5 * (((u-x)/sx)**2 + ((v-y)/sy)**2))
        np.maximum(deposits, patch, out=deposits)
        for _ in range(count):
            px = rng.gauss(x, sx * .70) * width
            py = rng.gauss(y, sy * .68) * height
            turn = rng.gauss(heading, .39)
            reach = rng.uniform(4, 37) * min(width, height) / 660
            end = (px + reach * math.cos(turn), py + reach * math.sin(turn))
            scrape(scratches, (px, py), end, rng.choice((1, 1, 2, 2, 3)), rng.uniform(60, 225), rng)

    if region in ("lid", "back", "lid_trim"):
        for x in (.075, .925):
            contact(x, .053, .063, .023, .98, 220, 1.04 if x < .5 else 2.02)
            contact(x, .948, .047, .031, .83, 128, .85 if x < .5 else 2.17)
            contact(x, .32, .027, .061, .54, 44, 1.18)
        for x in (.26, .46, .69, .81):
            contact(x, .035, .108, .014, .71, 72, 1.15)
        if region != "lid_trim":
            # The supplied shell uses these four molded rib heights in metres.
            for z in (.150, .333, .517, .700):
                y = (.832 - z - .010) / .832
                for x, weight in ((.203, .73), (.423, .43), (.72, .49), (.798, .69)):
                    contact(x, y+rng.uniform(-.006, .006), .061, .010, weight, 42, .42)
    elif region in ("left", "right"):
        for x, y, weight in ((.18, .061, .78), (.74, .069, .69), (.84, .94, .94), (.16, .952, .57),
                             (.52, .244, .51), (.53, .604, .58), (.35, .367, .38), (.33, .729, .45)):
            contact(x, y, .071, .028, weight, 69, 1.02)
    elif region in ("top", "bottom"):
        for x, y in ((.10, .16), (.90, .16), (.10, .84), (.90, .84), (.49, .11), (.54, .88)):
            contact(x, y, .090, .070, .84, 72, 1.11 if region == "top" else 1.54)

    grain = np.asarray(noise(size, 5, rng), dtype=np.float32) / 255
    lines = np.asarray(scratches, dtype=np.float32) / 255
    scatter = deposits * np.clip((grain - .29) * 1.92, .09, 1)
    abrasion = np.clip(scatter * .49 + lines * .87, 0, 1)
    dullness = np.clip(deposits * 1.19 + lines, 0, 1)
    return abrasion, dullness, lines


def wear_maps(regions, atlas_size, source_normal):
    specular = Image.new("RGB", atlas_size, (255, 11, 41))
    normal = Image.new("RGB", atlas_size, (128, 128, 255))
    finish = Image.new("RGBA", atlas_size)
    for region, (left, top, w, h) in regions.items():
        abrasion, dullness, cuts = wear_tile(region, (w, h))
        bright = np.stack((np.full_like(dullness, 255), 4 + 21*(1 - dullness)**2,
                           12 + 57*(1 - dullness)**2), axis=-1)
        specular.paste(Image.fromarray(bright.astype(np.uint8)), (left, top))

        relief = Image.fromarray((cuts*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.64))
        dy, dx = np.gradient(np.asarray(relief, dtype=np.float32) / 255)
        tile = np.asarray(source_normal.convert("RGB").resize((w, h), Image.Resampling.LANCZOS), dtype=np.float32)
        vectors = tile / 127.5 - 1
        vectors[..., 0] += dx * .57
        vectors[..., 1] -= dy * .57
        vectors /= np.maximum(1e-4, np.linalg.norm(vectors, axis=-1, keepdims=True))
        normal.paste(Image.fromarray(((vectors + 1)*127.5).clip(0, 255).astype(np.uint8)), (left, top))

        rub = Image.new("RGBA", (w, h), (168, 166, 147))
        rub.putalpha(Image.fromarray((abrasion*192).astype(np.uint8)))
        finish.paste(rub, (left, top))
    return specular, normal, finish
