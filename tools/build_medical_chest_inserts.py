"""Drawer 8 padlocks and the four drawer insert of the Hardigg medical chest.

Works on the open cabinet model that build_hardigg_medical_chest.py writes:
  medchest_open.p3d     eight drawers; the lanyards on drawer 8 are replaced by two hasps with padlocks
  medchest_open_4.p3d   the same shell with a four drawer insert
The four drawer model keeps the bones, sources and axes of the eight drawer one (drawer1 to drawer4), so
model.cfg only needs one derived class. The artwork for both goes into free space of the detail atlas.

Use alone to refresh an existing build:  python build_medical_chest_inserts.py <acme_medchest_b2 folder>
"""
import argparse
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PREFIX = r"acm_extended\data\medical_chest\hardigg" + "\\"
OUTPUT = Path(__file__).resolve().parents[1] / "addons/acm_extended/data/medical_chest/hardigg"
MATERIALS = {"case": ("case_co.paa", "case.rvmat"), "alu": ("alu_co.paa", "alu.rvmat"),
             "blackmetal": ("black_co.paa", "blackmetal.rvmat"), "blackplastic": ("black_co.paa", "blackplastic.rvmat"),
             "detail": ("detail_co.paa", "detail.rvmat")}
FONTS = ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", r"C:\Windows\Fonts\arialbd.ttf",
         "arialbd.ttf", "DejaVuSans-Bold.ttf")

# ---------------------------------------------------------------- four drawer layout (metres, Blender axes)
STACK_TOP, STACK_BOTTOM, GAP = 0.792, 0.058, 0.002        # the same stack as the eight drawer unit
COUNT4 = 4
HEIGHT4 = (STACK_TOP - STACK_BOTTOM - (COUNT4 - 1) * GAP) / COUNT4
PULL_DROP = 0.058                                          # pull centre below the top edge of a tall front
SLIDE_RISE = 0.050                                         # slide centre above the bottom edge
# Detail atlas (2048 x 2048, y down). The rows below y 1250 (left) and y 966 (right) were empty.
FRONT4_RECTS = ((0, 1252, 1024, 396), (0, 1650, 1024, 396), (1024, 968, 1024, 396), (1024, 1366, 1024, 396))
LOCK_STEEL = (1032, 1772, 300, 268)
LOCK_BLUE = (1340, 1772, 300, 268)
LOCK_KEY = (1648, 1772, 200, 200)
# dividers of each tall drawer: lengthwise walls (x) and cross walls (y)
DIVIDERS4 = (((-0.068, 0.068), ()),
             ((-0.122, -0.041, 0.041, 0.122), (-0.030,)),
             ((-0.1025, 0.0, 0.1025), (-0.030,)),
             ((0.0,), (-0.058, 0.002)))

# ---------------------------------------------------------------- padlock (metres)
LOCK_W, LOCK_T, LOCK_H = 0.040, 0.019, 0.031               # laminated body
SHACKLE_R, SHACKLE_X, SHACKLE_CLEAR = 0.0035, 0.012, 0.019
STAPLE_X = 0.172                                            # staple and padlock, from the centre line
HASP_DROP = 0.038                                           # hasp centre below the top edge of drawer 8
LOCK_Y = 0.0815                                             # shackle centre line in front of the cabinet
LOCK_POSE = {1: (6.0, 2.0), -1: (-4.0, -3.0)}               # side: yaw and roll in degrees, as they came to rest


def drawer4_z(i):
    top = STACK_TOP - (i - 1) * (HEIGHT4 + GAP)
    return top - HEIGHT4, top


# ---------------------------------------------------------------- small mesh helpers

def _normal(points):
    n = np.zeros(3)
    for a, b in zip(points, points[1:] + points[:1]):
        n += np.cross(a, b)
    return n


def _outward(part, inside):
    """Turn every face away from inside(face centre). Keeps explicit UVs in step."""
    faces, uvs = [], []
    for k, face in enumerate(part.f):
        points = [np.array(part.v[i]) for i in face]
        centre = sum(points) / len(points)
        flip = np.dot(_normal(points), centre - np.array(inside(centre))) < 0
        faces.append(tuple(reversed(face)) if flip else tuple(face))
        if part.uv is not None:
            uvs.append(list(reversed(part.uv[k])) if flip else list(part.uv[k]))
    part.f = faces
    if part.uv is not None:
        part.uv = uvs
    return part


