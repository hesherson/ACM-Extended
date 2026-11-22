#!/usr/bin/env python3
"""Fittings of the Hardigg chest: latches, handles, wheels, feet, relief valve and the bolts in the walls.

Model side (fit, bolted): every face of a fitting gets a plan view UV in one 2048 atlas. A fitting is
looked at from outside, along the normal of its frame; a wall folds in under its top edge, so that the
same rule works for every LOD and every copy of a fitting shares one tile. Each handle gets its backing
plate, and the open cabinet gets the bolt ends that show inside the empty case.

Texture side (build): the atlas is painted from a height map rasterised from those same faces, so rust
sits in the corners, bare steel on the edges and dust in the hollows of the real mesh.

  python tools/build_hardigg_fittings.py <acme_medchest_b2 folder> --models <folder with unfitted p3d files>
      [--output <hardigg data folder>] [--work <folder for PNG>] [--hemtt hemtt] [--png-only]

--models must hold models that have not been fitted yet; the generator calls fit() and bolted() itself.
"""
import argparse
import math
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from build_hardigg_surface import band_noise, blur, normal_map, smoothstep

PREFIX = r"acm_extended\data\medical_chest\hardigg" + "\\"
OUTPUT = Path(__file__).resolve().parents[1] / "addons/acm_extended/data/medical_chest/hardigg"
RELIEF = Path(__file__).with_name("assets") / "hardigg_fittings_relief.npz"
TEXTURE, MATERIAL = "fittings_co.paa", "fittings.rvmat"
ATLAS, PAD = 2048, 8
TILES = {"latch_0": (0, 0, 512, 1024), "latch_1": (512, 0, 512, 1024), "latch_2": (1024, 0, 512, 1024),
         "wheel": (1536, 0, 512, 512), "foot": (1536, 512, 256, 256), "valve": (1792, 512, 256, 256),
         "bolt": (1536, 768, 256, 256), "handle_0": (0, 1024, 768, 768), "handle_1": (768, 1024, 768, 768),
         "handle_side": (0, 1792, 768, 256)}
# A plain piece of the latch steel, for the faces one sees only when a latch hangs open: walls, backs, undersides.
PLAIN = (768, 1792, 256, 256)
PLAIN_SPAN = 0.12                                            # metres of a latch frame across that piece
# plan box (u0, v0, u1, v1) and depth range of each fitting in its frame; fold: how far a wall reaches under its edge
OLD_LATCH = (-0.026, -0.077, 0.026, 0.027)                  # the latch of the source, which fit() takes out
CLASSES = {"latch": dict(box=(-0.023, -0.046, 0.023, 0.051), depth=(-0.004, 0.016), fold=0.004),
           "handle": dict(box=(-0.062, -0.072, 0.062, 0.052), depth=(-0.005, 0.024), fold=0.008),
           # the side of a handle, seen along its hinge: along the arm, and up from the floor of the pocket
           "handle_side": dict(box=(-0.072, -0.004, 0.052, 0.022), depth=(0.0, 0.0), fold=0.0),
           "wheel": dict(box=(-0.040, -0.040, 0.040, 0.040), depth=(-0.016, 0.016), fold=0.010),
           "foot": dict(box=(-0.020, -0.020, 0.020, 0.020), depth=(-0.024, 0.024), fold=0.008),
           "valve": dict(box=(-0.016, -0.016, 0.016, 0.016), depth=(-0.003, 0.012), fold=0.004),
           "bolt": dict(box=(-0.010, -0.010, 0.010, 0.010), depth=(0.0, 0.0), fold=0.0)}
MADE_OF = {"latch": ("blackmetal", "alu"), "handle": ("blackplastic", "blackmetal"), "wheel": ("blackplastic", "alu"),
           "foot": ("blackplastic",), "valve": ("blackplastic", "alu")}
STEEL, PLASTIC, ZINC = 0, 1, 2
IDS = {"blackmetal": STEEL, "blackplastic": PLASTIC, "alu": ZINC}
LATCH_Z, END_LATCH_X = (.724, .506, .344, .126), 0.0          # as build_hardigg_hardware.py places them
HANDLE_SINK, POCKET = (.021, .016), (.022, .014)             # side and end handles: frame sink, pocket depth
PLATE = (-0.061, -0.066, 0.061, 0.047)                       # backing plate of a handle, in its frame
PLATE_RIVETS = ((-0.028, 0.000), (0.028, 0.000), (-0.028, -0.034), (0.028, -0.034))
LATCH_RIVETS = ((-0.006, -0.026), (0.006, -0.026))
# Rust is the exception: these latches of these finishes, and no other. 0 top end, 1 to 4 one side from the top,
# 5 wheel end, 6 to 9 the other side from the bottom.
RUSTY = {2: (4, 5, 6), 7: (3, 4), 10: (5, 8)}
LID_ORIGIN = (0.0, .1175, .416)


# ---------------------------------------------------------------- model side

def instances(geo):
    """Every fitting of the chest: class, atlas tile and frame (origin, U, V, N out of the case)."""
    saved = geo.LATCH_Z, geo.END_LATCH_X
    geo.LATCH_Z, geo.END_LATCH_X = LATCH_Z, END_LATCH_X
    try:
        latches, handles = geo.frames()
    finally:
        geo.LATCH_Z, geo.END_LATCH_X = saved
    out = [dict(cls="latch", tile="latch_%d" % (i % 2), frame=frame) for i, frame in enumerate(latches)]
    for i, (origin, across, along, normal) in enumerate(handles):
        end = 0 if normal[0] else 1
        sunk = tuple(p - HANDLE_SINK[end] * n for p, n in zip(origin, normal))
        out.append(dict(cls="handle", tile="handle_%d" % (i % 2), frame=(sunk, across, along, normal),
                        floor=HANDLE_SINK[end] - POCKET[end]))
    for side in (-1, 1):
        out.append(dict(cls="wheel", tile="wheel", frame=((side * 0.240, -0.120, 0.036), (0, 1, 0), (0, 0, 1), (side, 0, 0))))
        out.append(dict(cls="foot", tile="foot", frame=((side * 0.185, 0.030, 0.021), (1, 0, 0), (0, 1, 0), (0, 0, -1))))
    out.append(dict(cls="valve", tile="valve", frame=((0.150, 0.147, 0.610), (1, 0, 0), (0, 0, 1), (0, 1, 0))))
    return out


def _local(frame, points):
    origin, across, along, normal = (np.array(a, float) for a in frame)
    return (np.asarray(points, float) - origin) @ np.stack([across, along, normal]).T


def _claims(inst, point):
    kind = CLASSES[inst["cls"]]
    u0, v0, u1, v1 = kind["box"]
    return u0 <= point[0] <= u1 and v0 <= point[1] <= v1 and kind["depth"][0] <= point[2] <= kind["depth"][1]


def tile_uv(tile, cls, plan):
    """Plan coordinates in a frame (metres) to atlas UV."""
    u0, v0, u1, v1 = CLASSES[cls]["box"]
    x, y, w, h = TILES[tile]
    plan = np.asarray(plan, float)
    px = x + PAD + np.clip((plan[:, 0] - u0) / (u1 - u0), 0, 1) * (w - 2 * PAD)
    py = y + PAD + np.clip((v1 - plan[:, 1]) / (v1 - v0), 0, 1) * (h - 2 * PAD)
    return [(float(a) / ATLAS, 1 - float(b) / ATLAS) for a, b in zip(px, py)]


def plan_uv(inst, local, normal):
    """Seen from outside. A wall folds in under its own top edge, by at most the fold of its class."""
    fold = CLASSES[inst["cls"]]["fold"]
    plan = local[:, :2].copy()
    steep = math.hypot(normal[0], normal[1])
    if steep > 1e-4:
        depth = local[:, 2].max() - local[:, 2]
        reach = steep * fold * (1 - np.exp(-depth / fold))
        plan -= np.outer(reach, np.array(normal[:2]) / steep)
    return tile_uv(inst["tile"], inst["cls"], plan)


# The latch, measured off the maker's front view (strike plate 25.4 mm wide), v from the seam, lid side positive.
HINGE_UP = 0.014                                             # the drum is 8 mm under the seam; the rig of the source has it at 22
DRUM = ((0.0, -0.0080), 0.0082)                              # the drum the key turns: centre, radius
# The key (butterfly): sheet steel, its top cut round to clear the drum, its sides running straight out to two round
# lobes, its lower edge a little hollow between them. Right half, from the middle of the lower edge up to the ear.
KEY_HALF = ((0.0, -0.0392), (0.0035, -0.0397), (0.0075, -0.0412), (0.0120, -0.0422), (0.0160, -0.0415), (0.0190, -0.0390),
            (0.0206, -0.0345), (0.0210, -0.0290), (0.0195, -0.0220), (0.0160, -0.0130), (0.0125, -0.0050), (0.0098, -0.0046))
