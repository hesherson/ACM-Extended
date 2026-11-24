"""Put the HPMK-I shell model on a casualty: addons/acme_hpmk/hpmk_worn.p3d, hpmk_worn_sked.p3d, hpmk_worn_open.p3d
from the model as it was drawn (tools/assets/hpmk_worn_source.p3d).

The model as drawn is the shell lying flat and filled, with its hood: good to look at, but bound to the pelvis
alone, so it stood stiff while the casualty in it bent, and he came through it. Here every point of it is laid
on the casualty as he lies in the litter pose and then bound to the bones under it:

  - The bag's top sheet is laid over him as a cloth: a point so far from the bag's middle line in the drawing is
    put that far along the outline of his body and arms (measured in the game, tools/hpmk_body.py), over the top,
    down his side, and what is left over tucked under him. Its creases are kept: how far each point stands off the
    drawn sheet's own smooth shape, it stands off him.
  - The bottom sheet lies under him.
  - The hood is drawn loose round a head that is not there (with a blue disc where the face is). It is drawn in
    to the measured head, keeping its crumples, and the disc is left out.
  - Then each point is bound to the bones nearest to it and carried back to the rest position, so that the litter
    pose brings it exactly where it was laid (see tools/build_hpmk_shell.py for the binding).

Everything else of the drawing stays as it is: faces, pictures, creases marked sharp, all levels of detail.

The two opened models (his chest exposed) have the cover cut along a fold line and, drawn new, the cover folded
over with its lining and closure strip, the bottom sheet beside him and the kit's blanket on him:
tools/hpmk_opened.py. The lining's picture: tools/make_hpmk_lining.py.
It has to be run again whenever the litter pose changes (after a new scan).

  python tools/fit_hpmk_worn.py
  python tools/fit_hpmk_worn.py --look hpmk_worn_open     (only that model's preview, to look at: no model written)
"""
import math
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import build_hpmk_shell as H  # noqa: E402
import hpmk_opened as O  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).with_name("assets") / "hpmk_worn_source.p3d"
OUT = ROOT / "addons/acme_hpmk"
OUTLINE = Path(__file__).with_name("assets") / "hpmk_shell_outline.npy"

# He is undressed for the bag (ACME_fnc_hpmkDress, 2026-11-20: "you can safely take off the gear while they're in
# the HPMK"), so the room is for bare skin over the measured fire geometry: about 1 cm on trunk and thighs, up
# to 3 cm sideways at the forearms. (For a combat uniform with gloves and pads it was 4.4 cm, 3.0 cm least, and
# up to 3.4 cm more at hands and elbows: a bag of lumps, and wider than a SKED.)
CLEAR = 0.030         # the cloth's smooth shape stands this far off the measured outline
LEAST = 0.018         # and no crease comes closer to him than this
MOST = 0.016          # nor stands further off the cloth's smooth shape than this (the hood's string hangs free in the drawing)
# The drawn creases are kept at this share of their height ("some of the triangles are a little too pointy
# looking"), and almost flat where a strap of a litter lies across the bag, so that the strap lies on cloth and
# not on the tips of creases with air under it. In a SKED the bag is pulled taut all over by five straps.
# (2026-11-23, "too tented in a lot of spots": 0.55 and 2.2 cm before; and the creases are then smoothed, SMOOTH.)
RELIEF, RELIEF_STRAP, RELIEF_SKED = 0.40, 0.12, 0.20
# Along him the cloth leaves a high place no steeper than this (rise over run). At 0.6 (build_hpmk_shell.DROP_BAG)
# it stood off his shins 10 cm on the average and up to 25 cm, a tent from his toes; and from his chest over his belly.
DROP_ALONG = 1.2
# The top sheet's creases are rounded by this many passes of a smoothing that keeps their size (Taubin's: lambda,
# mu): drawn at full size the triangles met at sharp ridges, a fifth of them at more than 30 degrees on his legs.
SMOOTH = (6, 0.5, -0.53)
SMOOTH_DRAWN = 0.25
SHADOW_IN = 0.015
STRAPS_ACROSS = ((-0.215, -0.165), (0.215, 0.277))    # the Talon II's two straps, along him (scan axes)
STRAP_EASE = 0.05     # the creases come back over this distance beside a strap
BACK = -0.155         # the drawn bottom sheet: so far behind the model's middle
# Sideways the bag is held to the width of a SKED, but never closer to his outline than this
SIDE_LEAST = 0.034
# The elbow pads of a combat uniform stand further out of his measured outline than anything else at his sides
# (with 3 cm of cloth room a spot of the right one still came through, with 5.5 cm a speck of it, seen in game).
# Along his elbows the bag is this much wider, except in a SKED (which is no wider than the bag already, and
# undresses him).
# (the pad of a combat uniform's right elbow came through at 0.29 along him, below where this began at 0.34:
# found by casting the camera's ray through the picture's pixel at the fitted shell, after two runs of adding room)
# (bare: his forearms' skin reaches up to 3 cm further sideways than the fire geometry, hands the same)
ELBOWS, ELBOWS_MORE = (0.04, 0.52), 0.012
HANDS_MORE = 0.012
SOLES_DRAWN = -0.98   # where his soles are along the drawn model (rest position), and the bag's end there
END_DRAWN = -1.215
FOOT_END = 0.10       # the bag goes on so far beyond his soles (the drawn 23 cm gathered into it)
SHOULDERS = (0.575, 0.625)   # along him (scan axes): the outline that is carried on beside his neck and head,
FLAT_BY = 0.84               # sinking to a third of its height by here
STEP = 0.01
ROUND = 180           # points of an outline
HOOD_FROM = (0.56, 0.64)     # along the drawn model: below the first a point of the hood goes with the bag,
                             # above the second with the head
# (his head is measured as its fire geometry, which is coarse: with 1.2 cm and 0.5 cm his scalp showed)
HOOD_CLEAR, HOOD_LEAST = 0.020, 0.012
CRUMPLE_KEPT = 0.60   # how much of the drawn hood's crumples is kept
# Opened over his chest: the cover is cut at a fold line and what is taken off, the bottom sheet beside him and
# the kit's blanket are drawn new: tools/hpmk_opened.py.
INSIDE = (rb"acme_hpmk\data\hpmk_in_co.paa", rb"acme_hpmk\data\hpmk_in.rvmat")