def chamfer_box(K, lo, hi, c):
    """Box with every edge cut by c. 44 triangles."""
    lo, hi = np.array(lo, float), np.array(hi, float)
    verts, index = [], {}
    for sx in (0, 1):
        for sy in (0, 1):
            for sz in (0, 1):
                corner = np.array([(lo, hi)[s][a] for a, s in enumerate((sx, sy, sz))])
                inward = np.array([c if s == 0 else -c for s in (sx, sy, sz)])
                for axis in range(3):
                    p = corner + inward
                    p[axis] = corner[axis]
                    index[(sx, sy, sz, axis)] = len(verts)
                    verts.append(tuple(p))
    faces = []
    for axis in range(3):
        u, v = [a for a in range(3) if a != axis]
        for s in (0, 1):
            quad = []
            for su, sv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                key = [0, 0, 0]
                key[axis], key[u], key[v] = s, su, sv
                quad.append(index[(*key, axis)])
            faces.append(tuple(quad))
    for axis in range(3):                                   # edges that run along this axis
        u, v = [a for a in range(3) if a != axis]
        for su in (0, 1):
            for sv in (0, 1):
                ends = []
                for s in (0, 1):
                    key = [0, 0, 0]
                    key[axis], key[u], key[v] = s, su, sv
                    ends.append(tuple(key))
                a, b = ends
                faces.append((index[(*a, u)], index[(*b, u)], index[(*b, v)], index[(*a, v)]))
    for sx in (0, 1):
        for sy in (0, 1):
            for sz in (0, 1):
                faces.append(tuple(index[(sx, sy, sz, axis)] for axis in range(3)))
    centre = (lo + hi) / 2
    return _outward(K.Part(verts, faces), lambda _: centre)


def tube(K, path, radius, sides, plane_normal):
    """Round bar along a flat path, open at both ends. plane_normal is the normal of the plane of the path."""
    path = [np.array(p, float) for p in path]
    b = np.array(plane_normal, float)
    b /= np.linalg.norm(b)
    verts, faces = [], []
    for k, p in enumerate(path):
        before = path[k] - path[k - 1] if k else path[1] - path[0]
        after = path[k + 1] - path[k] if k + 1 < len(path) else before
        before, after = before / np.linalg.norm(before), after / np.linalg.norm(after)
        tangent = before + after
        tangent /= np.linalg.norm(tangent)
        side = np.cross(tangent, b)
        mitre = 1.0 / max(0.5, float(np.dot(tangent, after)))          # keeps the bar round through a bend
        for s in range(sides):
            a = 2 * math.pi * (s + 0.5) / sides
            verts.append(tuple(p + radius * (math.cos(a) * side * mitre + math.sin(a) * b)))
    for k in range(len(path) - 1):
        for s in range(sides):
            a, c = k * sides + s, k * sides + (s + 1) % sides
            faces.append((a, c, c + sides, a + sides))

    def inside(point):
        best, nearest = None, path[0]
        for a, c in zip(path, path[1:]):
            t = np.clip(np.dot(point - a, c - a) / np.dot(c - a, c - a), 0, 1)
            q = a + t * (c - a)
            d = np.linalg.norm(point - q)
            if best is None or d < best:
                best, nearest = d, q
        return nearest
    return _outward(K.Part(verts, faces), inside)


def atlas_faces(geo, part, rect, side=(0.0, 1.0, 0.0, 1.0), end=None, cap=None):
    """Explicit atlas UVs from the bounds of the part. Each range is (s0, s1, t0, t1) inside the rect:
    side for the broad upright faces, end for the narrow upright ones, cap for top and bottom."""
    points = np.array(part.v)
    lo, span = points.min(0), np.maximum(points.max(0) - points.min(0), 1e-9)
    ranges = (end or side, side, cap or side)                # by the axis the face looks along: x, y, z
    uvs = []
    for face in part.f:
        normal = _normal([np.array(part.v[i]) for i in face])
        axis = int(np.argmax(abs(normal)))
        u_axis, v_axis = ((1, 2), (0, 2), (0, 1))[axis]
        s0, s1, t0, t1 = ranges[axis]
        uv = []
        for i in face:
            p = (np.array(part.v[i]) - lo) / span
            uv.append(geo.atlas_uv(rect, s0 + (s1 - s0) * p[u_axis], t0 + (t1 - t0) * p[v_axis]))
        uvs.append(uv)
    part.uv = uvs
    return part


def open_end(part, z):
    """Take away the faces that reach the plane z (the cap of a chamfered box and its bevels)."""
    part.f = [f for f in part.f if not any(abs(part.v[i][2] - z) < 1e-9 for i in f)]
    return part.compact()


def rotate(part, origin, yaw, roll):
    """Yaw about the upright axis, then roll about the axis that points out of the cabinet. Degrees."""
    cy, sy, cr, sr = (f(math.radians(a)) for a in (yaw, roll) for f in (math.cos, math.sin))
    yaw_m = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    roll_m = np.array([[cr, 0, sr], [0, 1, 0], [-sr, 0, cr]])
    m = np.eye(4)
    m[:3, :3] = yaw_m @ roll_m
    m[:3, 3] = np.array(origin) - m[:3, :3] @ np.zeros(3)
    return part.xform(m)


# ---------------------------------------------------------------- padlocks on drawer 8

