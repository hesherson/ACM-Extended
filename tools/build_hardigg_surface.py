"""Shell textures of the Hardigg chests: rotomoulded olive polyethylene with wear that follows the mesh.

The wear is placed from four maps baked off the model (tools/assets/hardigg_bake_*.png, written by
bake_hardigg_surface.py): occlusion, model normal and model position. From them come
  curvature   outside corners and rib crests are rubbed pale, inside creases hold dirt
  prominence  how far a point stands out of the core box: bumpers and ribs take the sliding wear
  facing      dust settles on what faces up while the chest stands on its wheel end
Polyethylene does not chip. It scuffs to a pale, matt, slightly fuzzy surface and scratches in fine pale lines,
so the wear lightens and dulls the plastic instead of exposing another colour.

Writes case_<n>_co (12 finishes with the existing markings), case_co, case_nohq, case_smdi and case_as, and points
case.rvmat at the ambient shadow map.

Use: python build_hardigg_surface.py --work <folder> [--hemtt hemtt] [--only 0,2] [--png-only]
"""
import argparse
import math
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw

ASSETS = Path(__file__).with_name("assets")
OUTPUT = Path(__file__).resolve().parents[1] / "addons/acm_extended/data/medical_chest/hardigg"
W, H = 2048, 4096
REGIONS = {"lid": (8, 8, 1000, 1600), "back": (1032, 8, 1000, 1600), "right": (8, 1632, 640, 1600),
           "left": (664, 1632, 640, 1600), "top": (8, 3256, 1000, 640), "bottom": (1032, 3256, 1000, 640),
           "inside": (1320, 1632, 704, 704), "lid_left": (1320, 2368, 112, 704), "lid_right": (1444, 2368, 112, 704),
           "lid_top": (1570, 2368, 454, 112), "lid_bottom": (1570, 2492, 454, 112)}
LONG_FACES = ("lid", "back", "right", "left")              # the long axis of the case runs up these regions
PLASTIC = np.array([74.0, 80.0, 56.0]) / 255               # olive drab polyethylene, in shade
CHALK = np.array([122.0, 128.0, 106.0]) / 255              # the same plastic weathered by sun
SCUFF = np.array([139.0, 145.0, 124.0]) / 255              # abraded, fuzzy polyethylene
DIRT = np.array([46.0, 42.0, 34.0]) / 255
DUST = np.array([152.0, 143.0, 121.0]) / 255
CORE = (0.253, 0.150, 0.030, 0.820)                        # core half width, half depth, low end, high end
STAND = (0.012, 0.010, 0.012)                              # how far bumpers and ribs stand out of it