KEY_NOTCH = 0.0090                                           # radius of the cut round the drum
KEY_HOLE, KEY_SLOTS = ((0.0, -0.0285), 0.0062), ((0.0131, -0.0189, -0.0371), 0.0024)    # bore; slot at +-u, v to v, half width
STRIKE = ((-0.0157, 0.0125), (0.0157, 0.0125), (0.0157, 0.0205), (0.0127, 0.0245), (0.0127, 0.0457), (0.0107, 0.0477),
          (-0.0107, 0.0477), (-0.0127, 0.0457), (-0.0127, 0.0245), (-0.0157, 0.0205))
STRIKE_RIVETS, STRIKE_DIMPLE, STRIKE_NAME = ((-0.0070, 0.0337), (0.0070, 0.0337)), (0.0, 0.0385), (0.0, 0.0285)
FAR = ((-0.021, -0.029), (-0.012, -0.042), (0.012, -0.042), (0.021, -0.029), (0.0125, -0.005), (-0.0125, -0.005))


def _prism(K, outline, low, high):
    """A flat plate with this outline (anticlockwise, seen from outside, no hollow corner), without its underside."""
    count = len(outline)
    points = [(u, v, high) for u, v in outline] + [(u, v, low) for u, v in outline]
    faces = [(0, k, k + 1) for k in range(1, count - 1)]
    faces += [(count + k, count + (k + 1) % count, (k + 1) % count, k) for k in range(count)]
    return K.Part(points, faces)


def key_outline():
    """The whole outline of the key, anticlockwise: lower edge, right side, round the drum, left side."""
    (cu, cv), _ = DRUM
    start = math.asin((KEY_HALF[-1][1] - cv) / KEY_NOTCH)
    notch = [(cu + KEY_NOTCH * math.cos(start - (start + math.pi / 2) * k / 7), cv + KEY_NOTCH * math.sin(start - (start + math.pi / 2) * k / 7))
             for k in range(1, 8)]                           # from the right ear down to the lowest point of the cut
    right = list(KEY_HALF) + notch
    return right + [(-u, v) for u, v in right[-2:0:-1]]


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _crossing(a, b, c, d):
    """Do the segments a-b and c-d cross each other away from their ends?"""
    return _cross(a, b, c) * _cross(a, b, d) < -1e-16 and _cross(c, d, a) * _cross(c, d, b) < -1e-16


def _holed(points, outer, holes):
    """Triangles of a flat outline (anticlockwise) with holes (clockwise), as indices into points. Each hole is
    joined to the outline by a bridge, and the one outline that leaves is cut into ears."""
    order = list(outer)
    waiting = sorted(holes, key=lambda hole: -max(points[i][0] for i in hole))
    for place, hole in enumerate(waiting):
        edges = [(order[k - 1], order[k]) for k in range(len(order))]
        for other in waiting[place:]:
            edges += [(other[k - 1], other[k]) for k in range(len(other))]
        best = None
        for at_hole, h in enumerate(hole):
            for at_order, o in enumerate(order):
                span = (points[h][0] - points[o][0]) ** 2 + (points[h][1] - points[o][1]) ** 2
                # a point that already carries a bridge is in the outline twice: which of the two would be a guess
                if (best is None or span < best[0]) and order.count(o) == 1 and not any(
                        h not in edge and o not in edge and _crossing(points[h], points[o], points[edge[0]], points[edge[1]])
                        for edge in edges):
                    best = (span, at_hole, at_order)
        _, at_hole, at_order = best
        order = order[:at_order + 1] + hole[at_hole:] + hole[:at_hole + 1] + order[at_order:]
    triangles = []
    while len(order) > 3:
        for k in range(len(order)):
            i0, i1, i2 = order[k - 1], order[k], order[(k + 1) % len(order)]
            a, b, c = points[i0], points[i1], points[i2]
            turn = _cross(a, b, c)
            if abs(turn) <= 1e-14 and (i0 == i2 or len(order) > 3):
                if i0 == i2 or abs(turn) <= 1e-18:           # a bridge walked there and back, or a straight run
                    del order[k]
                    break
                continue
            if turn < 0:
                continue
            if not any(j not in (i0, i1, i2) and _cross(a, b, points[j]) > 1e-14 and _cross(b, c, points[j]) > 1e-14
                       and _cross(c, a, points[j]) > 1e-14 for j in order):
                triangles.append((i0, i1, i2))
                del order[k]
                break
        else:
            raise ValueError("The outline of the key could not be cut into triangles")
    if abs(_cross(*(points[i] for i in order))) > 1e-14:
        triangles.append(tuple(order))
    return triangles


def plate(K, outline, holes, low, high, bevel=0.0, under=True):
    """Sheet metal: this outline (anticlockwise) with these openings (each clockwise) cut through it, and its upper
    edges broken by a bevel, which with smooth shading reads as the rolled edge of a stamping."""
    points = list(outline)
    loops = [list(range(len(points)))]
    for shape in holes:
        loops.append(list(range(len(points), len(points) + len(shape))))
        points += shape
    triangles = _holed(points, loops[0], loops[1:])
    area = sum(_cross(points[a], points[b], points[c]) for a, b, c in triangles) / 2
    signed = [sum(_cross((0, 0), points[l[k - 1]], points[l[k]]) for k in range(len(l))) / 2 for l in loops]
    if abs(area - sum(signed)) > 1e-9 or any(_cross(points[a], points[b], points[c]) < -1e-14 for a, b, c in triangles):
        raise ValueError("A plate came out wrong: area %g against %g" % (area, sum(signed)))
    count = len(points)
    inset = list(points)
    if bevel:
        for loop in loops:                                   # the metal is on the left of every loop
            for k, i in enumerate(loop):
                before, after = points[loop[k - 1]], points[loop[(k + 1) % len(loop)]]
                normals = []
                for a, b in ((before, points[i]), (points[i], after)):
                    length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
                    normals.append((-(b[1] - a[1]) / length, (b[0] - a[0]) / length))
                mx, my = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
                scale = min(2.0, 2.0 / max(mx * mx + my * my, 1e-9)) * bevel
                inset[i] = (points[i][0] + mx * scale, points[i][1] + my * scale)
    # Two parts, because a part is shaded smooth within itself: the faces stay dead flat, the rim is rounded.
    # The upper face is cut into triangles as it really is, inside the bevel: cut from the outline and then moved,
    # its thinnest triangles turn inside out and show as dark lines across the face.
    upper = _holed(inset, loops[0], loops[1:]) if bevel else triangles
    if any(_cross(inset[a], inset[b], inset[c]) < -1e-14 for a, b, c in upper):
        raise ValueError("A triangle of a plate is inside out")
    flat = K.Part([(u, v, high) for u, v in inset] + [(u, v, low) for u, v in points],
                  list(upper) + ([(count + c, count + b, count + a) for a, b, c in triangles] if under else []))
    verts = [(u, v, high) for u, v in inset] + [(u, v, high - bevel) for u, v in points] + [(u, v, low) for u, v in points]
    faces = []
    for loop in loops:
        for k in range(len(loop)):
            i, j = loop[k - 1], loop[k]
            if bevel:
                faces.append((count + i, count + j, j, i))
            faces.append((2 * count + i, 2 * count + j, count + j, count + i))
    return [flat, K.Part(verts, faces)]


def key_plate(K, low, high, cut=True, under=None):
    """The key of the latch. cut: with its bore and its two slots cut through it, and its edges rolled."""
    holes = []
    if cut:
        (cu, cv), radius = KEY_HOLE
        holes.append([(cu + radius * math.cos(-2 * math.pi * k / 18), cv + radius * math.sin(-2 * math.pi * k / 18)) for k in range(18)])
        (place, top, bottom), half = KEY_SLOTS
        for side in (-1, 1):
            slot = [(side * place + half * math.cos(math.pi * k / 6), top + half * math.sin(math.pi * k / 6)) for k in range(7)]
            slot += [(side * place - half * math.cos(math.pi * k / 6), bottom - half * math.sin(math.pi * k / 6)) for k in range(7)]
            holes.append(slot[::-1])
    return plate(K, key_outline(), holes, low, high, 0.00045 if cut else 0.0, cut if under is None else under)