def padlock(geo, K, lod):
    """One padlock, shackle up. Origin: the centre line of the shackle at the top of its bend.
    Returns [(part, material, uv rule, smoothing angle)]."""
    top = -(SHACKLE_R + SHACKLE_CLEAR)
    hx, hy = LOCK_W / 2, LOCK_T / 2
    band, bevel = 0.0012, 0.0016
    sleeve_top = top - 0.0090                               # the bumper leaves the top plates bare
    sleeve_lo = (-hx - band, -hy - band, top - LOCK_H - band)
    sleeve_hi = (hx + band, hy + band, sleeve_top)
    plain = (0.30, 0.70, 0.515, 0.537)                      # a strip of the steel with no plate edge in it
    if lod == 3:
        blue = K.box(sleeve_lo, (sleeve_hi[0], sleeve_hi[1], top), omit=("-y",))
        return [(atlas_faces(geo, blue, LOCK_BLUE, cap=(0.1, 0.9, 0.05, 0.25)), "detail", "explicit", 35.0)]
    parts = []
    # laminated steel body: only the part above the bumper is built. Plates and two rivets on the broad faces.
    body_lo, body_hi = (-hx, -hy, sleeve_top - 0.002), (hx, hy, top)
    if lod == 1:
        body = open_end(chamfer_box(K, (body_lo[0], body_lo[1], body_lo[2] - 0.0012), body_hi, 0.0012),
                        body_lo[2] - 0.0012)
    else:
        body = K.box(body_lo, body_hi, omit=("-z",))
    parts.append((atlas_faces(geo, body, LOCK_STEEL, side=(0.0, 1.0, 0.60, 1.0), end=(0.30, 0.70, 0.60, 1.0),
                              cap=plain), "detail", "explicit", 35.0))
    # vinyl bumper: a sleeve over the lower part, with the key cylinder in its bottom
    if lod == 1:
        sleeve = open_end(chamfer_box(K, sleeve_lo, (sleeve_hi[0], sleeve_hi[1], sleeve_top + bevel), bevel),
                          sleeve_top + bevel)
    else:
        sleeve = K.box(sleeve_lo, sleeve_hi, omit=("+z",))
        sleeve.compact()
    sleeve = atlas_faces(geo, sleeve, LOCK_BLUE, cap=(0.2, 0.8, 0.2, 0.8))
    for k, face in enumerate(sleeve.f):
        if all(sleeve.v[i][2] < sleeve_lo[2] + 1e-6 for i in face):
            sleeve.uv[k] = [geo.atlas_uv(LOCK_KEY, 0.5 + (sleeve.v[i][0] / (2 * hx)) * 0.9,
                                         0.5 + (sleeve.v[i][1] / (2 * hx)) * 0.9) for i in face]
    parts.append((sleeve, "detail", "explicit", 50.0))
    # hardened shackle
    bend = 8 if lod == 1 else 3
    path = [(-SHACKLE_X, 0.0, top - 0.004), (-SHACKLE_X, 0.0, -SHACKLE_X)]
    path += [(-SHACKLE_X * math.cos(math.pi * k / bend), 0.0, -SHACKLE_X + SHACKLE_X * math.sin(math.pi * k / bend))
             for k in range(1, bend)]
    path += [(SHACKLE_X, 0.0, -SHACKLE_X), (SHACKLE_X, 0.0, top - 0.004)]
    parts.append((tube(K, path, SHACKLE_R, 8 if lod == 1 else 4, (0, 1, 0)), "alu", "box", 80.0))
    if lod == 1:                                            # collars where the shackle enters the body
        for x in (-SHACKLE_X, SHACKLE_X):
            parts.append((K.cyl((x, 0.0, top - 0.0002), (x, 0.0, top + 0.0012), SHACKLE_R + 0.0012, 8,
                                caps=(False, True)), "alu", "box", 50.0))
    return parts