def band_noise(rng, lo, hi, shape=(H, W)):
    """Noise with wavelengths between lo and hi pixels. Mean 0, deviation 1."""
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.rfftfreq(shape[1])[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    spectrum = np.fft.rfft2(rng.standard_normal(shape, dtype=np.float32))
    spectrum *= ((f >= 1.0 / hi) & (f <= 1.0 / lo)).astype(np.float32)
    out = np.fft.irfft2(spectrum, s=shape).astype(np.float32)
    out -= out.mean()
    return out / (out.std() + 1e-9)


def blur(a, radius):
    """Gaussian blur of a float image, radius in pixels (done in the frequency domain, edges wrap)."""
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    kernel = np.exp(-2 * (math.pi * radius) ** 2 * (fx * fx + fy * fy)).astype(np.float32)
    return np.fft.irfft2(np.fft.rfft2(a.astype(np.float32)) * kernel, s=a.shape).astype(np.float32)


def smoothstep(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


MASKS = ("ao", "ridge", "crease", "prominence", "up", "valid", "low", "back")


def mesh_masks(folder=ASSETS):
    """The wear masks, as 8 bit images in tools/assets. convert_bake() writes them after a new bake."""
    masks = {name: np.asarray(Image.open(folder / f"hardigg_mask_{name}.png"), np.float32) / 255.0 for name in MASKS}
    masks["valid"] = masks["valid"] > 0.5
    return masks


def convert_bake(folder, assets=ASSETS):
    """Occlusion, curvature split in ridge and crease, prominence, upward facing, and the baked area,
    from the float maps bake_hardigg_surface.py left in folder."""
    ao = np.load(folder / "hardigg_bake_ao.npy").astype(np.float32)[..., 0]
    raw = np.load(folder / "hardigg_bake_normal.npy").astype(np.float32)
    valid = raw.sum(-1) > 0.05                              # pixels the bake never reached stay black
    normal = raw * 2 - 1
    pos = np.load(folder / "hardigg_bake_pos.npy").astype(np.float32)
    pos = np.stack([(pos[..., 0] - 0.5) * 0.6, (pos[..., 1] - 0.5) * 0.4, pos[..., 2] * 0.85], -1)
    curvature = np.zeros((H, W), np.float32)
    for x, y, w, h in REGIONS.values():
        n, p, ok = normal[y:y + h, x:x + w], pos[y:y + h, x:x + w], valid[y:y + h, x:x + w]
        inner = ok[1:-1, 1:-1] & ok[1:-1, :-2] & ok[1:-1, 2:] & ok[:-2, 1:-1] & ok[2:, 1:-1]
        if inner.sum() < 100:
            continue
        local = np.zeros((h - 2, w - 2), np.float32)
        for axis in (1, 0):                                  # across the region, then down it
            a, b = (slice(1, -1), slice(2, None)) if axis == 1 else (slice(2, None), slice(1, -1))
            c, d = (slice(1, -1), slice(None, -2)) if axis == 1 else (slice(None, -2), slice(1, -1))
            step = np.median(((p[a, b] - p[c, d]) / 2)[inner], axis=0)      # metres for one pixel, as a vector
            local += ((n[a, b] - n[c, d]) / 2) @ step / max(float(step @ step), 1e-12)
        curvature[y + 1:y + h - 1, x + 1:x + w - 1] = np.where(inner, local, 0)
    curvature = blur(curvature, 1.2)
    # A 6 mm outside radius reads as 1. Bends gentler than 30 mm are left out: they are the facets of the mesh.
    ridge = np.clip((curvature - 32.0) / 140.0, 0, 1)
    crease = np.clip((-curvature - 32.0) / 140.0, 0, 1)
    hx, hy, z0, z1 = CORE
    out = np.stack([(np.abs(pos[..., 0]) - hx) / STAND[0], (np.abs(pos[..., 1]) - hy) / STAND[1],
                    np.maximum(pos[..., 2] - z1, z0 - pos[..., 2]) / STAND[2]], -1)
    prominence = np.clip((np.clip(out, 0, 1) * normal * normal).sum(-1), 0, 1) * valid
    up = np.clip(normal[..., 2], 0, 1) ** 2 * valid
    ao = np.where(valid, ao, 1.0)
    rib = folder / "hardigg_bake_rib.npy"
    if rib.exists():
        # The ribs are rotomoulded in one with the panels. Their foot is a soft fillet: a faint, wide shade,
        # and no crease for dirt to sit in.
        soft = blur(np.load(rib).astype(np.float32), 5.0)
        foot = np.clip(4 * soft * (1 - soft), 0, 1)
        crease *= 1 - np.clip(1.8 * blur(foot, 2.0), 0, 1)
        # The corners of a rib pad lie just under the panel in the mesh and bake black: they are skin like the rest.
        ao = np.where((soft > 0.02) & (soft < 0.98), np.maximum(ao, 0.92), ao)
        ao *= 1 - 0.12 * foot
    # Under a latch or a handle plate the bake is pitch black with an edge of whole texels, and one sees in
    # under them from the side: keep a little light there and soften the edge.
    ao = np.maximum(ao, 0.16)
    ao = 0.45 * ao + 0.55 * blur(ao, 1.6)
    x, y, w, h = REGIONS["inside"]
    ao[y:y + h, x:x + w] = np.maximum(ao[y:y + h, x:x + w], 0.55)
    low = np.clip((0.11 - pos[..., 2]) / 0.09, 0, 1) * valid      # the end that stands on the ground
    masks = dict(ao=ao, ridge=ridge, crease=crease, prominence=prominence, up=up, valid=valid, low=low,
                 back=np.clip(-normal[..., 1], 0, 1) * valid)
    for name in MASKS:
        Image.fromarray(np.clip(masks[name] * 255.0, 0, 255).astype(np.uint8)).save(
            assets / f"hardigg_mask_{name}.png", optimize=True)
        print("mask", name, round(float(np.mean(masks[name])), 4))


def region_mask(names):
    mask = np.zeros((H, W), bool)
    for name in names:
        x, y, w, h = REGIONS[name]
        mask[y:y + h, x:x + w] = True
    return mask


def scratch_layer(rng, weight, count, long_axis, length=(14.0, 0.9), widths=(1, 1, 1, 2), level=(60, 255)):
    """Fine scratches drawn at twice the size and scaled down. weight: where they fall. Returns 0..1."""
    canvas = Image.new("L", (W * 2, H * 2), 0)
    draw = ImageDraw.Draw(canvas)
    flat = np.cumsum(weight.ravel(), dtype=np.float64)
    picks = np.searchsorted(flat, rng.random(count) * flat[-1])
    ys, xs = np.divmod(picks, W)
    along = long_axis[ys, xs]
    angle = np.where(along & (rng.random(count) < 0.62), rng.normal(math.pi / 2, 0.42, count),
                     rng.uniform(0, math.pi, count))
    size = np.exp(rng.normal(math.log(length[0]), length[1], count)).clip(3, 420)
    bend = rng.normal(0, 0.10, count)
    tone = rng.uniform(level[0], level[1], count) * np.clip(1.25 - size / 300, 0.45, 1)
    wide = rng.choice(widths, count)
    for x, y, a, s, b, t, w in zip(xs, ys, angle, size, bend, tone, wide):
        dx, dy = math.cos(a) * s, math.sin(a) * s
        mx, my = -dy * b, dx * b                           # a slight bow: nothing slides in a ruled line
        draw.line([(2 * x - dx, 2 * y - dy), (2 * x + mx, 2 * y + my), (2 * x + dx, 2 * y + dy)],
                  fill=int(t), width=int(w))
    return np.asarray(canvas.resize((W, H), Image.Resampling.BOX), np.float32) / 255.0


def normal_map(height):
    dx = np.roll(height, -1, 1) - np.roll(height, 1, 1)
    dy = np.roll(height, -1, 0) - np.roll(height, 1, 0)
    length = np.sqrt(dx * dx + dy * dy + 1)
    return np.stack([-dx / length, dy / length, 1 / length], -1) * 127.5 + 127.5


def surface(masks, seed=7310):
    """Everything the twelve finishes share: wear masks, normal map, specular map, ambient shadow."""
    rng = np.random.default_rng(seed)
    valid, ridge, prominence = masks["valid"], masks["ridge"], masks["prominence"]
    inside = region_mask(("inside",))
    blotch, patch, grain = band_noise(rng, 40, 320), band_noise(rng, 9, 70), band_noise(rng, 3, 14)
    # exposure: what gets rubbed when the case is dragged, stacked and thrown on a truck
    edge = np.clip(blur(ridge, 2.5) * 2.2, 0, 1)
    corner = np.clip(blur(ridge, 20) * 7.0 - 0.25, 0, 1) ** 1.4       # where several edges meet
    exposure = np.clip(0.52 * edge + 0.24 * prominence + 0.50 * corner + 0.22 * masks["low"]
                       + 0.06 * masks["back"], 0, 1)
    exposure *= np.where(inside, 0.12, 1.0) * valid
    scuff = smoothstep(0.50, 1.05, exposure * 1.15 + 0.20 * blotch + 0.16 * patch + 0.05 * grain)
    scuff *= 0.55 + 0.45 * smoothstep(-0.6, 0.9, patch)      # broken up, never an even coat
    long_axis = region_mask(LONG_FACES)
    weight = (0.010 + 0.9 * exposure ** 1.6 + 1.6 * scuff) * valid * np.where(inside, 0.2, 1.0)
    fine = scratch_layer(rng, weight, 90000, long_axis, level=(40, 200))
    frost = scratch_layer(rng, (scuff ** 1.5 + 0.02 * exposure) * valid, 170000, long_axis,
                          length=(5.0, 0.6), level=(30, 150))
    lone = scratch_layer(rng, (0.12 + exposure) * valid * ~inside, 420, long_axis, length=(60.0, 0.7),
                         widths=(1, 1, 2), level=(90, 210))
    gouge = scratch_layer(rng, (0.05 + exposure ** 2) * valid * ~inside, 60, long_axis, length=(40.0, 0.6),
                          widths=(3, 4, 6), level=(200, 255))
    scratches = np.clip(fine * 0.85 + lone + frost * 0.55, 0, 1)
    # dirt in creases and under overhangs, dust on what faces up, a grimy band at the ground end
    cavity = np.clip((0.86 - masks["ao"]) / 0.55, 0, 1) ** 1.15
    dirt = np.clip(cavity * (0.75 + 0.25 * patch) + 0.55 * blur(masks["crease"], 2.0)
                   + 0.22 * masks["low"] * smoothstep(-0.4, 1.2, blotch), 0, 1) * valid
    dust = np.clip((0.62 * masks["up"] + 0.07 + 0.25 * cavity) * (0.55 + 0.45 * smoothstep(-1, 1, blotch))
                   - 0.35 * scuff, 0, 1) * valid
    # height: orange peel of the mould, slow waviness of a rotomoulded wall, scratches, gouges with a raised lip
    height = (0.008 * band_noise(rng, 2.4, 7) + 0.10 * band_noise(rng, 90, 340) + 0.012 * band_noise(rng, 14, 40)
              - 0.24 * fine - 0.34 * lone - 0.10 * frost - 0.85 * gouge + 0.40 * blur(gouge, 2.2))
    # specular (G) and gloss (B): a dull waxy sheen when clean, matt where scuffed, scratched or dusty
    sheen = smoothstep(0.9, 2.2, band_noise(rng, 50, 260)) * ~inside       # handled, slightly greasy patches
    gloss = (0.60 + 0.03 * blotch + 0.10 * sheen - 0.30 * scuff - 0.22 * scratches - 0.30 * dust - 0.28 * dirt
             - 0.20 * gouge)
    spec = 0.44 + 0.02 * patch + 0.06 * sheen - 0.14 * scuff - 0.10 * scratches - 0.22 * dust - 0.20 * dirt
    smdi = np.stack([np.ones((H, W), np.float32), np.clip(spec, 0.08, 0.7), np.clip(gloss, 0.10, 0.85)], -1)
    shadow = np.clip(masks["ao"] ** 0.9, 0, 1)
    ambient = np.stack([np.ones((H, W), np.float32), shadow, np.ones((H, W), np.float32)], -1)
    return dict(scuff=scuff, scratches=scratches, gouge=gouge, dirt=dirt, dust=dust, exposure=exposure,
                normal=normal_map(height), smdi=smdi * 255, ambient=ambient * 255, blotch=blotch, patch=patch)


def markings(index, glyphs):
    """The paint, tape and stencils of one finish, without the old contact wear (the scuffs come from here)."""
    import build_hardigg_wear as wear
    original = wear.contact_wear
    wear.contact_wear = lambda region, size, rng: (original(region, size, rng), Image.new("RGBA", size))[1]
    try:
        overlay = Image.new("RGBA", (W, H))
        wear.paint_finish(overlay, index, REGIONS, glyphs)
    finally:
        wear.contact_wear = original
    return np.asarray(overlay, np.float32) / 255.0


def paint_transfer(rng, masks, shared):
    """A few dry smears of white paint picked up from other cargo."""
    layer = np.zeros((H, W), np.float32)
    streak = band_noise(rng, 2, 9)
    names = ("back", "left", "right")                       # never on the lid: there it reads as smeared markings
    for _ in range(int(rng.integers(1, 4))):
        x, y, w, h = REGIONS[names[int(rng.integers(len(names)))]]
        cx, cy = x + rng.uniform(0.15, 0.85) * w, y + rng.uniform(0.1, 0.9) * h
        rx, ry, turn = rng.uniform(14, 46), rng.uniform(22, 90), rng.uniform(-0.6, 0.6)
        yy, xx = np.mgrid[int(cy - 110):int(cy + 110), int(cx - 110):int(cx + 110)]
        u = (xx - cx) * math.cos(turn) + (yy - cy) * math.sin(turn)
        v = -(xx - cx) * math.sin(turn) + (yy - cy) * math.cos(turn)
        fall = np.clip(1 - (u / rx) ** 2 - (v / ry) ** 2, 0, 1)
        patch = smoothstep(0.35, 0.75, fall * 1.1 + 0.33 * streak[yy.clip(0, H - 1), xx.clip(0, W - 1)])
        ys, xs = yy.clip(0, H - 1), xx.clip(0, W - 1)
        layer[ys, xs] = np.maximum(layer[ys, xs], patch * rng.uniform(0.30, 0.55))
    return layer * masks["valid"] * (0.4 + 0.6 * shared["exposure"])


RUBBED = {2: ((288, 450), (80, 100), 0.62)}                # finish: centre on the lid face, radii, how hard it was rubbed


def rubbed(index, shared):
    """What years of hands and straps leave of a marking: 1 where the paint is whole. The paint goes from the
    high spots first and stays in the pits of the moulded skin, so what is left is a speckled ghost, not a smear."""
    keep = np.ones((H, W), np.float32)
    if index not in RUBBED:
        return keep
    (cx, cy), (rx, ry), amount = RUBBED[index]
    left, top = REGIONS["lid"][:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fall = np.clip(1 - ((xx - left - cx) / rx) ** 2 - ((yy - top - cy) / ry) ** 2, 0, 1)
    rng = np.random.default_rng(7700 + index)
    pits, flakes = band_noise(rng, 2.2, 7), band_noise(rng, 5, 26)
    wear = fall ** 0.6
    # whole flakes are gone where it was rubbed hardest, and what is left there is thin
    gone = smoothstep(-0.25, 0.85, 0.55 * shared["patch"] + 0.55 * flakes + 1.5 * wear * amount - 0.80) * (fall > 0)
    gone *= 1 - 0.45 * smoothstep(0.55, 1.5, pits)          # specks of paint stay in the pits
    return (keep - gone) * (1 - 0.42 * amount * wear)


def albedo(index, masks, shared, glyphs):
    rng = np.random.default_rng(9100 + index * 17)
    blotch, patch = shared["blotch"], shared["patch"]
    tone = 1 + 0.030 * band_noise(rng, 160, 1100) + 0.012 * patch
    color = PLASTIC[None, None, :] * tone[..., None]
    color[..., 0] *= 1 + 0.010 * blotch                     # the pigment is never quite even
    fade = np.clip(0.11 * blur(masks["prominence"], 6) + 0.05 * masks["up"] + 0.03, 0, 1)
    color += (CHALK - color) * fade[..., None]
    if index == 8:                                          # a base half from another lot
        other = region_mask(("back", "right", "left", "top", "bottom", "inside"))
        color[other] *= np.array([0.86, 0.93, 0.88])
    paint = np.zeros((H, W), np.float32)
    if index == 11:                                         # lid sprayed matt black
        lid = region_mask(("lid", "lid_left", "lid_right", "lid_top", "lid_bottom")) & masks["valid"]
        black = (0.060 + 0.012 * patch)[..., None] * np.array([0.97, 1.0, 1.03])
        color = np.where(lid[..., None], black, color)
        paint = lid.astype(np.float32)
    marks = markings(index, glyphs)
    worn = np.clip(1 - 0.85 * shared["scratches"] - 0.55 * shared["scuff"], 0, 1)
    alpha = marks[..., 3] * worn * rubbed(index, shared)
    color += (marks[..., :3] - color) * alpha[..., None]
    paint = np.maximum(paint, alpha)
    rub = np.clip(shared["scuff"] * (0.50 + 0.38 * paint), 0, 1)             # paint rubs off sooner than plastic
    color += (SCUFF - color) * rub[..., None]
    line = np.clip(shared["scratches"] * (0.46 + 0.40 * paint), 0, 1)
    color += (SCUFF * 1.08 - color) * line[..., None]
    gouge = shared["gouge"]
    color += (SCUFF * 1.18 - color) * np.clip(blur(gouge, 1.6) * 1.2 - gouge, 0, 1)[..., None]
    color *= (1 - 0.45 * gouge)[..., None]                  # dirt packs into the bottom of a gouge
    smear = paint_transfer(rng, masks, shared)
    color += (np.array([0.86, 0.855, 0.82]) - color) * (smear * 0.9)[..., None]
    color += (DIRT - color) * (0.62 * shared["dirt"])[..., None]
    color += (DUST - color) * (0.34 * shared["dust"])[..., None]
    return np.clip(color * 255, 0, 255).astype(np.uint8)


FLOOR = (0.20, 0.14, 0.80, 0.86)                           # part of the inside tile that holds the floors


def inner_uv(lod, offset=(0.0, 0.0, 0.0)):
    """Unfold everything in the inside tile like a box: floors in the middle, walls in the bands round them.
    The plain projection it replaces drew each wall as one line of texels. offset: model origin in chest coordinates."""
    left, top, width, height = REGIONS["inside"]
    verts = np.asarray(lod["verts"], float) + np.asarray(offset, float)
    u0, v0, u1, v1 = FLOOR
    for face in lod["faces"]:
        if not face["tex"].lower().rsplit("\\", 1)[-1].startswith("case"):
            continue
        uv = np.asarray(face["uv"], float)
        px, py = uv[:, 0].mean() * W, (1 - uv[:, 1].mean()) * H
        if not (left <= px <= left + width and top <= py <= top + height):
            continue
        points = verts[face["v"]]
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        axis = int(np.argmax(np.abs(normal)))
        centre = points.mean(axis=0)
        u = u0 + (u1 - u0) * np.clip((points[:, 0] + 0.263) / 0.526, 0, 1)
        v = v0 + (v1 - v0) * np.clip((0.832 - points[:, 2]) / 0.832, 0, 1)
        depth = np.clip((points[:, 1] + 0.16) / 0.32, 0, 1)
        if axis == 0:
            u = u1 + (1 - u1) * depth if centre[0] > 0 else u0 - u0 * depth
        elif axis == 2:
            v = v0 - v0 * depth if centre[2] > 0.425 else v1 + (1 - v1) * depth
        face["uv"] = list(zip(((left + 3 + u * (width - 6)) / W).tolist(), (1 - (top + 3 + v * (height - 6)) / H).tolist()))


def moulded(lod, offset=(0.0, 0.0, 0.0)):
    """The ribs of the lid and the back are separate pads in the mesh, but one skin with the panel on the case.
    The points at the foot of a rib take the normal of the panel, so the light runs from one into the other."""
    verts = np.asarray(lod["verts"], float) + np.asarray(offset, float)
    normals = list(lod["normals"])
    flat = {}
    for face in lod["faces"]:
        if not face["tex"].lower().rsplit("\\", 1)[-1].startswith("case"):
            continue
        depth = verts[face["v"], 1]
        if abs(depth.mean()) <= 0.1502 or np.abs(verts[face["v"], 0]).max() > 0.21:
            continue
        side = 1.0 if depth.mean() > 0 else -1.0
        if side not in flat:
            flat[side] = len(normals)
            normals.append((0.0, side, 0.0))
        face["n"] = [flat[side] if abs(y) < 0.1502 else n for y, n in zip(depth, face["n"])]
    lod["normals"] = normals
    return lod


def point_rvmat(output):
    path = output / "case.rvmat"
    text = path.read_text()
    new = text.replace('texture = "#(argb,8,8,3)color(1,1,1,1,AS)";', f'texture = "{PREFIX}case_as.paa";')
    path.write_text(new)


PREFIX = r"acm_extended\data\medical_chest\hardigg" + "\\"


def build(output, work, hemtt="hemtt", glyphs=None, only=None, png_only=False):
    from build_medical_chest_stencils import stencil_glyphs
    glyphs = glyphs or stencil_glyphs(ASSETS / "hardigg_stencil.png")
    work.mkdir(parents=True, exist_ok=True)
    masks = mesh_masks()
    shared = surface(masks)

    def export(array, name):
        png = work / (name + ".png")
        Image.fromarray(np.clip(array, 0, 255).astype(np.uint8)).save(png)
        if not png_only:
            paa = output / (name + ".paa")
            paa.unlink(missing_ok=True)
            subprocess.run([hemtt, "utils", "paa", "convert", str(png), str(paa)], check=True,
                           stdout=subprocess.DEVNULL)
        return png

    export(shared["normal"], "case_nohq")
    export(shared["smdi"], "case_smdi")
    export(shared["ambient"], "case_as")
    for index in (range(12) if only is None else only):
        png = export(albedo(index, masks, shared, glyphs), f"case_{index}_co")
        if index == 0 and not png_only:
            (output / "case_co.paa").write_bytes((output / "case_0_co.paa").read_bytes())
        print("finish", index, png.name)
    if not png_only:
        point_rvmat(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--hemtt", default="hemtt")
    parser.add_argument("--only", help="Finish numbers, comma separated")
    parser.add_argument("--png-only", action="store_true", help="Write the PNG files to --work and stop")
    parser.add_argument("--bake", type=Path, help="Folder with a new bake: refresh the masks in tools/assets first")
    args = parser.parse_args()
    if args.bake:
        convert_bake(args.bake)
    only = [int(n) for n in args.only.split(",")] if args.only else None
    build(args.output, args.work, args.hemtt, only=only, png_only=args.png_only)


if __name__ == "__main__":
    main()
