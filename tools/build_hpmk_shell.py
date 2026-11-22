"""Build the HPMK shell a casualty wears: addons/acme_hpmk/hpmk_worn.p3d (closed), hpmk_worn_open.p3d (chest
and left arm uncovered, the cover folded over to his right) and hpmk_worn_sked.p3d (closed, its foot end inside
the SKED's foot cover).

The shell is a bag round the whole casualty with a hood that leaves the face free. It is built round the
casualty as he lies in the litter pose (acme_litter_side.rtm), from the outline measured in the game
(tools/assets/hpmk_body_scan.json, see tools/hpmk_body.py): at every station along him the bag is the outline a
cloth pulled round body and arms takes (the convex hull of what is there), a clearance further out. Every point is
then bound to the bones nearest to it and carried back to where it has to be in the model for the pose to bring it
exactly there: so in that pose the shell is exactly what was built, and in every other pose it goes with the
limbs under it.

Axes used while building: the Talon II's (x across with the casualty's left +, y along toward the head), z up
from what he lies on. The build has to be run again whenever the litter pose changes (after a new scan).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import build_litter_poses as poses  # noqa: E402
import p3d_skinned  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCAN = Path(__file__).with_name("assets") / "hpmk_body_scan.json"
OUT = ROOT / "addons/acme_hpmk"
DECK = 0.145          # the height of what he lies on, in the scan's axes

# ---------------------------------------------------------------- the shape
# The bag stands this far off the measured outline. That outline is his fire geometry, the same whatever he
# wears: about a centimetre proud of bare skin on trunk and thighs, level with it at the arms. Seen in game with
# 2.8 cm: nothing of a bare casualty came through, but of one in a combat uniform the gloves, a thigh pocket and
# the toe of a boot did.
CLEAR_BODY = 0.042
CLEAR_HEAD = 0.010    # the hood: an elastic cap, snug
# The real HPMK-I shell is a tarp laid round him, a top sheet over a bottom sheet: it does not narrow to his neck.
# Its top edge runs straight across, BAG_TOP along him (under his chin), as wide as his shoulders: up to there
# every station from SHOULDERS on has the outline of his shoulders. Over the last EDGE_IN the top sheet comes
# down onto him (EDGE_CLEAR off him at the edge). From the edge on it is the hood, a piece of its own.
BAG_TOP = 0.695
SHOULDERS = (0.575, 0.625)
EDGE_IN, EDGE_CLEAR = 0.04, 0.012
FEET_FROM, FEET_MORE = -0.50, 0.014    # boots are bigger than feet and shins (the room comes in over 12 cm)
HANDS = (-0.34, 0.04)                  # along him: where his hands lie
HANDS_MORE = 0.016                     # gloves: this much more room sideways there
# Sideways the bag is not let out further than this from the middle (the SKED is 0.272 wide inside where its
# straps are fixed), except that it always clears the measured outline by SIDE_LEAST.
SIDE_MOST, SIDE_LEAST = 0.288, 0.016
BODY_STEP, HEAD_STEP = 0.02, 0.01
FIRST, LAST = -0.90, 0.93   # his soles and his crown
FOOT_END = 0.055      # how far the bag goes on beyond his feet: down behind his soles, the rest tucked under
BOTTOM = -0.012       # the lowest the bag goes under what he lies on
# Along him the cloth leaves a high place no steeper than this (rise over run): the tarp is stiff and spans from
# his toes to his shins and from his chest to his belly; the hood is thin and follows his head.
DROP_BAG, DROP_HOOD = 0.6, 1.4
AROUND = 64           # points round the bag
# A tarp does not wrinkle, it breaks into flat pieces that meet in creases, mostly triangles: the bag's surface
# is pushed out by a faceted field (flat triangles FACET_CELL across, up to FACET high). The hood is crumpled:
# the same, much finer.
# (cells: so many faces of the finest mesh along and round; 4 is 8 cm along the bag, 2 is 2 cm along the hood)
FACET, FACET_CELL = 0.026, 4
CRUMPLE, CRUMPLE_CELL = 0.008, 2
GATHER = (0.004, 0.015, 0.030)   # the hood's elastic edge is gathered: puckers this high, this far apart, dying out over this
# The face stays free: an opening in the hood, seen from above. Its middle along him, half its length, half its
# width, how square it is (2: an oval), and how far the hood's edge there stands off the measured head.
FACE = (0.792, 0.084, 0.060)
FACE_SQUARE = 2.8
RIM_CLEAR = 0.004
RIM_BLEND = 0.035     # the hood comes down to the edge over this distance
HEM = (0.007, 0.024)  # the edge is turned in: this far toward the middle of the opening, and this far down
HEM_UNDER = (0.016, 0.050)   # and a second strip under that one, to here (it ends inside his head)
TILE = 0.60           # the cloth's picture repeats every 0.60 m
# Opened: from the first to the second place along him the cover is taken off his chest and left side, from a
# line this far to the right of his middle, and laid over to his right, inside up.
OPEN_ALONG = (0.11, BAG_TOP)
OPEN_FOLD = -0.05
FLAP_OFF = 0.012

# In a SKED the foot end of the bag has to stay inside the SKED's foot cover: from SKED_FROM along the SKED (its own
# axes; the casualty's pelvis is at SKED_PELVIS there, at TALON_PELVIS in the axes used here) no point of the bag
# is further out or higher than the SKED's own shape at that place, less SKED_ROOM, and the bag ends SKED_END.
SKED_MODEL = ROOT / "addons/acme_sked/sked_wrapped.p3d"
SKED_PELVIS, TALON_PELVIS = 0.056, 0.127
# (only where the cover is closed round the feet: with the open stretch before it included, from -0.84, the bag was
# pressed in further than his feet are wide there and a foot came through it, seen in game)
SKED_FROM, SKED_END, SKED_ROOM = -0.925, -1.030, 0.012

OUTSIDE = (r"acme_hpmk\data\hpmk_out_co.paa", r"acme_hpmk\data\hpmk_out.rvmat")
INSIDE = (r"acme_hpmk\data\hpmk_in_co.paa", r"acme_hpmk\data\hpmk_in.rvmat")
EDGE = (r"acme_hpmk\data\hpmk_edge_co.paa", r"acme_hpmk\data\hpmk_edge.rvmat")

# ---------------------------------------------------------------- the bones a point is bound to
# bone: the joint its length runs to, or a point given from its own joint in the model's rest position
REACH = {"pelvis": "spine", "spine": "spine1", "spine1": "spine2", "spine2": "spine3", "spine3": "neck",
         "neck": "neck1", "neck1": "head", "head": (0.0, 0.0, 0.17)}
for _s in ("left", "right"):
    REACH.update({_s + "shoulder": _s + "arm", _s + "arm": _s + "forearm", _s + "forearm": _s + "hand",
                  _s + "hand": _s + "handmiddle1", _s + "upleg": _s + "leg", _s + "leg": _s + "foot",
                  _s + "foot": (0.0, 0.16, -0.05)})
BONES_PER_POINT = 3


def step(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def hull(points):
    """Convex hull of 2D points, counter-clockwise."""
    pts = sorted(set((round(x, 5), round(y, 5)) for x, y in points))
    if len(pts) < 3:
        return pts

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out
    lower, upper = half(pts), half(reversed(pts))
    return lower[:-1] + upper[:-1]


def grown(points, by):
    """The hull of the points, standing off them by a distance all round."""
    ring = [(by * math.cos(a), by * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    return hull([(x + dx, y + dy) for x, y in hull(points) for dx, dy in ring])


def reach(poly, centre, angle):
    """How far a convex polygon reaches from a point inside it in a direction."""
    cx, cy = centre
    dx, dy = math.cos(angle), math.sin(angle)
    best = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - cx) * ey - (y1 - cy) * ex) / den
        u = ((x1 - cx) * dy - (y1 - cy) * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9:
            best = max(best, t)
    return best


class Body:
    """The measured outline."""

    def __init__(self):
        d = json.loads(SCAN.read_text())
        self.origin = np.array(d["frame"][0])
        self.axes = np.array(d["frame"][1:4]).T      # columns: the casualty's own axes in the scan's
        self.cuts = {}
        for kind, side, along, x0, dx in (("scanU", "sideU", 0.02, -0.34, 0.01), ("hscan", "hside", 0.01, -0.20, 0.005)):
            for j, row in d[kind].items():
                pts = [(x0 + i * dx, v - DECK) for i, v in enumerate(row) if v >= 0]
                for sign, reaches in zip((-1, 1), d[side][j]):
                    pts += [(sign * v, 0.10 + k * 0.01 - DECK) for k, v in enumerate(reaches) if v >= 0]
                self.cuts[(kind, int(j))] = (int(j) * along, pts)
        self.head_rows = {int(j): row for j, row in d["hscan"].items()}

    def cut(self, y, reach_along):
        """All measured points of him within a distance along of y: [(x, z)], z over what he lies on."""
        out = []
        for (kind, j), (at, pts) in self.cuts.items():
            if abs(at - y) <= reach_along + 1e-9 and ((kind == "hscan") == (at >= 0.60)):
                out += pts
        return out

    def head_top(self, x, y):
        """The top of his head under (x, y), or None."""
        j, i = round(y / 0.01), round((x + 0.20) / 0.005)
        best = None
        for jj in (j - 1, j, j + 1):
            row = self.head_rows.get(jj)
            if row:
                for ii in (i - 1, i, i + 1):
                    if 0 <= ii < len(row) and row[ii] >= 0:
                        best = max(best or -9, row[ii] - DECK)
        return best


def smooth(values, sigma):
    n = len(values)
    out = np.zeros(n)
    for i in range(n):
        w = np.exp(-0.5 * ((np.arange(n) - i) / sigma) ** 2)
        out[i] = (w * values).sum() / w.sum()
    return out


def _rand(i, j, salt=0.0):
    v = math.sin(i * 127.1 + j * 311.7 + salt * 74.7) * 43758.5453
    return v - math.floor(v)


def cell_of(s, k, n, salt):
    """The cell of the crease grid a point of the mesh is in (n faces along and round): its number along and
    round, where the point is in it (0..1 twice), and whether it is cut from its first corner to the opposite one."""
    i, j = s // n, k // n
    return i, j, (s - i * n) / n, (k - j * n) / n, _rand(i, j, salt + 1.0) < 0.5


def facets(s, k, n, salt):
    """The faceted field, 0..1, at a point of the mesh: every cell of the crease grid is two flat triangles."""
    i, j, fu, fv, straight = cell_of(s, k, n, salt)
    h = lambda di, dj: _rand(i + di, j + dj, salt)
    if straight:
        if fu >= fv:
            return h(0, 0) + (h(1, 0) - h(0, 0)) * fu + (h(1, 1) - h(1, 0)) * fv
        return h(0, 0) + (h(1, 1) - h(0, 1)) * fu + (h(0, 1) - h(0, 0)) * fv
    if fu + fv <= 1:
        return h(0, 0) + (h(1, 0) - h(0, 0)) * fu + (h(0, 1) - h(0, 0)) * fv
    return h(1, 1) + (h(0, 1) - h(1, 1)) * (1 - fu) + (h(1, 0) - h(1, 1)) * (1 - fv)


def creased(s, k, n, salt, corners):
    """The face between stations s, s+1 and points k, k+1 (corners: at (s,k), (s,k+1), (s+1,k+1), (s+1,k)) as the
    flat pieces of the crease grid it belongs to: [(corners, piece)], split in two where the cut runs through it."""
    i, j = s // n, k // n
    a, b = s - i * n, k - j * n
    p00, p01, p11, p10 = corners
    if _rand(i, j, salt + 1.0) < 0.5:
        if a > b:
            return [(corners, (salt, i, j, 0))]
        if a < b:
            return [(corners, (salt, i, j, 1))]
        return [([p00, p10, p11], (salt, i, j, 0)), ([p00, p11, p01], (salt, i, j, 1))]
    if a + b < n - 1:
        return [(corners, (salt, i, j, 0))]
    if a + b > n - 1:
        return [(corners, (salt, i, j, 1))]
    return [([p00, p10, p01], (salt, i, j, 0)), ([p10, p11, p01], (salt, i, j, 1))]


def rings(body, around, step_scale=1):
    """The shell as rings of points round him at stations along him: ys, centres, angles, radii[s][k], how far out
    sideways each ring may go (to his right, to his left), and the first station of the hood."""
    bag = list(np.arange(FIRST, 0.60 - 1e-9, BODY_STEP * step_scale)) + list(np.arange(0.60, BAG_TOP - 0.004, HEAD_STEP * step_scale)) + [BAG_TOP]
    hood = [BAG_TOP + 0.004] + list(np.arange(round(BAG_TOP + 0.015, 2), LAST + 1e-9, HEAD_STEP * step_scale))
    ys = bag + hood
    first_hood = len(bag)
    # the crease grid, in faces of this mesh (a coarser mesh has fewer faces to a cell)
    cells = (max(1, round(FACET_CELL / step_scale)), max(1, round(CRUMPLE_CELL / step_scale)))
    shoulders = [p for y in np.arange(SHOULDERS[0], SHOULDERS[1] + 1e-9, 0.01) for p in body.cut(y, 0.011)]
    polys, centres, caps = [], [], []
    for s, y in enumerate(ys):
        if s >= first_hood:
            # the hood goes round his neck and head
            clear = CLEAR_HEAD
            pts = body.cut(y, 0.011)
            if pts:
                pts = [(x, max(z, BOTTOM + clear)) for x, z in pts]
        else:
            clear = CLEAR_BODY + FEET_MORE * step((FEET_FROM - y) / 0.12)
            clear += (EDGE_CLEAR - CLEAR_BODY) * step((y - (BAG_TOP - EDGE_IN)) / EDGE_IN)
            pts = body.cut(y, 0.021 if y < 0.60 else 0.011) if y <= SHOULDERS[1] else list(shoulders)
            if pts:
                xs = [p[0] for p in pts]
                if HANDS[0] <= y <= HANDS[1]:
                    pts += [(min(xs) - HANDS_MORE, 0.03), (max(xs) + HANDS_MORE, 0.03), (min(xs) - HANDS_MORE, 0.09), (max(xs) + HANDS_MORE, 0.09)]
                    xs = [p[0] for p in pts]
                # he lies on something: at his sides the tarp goes down to it (and under him)
                low = BOTTOM + clear
                pts = [(x, max(z, low)) for x, z in pts] + [(min(xs), low), (max(xs), low)]
        if not pts:
            polys.append(None)
            centres.append(None)
            caps.append(None)
            continue
        xs = [p[0] for p in pts]
        poly = grown(pts, clear)
        polys.append(poly)
        centres.append((sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)))
        caps.append((min(-SIDE_MOST, min(xs) - SIDE_LEAST), max(SIDE_MOST, max(xs) + SIDE_LEAST)))
    # stations with nothing measured (beyond the crown) take the nearest one's
    known = [i for i, q in enumerate(polys) if q]
    for i in range(len(ys)):
        if not polys[i]:
            j = min(known, key=lambda k: abs(k - i))
            polys[i], centres[i], caps[i] = polys[j], centres[j], caps[j]
    parts = ((0, first_hood, DROP_BAG), (first_hood, len(ys), DROP_HOOD))
    cx, cz = np.zeros(len(ys)), np.zeros(len(ys))
    for lo, hi, _ in parts:
        cx[lo:hi] = smooth(np.array([c[0] for c in centres[lo:hi]]), 2.0)
        cz[lo:hi] = smooth(np.array([c[1] for c in centres[lo:hi]]), 2.0)
    # more points over the top than underneath
    angles = np.concatenate([np.linspace(-0.12 * math.pi, 1.12 * math.pi, around - 8, endpoint=True),
                             np.linspace(1.12 * math.pi, 1.88 * math.pi, 10)[1:-1]])
    radii = np.zeros((len(ys), len(angles)))
    for s, poly in enumerate(polys):
        inside = (min(q[0] for q in poly) < cx[s] < max(q[0] for q in poly)) and (min(q[1] for q in poly) < cz[s] < max(q[1] for q in poly))
        c = (cx[s], cz[s]) if inside else centres[s]
        cx[s], cz[s] = c
        for k, a in enumerate(angles):
            radii[s, k] = reach(poly, c, a)
    ya = np.array(ys)
    for lo, hi, drop in parts:
        # along him the cloth cannot drop from a high place faster than its stiffness lets it
        raw = radii[lo:hi].copy()
        for s in range(lo, hi):
            radii[s] = np.max(raw - drop * np.abs(ya[lo:hi] - ya[s])[:, None], axis=0)
        # and it lies smoothly: no steps from one station to the next
        for k in range(len(angles)):
            radii[lo:hi, k] = np.maximum(radii[lo:hi, k], smooth(radii[lo:hi, k], 1.2))
    # creases, outward only, on what is seen (not underneath)
    for s in range(len(ys)):
        for k, a in enumerate(angles):
            if -0.05 * math.pi < a < 1.05 * math.pi:
                if s >= first_hood:
                    radii[s, k] += CRUMPLE * facets(s - first_hood, k, cells[1], 1.0)
                else:
                    ends = min(1.0, (ys[s] - FIRST + 0.04) / 0.06) * (1 - step((ys[s] - (BAG_TOP - EDGE_IN)) / EDGE_IN))
                    radii[s, k] += FACET * ends * facets(s, k, cells[0], 0.0)
    return ys, cx, cz, angles, radii, caps, first_hood, cells


_SKED = {}


def in_sked(p, body):
    """A point of the bag, brought inside the SKED's shape at its foot end: under the cover that closes over his
    feet, between its sides, and over the sled's floor, which rises there. (Until 2026-11-20 the bag was also
    kept clear of his feet as measured, boots and all, which are wider than the cover: the bag stood out beside
    and under the SKED's foot end, seen in game. He is undressed for the bag now, and a bare foot that is wider
    than the cover would show through the cover with no bag as well.)"""
    x, y, z = p
    along = y - TALON_PELVIS + SKED_PELVIS
    if along > SKED_FROM:
        return [x, y, z]
    if not _SKED:
        import build_talon_strap_arcs as talon
        pts, nrm, recs, sels = talon.read_lod0(SKED_MODEL)
        straps = set().union(*sels.values())
        for i, (sx, sy, sz, _) in enumerate(pts):
            if i not in straps and sz < SKED_FROM + 0.06:
                # (by 3 cm along and 2 cm up: how far out the SKED is there)
                key = (round(sz / 0.03), round(sy / 0.02))
                _SKED[key] = max(_SKED.get(key, 0.0), abs(sx))
    along = max(along, SKED_END)
    a = round(along / 0.03)
    highs = [h for (k, h) in _SKED if k == a]
    if not highs:
        return [x, along - SKED_PELVIS + TALON_PELVIS, z]
    up = min(max(z + 0.003, min(highs) * 0.02 + SKED_ROOM), max(highs) * 0.02 - SKED_ROOM)
    h = min(highs, key=lambda v: abs(v * 0.02 - up))
    wide = max(0.02, _SKED[(a, h)] - SKED_ROOM)
    # His feet are turned out further than the cover is wide (measured: 21 cm from the middle against 18). Held
    # to the cover's width the bag let a bare foot through, beside the cover's rim (seen in game, 2026-11-20). So
    # at the height of a foot, and only there, the bag goes as far out as that foot and a little: a bulge round
    # the foot, not the whole foot end as wide as the feet at every height, as it was before.
    # (not at the level of his heels: down there a bulge hangs out under the sled's rounded edge as a brown tab,
    # seen in game, and what showed through the bag held to the cover was the ball of a foot, half way up)
    feet = [q for q in body.cut(y, 0.045) if abs(q[1] - (up - 0.003)) <= 0.03] if up >= FOOT_FROM else []
    right = min([-wide] + [q[0] - FOOT_ROOM for q in feet])
    left = max([wide] + [q[0] + FOOT_ROOM for q in feet])
    return [max(right, min(left, x)), along - SKED_PELVIS + TALON_PELVIS, up - 0.003]


_WALLS = {}
SKED_LIES = 0.003     # how high he lies in the SKED, in its own axes
FOOT_ROOM = 0.012     # the bag round a foot that stands out of the SKED's foot cover
FOOT_FROM = 0.07      # from this high over the sled's floor
WALL_ROOM = 0.008     # the bag stays this far inside the SKED's shell (its sheet's thickness and a little)
FLOOR_ROOM = 0.002


def held_in_sked(p):
    """A point of the bag, kept inside the SKED it lies in: over its floor, and between its side walls up to
    their rims (above them it may lean out a little). Seen in game, 2026-11-20: the bag went down to 1.5 cm under
    what he lies on, which in a SKED is under the sled, and its sides stood through the sled's walls."""
    x, y, z = p
    if not _WALLS:
        import build_talon_strap_arcs as talon
        pts, nrm, recs, sels = talon.read_lod0(SKED_MODEL)
        straps = set().union(*sels.values())
        raw, under = {}, {}
        for i, (sx, sy, sz, _) in enumerate(pts):
            # (its walls only: what lies flat beside it, handles and flaps, is no wall)
            if i not in straps and abs(sx) > 0.12 and sy > 0.012:
                key = (round(sz / 0.04), round(sy / 0.015))
                raw[key] = max(raw.get(key, 0.0), abs(sx))
            # its underside: the lowest of it at every distance from the middle
            if i not in straps and sy < 0.14:
                key = (round(sz / 0.04), round(abs(sx) / 0.015))
                under[key] = min(under.get(key, 9.0), sy)
        for a in {k[0] for k in raw}:
            col = sorted((h, w) for (k, h), w in raw.items() if k == a)
            # the rim: the highest place where the wall is still about as far out as at its widest
            widest = max(w for h, w in col)
            rim = max(h for h, w in col if w > widest - 0.03 and h * 0.015 < 0.16)
            # The sled is rounded underneath: its floor is flat in the middle and comes up toward the walls
            # (from 16 cm out at his legs, 22 cm at his trunk). The floor the bag lies on, by distance from the
            # middle, out to the wall, never falling outward.
            floor, high = [], 0.0
            for k in range(0, int(widest / 0.015) + 2):
                if (a, k) in under:
                    high = max(high, under[(a, k)])
                floor.append((k * 0.015, high))
            _WALLS[a] = ([(h * 0.015, w) for h, w in col if h <= rim], rim * 0.015, floor)
        # (where the sled's mesh has no point on its wall for 4 cm, only on a flap or handle beside it, the wall
        # is the one next to it)
        good = sorted(a for a, (col, rim, floor) in _WALLS.items() if rim >= 0.05)
        for a in list(_WALLS):
            if _WALLS[a][1] < 0.05:
                _WALLS[a] = _WALLS[min(good, key=lambda g: abs(g - a))]
    z = max(z, FLOOR_ROOM)
    a = round((y - TALON_PELVIS + SKED_PELVIS) / 0.04)
    # (at its foot end the SKED closes over his feet: in_sked(). Right up to there: 4 cm of the bag before it
    # were held to neither and hung out under the sled's corner as a tab, seen in game.)
    if a not in _WALLS or y - TALON_PELVIS + SKED_PELVIS <= SKED_FROM:
        return [x, y, z]
    col, rim, floor = _WALLS[a]
    up = z + SKED_LIES
    if up >= rim:
        wide = col[-1][1] - WALL_ROOM + 0.5 * (up - rim)
    else:
        lo = max([c for c in col if c[0] <= up], default=col[0])
        hi = min([c for c in col if c[0] >= up], default=col[-1])
        wide = (lo[1] if hi[0] == lo[0] else lo[1] + (hi[1] - lo[1]) * (up - lo[0]) / (hi[0] - lo[0])) - WALL_ROOM
    x = max(-wide, min(wide, x))
    # (over the sled's floor where that comes up toward the wall: lying flat out to the wall the bag showed as a
    # brown line under the sled's edge, seen in game from level with it)
    lo = max([c for c in floor if c[0] <= abs(x)], default=floor[0])
    hi = min([c for c in floor if c[0] >= abs(x)], default=floor[-1])
    under = lo[1] if hi[0] == lo[0] else lo[1] + (hi[1] - lo[1]) * (abs(x) - lo[0]) / (hi[0] - lo[0])
    return [x, y, max(z, under - SKED_LIES + WALL_ROOM)]