# ---------------------------------------------------------------- the model file, kept as it is
def read(path):
    d = Path(path).read_bytes()
    count = struct.unpack_from("<I", d, 8)[0]
    c = 12
    levels = []
    for _ in range(count):
        assert d[c:c + 4] == b"P3DM"
        head = d[c:c + 28]
        _, _, npts, nnrm, nfaces, _ = struct.unpack_from("<6I", d, c + 4)
        c += 28
        pts = np.frombuffer(d, "<f4", npts * 4, c).reshape(npts, 4).copy()
        flags = np.frombuffer(d, "<u4", npts * 4, c).reshape(npts, 4)[:, 3].copy()
        c += npts * 16
        nrm = np.frombuffer(d, "<f4", nnrm * 3, c).reshape(nnrm, 3).copy()
        c += nnrm * 12
        faces = []
        for _ in range(nfaces):
            n = struct.unpack_from("<I", d, c)[0]
            vs = [list(struct.unpack_from("<IIff", d, c + 4 + 16 * j)) for j in range(n)]
            fl = struct.unpack_from("<I", d, c + 68)[0]
            e = d.index(0, c + 72)
            e2 = d.index(0, e + 1)
            faces.append([vs, fl, d[c + 72:e], d[e + 1:e2]])
            c = e2 + 1
        assert d[c:c + 4] == b"TAGG"
        c += 4
        tags = []
        while True:
            e = d.index(0, c + 1)
            name = d[c + 1:e].decode("latin1")
            size = struct.unpack_from("<I", d, e + 1)[0]
            tags.append((name, d[e + 5:e + 5 + size]))
            c = e + 5 + size
            if name == "#EndOfFile#":
                break
        res = struct.unpack_from("<f", d, c)[0]
        c += 4
        levels.append(dict(head=head, pts=pts[:, :3].astype(float), flags=flags, nrm=nrm.astype(float), faces=faces, tags=tags, res=res))
    return levels


def write(path, levels):
    b = bytearray(b"MLOD" + struct.pack("<II", 257, len(levels)))
    for lv in levels:
        b += b"P3DM" + struct.pack("<6I", 28, 256, len(lv["pts"]), len(lv["nrm"]), len(lv["faces"]), 0)
        for p, f in zip(lv["pts"], lv["flags"]):
            b += struct.pack("<3fI", p[0], p[1], p[2], int(f))
        for n in lv["nrm"]:
            b += struct.pack("<3f", *n)
        for vs, fl, tex, mat in lv["faces"]:
            b += struct.pack("<I", len(vs))
            for j in range(4):
                b += struct.pack("<IIff", *(vs[j] if j < len(vs) else (0, 0, 0.0, 0.0)))
            b += struct.pack("<I", fl) + tex + b"\0" + mat + b"\0"
        b += b"TAGG"
        for name, data in lv["tags"]:
            b += b"\x01" + name.encode("latin1") + b"\0" + struct.pack("<I", len(data)) + data
        b += struct.pack("<f", lv["res"])
    Path(path).write_bytes(bytes(b))


def selection(lv, name):
    """The weights a level gives its points for a bone: an array, 0..1."""
    out = np.zeros(len(lv["pts"]))
    for tag, data in lv["tags"]:
        if tag == name:
            raw = np.frombuffer(data, "u1", len(lv["pts"]))
            out = np.where(raw == 0, 0.0, np.where(raw == 1, 1.0, (256.0 - raw) / 255.0))
    return out


# ---------------------------------------------------------------- the casualty's outline, as a cloth lies on it
class Outline:
    """At stations along him the line a cloth pulled round him takes, a clearance off him: from the middle of
    his top round each side and under him."""

    def __init__(self, body, clear, pads=True):
        self.body = body
        self.y0 = H.FIRST - FOOT_END
        self.ys = np.arange(self.y0, FLAT_BY + 0.03, STEP)
        shoulders = [p for y in np.arange(SHOULDERS[0], SHOULDERS[1] + 1e-9, 0.01) for p in body.cut(y, 0.011)]
        feet = body.cut(H.FIRST + 0.02, 0.031)
        polys = []
        for y in self.ys:
            c = clear + H.FEET_MORE * H.step((H.FEET_FROM - y) / 0.12)
            if y < H.FIRST:
                # beyond his soles the bag comes down in a quarter round
                f = min(1.0, (H.FIRST - y) / FOOT_END)
                pts = [(x, z * (math.cos(f * math.pi / 2) * 0.9 + 0.1)) for x, z in feet]
            elif y <= SHOULDERS[1]:
                pts = body.cut(y, 0.021 if y < 0.60 else 0.011)
            else:
                # beside his neck and head the cloth lies on, sinking
                g = 1 - 0.67 * H.step((y - SHOULDERS[1]) / (FLAT_BY - SHOULDERS[1]))
                pts = [(x, z * g) for x, z in shoulders]
                c = clear * (0.45 + 0.55 * g)
            xs = [p[0] for p in pts]
            if H.HANDS[0] <= y <= H.HANDS[1]:
                pts = pts + [(min(xs) - HANDS_MORE, 0.03), (max(xs) + HANDS_MORE, 0.03), (min(xs) - HANDS_MORE, 0.09), (max(xs) + HANDS_MORE, 0.09)]
                xs = [p[0] for p in pts]
            # (The cloth turns under him below what he lies on, not at it: rounded in at that level it came 3 cm
            # closer to him just where his elbows and hands rest.)
            if pads and ELBOWS[0] <= y <= ELBOWS[1]:
                pts = pts + [(min(xs) - ELBOWS_MORE, 0.02), (max(xs) + ELBOWS_MORE, 0.02), (min(xs) - ELBOWS_MORE, 0.08), (max(xs) + ELBOWS_MORE, 0.08)]
                xs = [q[0] for q in pts]
            low = H.BOTTOM + c - 0.04
            pts = [(x, max(z, low)) for x, z in pts] + [(min(xs), low), (max(xs), low)]
            polys.append((H.grown(pts, c), (min(-H.SIDE_MOST, min(xs) - SIDE_LEAST), max(H.SIDE_MOST, max(xs) + SIDE_LEAST))))
        centres = np.array([[sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)] for poly, _ in polys])
        cx, cz = H.smooth(centres[:, 0], 3.0), H.smooth(centres[:, 1], 3.0)
        angles = np.linspace(0, 2 * math.pi, ROUND, endpoint=False)
        radii = np.zeros((len(self.ys), ROUND))
        for s, (poly, _) in enumerate(polys):
            inside = min(p[0] for p in poly) < cx[s] < max(p[0] for p in poly) and min(p[1] for p in poly) < cz[s] < max(p[1] for p in poly)
            if not inside:
                cx[s], cz[s] = centres[s]
            for k, a in enumerate(angles):
                radii[s, k] = H.reach(poly, (cx[s], cz[s]), a)
        # a tarp is stiff: along him it leaves a high place no steeper than this, and lies without steps
        # (not beyond his soles: there the bag comes down to close)
        raw = radii.copy()
        for s in range(len(self.ys)):
            if self.ys[s] >= H.FIRST:
                radii[s] = np.max(raw - DROP_ALONG * np.abs(self.ys - self.ys[s])[:, None], axis=0)
        own = self.ys >= H.FIRST
        for k in range(ROUND):
            radii[own, k] = np.maximum(radii[own, k], H.smooth(radii[own, k], 1.5))
        self.paths = []
        for s in range(len(self.ys)):
            x = np.clip(cx[s] + radii[s] * np.cos(angles), polys[s][1][0], polys[s][1][1])
            z = np.maximum(cz[s] + radii[s] * np.sin(angles), H.BOTTOM)
            ring = np.stack([x, z], axis=1)
            # from the middle of the top (straight over x = 0) round each side to the middle underneath
            top = max((k for k in range(ROUND) if z[k] > cz[s]), key=lambda k: -abs(x[k]))
            under = max((k for k in range(ROUND) if z[k] <= cz[s]), key=lambda k: -abs(x[k]))
            sides = {}
            for sign in (1, -1):
                line = [ring[top]]
                k = top
                step = 1 if ring[(top + 1) % ROUND][0] * sign > ring[top][0] * sign else -1
                while k != under:
                    k = (k + step) % ROUND
                    line.append(ring[k])
                line = np.array(line)
                length = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))])
                sides[sign] = (length, line)
            self.paths.append(sides)

    def station(self, s, u):
        """Where the cloth is at a station, a length u from the middle of his top (his left +), and which way
        is out of it there."""
        length, line = self.paths[s][1 if u >= 0 else -1]
        a = min(abs(u), length[-1] - 1e-6)
        k = int(np.searchsorted(length, a, side="right")) - 1
        k = max(0, min(len(line) - 2, k))
        f = (a - length[k]) / max(length[k + 1] - length[k], 1e-9)
        p = line[k] + (line[k + 1] - line[k]) * f
        t = line[min(k + 2, len(line) - 1)] - line[max(k - 1, 0)]
        t = t / (np.linalg.norm(t) or 1.0)
        # (out of the cloth: to the left of the way it runs on his left side, to the right on his right)
        n = np.array([-t[1], t[0]]) if u >= 0 else np.array([t[1], -t[0]])
        return p, n

    def lengths(self, sign, y):
        """At a place along him, on one side: how long the cloth's line is from the middle of his top to the
        middle underneath, and how much of it (from underneath) lies flat on what he lies on."""
        f = (min(max(y, self.ys[0]), self.ys[-1]) - self.ys[0]) / STEP
        s = min(int(f), len(self.ys) - 2)
        f -= s
        out = []
        for k in (s, s + 1):
            length, line = self.paths[k][sign]
            up = np.nonzero(line[:, 1] > H.BOTTOM + 0.003)[0]
            out.append((length[-1], length[-1] - length[up[-1]] if len(up) else length[-1]))
        return out[0][0] + (out[1][0] - out[0][0]) * f, out[0][1] + (out[1][1] - out[0][1]) * f

    def at(self, u, y):
        """The same at any place along him: the point (x, y, z) and the way out (x, 0, z)."""
        f = (min(max(y, self.ys[0]), self.ys[-1]) - self.ys[0]) / STEP
        s = min(int(f), len(self.ys) - 2)
        f -= s
        (p0, n0), (p1, n1) = self.station(s, u), self.station(s + 1, u)
        p, n = p0 + (p1 - p0) * f, n0 + (n1 - n0) * f
        n = n / (np.linalg.norm(n) or 1.0)
        return np.array([p[0], y, p[1]]), np.array([n[0], 0.0, n[1]])