def add_padlocks(m, lod, geo, K):
    """Two hasps on drawer 8, each with a padlock through its staple. Fixed hinge leaves stay on the insert."""
    zb, zt = geo.drawer_z(8)
    zh = zt - HASP_DROP
    front, flange = geo.DR_YF, 0.0695
    sel = ("padlock",)

    def put(part, material, bone, uv="box", smooth=35.0):
        m.add(part, material, bone, uv=uv, tile=0.25, smooth=smooth, extra_sel=sel)

    for sx in (1, -1):
        xs = sx * STAPLE_X
        span = lambda a, b: tuple(sorted((sx * a, sx * b)))
        # hasp strap over the drawer front, with a slot for the staple
        y0, y1 = 0.0712, 0.0732
        if lod == 1:
            for (a, b), (z0, z1) in (((STAPLE_X + 0.004, 0.2185), (zh - 0.012, zh + 0.012)),
                                     ((0.150, STAPLE_X - 0.004), (zh - 0.012, zh + 0.012)),
                                     ((STAPLE_X - 0.004, STAPLE_X + 0.004), (zh + 0.010, zh + 0.012)),
                                     ((STAPLE_X - 0.004, STAPLE_X + 0.004), (zh - 0.012, zh - 0.010))):
                x0, x1 = span(a, b)
                put(K.box((x0, y0, z0), (x1, y1, z1)), "blackmetal", "drawer8")
            # hinge: leaf screwed to the flange of the insert, knuckle, pin heads
            x0, x1 = span(0.2195, 0.2262)
            put(K.box((x0, flange, zh - 0.015), (x1, flange + 0.0018, zh + 0.015), omit=("-y",)), "blackmetal", "insert")
            put(K.cyl((sx * 0.2185, 0.0728, zh - 0.015), (sx * 0.2185, 0.0728, zh + 0.015), 0.0028, 8),
                "blackmetal", "insert", smooth=60.0)
            for dz in (-0.009, 0.009):
                put(K.cyl((sx * 0.2229, flange + 0.0018, zh + dz), (sx * 0.2229, flange + 0.0028, zh + dz), 0.0016, 6,
                          caps=(False, True)), "alu", "insert", smooth=60.0)
            # staple: base plate riveted to the drawer front and the loop that takes the shackle
            put(K.box((xs - 0.0038, front, zh - 0.0098), (xs + 0.0038, front + 0.0015, zh + 0.0098), omit=("-y",)),
                "alu", "drawer8")
            loop = [(xs, front + 0.0010, zh + 0.007), (xs, 0.0862, zh + 0.007), (xs, 0.0890, zh + 0.0042),
                    (xs, 0.0890, zh - 0.0042), (xs, 0.0862, zh - 0.007), (xs, front + 0.0010, zh - 0.007)]
            put(tube(K, loop, 0.0022, 6, (1, 0, 0)), "alu", "drawer8", smooth=80.0)
        else:
            x0, x1 = span(0.150, 0.2185)
            put(K.box((x0, y0, zh - 0.012), (x1, y1, zh + 0.012), omit=("-y",)), "blackmetal", "drawer8")
        # the padlock hangs in the staple: the shackle rests on the lower leg of the loop
        hang = (xs, LOCK_Y, zh - 0.007 + 0.0022 + SHACKLE_R)
        yaw, roll = LOCK_POSE[sx]
        for part, material, uv, smooth in padlock(geo, K, lod):
            put(rotate(part, hang, yaw, roll), material, "drawer8", uv=uv, smooth=smooth)


# ---------------------------------------------------------------- four drawer insert

def _front(geo, K, zb, zt, zp, rect, hole):
    """Front face of a drawer front with its atlas UV, with an opening for the pull if hole is true."""
    hx, hw, hh = geo.DR_HX, geo.PULL_HW, geo.PULL_HH
    xs = [-hx, -hw, hw, hx] if hole else [-hx, hx]
    zs = [zb, zp - hh, zp + hh, zt] if hole else [zb, zt]
    v, f, uv = [], [], []
    for a in range(len(xs) - 1):
        for c in range(len(zs) - 1):
            if hole and a == 1 and c == 1:
                continue
            base = len(v)
            quad = [(xs[a], zs[c]), (xs[a + 1], zs[c]), (xs[a + 1], zs[c + 1]), (xs[a], zs[c + 1])][::-1]
            v += [(x, geo.DR_YF, z) for x, z in quad]
            f.append((base, base + 1, base + 2, base + 3))
            # the texture is drawn as seen from the front: its left edge is at +X
            uv.append([geo.atlas_uv(rect, (hx - x) / (2 * hx), (z - zb) / (zt - zb)) for x, z in quad])
    return K.Part(v, f, uv)