def build(body, around=AROUND, step_scale=1, opened=False, sked=False):
    ys, cx, cz, angles, radii, caps, first_hood, cells = rings(body, around, step_scale)
    S, K = radii.shape
    over = around - 8                       # the first so many points of a ring go over him, from his left side
    P = np.zeros((S, K, 3))
    for s in range(S):
        P[s, :, 0] = np.clip(cx[s] + radii[s] * np.cos(angles), caps[s][0], caps[s][1])
        P[s, :, 1] = ys[s]
        P[s, :, 2] = np.maximum(cz[s] + radii[s] * np.sin(angles), BOTTOM)
    # ---- the hood's edge round the face
    fy, fa, fb = FACE
    # (his head does not lie exactly on the middle line)
    mids = [np.mean([p[0] for p in body.cut(y, 0.006)]) for y in np.arange(fy - 0.04, fy + 0.04, 0.01) if body.cut(y, 0.006)]
    fx = float(np.mean(mids)) if mids else 0.0

    def face(p):
        """Where a point is from the middle of the face opening: 1 on its edge (seen from above)."""
        return (abs((p[1] - fy) / fa) ** FACE_SQUARE + abs((p[0] - fx) / fb) ** FACE_SQUARE) ** (1 / FACE_SQUARE)

    top = np.zeros((S, K), bool)
    for k in range(K):
        top[first_hood:, k] = 0.02 * math.pi < angles[k] < 0.98 * math.pi
    for s in range(S):
        for k in range(K):
            if not top[s, k]:
                continue
            p = P[s, k]
            beyond = (face(p) - 1.0) * min(fa, fb)
            if beyond < RIM_BLEND:
                head = body.head_top(p[0], p[1])
                if head is not None:
                    t = step(beyond / RIM_BLEND)
                    p[2] = min(p[2], (head + RIM_CLEAR) * (1 - t) + p[2] * t)
                    # the elastic gathers the cloth into puckers that run away from the edge
                    turn = math.atan2(p[1] - fy, p[0] - fx) * 0.07
                    p[2] += GATHER[0] * (0.5 + 0.5 * math.sin(2 * math.pi * turn / GATHER[1])) * (1 - step(max(beyond, 0.0) / GATHER[2]))
    pts = [list(P[s, k]) for s in range(S) for k in range(K)]
    index = lambda s, k: s * K + (k % K)
    faces = []          # (corners, picture, which way is out of it or None)
    hole = set()
    # ---- opened: the column of points the cover is folded at, and the stations it is open between
    fold = None
    if opened:
        mid = min(range(S), key=lambda s: abs(ys[s] - sum(OPEN_ALONG) / 2))
        fold = next(k for k in range(over) if P[mid, k, 0] < OPEN_FOLD)
    cut = set()
    for s in range(S - 1):
        for k in range(K):
            c = [index(s, k), index(s, k + 1), index(s + 1, k + 1), index(s + 1, k)]
            mid = np.mean([pts[i] for i in c], axis=0)
            if top[s, k] and top[s, (k + 1) % K] and face(mid) < 1.0:
                hole.add((s, k))
                continue
            if opened and k < fold and OPEN_ALONG[0] <= ys[s] and ys[s + 1] <= OPEN_ALONG[1]:
                cut.add((s, k))
                continue
            if s == first_hood - 1:
                # the bag's top edge: from the top sheet in to the hood (with the sheet folded back, not there)
                if not (opened and k < fold):
                    faces.append((c, OUTSIDE, np.array([0.0, 1.0, 0.15])))
                continue
            if k + 1 < over:
                # the cloth that is seen: flat pieces between creases
                part = (s - first_hood, cells[1], 1.0) if s >= first_hood else (s, cells[0], 0.0)
                faces += [(piece, OUTSIDE, None, group) for piece, group in creased(part[0], k, part[1], part[2], c)]
            else:
                faces.append((c, OUTSIDE, None))
    n_cloth = len(faces)
    # the points on the face opening's edge are laid on its outline itself, so that the edge is a clean line
    edge = set()
    for s, k in hole:
        for i in (index(s, k), index(s, k + 1), index(s + 1, k + 1), index(s + 1, k)):
            edge.add(i)
    kept = set(i for f in faces for i in f[0])
    rim = sorted(edge & kept)
    for i in rim:
        x, y, z = pts[i]
        d = face((x, y, z))
        if d > 1e-6:
            nx, ny = fx + (x - fx) / d, fy + (y - fy) / d
            head = body.head_top(nx, ny)
            pts[i] = [nx, ny, (head + RIM_CLEAR) if head is not None else z]
    # the hem round the face: the edge turned in and down
    hem = {}
    for i in rim:
        x, y, z = pts[i]
        v = np.array([fx - x, fy - y])
        v = v / (np.linalg.norm(v) or 1.0)
        hem[i] = len(pts)
        pts.append([x + v[0] * HEM[0], y + v[1] * HEM[0], z - HEM[1]])
        pts.append([x + v[0] * HEM_UNDER[0], y + v[1] * HEM_UNDER[0], z - HEM_UNDER[1]])
    edges = {}
    for f in faces:
        c = f[0]
        for a, b in zip(c, c[1:] + c[:1]):
            edges[(a, b)] = True
            edges[(b, a)] = edges.get((b, a), False)
    for (a, b), real in list(edges.items()):
        # (an edge of the cloth that has no face on its other side, taken once, the way its face runs)
        if real and a in hem and b in hem and not edges[(b, a)]:
            m = (np.array(pts[a]) + np.array(pts[b])) / 2
            faces.append(([b, a, hem[a], hem[b]], EDGE, np.array([fx - m[0], fy - m[1], 0.4])))
            faces.append(([hem[b], hem[a], hem[a] + 1, hem[b] + 1], EDGE, np.array([fx - m[0], fy - m[1], 0.4])))
    # ---- opened: what was over chest and left side lies folded over to his right, inside up
    if opened:
        lengths = np.zeros((S, over))
        for s in range(S):
            for k in range(1, over):
                lengths[s, k] = lengths[s, k - 1] + np.linalg.norm(P[s, k] - P[s, k - 1])
        flap = {}

        def laid(s, k):
            if (s, k) not in flap:
                want = lengths[s, fold] + (lengths[s, fold] - lengths[s, k]) * 0.96
                if want <= lengths[s, over - 1]:
                    j = int(np.searchsorted(lengths[s], want)) - 1
                    j = max(0, min(over - 2, j))
                    f = (want - lengths[s, j]) / max(lengths[s, j + 1] - lengths[s, j], 1e-9)
                    p = P[s, j] + (P[s, j + 1] - P[s, j]) * f
                    out = np.array([p[0] - cx[s], 0.0, p[2] - cz[s]])
                    p = p + out / (np.linalg.norm(out) or 1.0) * FLAP_OFF
                else:
                    end = P[s, over - 1]
                    p = np.array([end[0] - (want - lengths[s, over - 1]) - FLAP_OFF, ys[s], BOTTOM + FLAP_OFF])
                flap[(s, k)] = len(pts)
                pts.append([float(p[0]), ys[s], float(max(p[2], BOTTOM + FLAP_OFF))])
            return flap[(s, k)]
        rows = sorted(set(s for s, k in cut))
        for s, k in sorted(cut):
            band = k == 0 or s in (rows[0], rows[-1])
            faces.append(([laid(s, k), laid(s, k + 1), laid(s + 1, k + 1), laid(s + 1, k)], EDGE if band else INSIDE, np.array([-0.3, 0.0, 1.0])))
    # ---- the two ends: the crown of the hood closes on a point, the foot end runs out flat into a seam
    crown = len(pts)
    pts.append([cx[-1], ys[-1] + CLEAR_HEAD * 0.8, cz[-1]])
    for k in range(K):
        faces.insert(n_cloth, ([index(S - 1, k), index(S - 1, k + 1), crown], OUTSIDE, None))
        n_cloth += 1
    prev = [index(0, k) for k in range(K)]
    n_foot = max(2, int(round(FOOT_END / (BODY_STEP * step_scale))))
    n_foot = max(n_foot, 4)
    for r in range(1, n_foot + 1):
        f = r / n_foot
        # (down in a quarter round behind his soles; the last of it comes back under him)
        squeeze = math.cos(f * math.pi / 2) * 0.93 + 0.07
        back = FOOT_END * (math.sin(f * math.pi / 2) if f < 0.75 else math.sin(0.75 * math.pi / 2) - (f - 0.75) * 0.5)
        ring = []
        for k in range(K):
            x, y, z = pts[index(0, k)]
            ring.append(len(pts))
            pts.append([x * (1 - 0.06 * f), y - back, BOTTOM + 0.004 + (z - BOTTOM) * squeeze])
        # (out of the flattened end is away from its own middle, not from the bag's middle line)
        centre = np.mean([pts[i] for i in ring + prev], axis=0)
        for k in range(K):
            c = [ring[k], ring[(k + 1) % K], prev[(k + 1) % K], prev[k]]
            faces.insert(n_cloth, (c, OUTSIDE, np.mean([pts[i] for i in c], axis=0) - centre + np.array([0.0, -0.08, 0.0])))
            n_cloth += 1
        prev = ring
    # the seam: the flattened last ring is closed on its middle
    middle = len(pts)
    pts.append(list(np.mean([pts[i] for i in prev], axis=0)))
    for k in range(K):
        faces.append(([prev[k], prev[(k + 1) % K], middle], EDGE, np.array([0.0, -1.0, 0.0])))
    if sked:
        pts = [in_sked(q, body) for q in pts]
    return dict(pts=np.array(pts), faces=faces, cloth=n_cloth, opened=opened)