def blurred(grid, sigma):
    """A grid smoothed (cells without a value take their neighbours')."""
    have = np.isfinite(grid)
    val = np.where(have, grid, 0.0)
    w = have.astype(float)
    r = int(sigma * 3)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    for axis in (0, 1):
        val = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), axis, val)
        w = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), axis, w)
    return val / np.maximum(w, 1e-9)


class Drawn:
    """What the fitting needs to know of the model as drawn (from its finest level)."""

    def __init__(self, lv, body, skin):
        x, y, d = lv["pts"][:, 0], lv["pts"][:, 1], -lv["pts"][:, 2]
        fwd = point_normals(lv)[:, 0]
        hood = selection(lv, "head") + selection(lv, "neck1")
        front = (fwd > 0.3) & (hood < 0.5)
        # the top sheet's own smooth shape, on a grid of 2 cm
        self.x0, self.y0, self.cell = -0.60, -1.26, 0.02
        grid = np.full((62, 108), np.nan)
        for i in np.nonzero(front)[0]:
            a, b = int((x[i] - self.x0) / self.cell), int((y[i] - self.y0) / self.cell)
            if 0 <= a < 62 and 0 <= b < 108:
                grid[a, b] = d[i] if not np.isfinite(grid[a, b]) else max(grid[a, b], d[i])
        self.base = blurred(grid, 2.5)
        # how wide the bag is at each place along it
        self.wide = {}
        for i in np.nonzero(hood < 0.5)[0]:
            b = int(round(y[i] / 0.02))
            self.wide[b] = max(self.wide.get(b, 0.0), abs(x[i]))
        # his head in the model's rest position, as far out from its middle in every direction
        # (The rays saw his head from above and from the sides: nothing of the back of it, which he lies on. Seen in
        # game: a hood drawn in to that alone left his crown and the back of his head bare. So at every station
        # along his head its whole outline is taken: the hull of what was measured there, down to what he lies on.)
        cloud = []
        last = max(at for (kind, j), (at, pts) in body.cuts.items() if kind == "hscan" and pts)
        for (kind, j), (at, pts) in body.cuts.items():
            if kind == "hscan" and at >= 0.705 and pts:
                xs = [q[0] for q in pts]
                ring = H.hull(list(pts) + [(min(xs) * 0.8, 0.0), (max(xs) * 0.8, 0.0)])
                for (x1, z1), (x2, z2) in zip(ring, ring[1:] + ring[:1]):
                    steps = max(1, int(math.hypot(x2 - x1, z2 - z1) / 0.006))
                    cloud += [(x1 + (x2 - x1) * k / steps, at, z1 + (z2 - z1) * k / steps) for k in range(steps)]
                if at >= last - 0.011:
                    # his crown: the same outline, closing over 2 cm beyond the last station that met him
                    mx, mz = sum(q[0] for q in ring) / len(ring), sum(q[1] for q in ring) / len(ring)
                    for f, far in ((0.7, 0.008), (0.35, 0.016), (0.0, 0.02)):
                        cloud += [(mx + (qx - mx) * f, at + far, mz + (qz - mz) * f) for qx, qz in ring]
        back = np.linalg.inv(skin.M["head"])
        rest = np.array([(back @ np.append(skin.to_tool(p), 1.0))[:3] for p in cloud])
        self.middle = (rest.min(axis=0) + rest.max(axis=0)) / 2
        self.head = self.sphere(rest, np.max)
        hx = np.stack([x, -d, y], axis=1)[(hood > 0.5) & (y > HOOD_FROM[1])]
        self.hood = self.sphere(hx, np.mean)
        print("   his head in the rest position: middle %s, %.3f to %.3f out; the drawn hood there %.3f to %.3f out" % (
            np.round(self.middle, 3), np.nanmin(self.head), np.nanmax(self.head), np.nanmin(self.hood), np.nanmax(self.hood)))

    def bin(self, v):
        r = np.linalg.norm(v) or 1e-9
        return int((math.acos(max(-1.0, min(1.0, v[2] / r))) / math.pi) * 11.999), int(((math.atan2(v[1], v[0]) + math.pi) / (2 * math.pi)) * 23.999)

    def sphere(self, points, pick):
        """How far out a cloud of points is from the head's middle, by direction (12 by 24), every direction filled."""
        cells = {}
        for p in points:
            v = p - self.middle
            cells.setdefault(self.bin(v), []).append(np.linalg.norm(v))
        grid = np.full((12, 24), np.nan)
        for (a, b), vals in cells.items():
            grid[a, b] = pick(vals)
        while np.isnan(grid).any():
            new = grid.copy()
            for a in range(12):
                for b in range(24):
                    if np.isnan(grid[a, b]):
                        near = [grid[aa, bb % 24] for aa in (a - 1, a, a + 1) if 0 <= aa < 12 for bb in (b - 1, b, b + 1)]
                        near = [v for v in near if not np.isnan(v)]
                        if near:
                            new[a, b] = np.mean(near)
            grid = new
        # (smoothed a little round the head)
        out = grid.copy()
        for a in range(12):
            for b in range(24):
                near = [grid[aa, bb % 24] for aa in (a - 1, a, a + 1) if 0 <= aa < 12 for bb in (b - 1, b, b + 1)]
                out[a, b] = 0.5 * grid[a, b] + 0.5 * np.mean(near)
        return out

    def smooth_depth(self, x, y):
        a = min(max((x - self.x0) / self.cell, 0), 60.999)
        b = min(max((y - self.y0) / self.cell, 0), 106.999)
        i, j = int(a), int(b)
        fa, fb = a - i, b - j
        g = self.base
        return (g[i, j] * (1 - fa) + g[i + 1, j] * fa) * (1 - fb) + (g[i, j + 1] * (1 - fa) + g[i + 1, j + 1] * fa) * fb

    def half_width(self, y):
        b = int(round(y / 0.02))
        return max(self.wide.get(b, 0.0), self.wide.get(b - 1, 0.0), self.wide.get(b + 1, 0.0), 0.05)