def latch_parts(K, level):
    """A Hardigg butterfly latch in its seam frame (u along the seam, v to the lid, n out): (part, material, role, smoothing).
    Lid: the strike, a plate with shoulders, two eyelet rivets and its lower edge rolled into a lip.
    Base: a link that hangs in that lip from the housing at the seam; in the housing the drum with its bright pin;
    hinged on the drum the key, which lies flat over the bracket, spring and studs when the latch is shut."""
    if level == 3:
        return [(K.box((-0.0127, 0.0125, 0.0045), (0.0127, 0.0477, 0.0061), omit=("-z",)), "blackmetal", "lid", 35.0),
                (K.box((-0.0125, -0.040, 0.0030), (0.0125, -0.005, 0.0114)), "blackmetal", "swing", 35.0)]
    fine = level == 1
    (du, dv), radius = DRUM
    sheet = lambda parts, role: [(parts[0], "blackmetal", role, 20.0), (parts[1], "blackmetal", role, 60.0)]
    out = sheet(plate(K, STRIKE, [], 0.0045, 0.0061, 0.0004 if fine else 0.0, False), "lid") + [
           (K.cyl((-0.0157, 0.0146, 0.0072), (0.0157, 0.0146, 0.0072), 0.0022, 10 if fine else 5), "blackmetal", "lid", 60.0),
           (K.box((-0.010, -0.032, -0.0003), (0.010, 0.0000, 0.0020), omit=("-z",)), "blackmetal", "base", 35.0),
           (K.box((-0.005, -0.036, 0.0020), (0.005, -0.030, 0.0030)), "blackmetal", "swing", 35.0),
           (K.box((-0.0097, 0.0075, 0.0052), (0.0097, 0.0175, 0.0066)), "blackmetal", "body", 35.0),                    # link
           ((K.rbox((-0.0115, -0.0055, 0.0030), (0.0115, 0.0083, 0.0095), 0.0012, 2) if fine else
             K.box((-0.0115, -0.0055, 0.0030), (0.0115, 0.0083, 0.0095))), "blackmetal", "body", 60.0),                 # housing
           (K.box((-0.0100, -0.0400, 0.0030), (0.0100, -0.0055, 0.0052)), "blackmetal", "body", 35.0),                  # back
           (K.revolve(K.round_profile(radius, 0.0068, 0.0022, 2 if fine else 1), (du, dv, 0.0052), (0, 0, 1), 16 if fine else 8),
            "blackmetal", "turn", 60.0),
           ] + sheet(key_plate(K, 0.0098, 0.0114, fine, True), "wing")
    if fine:
        out.append((K.dome((du, dv - 0.0027, 0.0120), 0.0031, 0.0011, 18), "alu", "turn", 60.0))        # the bright pin
        out.append((K.cyl((-0.0045, -0.0262, 0.0068), (0.0045, -0.0262, 0.0068), 0.0017, 8), "alu", "body", 60.0))   # spring
        for side in (-1, 1):
            out.append((K.dome((side * 0.0070, 0.0337, 0.0061), 0.0027, 0.0005, 10), "blackmetal", "lid", 60.0))
            a, b = sorted((side * 0.0118, side * 0.0144))
            out.append((K.box((a, -0.0290, 0.0052), (b, -0.0225, 0.0078)), "blackmetal", "body", 35.0))   # studs
    return out


def rig(lod):
    """Memory points of the latches: the source hinges key and drum 22 mm under the seam. They go to the real drum."""
    if lod["faces"]:
        return lod
    moved = set()
    for name, points in lod["sels"].items():
        if name.startswith("latch") and name[5:].split("_", 1)[0].isdigit():
            moved |= set(points)
    lod["verts"] = [(x, y + HINGE_UP, z) if i in moved else (x, y, z) for i, (x, y, z) in enumerate(lod["verts"])]
    return lod


GRIP = (-0.056, 0.0090, 0.0085)                             # grip bar: place along the arm, height, radius
ARM = ((0.040, -0.056), (0.060, -0.056), (0.060, -0.006), (0.056, 0.004), (0.046, 0.004), (0.046, -0.012), (0.040, -0.022))


def arm_top(v):
    """An arm is as thick as the grip where it meets it and tapers to the hinge."""
    return 0.0110 + 0.0065 * min(1.0, max(0.0, (0.004 - v) / 0.050))


def handle_parts(K, level, floor):
    """A Hardigg spring handle in its frame, lying in its pocket: (part, smoothing angle). The bracket is a
    label block between two taller lugs with a bolt ear outside each; the bail has two arms that taper from a
    round grip bar to the hinge under the lugs."""
    steps = {1: 3, 2: 2, 3: 2}[level]
    block = (lambda lo, hi: K.rbox(lo, hi, 0.003, steps)) if level < 3 else (lambda lo, hi: K.box(lo, hi, omit=("-z",)))
    out = [(block((-0.034, 0.010, floor - 0.0005), (0.034, 0.044, floor + 0.0130)), 60.0)]
    for side in (-1, 1):
        a, b = sorted((side * 0.033, side * 0.050))
        out.append((block((a, 0.003, floor - 0.0005), (b, 0.046, floor + 0.0160)), 60.0))
        if level < 3:
            a, b = sorted((side * 0.049, side * 0.060))
            out.append((K.box((a, 0.030, floor - 0.0005), (b, 0.046, floor + 0.0050), omit=("-z",)), 35.0))
        outline = [(side * u, v) for u, v in ARM]
        count = len(outline)
        points = [(u, v, floor + arm_top(v)) for u, v in outline] + [(u, v, floor + 0.0005) for u, v in outline]
        faces = [(1, k, k + 1) for k in range(2, count - 1)] + [(1, count - 1, 0)]
        faces += [(count + k, count + (k + 1) % count, (k + 1) % count, k) for k in range(count)]
        arm = K.Part(points, faces)
        if side < 0:
            arm.flip()
        out.append((arm, 35.0))
    v, n, radius = GRIP
    out.append((K.cyl((-0.060, v, floor + n), (0.060, v, floor + n), radius, {1: 14, 2: 8, 3: 6}[level]), 60.0))
    return out


def _stem(face):
    return face["mat"].rsplit("\\", 1)[-1].rsplit(".", 1)[0].lower()


def _append(lod, mesh, K, materials):
    """Append a kit mesh to a visual LOD and keep one run of faces for each material."""
    verts, normals, faces, sharp = K.bake(mesh)
    v0, n0 = len(lod["verts"]), len(lod["normals"])
    out = {**lod, "verts": list(lod["verts"]) + [tuple(map(float, p)) for p in verts],
           "normals": list(lod["normals"]) + normals, "faces": list(lod["faces"]),
           "sharp": list(lod["sharp"]) + [(a + v0, b + v0) for a, b in sharp],
           "sels": {name: set(points) for name, points in lod["sels"].items()}}
    if lod.get("mass") is not None:
        out["mass"] = list(lod["mass"]) + [0.0] * len(verts)
    for f in faces:
        tex, mat = materials[f["mat"]]
        ids = [v0 + i for i in f["v"]]
        out["faces"].append(dict(v=ids, n=[n0 + i for i in f["n"]], uv=f["uv"], tex=PREFIX + tex, mat=PREFIX + mat))
        for name in ((f["bone"],) if f["bone"] else ()) + tuple(f["sel"]):
            out["sels"].setdefault(name, set()).update(ids)
    return _runs(out)


def _runs(lod):
    order = {}
    for f in lod["faces"]:
        order.setdefault((f["tex"].lower(), f["mat"].lower()), len(order))
    lod["faces"].sort(key=lambda f: order[(f["tex"].lower(), f["mat"].lower())])
    return lod