# ---------------------------------------------------------------- binding to the bones
class Skin:
    def __init__(self, body):
        names, mats = poses.read_rtm(poses.OUTPUT / "acme_litter_side.rtm")
        self.M = {n.lower(): m for n, m in zip(names, mats[0])}
        self.piv = {k.lower(): v for k, v in poses.PIV.items()}
        self.body = body
        self.segments = {}
        for bone, to in REACH.items():
            a = self.posed(bone, self.piv[bone])
            b = self.posed(bone, self.piv[to] if isinstance(to, str) else self.piv[bone] + np.array(to))
            self.segments[bone] = (a, b)

    def posed(self, bone, rest):
        return (self.M[bone] @ np.append(rest, 1.0))[:3]

    def turned(self, v):
        """A direction, from the scan's axes to the ones the pose is worked in."""
        own = self.body.axes.T @ np.asarray(v)
        return np.array([-own[0], -own[1], own[2]])

    def to_tool(self, p):
        """A place, from the scan's axes (heights over what he lies on) to the ones the pose is worked in: the
        casualty's own, turned half round (x his left, y backward, z up)."""
        return self.turned(np.asarray(p) + np.array([0.0, 0.0, DECK]) - self.body.origin)

    def weights(self, t):
        ds = []
        for bone, (a, b) in self.segments.items():
            ab = b - a
            f = min(1.0, max(0.0, float((t - a) @ ab) / max(float(ab @ ab), 1e-9)))
            ds.append((float(np.linalg.norm(t - (a + f * ab))), bone))
        ds.sort()
        best = ds[:BONES_PER_POINT]
        w = np.array([1.0 / (d + 0.02) ** 4 for d, _ in best])
        w /= w.sum()
        keep = [(bone, float(x)) for (d, bone), x in zip(best, w) if x >= 0.04]
        total = sum(x for _, x in keep)
        return [(bone, x / total) for bone, x in keep]

    def back(self, weights):
        """What carries a posed point bound like this back to the model's rest position."""
        M = sum(w * self.M[bone] for bone, w in weights)
        if abs(np.linalg.det(M[:3, :3])) < 0.3:
            M = self.M[max(weights, key=lambda bw: bw[1])[0]]
        return np.linalg.inv(M)