def add_drawer4(m, lod, geo, K, i):
    b = "drawer%d" % i
    zb, zt = drawer4_z(i)
    zp = zt - PULL_DROP
    hx, yf, yb = geo.DR_HX, geo.DR_YF, geo.DR_YB
    hw, hh, depth = geo.PULL_HW, geo.PULL_HH, geo.PULL_D
    alu, plastic = "alu", "blackplastic"
    hole = lod == 1
    add = lambda part, material=alu, bone=b: m.add(part, material, bone, tile=0.25)
    m.add(geo.face_to(_front(geo, K, zb, zt, zp, FRONT4_RECTS[i - 1], hole), (0, 1, 0)), "detail", b, uv="explicit")
    add(K.box((-hx, yb, zb), (hx, yf, zt), omit=("+y", "-y")), plastic)
    back = _front(geo, K, zb, zt, zp, FRONT4_RECTS[i - 1], hole)
    back.v = [(p[0], yb, p[2]) for p in back.v]
    back.uv = None
    add(geo.face_to(back, (0, -1, 0)), plastic)
    tx, tyb, t = 0.205, -0.120, 0.002
    tz0, tz1 = zb + 0.004, zt - 0.014
    if lod == 3:
        add(K.box((-tx, tyb, tz0), (tx, yb, tz1), omit=("+y",)))
        return
    if hole:
        add(K.inbox((-hw, yf - depth, zp - hh), (hw, yf, zp + hh), omit=("+y",)))
        add(K.box((-hw, yf - 0.008, zp + hh - 0.006), (hw, yf - 0.0005, zp + hh), omit=("+z", "-x", "+x")))
        add(K.box((-hw - 0.001, yf - depth - 0.001, zp - hh - 0.001), (hw + 0.001, yb, zp + hh + 0.001), omit=("+y",)))
    # tray: outside, inside, rim
    add(K.box((-tx, tyb, tz0), (tx, yb, tz1), omit=("+y", "+z")))
    add(K.inbox((-tx + t, tyb + t, tz0 + t), (tx - t, yb, tz1), omit=("+y", "+z")))
    for lo, hi in (((-tx, tyb), (-tx + t, yb)), ((tx - t, tyb), (tx, yb)), ((-tx + t, tyb), (tx - t, tyb + t))):
        add(K.box((lo[0], lo[1], tz1 - 0.0001), (hi[0], hi[1], tz1), omit=("-z", "-x", "+x", "-y", "+y")))
    if lod != 1:
        return
    # slide: member on the drawer, release lever at its front end
    zs = zb + SLIDE_RISE
    for sx in (-1, 1):
        a, c = sorted((sx * tx, sx * 0.211))
        add(K.box((a, tyb, zs - 0.018), (c, 0.056, zs + 0.018), omit=("+x" if sx < 0 else "-x",)))
        a, c = sorted((sx * 0.2112, sx * 0.2138))
        add(K.box((a, 0.026, zs - 0.006), (c, 0.054, zs + 0.006), omit=("+x" if sx < 0 else "-x",)), plastic)
    # dividers: slotted aluminium walls that stop short of the rim
    lengthwise, cross = DIVIDERS4[i - 1]
    floor, wall_top, w = tz0 + t, tz1 - 0.006, 0.0008
    for y in cross:
        add(K.box((-tx + t, y - w, floor), (tx - t, y + w, wall_top), omit=("-z", "-x", "+x")))
    rows = [tyb + t] + list(cross) + [yb]
    for row, (ya, yc) in enumerate(zip(rows[:-1], rows[1:])):
        shift = 0.0 if row % 2 == 0 or not cross else 0.020          # the rows are set off against each other
        for x in lengthwise:
            add(K.box((x + shift - w, ya, floor), (x + shift + w, yc, wall_top - 0.006 * (row % 2)),
                      omit=("-z", "-y", "+y")))


def add_insert4(m, lod, geo, K):
    """The aluminium drawer unit with four tall drawers. Bone 'insert' for the fixed parts."""
    b = "insert"
    z0, z1, fx, yb, yf = 0.055, 0.795, 0.219, -0.126, 0.0695
    m.add(K.inbox((-fx, yb, z0), (fx, yf, z1), omit=("+y",)), "alu", b, tile=0.25)
    n = {1: 6, 2: 2, 3: 2}[lod]
    loop = K.rrect_loop(geo.IX, (geo.IZ1 - geo.IZ0) / 2, geo.IR, n, (geo.IZ0 + geo.IZ1) / 2)[0]
    inner = [(min(max(p[0], -fx), fx), min(max(p[1], z0), z1)) for p in loop]
    m.add(geo.face_to(K.strip_between(loop, inner, yf), (0, 1, 0)), "alu", b, tile=0.25)
    for i in range(1, COUNT4 + 1):
        add_drawer4(m, lod, geo, K, i)
        if lod == 1:                                        # the cabinet member of each slide
            zs = drawer4_z(i)[0] + SLIDE_RISE
            for sx in (-1, 1):
                a, c = sorted((sx * 0.211, sx * 0.219))
                m.add(K.box((a, -0.124, zs - 0.022), (c, 0.058, zs + 0.022), omit=("-x" if sx < 0 else "+x",)),
                      "alu", b, tile=0.25)


# ---------------------------------------------------------------- LOD surgery

def _drop(lod, drop_face=None, drop_vert=None):
    """Remove faces (and the points only they used), or named points of a LOD without faces."""
    faces = [f for f in lod["faces"] if not (drop_face and drop_face(f))]
    if drop_vert is None:
        used = {i for f in faces for i in f["v"]}
        if not lod["faces"]:
            used = set(range(len(lod["verts"])))
    else:
        used = {i for i in range(len(lod["verts"])) if not drop_vert(i)}
    keep = sorted(used)
    index = {old: new for new, old in enumerate(keep)}
    return {**lod,
            "verts": [lod["verts"][i] for i in keep],
            "faces": [{**f, "v": [index[i] for i in f["v"]]} for f in faces],
            "sharp": [(index[a], index[b]) for a, b in lod["sharp"] if a in index and b in index],
            "mass": [lod["mass"][i] for i in keep] if lod["mass"] is not None else None,
            "sels": {name: picked for name, points in lod["sels"].items()
                     if (picked := {index[i] for i in points if i in index})}}