def fit(lod, geo, K, offset=(0.0, 0.0, 0.0), base=True, record=False):
    """Move the fittings of a visual LOD on to the fittings atlas. offset: model origin in chest coordinates.
    base: the LOD holds the base half, so the handles get their backing plates. record: keep the relief."""
    level = int(round(lod["res"]))
    found = instances(geo)
    if base:
        # The handles of the source are a flat frame. They are taken out and built to the real part.
        from build_medical_chest_inserts import _drop
        handles = [i for i in found if i["cls"] == "handle"]
        before = np.asarray(lod["verts"], float) + np.asarray(offset, float)
        latches = found[:10]
        lid = bool(lod["sels"].get("lid"))

        def old(face):
            centre = before[face["v"]].mean(axis=0)[None]
            if _stem(face) == "blackplastic":
                return any(_claims(i, _local(i["frame"], centre)[0]) for i in handles)
            if _stem(face) in ("blackmetal", "alu"):
                for i in latches:
                    u, v, n = _local(i["frame"], centre)[0]
                    if OLD_LATCH[0] <= u <= OLD_LATCH[2] and OLD_LATCH[1] <= v <= OLD_LATCH[3] and -0.004 <= n <= 0.016:
                        return True
            return False

        lod = _drop(lod, old)
        mesh = K.Mesh()
        for number, inst in enumerate(latches, 1):           # the latches of the source are not the real part either
            for part, mat, role, smooth in latch_parts(K, level):
                if role == "lid" and not lid:
                    continue
                bone = "lid" if role == "lid" else "" if role == "base" else "latch%d_%s" % (number, "swing" if level == 3 else role)
                part.place(*inst["frame"])
                mesh.add(part, mat, bone, smooth=smooth)
        for inst in handles:
            for part, smooth in handle_parts(K, level, inst["floor"]):
                part.place(*inst["frame"])
                mesh.add(part, "blackplastic", "", smooth=smooth)
            if level < 3:
                u0, v0, u1, v1 = PLATE
                plate = K.box((u0, v0, inst["floor"] - 0.0004), (u1, v1, inst["floor"] + 0.0016), omit=("-z",))
                plate.place(*inst["frame"])
                mesh.add(plate, "blackmetal", "", smooth=35.0)
        lod = _append(lod, mesh, K, {"blackmetal": ("black_co.paa", "blackmetal.rvmat"), "alu": ("alu_co.paa", "alu.rvmat"),
                                     "blackplastic": ("black_co.paa", "blackplastic.rvmat")})
    verts = np.asarray(lod["verts"], float) + np.asarray(offset, float)
    relief, first = {}, {}
    inner = set().union(*(points for name, points in lod["sels"].items()
                          if name.startswith(("drawer", "insert", "padlock"))))
    for face in lod["faces"]:
        stem = _stem(face)
        if stem not in IDS:
            continue
        points = verts[face["v"]]
        centre = points.mean(axis=0)
        for inst in found:
            if stem in MADE_OF[inst["cls"]] and _claims(inst, _local(inst["frame"], centre[None])[0]):
                break
        else:
            if stem == "blackmetal" and not all(i in inner for i in face["v"]):      # hasps stay as they are
                raise ValueError("A latch face at %s is outside every latch frame" % np.round(centre, 3))
            continue
        local = _local(inst["frame"], points)
        world = np.cross(points[1] - points[0], points[2] - points[0])
        length = np.linalg.norm(world)
        normal = _local((np.zeros(3),) + tuple(inst["frame"][1:]), (world / length if length else world)[None])[0]
        if np.dot(np.cross(inst["frame"][1], inst["frame"][2]), inst["frame"][3]) < 0:
            local, normal = local * (-1, 1, 1), normal * (-1, 1, 1)      # lettering reads the same on every side
        if inst["cls"] == "latch" and stem == "blackmetal" and normal[2] < 0.3:
            x, y, w, h = PLAIN
            face["uv"] = [((x + PAD + min(max(u / PLAIN_SPAN + 0.5, 0), 1) * (w - 2 * PAD)) / ATLAS,
                           1 - (y + PAD + min(max(v / PLAIN_SPAN + 0.5, 0), 1) * (h - 2 * PAD)) / ATLAS)
                          for u, v in (local[:, :2] + local[:, 2:3] * (0.5, 0.5))]
        elif inst["cls"] == "handle" and abs(normal[0]) > 0.8 and abs(local[:, 0].mean()) > 0.036:
            # the flanks of the arms and lugs have their own picture: the webbing, the bore of the grip
            face["uv"] = tile_uv("handle_side", "handle_side", np.stack([local[:, 1], local[:, 2] - inst["floor"]], 1))
        else:
            face["uv"] = plan_uv(inst, local, normal)
        face["tex"], face["mat"] = PREFIX + TEXTURE, PREFIX + MATERIAL
        if record and first.setdefault(inst["cls"], inst) is inst and not (
                inst["cls"] == "latch" and normal[2] < -0.3):               # one copy of each fitting; no undersides
            tris, ids = relief.setdefault(inst["cls"], ([], []))
            for k in range(1, len(local) - 1):
                tris.append(local[[0, k, k + 1]])
                ids.append(IDS[stem])
    if record:
        RELIEF.parent.mkdir(exist_ok=True)
        np.savez_compressed(RELIEF, **{name + "_tris": np.asarray(value[0], np.float32) for name, value in relief.items()},
                            **{name + "_ids": np.asarray(value[1], np.uint8) for name, value in relief.items()})
    return _runs(lod)


def weather(lod, geo, index, offset=(0.0, 0.0, 0.0)):
    """The few rusty latches of a finish (RUSTY): their faces move from a clean tile to the rusty one."""
    picks = RUSTY.get(index, ())
    if not picks:
        return lod
    found = instances(geo)
    verts = np.asarray(lod["verts"], float) + np.asarray(offset, float)
    for face in lod["faces"]:
        if not face["tex"].lower().endswith(TEXTURE):
            continue
        centre = verts[face["v"]].mean(axis=0)
        for inst in (found[i] for i in picks):
            x, y, w, h = TILES[inst["tile"]]
            if _claims(inst, _local(inst["frame"], centre[None])[0]) and face["uv"][0][0] * ATLAS < x + w:
                shift = (TILES["latch_2"][0] - x) / ATLAS
                face["uv"] = [(u + shift, v) for u, v in face["uv"]]
                break
    return lod