def to_file(t):
    """From the pose's working axes (those of the animation file with its second and third axes exchanged) to
    the model file's (x, up, the third): the same exchange."""
    return (t[0], t[2], t[1])


def level(shape, skin, res):
    pts = shape["pts"]
    # which way round each face is: out of the bag is away from its middle line, unless the face says otherwise
    smooth_n = np.zeros_like(pts)
    oriented, flat = [], {}
    for entry in shape["faces"]:
        c, pic, hint = entry[:3]
        group = entry[3] if len(entry) > 3 else None
        p = pts[c]
        n = np.cross(p[1] - p[0], p[2] - p[0]) if len(c) == 3 else np.cross(p[2] - p[0], p[3] - p[1])
        mid = p.mean(axis=0)
        out = hint if hint is not None else mid - np.array([0.0, mid[1], 0.07])
        if n @ out < 0:
            c = c[::-1]
            n = -n
        oriented.append((c, pic, group, n / (np.linalg.norm(n) or 1.0)))
        for i in c:
            smooth_n[i] += n
        if group is not None:
            flat[group] = flat.get(group, 0.0) + n
    smooth_n /= np.maximum(np.linalg.norm(smooth_n, axis=1), 1e-12)[:, None]
    flat = {g: v / (np.linalg.norm(v) or 1.0) for g, v in flat.items()}
    tool = np.array([skin.to_tool(p) for p in pts])
    points, normals, weights, back = [], [], {}, []
    unit = lambda v: v / (np.linalg.norm(v) or 1.0)
    for i in range(len(pts)):
        w = skin.weights(tool[i])
        inv = skin.back(w)
        back.append(inv[:3, :3])
        points.append(to_file((inv @ np.append(tool[i], 1.0))[:3]))
        # (the file keeps its normals pointing into the surface)
        normals.append(to_file(-unit(inv[:3, :3] @ skin.turned(smooth_n[i]))))
        for bone, x in w:
            weights.setdefault(bone, {})[i] = x
    made, other = {}, {}

    def flat_normal(group, i):
        """The normal of a flat piece at one of its points (the piece is one plane where he lies as built)."""
        if (group, i) not in made:
            made[(group, i)] = len(normals)
            normals.append(to_file(-unit(back[i] @ skin.turned(flat[group]))))
        return made[(group, i)]

    def turned_over(n):
        if n not in other:
            other[n] = len(normals)
            normals.append(tuple(-v for v in normals[n]))
        return other[n]

    # The file's faces: seen from outside, cross(p1 - p0, p2 - p0) points INTO the surface (seen in game: built
    # the other way round the shell showed only its inside).
    posed_file = np.array([to_file(t) for t in tool])
    out_faces, plain = [], []
    for f, (c, pic, group, face_n) in enumerate(oriented):
        p = posed_file[c]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        want = np.array(to_file(skin.turned(face_n)))
        order = c if n @ want < 0 else c[::-1]
        # the cloth's picture: round the bag and along it, by length
        uv = []
        for i in order:
            x, y, z = pts[i]
            uv.append((math.atan2(z - 0.07, x) * 0.22 / TILE, y / TILE))
        us = [u for u, _ in uv]
        if max(us) - min(us) > 0.5:
            # (keep the picture whole across the place where the angle jumps)
            uv = [(u + (2 * math.pi * 0.22 / TILE if u < 0 else 0.0), v) for u, v in uv]
        ns = [i if group is None else flat_normal(group, i) for i in order]
        out_faces.append(([(i, m, u, v) for i, m, (u, v) in zip(order, ns, uv)], pic[0], pic[1]))
        plain.append((c, pic))
        if shape["opened"] and f < shape["cloth"]:
            # the cloth is seen from inside too
            out_faces.append(([(i, turned_over(m), u, v) for i, m, (u, v) in zip(order[::-1], ns[::-1], uv[::-1])], INSIDE[0], INSIDE[1]))
    return dict(res=res, points=points, normals=normals, faces=out_faces, weights=weights), plain