def parts(lv):
    """The parts a level is made of: sets of points that hang together by faces or lie at the same place."""
    n = len(lv["pts"])
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    same = {}
    for i, q in enumerate(lv["pts"]):
        k = tuple(np.round(q, 4))
        if k in same:
            parent[find(i)] = find(same[k])
        else:
            same[k] = i
    for vs, fl, tex, mat in lv["faces"]:
        for v in vs[1:]:
            parent[find(v[0])] = find(vs[0][0])
    out = {}
    for i in range(n):
        out.setdefault(find(i), []).append(i)
    return sorted(out.values(), key=len, reverse=True)


def hood_cap(lv, hood):
    """The points of the hood's cap: the biggest part of the level that is all hood."""
    whole = [ids for ids in parts(lv) if all(hood[i] > 0.5 for i in ids)]
    return set(whole[0]) if whole else set()


def point_normals(lv):
    """For every point: how far its surface faces forward (out of the front of the bag), and the mean normal."""
    acc = np.zeros((len(lv["pts"]), 3))
    for vs, fl, tex, mat in lv["faces"]:
        for point, normal, u, v in vs:
            acc[point] -= lv["nrm"][normal]       # (the file keeps normals pointing inward)
    acc /= np.maximum(np.linalg.norm(acc, axis=1), 1e-9)[:, None]
    return np.stack([-acc[:, 2], acc[:, 0], acc[:, 1]], axis=1)