def _bake_into(lod, mesh, K):
    """Append a kit mesh to a visual LOD and keep one run of faces for each material."""
    verts, normals, faces, sharp = K.bake(mesh)
    v0, n0 = len(lod["verts"]), len(lod["normals"])
    out = {**lod, "verts": lod["verts"] + [tuple(map(float, p)) for p in verts],
           "normals": list(lod["normals"]) + normals, "faces": list(lod["faces"]),
           "sharp": list(lod["sharp"]) + [(a + v0, b + v0) for a, b in sharp],
           "sels": {name: set(points) for name, points in lod["sels"].items()}}
    for f in faces:
        tex, mat = MATERIALS[f["mat"]]
        ids = [v0 + i for i in f["v"]]
        out["faces"].append(dict(v=ids, n=[n0 + i for i in f["n"]], uv=f["uv"], tex=PREFIX + tex, mat=PREFIX + mat))
        for name in ((f["bone"],) if f["bone"] else ()) + tuple(f["sel"]):
            out["sels"].setdefault(name, set()).update(ids)
    order = {}
    for f in out["faces"]:
        order.setdefault((f["tex"].lower(), f["mat"].lower()), len(order))
    out["faces"].sort(key=lambda f: order[(f["tex"].lower(), f["mat"].lower())])
    return out


def _drawers(lod, count=8):
    return set().union(*(lod["sels"].get("drawer%d" % i, set()) for i in range(1, count + 1)))


def padlocked(io, K, geo, cabinet):
    """Eight drawer cabinet: lanyards on drawer 8 off, hasps and padlocks on."""
    out = []
    for lod in cabinet:
        if lod["res"] >= 1000:
            out.append(lod)
            continue
        old = lod["sels"].get("padlock", set())
        drawer8 = lod["sels"].get("drawer8", set())
        lanyard = lambda f: (all(i in drawer8 for i in f["v"])
                             and max(lod["verts"][i][1] for i in f["v"]) > geo.DR_YF + 1e-4)
        bare = _drop(lod, lambda f: all(i in old for i in f["v"]) or lanyard(f))
        mesh = K.Mesh()
        add_padlocks(mesh, int(round(lod["res"])), geo, K)
        out.append(_bake_into(bare, mesh, K))
    return out


def four_drawer(io, K, geo, cabinet):
    """The cabinet with the four drawer insert in place of the eight drawer one."""
    out = []
    for lod in cabinet:
        res = lod["res"]
        if res < 1000:
            gone = _drawers(lod) | lod["sels"].get("insert", set()) | lod["sels"].get("padlock", set())
            bare = _drop(lod, lambda f: all(i in gone for i in f["v"]))
            mesh = K.Mesh()
            add_insert4(mesh, int(round(res)), geo, K)
            out.append(_bake_into(bare, mesh, K))
        elif res == io.LOD_SHADOW:
            gone = _drawers(lod)
            new = _drop(lod, lambda f: all(i in gone for i in f["v"]))
            new = {**new, "verts": list(new["verts"]), "faces": list(new["faces"]), "sharp": list(new["sharp"]),
                   "sels": dict(new["sels"])}
            for i in range(1, COUNT4 + 1):
                zb, zt = drawer4_z(i)
                box = K.box((-geo.DR_HX, -0.120, zb), (geo.DR_HX, geo.DR_YF, zt))
                base = len(new["verts"])
                new["verts"] += box.v
                edges = set()
                for quad in box.f:
                    for tri in ((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])):
                        ids = [base + k for k in tri]
                        new["faces"].append(dict(v=ids, n=[0, 0, 0], uv=[(0.0, 0.0)] * 3, tex="", mat=""))
                        edges.update((min(a, c), max(a, c)) for a, c in zip(ids, ids[1:] + ids[:1]))
                new["sharp"] += sorted(edges)
                new["sels"]["drawer%d" % i] = set(range(base, base + len(box.v)))
            out.append(new)
        elif math.isclose(res, io.LOD_MEMORY, rel_tol=1e-6):
            spare = set().union(*(lod["sels"].get(name, set()) for i in range(COUNT4 + 1, 9)
                                  for name in ("drawer%d_pos" % i,)))
            new = _drop(lod, drop_vert=lambda i: i in spare)
            new = {**new, "verts": list(new["verts"])}
            for i in range(1, COUNT4 + 1):
                zb, zt = drawer4_z(i)
                for point in new["sels"].get("drawer%d_pos" % i, ()):
                    new["verts"][point] = (0.0, geo.DR_YF, (zb + zt) / 2)
            out.append(new)
        else:
            out.append(lod)
    return out


def model_cfg(text):
    """Add the model class of the four drawer cabinet. It uses the skeleton and axes of medchest."""
    line = '    class medchest_open_4: medchest { sections[] = {"camo"}; };'
    if "class medchest_open_4:" in text:
        return text
    anchor = '    class medchest_open: medchest { sections[] = {"camo"}; };'
    if anchor not in text:
        raise ValueError("model.cfg has no medchest_open class to follow")
    return text.replace(anchor, anchor + "\n" + line, 1)