LAID = Path(__file__).with_name("assets") / "hpmk_shell_outline.npy"


def outline(lo, hi, opened=False, sked=False):
    """The surface of the shell the casualty wears between two places along him (the Talon II's axes): [(x, z)],
    z over what he lies on. For fitting a litter's straps over the shell. The shell is the drawn model as
    tools/fit_hpmk_worn.py lays it on him (which leaves its points here); in a SKED he wears the one that is held
    inside the SKED and pulled taut (until 2026-11-20 the SKED's straps were laid over the other one, and stood
    off the bag they are seen on)."""
    pts = np.load(LAID.with_name("hpmk_shell_outline_sked.npy") if sked else LAID)
    return [(float(x), float(z)) for x, y, z in pts if lo - 0.011 <= y <= hi + 0.011]


def obj(path, pts, faces):
    """The shell as built round him (scan axes), to look at outside the game."""
    with open(path, "w") as f:
        for p in pts:
            f.write("v %.5f %.5f %.5f\n" % tuple(p))
        for c, _ in faces:
            f.write("f " + " ".join(str(i + 1) for i in c) + "\n")


def main():
    """A shell made here from nothing but his outline (no drawing): kept for looking at, not used by the mod.
    The models the mod uses are the drawn HPMK-I shell laid on him: tools/fit_hpmk_worn.py."""
    body = Body()
    skin = Skin(body)
    shape = build(body, AROUND, 1, False, False)
    lvl, faces = level(shape, skin, 1.0)
    obj(Path(__file__).with_name("assets") / "hpmk_generated_preview.obj", shape["pts"], faces)
    print("wrote a preview of the generated shell (%d points); the mod's models come from tools/fit_hpmk_worn.py" % len(lvl["points"]))


if __name__ == "__main__":
    main()