def bolted(lod, geo, K):
    """Bolt ends and washers on the inside of the walls, behind every handle and latch (open cabinet, LOD 1)."""
    mesh = K.Mesh()
    ring = [(math.cos(math.radians(22.5 + 45 * k)), math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    for inst in instances(geo):
        if inst["cls"] not in ("handle", "latch"):
            continue
        origin, across, along, normal = (np.array(a, float) for a in inst["frame"])
        spots, radius = (PLATE_RIVETS, 0.0080) if inst["cls"] == "handle" else (LATCH_RIVETS, 0.0055)
        wall = geo.IX if normal[0] else (geo.IZ1 if normal[2] > 0 else -geo.IZ0)
        for u, v in spots:
            centre = origin + u * across + v * along
            centre += ((wall - 0.0008) - centre @ normal) * normal          # on the inner face of that wall
            points = [tuple(centre + radius * (a * across + b * along)) for a, b in ring]
            part = K.Part(points, [tuple(range(8))[::-1]])
            if np.dot(np.cross(across, along), normal) < 0:
                part.flip()
            for face in [(0, k, k + 1) for k in range(1, 7)]:
                order = [part.f[0][i] for i in face]
                uv = tile_uv("bolt", "bolt", [(0.0088 * ring[i][0], 0.0088 * ring[i][1]) for i in order])
                mesh.add(K.Part([part.v[i] for i in order], [(0, 1, 2)], [uv]), "fittings", "", uv="explicit")
    return _append(lod, mesh, K, {"fittings": (TEXTURE, MATERIAL)})


# ---------------------------------------------------------------- texture side

def raster(tris, ids, cls, size, scale=3):
    """Height (metres) and material of the topmost surface in a tile, with the part of each texel that is covered."""
    u0, v0, u1, v1 = CLASSES[cls]["box"]
    w, h = size
    W, H = w * scale, h * scale
    height = np.full((H, W), -np.inf, np.float32)
    what = np.zeros((H, W), np.uint8)
    px = (PAD + (tris[:, :, 0] - u0) / (u1 - u0) * (w - 2 * PAD)) * scale
    py = (PAD + (v1 - tris[:, :, 1]) / (v1 - v0) * (h - 2 * PAD)) * scale
    for x, y, z, kind in zip(px, py, tris[:, :, 2], ids):
        area = (x[1] - x[0]) * (y[2] - y[0]) - (x[2] - x[0]) * (y[1] - y[0])
        if abs(area) < 1e-6:
            continue
        xa, xb = max(int(math.floor(x.min())), 0), min(int(math.ceil(x.max())) + 1, W)
        ya, yb = max(int(math.floor(y.min())), 0), min(int(math.ceil(y.max())) + 1, H)
        if xa >= xb or ya >= yb:
            continue
        gx, gy = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
        b1 = ((gx - x[0]) * (y[2] - y[0]) - (x[2] - x[0]) * (gy - y[0])) / area
        b2 = ((x[1] - x[0]) * (gy - y[0]) - (gx - x[0]) * (y[1] - y[0])) / area
        b0 = 1 - b1 - b2
        inside = (b0 >= -1e-4) & (b1 >= -1e-4) & (b2 >= -1e-4)
        level = (b0 * z[0] + b1 * z[1] + b2 * z[2]).astype(np.float32)
        view = height[ya:yb, xa:xb]
        better = inside & (level > view)
        view[better] = level[better]
        what[ya:yb, xa:xb][better] = kind
    covered = np.isfinite(height)
    blocks = lambda a: a.reshape(h, scale, w, scale)
    cover = blocks(covered.astype(np.float32)).mean(axis=(1, 3))
    total = blocks(np.where(covered, height, 0)).sum(axis=(1, 3))
    mean = np.where(cover > 0, total / np.maximum(cover * scale * scale, 1), 0).astype(np.float32)
    top = blocks(np.where(covered, height, -1.0)).transpose(0, 2, 1, 3).reshape(h, w, -1).argmax(-1)
    kinds = np.take_along_axis(blocks(what).transpose(0, 2, 1, 3).reshape(h, w, -1), top[..., None], -1)[..., 0]
    return mean, kinds, cover


def lettering(shape, cls):
    """What is moulded into the hinge block of a handle: (raised letters, sunk panel), 0..1 in the plan of the tile."""
    u0, v0, u1, v1 = CLASSES[cls]["box"]
    h, w = shape
    to_x = lambda u: PAD + (u - u0) / (u1 - u0) * (w - 2 * PAD)
    to_y = lambda v: PAD + (v1 - v) / (v1 - v0) * (h - 2 * PAD)
    left, right, top, bottom = to_x(-0.0315), to_x(0.0315), to_y(0.0432), to_y(0.0138)
    panel = Image.new("L", (w, h), 0)
    ImageDraw.Draw(panel).rounded_rectangle((left, top, right, bottom), radius=(bottom - top) * 0.16, fill=255)
    text = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(text)
    span = bottom - top

    def font(names, size):
        for name in names:
            try:
                return ImageFont.truetype(name, max(6, round(size)))
            except OSError:
                continue
        return ImageFont.load_default()

    slanted, upright = ("arialbi.ttf", "DejaVuSans-BoldOblique.ttf"), ("arialbd.ttf", "DejaVuSans-Bold.ttf")
    middle = (left + right) / 2
    # the maker's mark: an H in a slanted frame, and the name beside it
    x, y, mark = left + span * 0.16, top + span * 0.07, span * 0.36
    lean = mark * 0.30
    draw.polygon([(x + lean, y), (x + mark * 1.5 + lean, y), (x + mark * 1.5, y + mark), (x, y + mark)], outline=255, width=2)
    draw.text((x + mark * 0.75 + lean / 2, y + mark / 2), "H", font=font(slanted, mark * 0.95), fill=255, anchor="mm")
    draw.text((x + mark * 1.75 + lean, y + mark * 0.26), "HARDIGG", font=font(slanted, span * 0.185), fill=255, anchor="lm")
    draw.text((x + mark * 1.95 + lean, y + mark * 0.78), "CASES", font=font(slanted, span * 0.185), fill=255, anchor="lm")
    small = font(upright, span * 0.118)
    for place, words in ((0.515, "SOUTH DEERFIELD, MA"), (0.635, "USA 01373"), (0.755, "US PAT. 5461755, D362805")):
        draw.text((middle, top + span * place), words, font=small, fill=255, anchor="mm")
    draw.text((middle, top + span * 0.895), "HAND LIFT ONLY", font=font(upright, span * 0.150), fill=255, anchor="mm")
    return np.asarray(text, np.float32) / 255.0, np.asarray(panel, np.float32) / 255.0


def spread(values, known, rounds=24):
    """Carry the known texels out into the unknown ones, so that nothing bleeds in from an empty tile."""
    values = np.where(known[..., None] if values.ndim == 3 else known, values, 0).astype(np.float32)
    weight = known.astype(np.float32)
    for _ in range(rounds):
        near = blur(weight, 2.0)
        if values.ndim == 3:
            grown = np.stack([blur(values[..., c] * weight, 2.0) for c in range(values.shape[-1])], -1)
            grown /= np.maximum(near, 1e-6)[..., None]
            values = np.where((weight > 0)[..., None], values, grown)
        else:
            values = np.where(weight > 0, values, blur(values * weight, 2.0) / np.maximum(near, 1e-6))
        weight = np.maximum(weight, (near > 0.02).astype(np.float32))
    return values


def disc(shape, ppm, cls, centre, radius, soft=0.6):
    """1 inside a circle in the plan of a tile, with a soft edge of that many texels."""
    u0, v0, u1, v1 = CLASSES[cls]["box"]
    h, w = shape
    x = PAD + (centre[0] - u0) / (u1 - u0) * (w - 2 * PAD)
    y = PAD + (v1 - centre[1]) / (v1 - v0) * (h - 2 * PAD)
    gy, gx = np.mgrid[0:h, 0:w]
    distance = np.hypot(gx + 0.5 - x, gy + 0.5 - y) / ppm
    return np.clip((radius - distance) * ppm / soft + 0.5, 0, 1).astype(np.float32), distance.astype(np.float32)


def plan_grid(shape, cls):
    u0, v0, u1, v1 = CLASSES[cls]["box"]
    h, w = shape
    gy, gx = np.mgrid[0:h, 0:w]
    return (u0 + (gx + 0.5 - PAD) / (w - 2 * PAD) * (u1 - u0)).astype(np.float32), \
           (v1 - (gy + 0.5 - PAD) / (h - 2 * PAD) * (v1 - v0)).astype(np.float32)


def scratches(rng, shape, count, length, tone=(70, 255)):
    canvas = Image.new("L", (shape[1] * 2, shape[0] * 2), 0)
    draw = ImageDraw.Draw(canvas)
    for _ in range(count):
        x, y = rng.uniform(0, shape[1] * 2), rng.uniform(0, shape[0] * 2)
        a, s = rng.uniform(0, math.pi), float(np.exp(rng.normal(math.log(length), 0.8)))
        bow = rng.normal(0, 0.12)
        dx, dy = math.cos(a) * s, math.sin(a) * s
        draw.line([(x - dx, y - dy), (x - dy * bow, y + dx * bow), (x + dx, y + dy)],
                  fill=int(rng.uniform(*tone)), width=int(rng.choice((1, 1, 2))))
    return np.asarray(canvas.resize((shape[1], shape[0]), Image.Resampling.BOX), np.float32) / 255.0


COAT = np.array([27.0, 28.0, 30.0]) / 255                    # black coated steel
SATIN = np.array([30.0, 31.0, 33.0]) / 255                   # the black finish of the latches: satin, not paint
BARE = np.array([132.0, 130.0, 126.0]) / 255                 # the steel under it, rubbed bright
RUST_DEEP, RUST_BRIGHT = np.array([54.0, 30.0, 19.0]) / 255, np.array([132.0, 73.0, 36.0]) / 255
RUST_STAIN = np.array([88.0, 52.0, 30.0]) / 255
NYLON = np.array([25.0, 25.0, 26.0]) / 255                   # glass filled nylon of the handles
NYLON_WORN = np.array([82.0, 82.0, 78.0]) / 255
RUBBER = np.array([30.0, 29.0, 28.0]) / 255
PLATING = np.array([172.0, 174.0, 172.0]) / 255              # zinc plated rivets and bolts
PLATING_DULL = np.array([118.0, 116.0, 108.0]) / 255
DUST = np.array([148.0, 138.0, 116.0]) / 255
GRIME = np.array([40.0, 36.0, 30.0]) / 255


def mix(a, b, t):
    return a + (b - a) * t[..., None]


def paint_tile(name, cls, size, source, seed):
    """One tile: colour, micro height (metres), specular, gloss, ambient shadow and the covered texels."""
    rng = np.random.default_rng(seed)
    w, h = size
    shape = (h, w)
    u0, v0, u1, v1 = CLASSES[cls]["box"]
    ppm = (w - 2 * PAD) / (u1 - u0)
    U, V = plan_grid(shape, cls)
    radial = np.hypot(U, V)
    if cls == "bolt":
        height, kinds, cover = bolt_relief(shape, radial, U, V)
    elif cls == "handle_side":
        height, kinds, cover = side_relief(shape, cls)
    else:
        height, kinds, cover = raster(source[cls + "_tris"], source[cls + "_ids"], cls, size)
    known = cover > 0.5
    floor = float(height[known].min()) - 0.004
    solid = np.where(cover > 0, height * cover + floor * (1 - cover), floor).astype(np.float32)
    fine = solid - blur(solid, 0.0006 * ppm)
    edge = np.clip(fine / 0.0005, 0, 1) ** 0.8
    nook = np.clip(-fine / 0.0005, 0, 1) * known
    hollow = np.clip((blur(solid, 0.0026 * ppm) - solid) / 0.0020, 0, 1) * known
    mm = ppm / 1000                                          # texels in a millimetre
    blotch, patch, grain = (band_noise(rng, 4 * mm, 22 * mm, shape), band_noise(rng, 0.9 * mm, 4.5 * mm, shape),
                            band_noise(rng, max(1.6, 0.16 * mm), max(5.0, 0.5 * mm), shape))
    broad = np.clip((solid - blur(solid, 0.003 * ppm)) / 0.0012, 0, 1) * known     # crowns of round shapes
    micro = np.zeros(shape, np.float32)                      # height the mesh does not have, for the normal map
    extra_kind = kinds.copy()

    # ---- details that exist only in the texture
    if cls == "handle":
        for spot in PLATE_RIVETS:
            head, distance = disc(shape, ppm, cls, spot, 0.0042)
            micro += head * 0.0011 * np.sqrt(np.clip(1 - (distance / 0.0042) ** 2, 0, 1))
            extra_kind = np.where((head > 0.5) & (kinds == STEEL), ZINC, extra_kind)
            ring = np.clip(1 - np.abs(distance - 0.0047) / 0.0007, 0, 1) * (kinds == STEEL)
            nook = np.maximum(nook, ring * 0.9)
            hollow = np.maximum(hollow, np.clip(1 - np.abs(distance - 0.0052) / 0.0022, 0, 1) * (kinds == STEEL) * 0.6)
        letters, panel = lettering(shape, cls)
        letters, panel = letters * (kinds == PLASTIC), panel * (kinds == PLASTIC)
        micro += 0.00042 * blur(letters, 0.6) - 0.00028 * blur(panel, 1.0)             # raised in a sunk panel
        hollow = np.maximum(hollow, np.clip(panel - letters, 0, 1) * 0.30)
        grip = (np.abs(U) < 0.050) & (kinds == PLASTIC)
        micro += 0.00012 * np.exp(-((V + 0.056) / 0.00035) ** 2) * grip          # parting line of the mould
        for spot in ((-0.0415, 0.036), (0.0415, 0.036)):                          # ejector pin marks on the lugs
            pin, distance = disc(shape, ppm, cls, spot, 0.0025)
            micro -= 0.00008 * pin * (kinds == PLASTIC)
    cut = np.zeros(shape, np.float32)
    if cls == "latch":
        cut, _ = disc(shape, ppm, cls, *KEY_HOLE)
        (place, top, low), half = KEY_SLOTS
        along = np.clip(V, low, top)
        for side in (-1, 1):
            reach = np.hypot(U - side * place, V - along)
            cut = np.maximum(cut, np.clip((half - reach) * ppm + 0.5, 0, 1))
        cut = cut * (kinds == STEEL)
        micro -= 0.0012 * blur(cut, 0.8)
        u0, v0, u1, v1 = CLASSES[cls]["box"]
        to_x = lambda u: PAD + (u - u0) / (u1 - u0) * (w - 2 * PAD)
        to_y = lambda v: PAD + (v1 - v) / (v1 - v0) * (h - 2 * PAD)
        mm_v = 0.001 * (h - 2 * PAD) / (v1 - v0)
        marks = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(marks)

        def face(size):
            try:
                return ImageFont.truetype("arialbd.ttf", max(8, round(size * mm_v)))
            except OSError:
                return ImageFont.load_default()

        draw.text((to_x(STRIKE_NAME[0]), to_y(STRIKE_NAME[1])), "HARDIGG", font=face(2.9), fill=255, anchor="mm")   # raised
        raised = np.asarray(marks, np.float32) / 255.0 * (kinds == STEEL)
        micro += 0.00010 * blur(raised, 0.7)
        for spot in STRIKE_RIVETS:                           # eyelet rivets: a raised ring round a hole
            ring, distance = disc(shape, ppm, cls, spot, 0.0027)
            bore, _ = disc(shape, ppm, cls, spot, 0.0011)
            micro += 0.00025 * ring * np.clip((distance - 0.0011) / 0.0010, 0, 1) - 0.0006 * bore
            cut = np.maximum(cut, bore * 0.8)
            nook = np.maximum(nook, np.clip(1 - np.abs(distance - 0.0030) / 0.0006, 0, 1) * 0.5)
        dimple, _ = disc(shape, ppm, cls, STRIKE_DIMPLE, 0.0012)
        micro -= 0.0003 * dimple
        coil = (np.abs(V + 0.0262) < 0.0019) & (np.abs(U) < 0.0046) & (kinds == ZINC)       # the spring behind the bore
        micro += 0.00035 * np.sin(U * 2 * math.pi / 0.0011) * coil
        stamp = Image.new("L", (w, h), 0)
        ImageDraw.Draw(stamp).text((to_x(0.0), to_y(-0.0371)), "S/S", font=face(1.9), fill=255, anchor="mm")
        stamped = np.asarray(stamp, np.float32) / 255.0 * (kinds == STEEL)
        micro -= 0.00010 * stamped
        nook = np.maximum(nook, stamped * 0.4)
    if cls == "wheel":
        for groove in (0.0185, 0.0290):
            micro -= 0.00035 * np.exp(-((radial - groove) / 0.0007) ** 2) * (kinds == PLASTIC)
            hollow = np.maximum(hollow, np.exp(-((radial - groove) / 0.0010) ** 2) * (kinds == PLASTIC) * 0.7)
        micro += 0.00003 * np.sin(radial * 2 * math.pi / 0.0011) * (kinds == PLASTIC) * (radial < 0.030)
    if cls == "valve":
        slot = (np.abs(V) < 0.0007) & (np.abs(U) < 0.0036) & (kinds == ZINC)
        micro -= 0.0006 * blur(slot.astype(np.float32), 0.7)
        nook = np.maximum(nook, blur(slot.astype(np.float32), 0.7))
        for groove in (0.0085,):
            micro -= 0.0003 * np.exp(-((radial - groove) / 0.0005) ** 2) * (kinds == PLASTIC)
    kinds = extra_kind

    # ---- black coated steel: bare on the edges, rust from every breach and every wet corner
    amount = 0.66 if name == "latch_2" else 0.0             # one tile of the atlas is rusty, see RUSTY
    lines = scratches(rng, shape, int(260 * w * h / 524288), 0.006 * ppm)
    rim = np.clip(blur(edge, 0.0008 * ppm) * 2.2, 0, 1)
    worn = smoothstep(0.80, 1.0, edge * 1.1 + 0.30 * lines) * (0.22 if cls == "latch" else 0.7)   # edges rub through a little
    breach = (0.52 + 0.32 * amount) * rim + 0.60 * hollow + 0.45 * nook + 0.50 * blotch + 0.20 * patch + 0.04 * grain
    start = 1.30 - 0.95 * amount
    rust = smoothstep(start, start + 0.38, breach) * (amount > 0)
    near = np.clip(blur(rust, 0.0015 * ppm) * 1.6, 0, 1)
    rust = np.maximum(rust, 0.8 * smoothstep(1.1, 1.7, grain + 0.6 * patch) * smoothstep(0.12, 0.6, near))   # freckles round a patch
    stain = np.clip(blur(rust, 0.0013 * ppm) * 1.5, 0, 1) * (1 - rust)
    steel = (SATIN if cls == "latch" else COAT) * (1 + 0.02 * blotch[..., None] + 0.02 * grain[..., None])
    steel = mix(steel, BARE, worn * 0.85)
    steel = mix(steel, RUST_STAIN, stain * 0.62)
    steel = mix(steel, mix(RUST_DEEP, RUST_BRIGHT, smoothstep(-0.9, 1.9, 0.8 * patch + 0.45 * grain + 0.3 * blotch)), rust)
    steel = mix(steel, np.array([0.020, 0.020, 0.022]), cut * 0.88)     # what one sees through them lies in the dark
    steel_spec = (0.30 + 0.48 * worn * (1 - rust) - 0.24 * rust - 0.10 * stain) * (1 - 0.9 * cut)
    steel_gloss = 0.46 + 0.20 * worn * (1 - rust) - 0.36 * rust - 0.14 * stain
    if cls == "latch":                                       # satin: it takes a soft, wide highlight
        steel_spec = steel_spec + 0.10 * (1 - rust) * (1 - cut)
        steel_gloss = steel_gloss + 0.06 * (1 - rust)
    steel_micro = rust * (0.000016 * grain + 0.00003 * patch) - 0.00002 * lines * (1 - rust)

    # ---- moulded plastic and rubber: greys where it is rubbed, shines where hands hold it
    body = RUBBER if cls in ("wheel", "foot") else NYLON
    chips = smoothstep(0.55, 0.9, edge) * smoothstep(1.15, 1.7, band_noise(rng, 2.5 * mm, 9 * mm, shape))
    chips = np.maximum(chips, smoothstep(0.35, 0.8, blur(edge, 0.0012 * ppm) * 2.4)          # a corner takes more
                       * smoothstep(1.5, 2.1, band_noise(rng, 4 * mm, 14 * mm, shape)))
    rubbed = smoothstep(0.80, 1.0, edge) * 0.35 + 0.30 * lines
    plastic = body * (1 + 0.015 * blotch[..., None] + 0.02 * grain[..., None])
    plastic = mix(plastic, NYLON_WORN, np.clip(rubbed, 0, 1) * 0.45)
    plastic = mix(plastic, NYLON_WORN * 0.9, chips * 0.6)
    if cls == "handle":
        plastic = mix(plastic, NYLON_WORN, letters * 0.34)                             # the tops of the letters are rubbed
    held = np.zeros(shape, np.float32)
    if cls == "handle":
        held = smoothstep(0.050, 0.020, np.abs(U)) * smoothstep(-0.040, -0.050, V) * smoothstep(-0.070, -0.062, V)
    plastic_spec = 0.17 + 0.10 * held - 0.06 * rubbed - 0.08 * chips
    plastic_gloss = 0.38 + 0.28 * held - 0.14 * rubbed - 0.2 * chips
    plastic_micro = 0.000012 * grain * (1 - 0.7 * held) - 0.00002 * lines - 0.00028 * blur(chips, 0.8)
    if cls == "wheel":                                       # the tread carries the ground it rolled on
        tread = smoothstep(0.026, 0.033, radial)
        plastic = mix(plastic, mix(GRIME, DUST, 0.42 + 0.12 * np.clip(patch + 0.6 * blotch, -1.5, 1.5)), tread * 0.66)
        plastic_spec -= 0.08 * tread
        plastic_gloss -= 0.18 * tread
        plastic_micro += 0.00005 * patch * tread
    if cls == "foot":
        plastic = mix(plastic, DUST, np.clip(0.30 + 0.20 * blotch, 0, 1))

    # ---- zinc plated heads
    tarnish = smoothstep(-0.6, 1.6, blotch + 0.3 * patch)
    plating = np.array([172.0, 150, 84]) / 255 if cls == "bolt" else PLATING     # bolts and washers are yellow zinc
    zinc = mix(plating * (1 + 0.03 * grain[..., None]), PLATING_DULL * (0.9 if cls == "bolt" else 1.0), tarnish * 0.6)
    spot = smoothstep(1.9 - 0.8 * amount, 2.3 - 0.8 * amount, 0.9 * patch + 0.3 * grain + 1.2 * nook)
    spot = spot * (amount > 0)
    zinc = mix(zinc, RUST_BRIGHT * 0.8, spot * 0.8)
    zinc_spec, zinc_gloss = 0.66 - 0.2 * tarnish - 0.3 * spot, 0.60 - 0.16 * tarnish - 0.3 * spot

    def pick(a, b, c):
        if a.ndim == 3:
            return np.where((kinds == STEEL)[..., None], a, np.where((kinds == PLASTIC)[..., None], b, c))
        return np.where(kinds == STEEL, a, np.where(kinds == PLASTIC, b, c))

    colour = pick(steel, plastic, zinc)
    spec = pick(steel_spec, plastic_spec, np.broadcast_to(zinc_spec, shape))
    gloss = pick(steel_gloss, plastic_gloss, np.broadcast_to(zinc_gloss, shape))
    micro = micro + pick(steel_micro, plastic_micro, 0.000004 * grain)

    # ---- what settles on all of it: dust in the hollows, grime in the tight corners
    settled = np.clip(0.55 * hollow - 0.05, 0, 1) * (0.5 if cls != "bolt" else 0.3)
    colour = mix(colour, DUST, settled * 0.30)
    colour = mix(colour, GRIME, np.clip(nook * 0.75, 0, 1) * (0.2 if cls == "latch" else 0.6))
    spec = spec * (1 - 0.5 * settled) * (1 - 0.4 * nook)
    gloss = gloss * (1 - 0.45 * settled) * (1 - 0.3 * nook)
    shadow = 1 - np.clip(0.60 * hollow + 0.40 * nook, 0, 0.82)
    colour = colour * (0.80 + 0.20 * shadow)[..., None]
    return dict(colour=spread(np.clip(colour, 0, 1), known), micro=spread(micro, known), ppm=ppm,
                spec=spread(np.clip(spec, 0.02, 1), known), gloss=spread(np.clip(gloss, 0.03, 1), known),
                shadow=spread(shadow, known))


def side_relief(shape, cls):
    """The flank of a handle arm as a height field: a web of triangles between its flanges, the bore of the grip
    bar and the hinge pin. Along the tile runs the arm, up it the thickness."""
    u0, v0, u1, v1 = CLASSES[cls]["box"]
    h, w = shape
    at = lambda v, n: (PAD + (v - u0) / (u1 - u0) * (w - 2 * PAD), PAD + (v1 - n) / (v1 - v0) * (h - 2 * PAD))
    sunk = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(sunk)
    bays = np.linspace(-0.0445, 0.0005, 4)
    for a, b in zip(bays[:-1], bays[1:]):
        low, rim = 0.0022, 0.0020
        corners = [(a + 0.0008, low), (b - 0.0008, low), (b - 0.0008, arm_top(b) - rim), (a + 0.0008, arm_top(a) - rim)]
        middle = (sum(c[0] for c in corners) / 4, sum(c[1] for c in corners) / 4)
        for k in range(4):
            tri = (corners[k], corners[(k + 1) % 4], middle)
            cx, cy = sum(t[0] for t in tri) / 3, sum(t[1] for t in tri) / 3
            draw.polygon([at(cx + (t[0] - cx) * 0.70, cy + (t[1] - cy) * 0.70) for t in tri], fill=120)
    grip, height, radius = GRIP
    for (v, n), r, depth in (((grip, height), radius * 0.72, 255), ((0.0, 0.0058), 0.0022, 200)):
        x, y = at(v, n)
        rx, ry = r / (u1 - u0) * (w - 2 * PAD), r / (v1 - v0) * (h - 2 * PAD)
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=depth)
    depth = np.asarray(sunk.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255.0
    return (-0.006 * depth).astype(np.float32), np.full(shape, PLASTIC, np.uint8), np.ones(shape, np.float32)


def bolt_relief(shape, radial, U, V):
    """A washer, a hex nut and the end of the bolt, as a height field: the mesh is one flat disc."""
    washer = (radial < 0.0086).astype(np.float32) * 0.0012
    angle = np.arctan2(V, U)
    flats = radial * np.cos((angle + math.pi / 6) % (math.pi / 3) - math.pi / 6)
    nut = np.clip((0.0050 - flats) / 0.0003, 0, 1) * 0.0034 * np.clip((0.0064 - radial) / 0.0012, 0.72, 1)
    stud = np.clip((0.0029 - radial) / 0.0004, 0, 1) * 0.0012 * np.sqrt(np.clip(1 - (radial / 0.0036) ** 2, 0, 1))
    height = np.maximum(washer, 0.0012 + nut + stud).astype(np.float32)
    return height, np.full(shape, ZINC, np.uint8), (radial < 0.0100).astype(np.float32)


def paint(source):
    """The whole atlas: colour, normal map, specular map and ambient shadow, as float arrays 0..255."""
    colour = np.zeros((ATLAS, ATLAS, 3), np.float32)
    colour[:] = COAT * 255
    normal = np.zeros((ATLAS, ATLAS, 3), np.float32)
    normal[:] = (127.5, 127.5, 255)
    smdi = np.zeros((ATLAS, ATLAS, 3), np.float32)
    smdi[:] = (255, 60, 90)
    ambient = np.full((ATLAS, ATLAS, 3), 255, np.float32)
    for seed, (name, (x, y, w, h)) in enumerate(TILES.items()):
        cls = name.rsplit("_", 1)[0] if name[-1].isdigit() else name
        tile = paint_tile(name, cls, (w, h), source, 4100 + seed)
        colour[y:y + h, x:x + w] = tile["colour"] * 255
        relief = tile["micro"]
        if cls == "bolt":                                    # here the texture has to stand in for the shape
            U, V = plan_grid((h, w), cls)
            relief = relief + blur(bolt_relief((h, w), np.hypot(U, V), U, V)[0], 0.8) * 0.45
        if cls == "handle_side":
            relief = relief + blur(side_relief((h, w), cls)[0], 0.8) * 0.35
        normal[y:y + h, x:x + w] = normal_map(relief * tile["ppm"] / 2)
        smdi[y:y + h, x:x + w] = np.stack([np.ones((h, w)), tile["spec"], tile["gloss"]], -1) * 255
        ambient[y:y + h, x:x + w] = (tile["shadow"] * 255)[..., None]
        print("fitting tile", name, "%.2f mm per texel" % (1000 / tile["ppm"]))
        if name == "latch_0":
            flat = (tile["shadow"] > 0.97) & (np.abs(tile["colour"] - SATIN).max(axis=-1) < 0.03)
            steel = [float(np.median(tile[key][flat])) for key in ("spec", "gloss")]
    x, y, w, h = PLAIN
    rng = np.random.default_rng(4199)
    grain = blur(rng.normal(0, 1, (h, w)).astype(np.float32), 1.2) * 0.012
    colour[y:y + h, x:x + w] = (SATIN * (1 + grain[..., None])) * 255
    smdi[y:y + h, x:x + w] = np.stack([np.ones((h, w)), np.full((h, w), steel[0]) * (1 - 2 * np.abs(grain)),
                                       np.full((h, w), steel[1])], -1) * 255
    return dict(fittings_co=colour, fittings_nohq=normal, fittings_smdi=smdi, fittings_as=ambient)


def material(output, source, name, stages, specular, power, fresnel=None):
    """Write a material from one of the chest: stage number to texture, the specular terms, and the fresnel pair
    (N, K). The source materials have fresnel(1.3, 7), which is chrome: seen in the game on 2026-11-17, black
    latches turned silver at a slant, tape looked like foil and the laminated sheet shimmered."""
    import re
    text = (output / source).read_text()
    for stage, texture in stages.items():
        text, count = re.subn(r'(class Stage%d \{\s*texture = ")[^"]*(")' % stage,
                              lambda m: m.group(1) + PREFIX + texture + m.group(2), text)
        if count != 1:
            raise ValueError("%s has no stage %d" % (source, stage))
    text = re.sub(r"specular\[\] = \{[^}]*\};", "specular[] = {%g, %g, %g, 1};" % (specular, specular, specular), text)
    text = re.sub(r"specularPower = [0-9.]+;", "specularPower = %g;" % power, text)
    if fresnel:
        text, count = re.subn(r"fresnel\([^)]*\)", "fresnel(%g,%g)" % fresnel, text)
        if count != 1:
            raise ValueError("%s has no fresnel stage" % source)
    (output / name).write_text(text)


def rvmat(output):
    material(output, "blackmetal.rvmat", MATERIAL, {1: "fittings_nohq.paa", 4: "fittings_as.paa", 5: "fittings_smdi.paa"},
             0.5, 50, (2.0, 0.9))                            # satin black steel, not chrome
    material(output, "alu.rvmat", "alu.rvmat", {1: "alu_nohq.paa", 5: "alu_smdi.paa"}, 0.7, 90)
    material(output, "blackmetal.rvmat", "blackmetal.rvmat", {1: "black_nohq.paa", 5: "black_smdi.paa"}, 0.4, 45, (2.0, 0.9))
    material(output, "blackplastic.rvmat", "blackplastic.rvmat", {1: "black_nohq.paa", 5: "black_smdi.paa"}, 0.4, 45, (1.45, 0.35))


def _streaks(rng, size, along, across):
    """Noise drawn out along x, as a brush leaves it. Tiles. Mean 0, deviation 1."""
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.rfftfreq(size)[None, :]
    kernel = np.exp(-2 * (math.pi ** 2) * ((fx * along) ** 2 + (fy * across) ** 2)).astype(np.float32)
    out = np.fft.irfft2(np.fft.rfft2(rng.standard_normal((size, size), dtype=np.float32)) * kernel, s=(size, size))
    out -= out.mean()
    return (out / (out.std() + 1e-9)).astype(np.float32)


def _wrapped_lines(rng, size, count, length, level=(60, 230), lean=None):
    """Scratches that run off one edge of a tile and come back on the other."""
    canvas = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(canvas)
    for _ in range(count):
        x, y = rng.uniform(0, size, 2)
        angle = rng.uniform(0, math.pi) if lean is None else rng.normal(lean, 0.25)
        reach = float(np.exp(rng.normal(math.log(length), 0.7)))
        dx, dy, bow = math.cos(angle) * reach, math.sin(angle) * reach, rng.normal(0, 0.1)
        tone = int(rng.uniform(*level))
        for ox in (-size, 0, size):
            for oy in (-size, 0, size):
                draw.line([(x - dx + ox, y - dy + oy), (x - dy * bow + ox, y + dx * bow + oy), (x + dx + ox, y + dy + oy)],
                          fill=tone, width=1)
    return np.asarray(canvas, np.float32) / 255.0


def plain(size=1024):
    """Tiling surfaces of the drawer unit, a quarter of a metre to the tile: brushed aluminium and black coat."""
    rng = np.random.default_rng(5150)
    shape = (size, size)
    brush = 0.6 * _streaks(rng, size, 90, 0.7) + 0.4 * _streaks(rng, size, 30, 0.5)
    blotch, patch = band_noise(rng, 80, 400, shape), band_noise(rng, 10, 60, shape)
    lines = np.maximum(_wrapped_lines(rng, size, 70, 40), _wrapped_lines(rng, size, 40, 90, lean=0.0))
    # hands leave dull patches on bare aluminium, and the oxide takes the shine off it over the years
    dull = np.zeros(shape, np.float32)                       # no patches: plain brushed sheet
    tone = 0.585 * (1 + 0.035 * brush)
    alu = tone[..., None] * np.array([0.985, 1.0, 1.01]) + (lines * 0.14)[..., None]
    alu_spec = np.clip(0.62 - 0.22 * dull + 0.15 * lines, 0.05, 1)
    alu_gloss = np.clip(0.58 - 0.20 * dull + 0.04 * brush, 0.05, 1)
    alu_height = 0.10 * brush - 0.5 * lines
    # black coat on the drawer bodies and hasps: orange peel, pale scratches, dust
    peel = band_noise(rng, 5, 16, shape)
    scuff = np.zeros(shape, np.float32)
    black = (0.098 * (1 + 0.015 * peel))[..., None] * np.array([0.99, 1.0, 1.02])
    black = mix(black, NYLON_WORN, np.clip(lines * 0.5, 0, 1))
    black_spec = np.clip(0.26 - 0.10 * scuff + 0.10 * lines, 0.03, 1)
    black_gloss = np.clip(0.42 - 0.16 * scuff - 0.05 * peel, 0.03, 1)
    black_height = 0.22 * peel - 0.6 * lines
    pack = lambda spec, gloss: np.stack([np.ones(shape), spec, gloss], -1) * 255
    return dict(alu_co=np.clip(alu, 0, 1) * 255, alu_nohq=normal_map(alu_height), alu_smdi=pack(alu_spec, alu_gloss),
                black_co=np.clip(black, 0, 1) * 255, black_nohq=normal_map(black_height),
                black_smdi=pack(black_spec, black_gloss))


def build(output, work, hemtt="hemtt", png_only=False):
    """Paint the atlas from the relief that fit() recorded and write the textures and the material."""
    work.mkdir(parents=True, exist_ok=True)
    with np.load(RELIEF) as source:
        maps = {**paint({name: source[name] for name in source.files}), **plain()}
    for name, array in maps.items():
        png = work / (name + ".png")
        image = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
        if name == "fittings_as":
            image = image.resize((ATLAS // 2, ATLAS // 2), Image.Resampling.BOX)
        image.save(png)
        if not png_only:
            paa = output / (name + ".paa")
            paa.unlink(missing_ok=True)
            subprocess.run([hemtt, "utils", "paa", "convert", str(png), str(paa)], check=True,
                           stdout=subprocess.DEVNULL)
    if not png_only:
        rvmat(output)


def main():
    from build_medical_chest_inserts import load_source
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="Extracted acme_medchest_b2 folder")
    parser.add_argument("--models", type=Path, help="Folder with chest models that have not been fitted")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--work", type=Path, help="Folder for the PNG files. Without it no texture is painted.")
    parser.add_argument("--hemtt", default="hemtt")
    parser.add_argument("--png-only", action="store_true")
    args = parser.parse_args()
    io, kit, geo = load_source(args.source.resolve())
    if args.models:
        for path in sorted(args.models.glob("*.p3d")):
            lods = io.read_p3d(path)
            loose, cabinet = path.name.startswith("hardigg_lid"), path.name.startswith("medchest_open")
            for index, lod in enumerate(lods):
                if lod["res"] >= 1000:
                    continue
                origin = LID_ORIGIN if loose else (0, 0, 0)
                lod = fit(lod, geo, kit, origin, base=not loose, record=path.name == "medchest.p3d" and lod["res"] == 1)
                finish = path.stem.rsplit("_", 1)[-1]
                lod = weather(lod, geo, int(finish) if finish.isdigit() else 0, origin)
                if cabinet and lod["res"] == 1:
                    lod = bolted(lod, geo, kit)
                lods[index] = lod
            io.write_p3d(args.output / path.name, lods)
            print(path.name, "triangles LOD 1 to 3:", [sum(len(f["v"]) - 2 for f in lod["faces"]) for lod in lods[:3]])
    if args.work:
        build(args.output, args.work, args.hemtt, args.png_only)


if __name__ == "__main__":
    main()