class Fit:
    def __init__(self):
        self.body = H.Body()
        self.skin = H.Skin(self.body)
        self.wide_line = Outline(self.body, CLEAR)
        self.sked_line = Outline(self.body, CLEAR, pads=False)
        self.line = self.wide_line
        self.in_sked = False
        self.source = read(SOURCE)
        self.opened = {}
        self.why = None       # a place (across, along, up): level() says what the drawn points next to it are
        self.drawn = Drawn(self.source[0], self.body, self.skin)
        # along him: the drawn model's rest position against how he lies
        along = lambda bone: float(self.from_tool(self.skin.posed(bone, self.skin.piv[bone]))[1])
        self.marks = [(END_DRAWN, H.FIRST - FOOT_END), (SOLES_DRAWN, H.FIRST), (0.0, along("pelvis")),
                      (float(self.skin.piv["neck"][2]), along("neck"))]
        print("   along him, drawn -> as he lies:", " ".join("%.3f->%.3f" % m for m in self.marks))

    def from_tool(self, t):
        own = np.array([-t[0], -t[1], t[2]])
        return self.body.axes @ own + self.body.origin - np.array([0.0, 0.0, H.DECK])

    def along(self, y):
        m = self.marks
        if y >= m[-1][0]:
            return m[-1][1] + (y - m[-1][0])
        for (a0, b0), (a1, b1) in zip(m, m[1:]):
            if y <= a1:
                return b0 + (b1 - b0) * (y - a0) / (a1 - a0)
        return m[-1][1]

    def relief(self, Y):
        """How much of a drawn crease's height is kept at this place along him."""
        if self.in_sked:
            return RELIEF_SKED
        near = min(max(lo - Y, Y - hi, 0.0) for lo, hi in STRAPS_ACROSS)
        return RELIEF_STRAP + (RELIEF - RELIEF_STRAP) * H.step(near / STRAP_EASE)

    def laid(self, x, y, d, facing, folded=None, press=1.0, sink=0.0):
        """Where a point of the drawn bag (across, along, forward; how far its surface faces forward) comes to
        lie on him, in the scan's axes. press: the share of a crease's height it keeps; sink: how far it lies
        off the cloth's line besides (minus: closer to him)."""
        Y = self.along(y)
        base = self.drawn.smooth_depth(x, y)
        u = x
        off = 0.0
        if folded is not None:
            u, y_f, off = folded
            Y = self.along(y_f)
        # Where the drawn bag is not wide enough to reach down to what he lies on (at his elbows: its edge ended a
        # hand over the ground and his elbow showed under it, seen in game on both litters and on the ground), the
        # top sheet is let out sideways just enough to reach it and turn under by 4 cm.
        side = 1 if u >= 0 else -1
        whole_s, flat_s = self.line.lengths(side, Y)
        if Y <= SHOULDERS[1]:
            u *= max(1.0, (whole_s - flat_s + 0.04) / self.drawn.half_width(y if folded is None else folded[1]))
        top, out = self.line.at(u, Y)
        if facing > 0.3:
            share, stands = 0.0, min(max((d - base) * self.relief(Y), LEAST - CLEAR), MOST)
        elif facing < -0.3:
            share, stands = 1.0, 0.0
        else:
            share, stands = min(1.0, max(0.0, (base - d) / max(base - BACK, 0.02))), 0.0
        top = top + out * (stands * press + off + sink)
        if share == 0.0:
            return top
        # The bottom sheet lies under him, from the middle outward to where his sides come down. Beyond his soles
        # it is tucked back under his heels (lying on flat there it stood out past the end of a litter's deck as a
        # dark board, seen in game).
        sign = 1 if x >= 0 else -1
        wide = self.drawn.half_width(y)
        whole, flat = self.line.lengths(sign, Y)
        reach = flat
        here, out_here = self.line.at(sign * (whole - reach * min(1.0, abs(x) / wide)), Y)
        under = here - out_here * 0.006
        under[1] = max(Y, H.FIRST + 0.02)
        under[2] = max(under[2], H.BOTTOM - 0.003) if under[2] > H.BOTTOM + 0.004 else H.BOTTOM - 0.003
        return top + (under - top) * share

    def hood(self, rest, kept=CRUMPLE_KEPT, clear=HOOD_CLEAR):
        """A point of the drawn hood (rest position, the pose's working axes), drawn in to his head. kept: the
        share of the drawn crumples it keeps; clear: how far off his head its smooth shape is."""
        v = rest - self.drawn.middle
        r = np.linalg.norm(v) or 1e-9
        a, b = self.drawn.bin(v)
        head, drawn = self.drawn.head[a, b], self.drawn.hood[a, b]
        # (never closer than HOOD_LEAST, and nothing of it, its string either, further off than MOST)
        new = min(max(head + clear + (r - drawn) * kept, head + min(HOOD_LEAST, clear)), head + clear + MOST * kept / CRUMPLE_KEPT)
        return self.drawn.middle + v * (new / r)

    def level(self, lv, opened=False, sked=False, detail=1, shadow_open=False):
        self.line = self.sked_line if sked else self.wide_line
        self.in_sked = sked
        kind = None
        if opened:
            # the cover is cut clean along the fold line (tools/hpmk_opened.py)
            hood0 = np.clip(selection(lv, "head") + selection(lv, "neck1"), 0, 1)
            kind0 = O.kinds(lv, parts, hood0)
            f0 = point_normals(lv)[:, 0]
            f0[kind0 > 0] = 1.0
            q0 = lv["pts"]
            top0 = [hood0[i] < 0.5 and (f0[i] > -0.3 or self.drawn.smooth_depth(q0[i, 0], q0[i, 1]) + q0[i, 2] < 0.015)
                    for i in range(len(q0))]
            # (Of the cover: everything but what faces backward and lies deeper than the cover's own smooth shape.
            # The walls of the drawn bag's opening round his neck, which face sideways half way down to the
            # bottom sheet, were taken for bottom sheet at first: they stayed when the cover was taken off and
            # stood over his chest and beside his throat in pieces, found by casting the camera's ray through them.)
            first = lv is self.source[0]
            lv, kind, counts = O.clipped(lv, kind0, top0)
            if sked not in self.opened:
                self.opened[sked] = O.Opened(self, sked)
            op = self.opened[sked]
            if first:
                print("   opened: %d faces of the cover taken off, %d cut at the fold; the cut comes down at %.3f (his left) and %.3f along him" % (
                    counts[0], counts[1], op.cut_l, op.cut_r))
        P = lv["pts"]
        x, y, d = P[:, 0], P[:, 1], -P[:, 2]
        facing = point_normals(lv)[:, 0]
        w_head, w_neck = selection(lv, "head"), selection(lv, "neck1")
        hood = np.clip(w_head + w_neck, 0, 1)
        n = len(P)
        # What is sewn or stuck on the bag (its label, the hood's cord and toggles) lies on the top sheet whole:
        # every point of it, whichever way its own surface faces. (Seen in game: the underside of the label's
        # rolled edge was taken for bottom sheet and lay at the ground beside his elbow, a white lump.)
        if kind is None:
            for ids in parts(lv)[1:]:
                facing[ids] = 1.0
        else:
            facing[kind > 0] = 1.0
        target = np.zeros((n, 3))
        folded = np.zeros(n, bool)
        if opened:
            # near the fold the cover lies down on the blanket, and under the flap its creases are pressed flat
            press, sink, dist = op.treat(x, y, facing, hood, kind, CLEAR)
        # Opened, the hood is a thing of its own: all of it goes with his head and is drawn in to it, down to
        # where it ends under his chin. (On the closed bag its lower part lies on the cover.)
        of_hood = (O.kinds(lv, parts, hood) == 2) if shadow_open else np.zeros(n, bool)
        # (The hood's part of the shadow's level is drawn as a box 80 cm wide. Half bound to his head it stood
        # 25 cm out on both sides of it, hidden under the closed bag's head end; with that gone it cast the
        # shadow of a sheet beside his head, seen in game. Opened, it is drawn in to his head whole.)
        own_hood = (kind == 2) if opened else (of_hood & (hood >= 0.5))
        folded = own_hood.copy()
        # The level that casts the shadow, for the opened bag: what is taken off (his chest's cover, the bag's
        # head end, what hangs from the hood) is drawn together into a point inside him, and the faces that lose
        # their size by it are left out below: the shape stays closed and ends at the fold. (Left as the closed
        # bag's it stood 3 cm over his chest: the blanket under it lay in its shadow but for the patches that
        # reached out of it, light blotches on a dark blanket, seen in game and taken for glare at first. Drawn
        # in by a share only, its head end cast a shadow of the bag's shape beside his head.)
        together = {}
        for i in range(n):
            if opened:
                target[i] = self.laid(x[i], y[i], d[i], facing[i], None, press[i], sink[i])
            elif shadow_open and hood[i] < 0.5 and (of_hood[i] or (O.FOLD.dist(x[i], y[i]) > 0 and (facing[i] > -0.3 or y[i] >= O.SHADOW_BACK))):
                to = O.SHADOW_NECK if of_hood[i] else O.SHADOW_CHEST
                target[i] = (0.0, to[0], to[1])
                together.setdefault(to, []).append(i)
                hood[i] = 0.0
            else:
                target[i] = self.laid(x[i], y[i], d[i], facing[i])
            if hood[i] > 0 or own_hood[i]:
                rest = np.array([x[i], -d[i], y[i]])
                with_head = 1.0 if own_hood[i] else H.step((y[i] - HOOD_FROM[0]) / (HOOD_FROM[1] - HOOD_FROM[0])) * hood[i]
                if with_head > 0:
                    if shadow_open:
                        drawn_in = self.hood(rest, 0.0, 0.004)
                    elif own_hood[i]:
                        # Its lower edge, under his chin, is an elastic hem: smooth and close. (With the crumples
                        # of the rest it hung there in points, over the padded strips: seen in game.)
                        e = H.step((y[i] - O.CHIN) / 0.06)
                        drawn_in = self.hood(rest, 0.12 + (CRUMPLE_KEPT - 0.12) * e, 0.014 + (HOOD_CLEAR - 0.014) * e)
                    else:
                        drawn_in = self.hood(rest)
                    posed = self.from_tool((self.skin.M["head"] @ np.append(drawn_in, 1.0))[:3])
                    # (The hood lies on what he lies on, not under it: sunk as the bag's bottom sheet is, its inside
                    # under his head was not there to see, and looking into the hood from above one saw the
                    # ground between his crown and its rim.)
                    posed[2] = max(posed[2], 0.005)
                    target[i] = target[i] + (posed - target[i]) * with_head
            if sked:
                target[i] = H.held_in_sked(H.in_sked(list(target[i]), self.body))
        # The top sheet's creases rounded (SMOOTH): every point of the bag's cover that is not of the hood, not of
        # the bottom sheet under him and not drawn together for the shadow, among neighbours that are so too.
        cover = (hood < 0.5) & ~own_hood & (facing > -0.3)
        for to, ids in together.items():
            cover[ids] = False
        near = [set() for _ in range(n)]
        for vs, fl, tex, mat in lv["faces"]:
            ids = [v[0] for v in vs]
            for a in ids:
                near[a].update(b for b in ids if b != a)
        inner = [i for i in range(n) if cover[i] and near[i] and all(cover[b] for b in near[i])]
        nb = [np.array(sorted(near[i])) for i in inner]
        inner = np.array(inner, int)
        passes, lam, mu = SMOOTH
        # (not the level that casts the shadow: coarse, smoothed on its own it stood out of the smoothed bag in
        # places and shaded it in dark patches, seen in game; it is drawn a little inside the bag instead, below)
        shadow_level = lv["res"] >= 1000
        if shadow_level:
            passes = 0
        for _ in range(passes):
            for f in (lam, mu):
                mean = np.array([target[b].mean(axis=0) for b in nb]) if len(inner) else np.zeros((0, 3))
                target[inner] = target[inner] + f * (mean - target[inner])
        if sked:
            for i in inner:
                target[i] = H.held_in_sked(H.in_sked(list(target[i]), self.body))
        # The smoothed points are lit as the smoothed surface lies: each one's normal is the mean of its faces' (as
        # laid, scan axes), with a little of the drawn one's turn kept for the cloth's texture (SMOOTH_DRAWN). (With
        # the drawn normals alone the flattened creases still shaded as sharp ones: dark blotches, seen in game.)
        smoothed = set(inner.tolist())
        geom = np.zeros((n, 3))
        for vs, fl, tex, mat in lv["faces"]:
            ids = [v[0] for v in vs]
            q = target[ids]
            for k in range(1, len(ids) - 1):
                c = np.cross(q[k] - q[0], q[k + 1] - q[0])
                for a in (ids[0], ids[k], ids[k + 1]):
                    geom[a] += c
        if shadow_level:
            # the shadow's cover SHADOW_IN inside the bag's: along its own normal, toward his middle
            for i in np.nonzero(cover)[0]:
                g = geom[i]
                if np.linalg.norm(g) < 1e-12:
                    continue
                g = g / np.linalg.norm(g)
                if g @ (target[i] - np.array([0.0, target[i][1], 0.08])) < 0:
                    g = -g
                target[i] = target[i] - g * SHADOW_IN
            smoothed = set()
        # opened: the hood ends in a straight hem under his chin (hpmk_opened.HOOD_ENDS). Its faces that come to lie
        # wholly below that are left out; corners of the others that are below it are brought up to the hem.
        below = np.zeros(n, bool)
        if opened:
            below = own_hood & (target[:, 1] < O.HOOD_ENDS)
            if self.why is not None and lv["res"] == self.source[0]["res"]:
                used = {v[0] for vs, fl, tex, mat in lv["faces"] for v in vs}
                near = sorted(used, key=lambda i: np.linalg.norm(target[i] - self.why))[:6]
                for i in near:
                    print("   why: %.3f m off, lies at %s, drawn at across %.3f along %.3f forward %.3f, facing %.2f, head %.2f, kind %d, of the hood %s, below its hem %s" % (
                        np.linalg.norm(target[i] - self.why), np.round(target[i], 3), x[i], y[i], d[i], facing[i], hood[i], kind[i], own_hood[i], below[i]))
            target[below, 1] = O.HOOD_ENDS
        # opened: what is drawn new for it (the flap, the bottom sheet beside him, the blanket)
        n_drawn = n
        extra = []
        if opened:
            for name, mesh in op.meshes(detail):
                extra.append((name, len(target), mesh))
                target = np.vstack([target, np.array(mesh.pts)])
            n = len(target)
            own_hood = np.concatenate([own_hood, np.zeros(n - n_drawn, bool)])
            hood = np.concatenate([hood, np.zeros(n - n_drawn)])
            y = np.concatenate([y, np.zeros(n - n_drawn)])
        # bound to the bones under it, and carried back
        tool = np.array([self.skin.to_tool(p) for p in target])
        back, weights = [], {}
        new = np.zeros((n, 3))
        for i in range(n):
            w = self.skin.weights(tool[i])
            with_head = 1.0 if own_hood[i] else H.step((y[i] - HOOD_FROM[0]) / (HOOD_FROM[1] - HOOD_FROM[0])) * hood[i]
            if with_head > 0.02:
                w = [(bone, v * (1 - with_head)) for bone, v in w if bone != "head"] + [("head", with_head + sum(v for bone, v in w if bone == "head") * (1 - with_head))]
                w = sorted(w, key=lambda bw: -bw[1])[:4]
                total = sum(v for _, v in w)
                w = [(bone, v / total) for bone, v in w if v / total >= 0.03]
                total = sum(v for _, v in w)
                w = [(bone, v / total) for bone, v in w]
            inv = self.skin.back(w)
            back.append(inv)
            new[i] = H.to_file((inv @ np.append(tool[i], 1.0))[:3])
            for bone, v in w:
                weights.setdefault(bone, {})[i] = v
        # the normals: turned as the surface round each point was turned (from three points beside it)
        e = 0.004
        nrm = [tuple(v) for v in lv["nrm"]]
        turn = {}

        def turned(i):
            if i not in turn:
                if hood[i] > 0.5 or folded[i]:
                    turn[i] = None
                else:
                    o = self.laid(x[i], y[i], d[i], facing[i])
                    jx = (self.laid(x[i] + e, y[i], d[i], facing[i]) - o) / e
                    jy = (self.laid(x[i], y[i] + e, d[i], facing[i]) - o) / e
                    jd = np.cross(jx, jy)
                    jx, jy, jd = (v / (np.linalg.norm(v) or 1.0) for v in (jx, jy, jd))
                    # drawn (across, along, forward) -> scan axes -> the pose's -> back to rest -> the file's
                    scan = np.stack([jx, jy, jd], axis=1)
                    turn[i] = back[i][:3, :3] @ np.array([self.skin.turned(scan[:, c]) for c in range(3)]).T
            return turn[i]

        # The hood's cap is drawn inside out (nine faces in ten of it face his head: from outside one saw through
        # it, seen in game). Every face of it that faces the head's middle is turned round.
        cap = hood_cap(lv, hood)

        # The hood has an inside. (Drawn as one skin, and that turned to face outward: looking into it from
        # above his head one saw through its far side, "the inside of the hood must not be see through",
        # 2026-11-20.) Every face of its cloth gets a second one the other way round, of the same cloth: the
        # photographs show no blue at the hood, and with the lining's picture the turned-in hem round his face
        # was a bright blue ring (seen in game).
        lined = [0]

        def inside_of(corners, tex, mat):
            if lv["res"] >= 1000 or not tex.lower().endswith(b"hpmk_out_co.paa"):
                return
            if not all(hood[v[0]] > 0.5 or own_hood[v[0]] for v in corners):
                return
            rev = []
            for point, normal, u, v in corners[::-1]:
                nrm.append(tuple(-c for c in nrm[normal]))
                rev.append([point, len(nrm) - 1, u, v])
            faces.append([rev, lv["faces"][0][1], tex, mat])
            lined[0] += 1
        middle = np.array(H.to_file(self.drawn.middle))
        turned_round = 0
        done = {}
        faces = []
        for vs, fl, tex, mat in lv["faces"]:
            if cap and all(v[0] in cap for v in vs):
                q = P[[v[0] for v in vs]]
                if np.cross(q[1] - q[0], q[2] - q[0]) @ (q.mean(axis=0) - middle) > 0:
                    fixed = []
                    for point, normal, u, v in vs[::-1]:
                        nrm.append(tuple(-c for c in lv["nrm"][normal]))
                        fixed.append([point, len(nrm) - 1, u, v])
                    faces.append([fixed, fl, tex, mat])
                    inside_of(fixed, tex, mat)
                    turned_round += 1
                    continue
            if tex.lower().endswith(b"hpmk_in_co.paa") and all(hood[v[0]] > 0.5 for v in vs):
                continue                      # the blue disc where his face is
            if opened and all(below[v[0]] for v in vs):
                continue                      # of the hood, below its hem under his chin
            out = []
            for point, normal, u, v in vs:
                key = (point, normal)
                if key not in done:
                    m = turned(point)
                    if m is None:
                        done[key] = normal
                    else:
                        drawn_n = np.array([lv["nrm"][normal][0], lv["nrm"][normal][1], -lv["nrm"][normal][2]])
                        t = m @ drawn_n
                        t = t / (np.linalg.norm(t) or 1.0)
                        if point in smoothed and np.linalg.norm(geom[point]) > 1e-12:
                            g = back[point][:3, :3] @ self.skin.turned(geom[point] / np.linalg.norm(geom[point]))
                            g = g / (np.linalg.norm(g) or 1.0)
                            if g @ t < 0:
                                g = -g
                            t = g * (1 - SMOOTH_DRAWN) + t * SMOOTH_DRAWN
                            t = t / (np.linalg.norm(t) or 1.0)
                        done[key] = len(nrm)
                        nrm.append(tuple(H.to_file(t)))
                out.append([point, done[key], u, v])
            faces.append([out, fl, tex, mat])
            inside_of(out, tex, mat)
            if opened and all(kind[v[0]] == 0 and hood[v[0]] < 0.5 and facing[v[0]] > 0.3
                              and -0.12 < dist[v[0]] <= 1e-6 for v in vs):
                # beside its cut edges the cover shows its lining to who looks under it
                rev = []
                for point, m, u, v in out[::-1]:
                    nrm.append(tuple(-c for c in nrm[m]))
                    rev.append([point, len(nrm) - 1, u, v])
                faces.append([rev, fl, INSIDE[0], INSIDE[1]])
        for name, first_point, mesh in extra:
            out_of = mesh.normals()
            at = {}
            for i, v in enumerate(out_of):
                t = back[first_point + i][:3, :3] @ self.skin.turned(-v)      # (the file keeps normals pointing inward)
                at[i] = len(nrm)
                nrm.append(tuple(H.to_file(t / (np.linalg.norm(t) or 1.0))))
            for ids, uvs, tex in mesh.faces:
                # (where the flap goes under him, or a SKED's wall holds it, points come to lie in one place:
                # a face without a size is left out; the game's model compiler warns of each)
                q = target[[first_point + i for i in ids]]
                size = np.linalg.norm(np.cross(q[1] - q[0], q[2] - q[0]))
                if len(ids) == 4:
                    size = min(size, np.linalg.norm(np.cross(q[2] - q[0], q[3] - q[0])))
                short = min(np.linalg.norm(q[a] - q[(a + 1) % len(q)]) for a in range(len(q)))
                if size < 1e-6 or short < 0.0004:
                    continue
                faces.append([[[first_point + i, at[i], uv[0], uv[1]] for i, uv in zip(ids, uvs)], lv["faces"][0][1], tex[0], tex[1]])
        if lined[0] and lv["res"] == self.source[0]["res"]:
            print("   %d faces of the hood given an inside" % lined[0])
        if turned_round and lv is self.source[0]:
            print("   %d faces of the hood's cap turned round" % turned_round)
        flags = np.concatenate([lv["flags"], np.full(n - n_drawn, lv["flags"][0], lv["flags"].dtype)])
        nrm = np.array(nrm)
        # A corner the drawing gives no normal (ten of them in the level that casts the shadow: the game's model
        # compiler warns of each, "very small normal 0,0,0") gets its face's own.
        for vs, fl, tex, mat in faces:
            if any(np.linalg.norm(nrm[v[1]]) < 0.1 for v in vs):
                q = new[[v[0] for v in vs]]
                g = np.cross(q[1] - q[0], q[2] - q[0])
                g = g / (np.linalg.norm(g) or 1.0)
                for v in vs:
                    if np.linalg.norm(nrm[v[1]]) < 0.1:
                        nrm[v[1]] = g
        marked = {name: np.concatenate([np.frombuffer(data, "u1", n_drawn), np.zeros(n - n_drawn, "u1")])
                  for name, data in lv["tags"] if not name.startswith("#") and name not in ("pelvis", "head", "neck1")}
        edges = {name: np.frombuffer(data, "<u4").reshape(-1, 2) for name, data in lv["tags"] if name == "#SharpEdges#"}
        if together:
            first = {i: ids[0] for ids in together.values() for i in ids}
            kept_faces = []
            for vs, fl, tex, mat in faces:
                for v in vs:
                    v[0] = first.get(v[0], v[0])
                if len({v[0] for v in vs}) == len(vs):
                    kept_faces.append([vs, fl, tex, mat])
            edges_used = {}
            for vs, fl, tex, mat in kept_faces:
                for a in range(len(vs)):
                    e = tuple(sorted((vs[a][0], vs[(a + 1) % len(vs)][0])))
                    edges_used[e] = edges_used.get(e, 0) + 1
            print("   shadow, opened: %d points drawn together, %d of %d faces left; edges not between two faces: %d" % (
                sum(len(ids) for ids in together.values()), len(kept_faces), len(faces), sum(1 for c in edges_used.values() if c != 2)))
            faces = kept_faces
        if opened or together:
            # What no face uses any more is left out: the points of the cover that was taken off (a quarter of
            # the drawing) and the normals of its faces went into the model as dead weight.
            used, used_n = np.zeros(n, bool), np.zeros(len(nrm), bool)
            for vs, fl, tex, mat in faces:
                for v in vs:
                    used[v[0]] = True
                    used_n[v[1]] = True
            to, to_n = np.cumsum(used) - 1, np.cumsum(used_n) - 1
            for vs, fl, tex, mat in faces:
                for v in vs:
                    v[0], v[1] = int(to[v[0]]), int(to_n[v[1]])
            weights = {bone: {int(to[point]): v for point, v in by_point.items() if used[point]} for bone, by_point in weights.items()}
            marked = {name: data[used] for name, data in marked.items()}
            edges = {name: to[pairs[used[np.minimum(pairs, n - 1)].all(axis=1) & (pairs < n).all(axis=1)]] for name, pairs in edges.items()}
            if lv["res"] == self.source[0]["res"]:
                print("   %d of %d points and %d of %d normals left out as unused" % (n - used.sum(), n, len(nrm) - used_n.sum(), len(nrm)))
            new, target, flags, nrm = new[used], target[used], flags[used], nrm[used_n]
            n = len(new)
        tags = []
        for bone, by_point in weights.items():
            if not by_point:
                continue
            blob = bytearray(n + len(faces))
            for point, v in by_point.items():
                blob[point] = H.p3d_skinned.weight_byte(v)
            for f, (vs, fl, tex, mat) in enumerate(faces):
                if all(blob[v[0]] for v in vs):
                    blob[n + f] = 1
            tags.append((bone, bytes(blob)))
        for name, data in lv["tags"]:
            if name in ("pelvis", "head", "neck1", "#UVSet#", "#EndOfFile#"):
                continue
            if name in marked:
                # (another selection of the drawing: its faces are no longer the same count)
                data = marked[name].tobytes() + bytes(len(faces))
            elif name in edges:
                data = edges[name].astype("<u4").tobytes()
            tags.append((name, data))
        tags.append(("#EndOfFile#", b""))
        return dict(pts=new, flags=flags, nrm=nrm, faces=faces, tags=tags, res=lv["res"]), target