# ---------------------------------------------------------------- detail atlas

def _font(size):
    for name in FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    raise OSError("No bold sans font found for the drawer numbers")


def _rivet(d, cx, cy, r):
    d.ellipse([cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1], fill=(8, 8, 8, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(150, 152, 155, 255))
    d.ellipse([cx - r * 0.55, cy - r * 0.75, cx + r * 0.25, cy + r * 0.05], fill=(205, 207, 210, 255))


def plain_fronts(img, geo_fronts):
    """Drawer fronts are black sheet: one even tone with a fine brushed grain and a few scratches. The clouds the
    source atlas has there go; pulls, numbers, rivets and labels (everything light) stay as they are."""
    rng = np.random.default_rng(4204)
    pixels = np.asarray(img, np.float32)
    for x, y, w, h in geo_fronts:
        tile = pixels[y:y + h, x:x + w]
        level = tile @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        streak = np.repeat(rng.normal(0, 1, (h, 1)), w, axis=1) * 0.6 + rng.normal(0, 1, (h, w)) * 0.5
        sheet = 30.0 * (1 + 0.035 * streak)[..., None] * np.array([0.98, 1.0, 1.04], np.float32)
        marks = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(marks)
        for _ in range(int(w * h / 9000)):
            px, py, reach = rng.uniform(0, w), rng.uniform(0, h), float(np.exp(rng.normal(3.0, 0.8)))
            angle = rng.normal(0, 0.5)
            draw.line([(px - math.cos(angle) * reach, py - math.sin(angle) * reach),
                       (px + math.cos(angle) * reach, py + math.sin(angle) * reach)], fill=int(rng.uniform(40, 150)), width=1)
        sheet += (np.asarray(marks, np.float32) / 255.0 * 34)[..., None]
        dark = np.clip((92 - level) / 30, 0, 1)[..., None]                 # the clouds are all darker than this
        pixels[y:y + h, x:x + w] = tile * (1 - dark) + sheet * dark
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))