def preview(path, lv, target):
    """The shell as it lies on him (scan axes), with each face's picture, to look at outside the game."""
    with open(path, "w") as f:
        for p in target:
            f.write("v %.5f %.5f %.5f\n" % tuple(p))
        for vs, fl, tex, mat in lv["faces"]:
            f.write("usemtl %s\n" % tex.decode("latin1").replace("\\", "/").split("/")[-1])
            f.write("f " + " ".join(str(v[0] + 1) for v in vs) + "\n")
            # (for the pictures drawn outside the game: where each corner is in its picture)
            f.write("#uv " + " ".join("%.4f %.4f" % (v[2], v[3]) for v in vs) + "\n")


def main():
    fit = Fit()
    look = sys.argv[2:] if sys.argv[1:2] == ["--look"] else None
    if look and "--why" in look:
        fit.why = np.array([float(a) for a in look[look.index("--why") + 1].split(",")])
    for name, opened, sked in (("hpmk_worn", False, False), ("hpmk_worn_sked", False, True), ("hpmk_worn_open", True, False),
                               ("hpmk_worn_open_sked", True, True)):
        if look is not None and name not in look:
            continue
        levels = []
        for k, lv in enumerate(fit.source[:1] if look is not None else fit.source):
            if len(lv["pts"]) == 0:
                levels.append(dict(pts=lv["pts"], flags=lv["flags"], nrm=lv["nrm"], faces=lv["faces"], tags=lv["tags"], res=lv["res"]))
                continue
            # (what is drawn new for the opened bag is coarser in the lower levels of detail)
            new, target = fit.level(lv, opened and lv["res"] < 1000, sked, (1, 1, 2, 3, 4)[min(k, 4)], opened and lv["res"] >= 1000)
            levels.append(new)
            if lv is fit.source[0]:
                preview(Path(__file__).with_name("assets") / (name + "_preview.obj"), new, target)
                print("%s: %d points, %d faces (drawn %d); as laid: across %.3f..%.3f, along %.3f..%.3f, up %.3f..%.3f" % (
                    name, len(new["pts"]), len(new["faces"]), len(lv["faces"]), target[:, 0].min(), target[:, 0].max(),
                    target[:, 1].min(), target[:, 1].max(), target[:, 2].min(), target[:, 2].max()))
                if not opened and look is None:
                    np.save(OUTLINE.with_name("hpmk_shell_outline_sked.npy") if sked else OUTLINE, target)
        if look is None:
            write(OUT / (name + ".p3d"), levels)
            print("wrote", OUT / (name + ".p3d"))


if __name__ == "__main__":
    main()