def paint_detail(source, hx=0.2165, pull_hw=0.048, pull_hh=0.013):
    """The detail atlas with the four tall drawer fronts and the padlock faces added in its empty rows."""
    with Image.open(source) as opened:
        img = opened.convert("RGB")
    if img.size != (2048, 2048):
        raise ValueError(f"The detail atlas must be 2048 x 2048, not {img.size}")
    rng = np.random.default_rng(4104)
    d = ImageDraw.Draw(img, "RGBA")
    for number, (x, y, w, h) in enumerate(FRONT4_RECTS, 1):
        ppx, ppz = w / (2 * hx), h / HEIGHT4
        cx, cy = x + w / 2, y + PULL_DROP * ppz
        hw, hh = pull_hw * ppx, pull_hh * ppz
        d.rectangle([cx - hw - 5, cy - hh - 5, cx + hw + 5, cy + hh + 5], fill=(120, 122, 126, 255))
        d.rectangle([cx - hw, cy - hh, cx + hw, cy + hh], fill=(150, 152, 156, 255))
        for k in range(int(hh * 0.9)):
            d.line([cx - hw, cy - hh + k, cx + hw, cy - hh + k], fill=(20, 20, 22, int(150 * (1 - k / (hh * 0.9)))))
        d.line([cx - hw, cy + hh - 1, cx + hw, cy + hh - 1], fill=(215, 217, 220, 255), width=2)
        for sx in (-1, 1):
            for sy in (-1, 1):
                _rivet(d, cx + sx * (hw + 14), cy + sy * (hh + 6), 4)
            # panel rivets: corners, and one pair along the top edge
            _rivet(d, cx + sx * (w / 2 - 0.030 * ppx), y + 0.022 * ppz, 4)
            _rivet(d, cx + sx * (w / 2 - 0.030 * ppx), y + h - 0.022 * ppz, 4)
            _rivet(d, cx + sx * (w / 2 - 0.115 * ppx), y + 0.022 * ppz, 4)
        d.text((cx + hw + 26, cy), str(number), font=_font(int(pull_hh * ppx * 2.05)), fill=(236, 236, 232, 255),
               anchor="lm")
        d.rectangle([x, y, x + w - 1, y + h - 1], outline=(12, 12, 13, 255), width=2)
    # handling dust and fine scratches on the new fronts, as on the eight drawer ones
    arr = np.asarray(img, np.float32)
    size = arr.shape[0]
    cloud = np.zeros((size, size), np.float32)
    for cells, weight in ((size // 56, 0.65), (size // 20, 0.35)):       # blotches of two sizes, as on the old fronts
        layer = Image.fromarray((rng.random((cells, cells)) * 255).astype(np.uint8))
        layer = layer.resize((size, size), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(3))
        cloud += np.asarray(layer, np.float32) / 255.0 * weight
    cloud = np.clip((cloud - 0.50) * 3.2, 0, 1) * 0.10
    scratches = Image.new("L", (size, size), 0)
    sd = ImageDraw.Draw(scratches)
    for _ in range(260):
        x, y, w, h = FRONT4_RECTS[rng.integers(len(FRONT4_RECTS))]
        px, py = x + rng.random() * w, y + rng.random() * h
        angle, length = rng.normal(0, 0.35), rng.uniform(10, 90)
        sd.line([px, py, px + math.cos(angle) * length, py + math.sin(angle) * length],
                fill=int(rng.uniform(12, 64)), width=int(rng.integers(1, 3)))
    mask = np.zeros((size, size), np.float32)
    for x, y, w, h in FRONT4_RECTS:
        mask[y:y + h, x:x + w] = 1
    mix = (np.clip(cloud + np.asarray(scratches, np.float32) / 255.0 * 0.35, 0, 1) * mask)[..., None]
    arr = arr * (1 - mix) + np.array([150.0, 148.0, 140.0]) * mix
    # laminated steel: stacked plates with a bright edge each, four rivet heads
    x, y, w, h = LOCK_STEEL
    steel = np.full((h, w, 3), (164.0, 166.0, 170.0), np.float32)
    steel += rng.normal(0, 3.0, (h, 1, 1)) + rng.normal(0, 2.0, (h, w, 1))
    for row in range(0, h, 12):
        steel[row:row + 2] *= 0.52
        steel[row + 2:row + 4] *= 1.12
    arr[y:y + h, x:x + w] = steel
    # vinyl bumper: blue, a little lighter at the moulded edges
    x, y, w, h = LOCK_BLUE
    blue = np.full((h, w, 3), (30.0, 66.0, 146.0), np.float32) + rng.normal(0, 2.5, (h, w, 1))
    ramp = np.minimum(np.arange(h)[:, None], h - 1 - np.arange(h)[:, None]) / 14.0
    blue *= (1.16 - 0.16 * np.clip(ramp, 0, 1))[..., None]
    arr[y:y + h, x:x + w] = blue
    x, y, w, h = LOCK_KEY
    arr[y:y + h, x:x + w] = np.array((28.0, 62.0, 138.0)) + rng.normal(0, 2.5, (h, w, 1))
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    x, y, w, h = LOCK_STEEL
    for px, py in ((0.14, 0.20), (0.86, 0.20), (0.14, 0.80), (0.86, 0.80)):
        _rivet(d, x + px * w, y + py * h, 15)
    x, y, w, h = LOCK_KEY                                   # key cylinder: brass face, steel shutter, keyway
    cx, cy, r = x + w / 2, y + h / 2, h * 0.34
    d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], fill=(16, 34, 78, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(176, 150, 82, 255))
    d.ellipse([cx - r * 0.72, cy - r * 0.72, cx + r * 0.72, cy + r * 0.72], fill=(198, 172, 100, 255))
    d.rectangle([cx - r * 0.50, cy - r * 0.09, cx + r * 0.50, cy + r * 0.09], fill=(22, 20, 16, 255))
    eight = [(0, k * 184, 1024, 184) for k in range(4)] + [(1024, k * 241, 1024, 241) for k in range(4)]
    return plain_fronts(img, eight + list(FRONT4_RECTS))


# ---------------------------------------------------------------- stand-alone refresh of an existing build

def load_source(source):
    build = source / "acme_medchest_src/build"
    spec = importlib.util.spec_from_file_location("medchest_mlod", build / "mc_p3d.py")
    io = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io)
    sys.path.insert(0, str(build))
    import mc_geo as geo
    import mc_kit as kit
    return io, kit, geo


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="Extracted acme_medchest_b2 folder")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--work", type=Path, help="Folder for the atlas PNG. Without it the PAA is left alone.")
    parser.add_argument("--hemtt", default="hemtt")
    args = parser.parse_args()
    source = args.source.resolve()
    io, kit, geo = load_source(source)
    cabinet = padlocked(io, kit, geo, io.read_p3d(args.output / "medchest_open.p3d"))
    io.write_p3d(args.output / "medchest_open.p3d", cabinet)
    four = four_drawer(io, kit, geo, cabinet)
    io.write_p3d(args.output / "medchest_open_4.p3d", four)
    cfg = args.output / "model.cfg"
    cfg.write_text(model_cfg(cfg.read_text()))
    for name, lods in (("medchest_open", cabinet), ("medchest_open_4", four)):
        print(name, "triangles LOD 1 to 3:", [sum(len(f["v"]) - 2 for f in lod["faces"]) for lod in lods[:3]])
    if args.work:
        args.work.mkdir(parents=True, exist_ok=True)
        png = args.work / "detail_co.png"
        paint_detail(source / "acme_medchest_src/textures_png/detail_co.png").save(png)
        paa = args.output / "detail_co.paa"
        paa.unlink(missing_ok=True)
        subprocess.run([args.hemtt, "utils", "paa", "convert", str(png), str(paa)], check=True)
        print("wrote", paa)


if __name__ == "__main__":
    main()
