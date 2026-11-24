"""The HPMK-I shell opened over the casualty's chest: what tools/fit_hpmk_worn.py draws new for it.

The cover is taken off his chest along a straight line (from his right shoulder to his left hip, across the model
as drawn) and lies folded over that line on the part that stays closed, its lining up. Asked for on 2026-11-20
with two photographs of the kit in use: "the inside is a fuzzy blue with a black velcro strip running along its
length", and "a readyheat blanket ... lays on top of the patient". So, besides the drawn cover cut clean at the
line (clipped(), where it was a row of teeth: whole faces left out):

  - flap():    the folded-over cover, a clean sheet rolled over at the fold: lining up, the outside underneath, and
               along what were its edges the closure as the kit's own edge picture has it (hpmk_edge_co.paa): the
               black hook-and-loop strip, the coyote band outside it and a black binding at the very edge.
  - panel():   the bottom sheet he lies on, which now shows beside his shoulders and his arm: lining up, with the
               same closure along its edges.
  - blanket(): the kit's self-heating blanket (the picture of it is in the kit's atlas, hpmk_co.paa) laid over
               his trunk and arms, under the cover where that stays closed.
  - collar():  the hood's padded strips under his chin. The hood is a thing of its own on the bag: it ends right
               under his chin (clipped(): what the drawing has of it below, a bib with cords, lay in pieces on
               the blanket and stood through it, seen in game), and there, round his throat, it has strips of
               padding (asked for on 2026-11-20 with two photographs of the hood).

In a SKED the folded cover lies over the sled's strap across his pelvis, which stays closed ("the folded piece of
the blanket should go OVER the straps, not under", 2026-11-20): flap_point() reads the strap's model, so
tools/build_sked_strap_arcs.py has to have run (after the closed bag was fitted) before the opened bag is fitted.

Everything is laid in the scan's axes (x across with his left +, y along him toward his head, z up over what he
lies on) and bound to his bones by fit_hpmk_worn.py like the drawn points.

The closure and the blanket have pictures and materials of their own (make_pictures()), made from the kit's: as
light as the kit's are, in the game the band was cream where the photographs have a tan one, and the blanket
burnt out to white wherever the light fell on it squarely.

  python tools/hpmk_opened.py        (writes the pictures and materials; needs Arma 3 Tools' ImageToPAA)
"""
import math

import numpy as np

import build_hpmk_shell as H

# The fold line, across (his left +) and along the model as drawn: what lies on its upper left is taken off.
# (Until 2026-11-20 it ran from his right collar bone, (-0.16, 0.62): half his chest stayed covered.)
FOLD_A, FOLD_B = (-0.40, 0.50), (0.52, -0.08)
TOP = 0.66            # along the drawn model: the cover's top edge, at his chin
CHIN = 0.61           # along the drawn model: the hood ends here (drawn in to his head that is right under his chin)
# And along him as he lies: nothing of the hood is below this line under his chin. (Cut along the drawing only,
# pieces of it that are drawn in front of the face came to hang over his chest and beside his throat once drawn
# in to his head: found by casting the camera's ray through them, 2026-11-20.)
HOOD_ENDS = 0.705
COLLAR = (0.668, 0.728, 3)        # the hood's padded strips round his throat: from, to (along him), how many
COLLAR_OFF, COLLAR_PUFF = 0.012, 0.010      # off the measured neck at the seams between them, and how far they stand out more
OVER_STRAP = 0.005    # the flap lies this far over a strap under it
ROLL = 0.008          # the fold is a roll of this radius, and the flap lies two of them over the cover
GAP = 0.002
# Across the closure, from the bag's edge inward, as the kit's edge picture has it: a black binding, the coyote
# band, the hook-and-loop strip (1.5 in).
BIND, BAND, HOOK = 0.010, 0.024, 0.038
RIM = BIND + BAND
SIT = 0.026           # the cover comes down to this far off him at the fold (it lies on the blanket there)
SIT_HOOD = 0.024      # and what hangs from the hood on his chest
PRESSED = 0.30        # the creases of the cover under the flap keep this share of their height
EDGE_REPEAT = 0.30    # the edge picture repeats along the closure
LINING_TILE = 0.40
OUT_TILE = 0.60
BORDER = 0.15         # the bottom sheet shows this far beside him (as drawn the bag is 45 cm wide from its middle)
PANEL_UP = 0.010      # and lies this high over what he lies on (clear of ground that is not level)
PANEL_TO = 0.735      # along him: to behind his neck (above that the photographs show the hood alone)
CURL = (0.06, 0.012)  # its edge stands up a little: over this width, by this much
# The blanket: a Ready-Heat II 4-panel, 34 x 48 in, the long way along him (chosen 2026-11-23: "it lays over the
# patient like a blanket from arm to arm"; until then it was 0.80 square and lay on him as close as a vest, tucked
# under at his sides). It comes up to here along him (the base of his neck).
BLANKET_W, BLANKET_L = 0.864, 1.219
BLANKET_TOP = 0.668   # (at his throat, under the hood's strips)
BLANKET_SIDE = 0.708  # and to here beside his neck, just under the hood's hem (lower, his shoulders showed between blanket and hood, seen in game)
# The level that casts the shadow, for the opened bag: what of it is taken off is drawn together into one point
# inside his chest, and what hangs from the hood into one inside his neck (along him, up).
SHADOW_CHEST, SHADOW_NECK = (0.45, 0.09), (0.70, 0.12)
# (the bottom sheet too from his shoulders up, along the drawn model: beside his neck nothing of him is over it,
# and what was left of the shape there cast a shadow on the bare ground)
SHADOW_BACK = 0.50
BLANKET_OFF = 0.016   # over the measured body (his skin is about 1 cm proud of it)
# Laid loose, it spans from what it rests on to what it rests on (shoulder to chest to arm) and sags between them
# by about this much over a span of this width (a blur of these widths, across and along, kept over his outline);
# off his arms it falls to what he lies on over about REACH of its height, and the rest lies flat there.
SPAN_X, SPAN_Y = 0.045, 0.040
REACH = 0.55
LOOSE_FROM = 0.06     # beside the fold it comes down to lie close to him over this far (the cover lies on it there)
PAD = 0.004           # the heating cells stand this high in the blanket
# the blanket's picture in the kit's atlas (2048 x 2048): left, top, size in pixels (make_pictures() cuts it out)
ATLAS = (4, 770, 982)
CELLS = ((0.036, 0.517, 0.965), (0.042, 0.519, 0.952))   # the cells' frame in the blanket's picture: edges and middle

OUTSIDE = (rb"acme_hpmk\data\hpmk_out_co.paa", rb"acme_hpmk\data\hpmk_out.rvmat")
INSIDE = (rb"acme_hpmk\data\hpmk_in_co.paa", rb"acme_hpmk\data\hpmk_in.rvmat")
EDGE = (rb"acme_hpmk\data\hpmk_closure_co.paa", rb"acme_hpmk\data\hpmk_closure.rvmat")
KIT = (rb"acme_hpmk\data\hpmk_blanket_co.paa", rb"acme_hpmk\data\hpmk_blanket.rvmat")


class Fold:
    def __init__(self):
        a, b = np.array(FOLD_A), np.array(FOLD_B)
        self.a = a
        self.t = (b - a) / np.linalg.norm(b - a)
        self.n = np.array([-self.t[1], self.t[0]])       # toward what is taken off

    def dist(self, x, y):
        """How far a place of the drawn cover is on the side that is taken off (minus: on the side that stays)."""
        return float((x - self.a[0]) * self.n[0] + (y - self.a[1]) * self.n[1])

    def off(self, x, y):
        return self.dist(x, y) > 0 and y < TOP


FOLD = Fold()


def wave(x, y):
    """A slow unevenness, about -1 to 1."""
    return (math.sin(17.3 * x + 1.1) * math.sin(13.7 * y + 0.6) + 0.6 * math.sin(31.0 * x + 23.0 * y + 2.0)
            + 0.4 * math.sin(41.0 * x - 37.0 * y + 0.3)) / 2.0


def cut(poly, vals, mix):
    """A polygon cut by a line: what of it has a value of 0 or more."""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        fp, fq = vals[i], vals[(i + 1) % len(poly)]
        if fp >= 0:
            out.append(p)
        if (fp > 0 > fq) or (fp < 0 < fq):
            out.append(mix(p, q, fp / (fp - fq)))
    return out if len(out) >= 3 else []


def fan(poly):
    if len(poly) <= 4:
        return [poly] if len(poly) >= 3 else []
    return [[poly[0], poly[k], poly[k + 1]] for k in range(1, len(poly) - 1)]


# ---------------------------------------------------------------- the drawn cover, cut at the fold
def kinds(lv, parts, hood):
    """What every drawn point belongs to: 0 the bag, 1 what is stuck on its cover (the card: taken off with it),
    2 the hood and what hangs from it (stays)."""
    y = lv["pts"][:, 1]
    kind = np.zeros(len(y), int)
    for ids in parts(lv)[1:]:
        kind[ids] = 2 if (y[ids].min() >= 0.44 or hood[ids].max() >= 0.5) else 1
    return kind


def clipped(lv, kind, top):
    """The drawn level with its cover cut clean along the fold line: faces of the cover wholly on the side that
    is taken off are left out, faces across the line are cut at it. New points come after the old ones.
    kind: kinds(); top: for every point, whether it is of the cover (not the bottom sheet, not the hood).

    The bag's head end goes with the cover, to its very end beside his head: nothing of the bag's own is bound
    to his head, the hood is a part of its own. (First the cover was cut across at his chin and what was above
    left standing, then brought down beside his neck: one looked under it, and it came down as a comb of spikes,
    seen in game. The photographs show the hood alone above his shoulders.)"""
    n0 = len(lv["pts"])
    pts = [np.array(p, float) for p in lv["pts"]]
    flags = list(lv["flags"])
    nrm = [np.array(v, float) for v in lv["nrm"]]
    kind = list(kind)
    bones = {}
    for name, data in lv["tags"]:
        if not name.startswith("#"):
            raw = np.frombuffer(data, "u1", n0)
            bones[name] = list(np.where(raw == 0, 0.0, np.where(raw == 1, 1.0, (256.0 - raw) / 255.0)))
    cache = {}

    def mix(p, q, t):
        a, b = (p[0], q[0]) if p[0] < q[0] else (q[0], p[0])
        key = (a, b, round(t if p[0] < q[0] else 1 - t, 5))
        if key not in cache:
            pts.append(pts[p[0]] + (pts[q[0]] - pts[p[0]]) * t)
            flags.append(flags[p[0]])
            kind.append(kind[p[0]])
            for w in bones.values():
                w.append(w[p[0]] + (w[q[0]] - w[p[0]]) * t)
            cache[key] = len(pts) - 1
        v = nrm[p[1]] + (nrm[q[1]] - nrm[p[1]]) * t
        nrm.append(v / (np.linalg.norm(v) or 1.0))
        return [cache[key], len(nrm) - 1, p[2] + (q[2] - p[2]) * t, p[3] + (q[3] - p[3]) * t]

    faces, gone, cuts = [], 0, 0
    for vs, fl, tex, mat in lv["faces"]:
        of_cover = [bool(top[v[0]]) for v in vs]
        d = [FOLD.dist(pts[v[0]][0], pts[v[0]][1]) for v in vs]
        if all(kind[v[0]] == 0 for v in vs) and min(pts[v[0]][1] for v in vs) >= TOP - 0.02 and all(a > 0 for a in d):
            # (the bag's head end whole, its bottom sheet too: bits of its end seam stood beside his head)
            gone += 1
            continue
        if any(kind[v[0]] == 2 for v in vs):
            # the hood and what hangs from it: it ends under his chin
            ys = [pts[v[0]][1] for v in vs]
            if min(ys) >= CHIN:
                faces.append([vs, fl, tex, mat])
            elif max(ys) > CHIN:
                for f in fan(cut(vs, [b - CHIN for b in ys], mix)):
                    faces.append([f, fl, tex, mat])
            else:
                gone += 1
            continue
        if not any(of_cover):
            faces.append([vs, fl, tex, mat])
            continue
        if not all(of_cover):
            # a face between the cover and the bottom sheet: it stays where the cover stays, and under him
            if min(pts[v[0]][1] for v in vs) >= TOP - 0.02 and all(a > 0 for a in d):
                gone += 1
            else:
                faces.append([vs, fl, tex, mat])
            continue
        if all(a <= 0 for a in d):
            faces.append([vs, fl, tex, mat])
            continue
        if all(a > 0 for a in d):
            gone += 1
            continue
        cuts += 1
        for f in fan(cut(vs, [-a for a in d], mix)):
            faces.append([f, fl, tex, mat])
    tags = []
    for name, data in lv["tags"]:
        if name.startswith("#"):
            tags.append((name, data))
        else:
            blob = bytes(H.p3d_skinned.weight_byte(w) if w > 0.004 else 0 for w in bones[name])
            tags.append((name, blob + bytes(len(faces))))
    out = dict(lv)
    out.update(pts=np.array(pts), flags=np.array(flags), nrm=np.array(nrm), faces=faces, tags=tags)
    return out, np.array(kind), (gone, cuts)


# ---------------------------------------------------------------- a mesh drawn new
class Mesh:
    def __init__(self):
        self.pts, self.keys, self.faces = [], {}, []

    def point(self, key, place):
        if key not in self.keys:
            self.keys[key] = len(self.pts)
            self.pts.append(np.array(place(), float))
        return self.keys[key]

    def face(self, ids, uvs, tex):
        """ids in the order that, seen from the side the face shows to, runs against the clock."""
        if len(set(ids)) == len(ids):
            self.faces.append((list(ids), [tuple(uv) for uv in uvs], tex))

    def normals(self):
        """For every point the way out of the side it shows to."""
        P = np.array(self.pts)
        acc = np.zeros((len(P), 3))
        for ids, uvs, tex in self.faces:
            q = P[ids]
            c = np.cross(q[1] - q[0], q[2] - q[0])
            if len(ids) == 4:
                c = c + np.cross(q[2] - q[0], q[3] - q[0])
            for i in ids:
                acc[i] += c
        return acc / np.maximum(np.linalg.norm(acc, axis=1), 1e-12)[:, None]


def edge_uv(along, e, band):
    """A place of the closure in the kit's edge picture, e from the bag's edge: band 'bind' (the black binding at
    the edge), 'band' (the coyote band) or 'hook' (the black strip)."""
    if band == "bind":
        v = 254.0 - 28.0 * e / BIND
    elif band == "band":
        v = 220.0 - 76.0 * (e - BIND) / BAND
    else:
        v = 136.0 - 128.0 * (e - RIM) / HOOK
    return (along / EDGE_REPEAT, v / 256.0)


def bands(cols):
    """What the strips between a row's columns are: the closure at both ends, the lining between."""
    names = ["in"] * (cols - 1)
    for j, name in enumerate(("bind", "band", "hook")):
        names[j] = names[cols - 2 - j] = name
    return names


def columns(lo, hi, inner):
    return [lo, lo + BIND, lo + RIM] + list(np.linspace(lo + RIM + HOOK, hi - RIM - HOOK, inner + 1)) + [hi - RIM, hi - BIND, hi]


def in_sled(p, body, room=0.0):
    """A point of what lies flat beside him, in a SKED: what is too wide for the sled goes up its wall, as far
    as its rim. (Higher it stood over the rim beside his shoulders like two ears, seen in game.)"""
    x, y, z = p
    s = 1.0 if x >= 0 else -1.0
    q = H.held_in_sked([x + s * room, y, z])
    over = abs(x + s * room) - abs(q[0])
    if over > 1e-4:
        up = max(z, q[2]) + over
        a = round((y - H.TALON_PELVIS + H.SKED_PELVIS) / 0.04)
        if a in H._WALLS:
            up = min(up, max(z, q[2], H._WALLS[a][1] - H.SKED_LIES - 0.006 - room))
        q = H.held_in_sked([x + s * room, y, up])
    q[0] -= s * room
    return H.in_sked(q, body)


class Opened:
    """What the fitting knows, worked out once for a bag (wide or in a SKED)."""

    def __init__(self, fit, sked):
        self.fit, self.sked = fit, sked
        d = fit.drawn
        # the drawn bag's half width, smooth along it
        self.hw_y = np.arange(-0.30, 0.80, 0.01)
        self.hw_v = H.smooth(np.array([d.half_width(y) for y in self.hw_y]), 2.0)
        # how far out he reaches on each side at every place along him (beside his neck and head: his shoulders)
        self.ext_y = np.arange(-0.30, 0.90, 0.01)
        left, right = [], []
        for Y in self.ext_y:
            xs = [p[0] for p in fit.body.cut(min(Y, 0.615), 0.021)]
            left.append(max(xs))
            right.append(min(xs))
        self.ext_l, self.ext_r = H.smooth(np.array(left), 2.5), H.smooth(np.array(right), 2.5)
        # where the fold line comes down to what he lies on, on each side
        lows = []
        for f in np.arange(-0.2, 1.2001, 0.01):
            x, y = FOLD.a + FOLD.t * f * np.linalg.norm(np.array(FOLD_B) - np.array(FOLD_A))
            if abs(x) <= self.hw(y):
                p = fit.laid(x, y, d.smooth_depth(x, y), 1.0)
                if p[2] < 0.035:
                    lows.append((x, p[1]))
        self.cut_l = max(Y for x, Y in lows if x > 0)
        self.cut_r = min([Y for x, Y in lows if x < 0], default=fit.along(FOLD_A[1]))
        # what the flap lies over besides the cover: in a SKED the strap across his pelvis (the straps over his
        # belly and chest are undone for the opened bag: acmeStrapArcHpmkOpen[] in the SKED's class)
        self.straps = np.zeros((0, 3))
        self.flap_at = {}
        if sked:
            import build_talon_strap_arcs as talon
            path = H.ROOT / "addons/acme_sked/sked_strap_pelvis_hpmk.p3d"
            pts = talon.read_lod0(path)[0]
            self.straps = np.array([[sx, sz - H.SKED_PELVIS + H.TALON_PELVIS, sy - H.SKED_LIES] for sx, sy, sz, _ in pts])
            print("   the flap lies over %s: %d points, along him %.3f..%.3f, up to %.3f" % (
                path.name, len(self.straps), self.straps[:, 1].min(), self.straps[:, 1].max(), self.straps[:, 2].max()))

    def hw(self, y):
        return float(np.interp(y, self.hw_y, self.hw_v))

    def drawn_along(self, Y):
        """Along the drawn model, from along him."""
        m = self.fit.marks
        for (a0, b0), (a1, b1) in zip(m, m[1:]):
            if Y <= b1:
                return a0 + (a1 - a0) * (Y - b0) / (b1 - b0)
        return m[-1][0] + (Y - m[-1][1])

    def let_out(self, y):
        """By how much the drawn cover is let out sideways at a place along it (fit.laid)."""
        Y = self.fit.along(y)
        if Y > 0.625:
            return 1.0
        whole, flat = self.fit.line.lengths(1, Y)
        return max(1.0, (whole - flat + 0.04) / self.fit.drawn.half_width(y))

    # ------------------------------------------------------------ the drawn points that stay
    def treat(self, x, y, facing, hood, kind, clear):
        """For the drawn points: how much of a crease's height each keeps, and how far it comes down."""
        n = len(x)
        press, sink, dist = np.ones(n), np.zeros(n), np.zeros(n)
        for i in range(n):
            dist[i] = FOLD.dist(x[i], y[i])
            if hood[i] >= 0.5 or y[i] >= TOP:
                continue
            if kind[i] == 2:
                if dist[i] > 0:
                    sink[i] = -(clear - SIT_HOOD)
                continue
            if facing[i] <= 0.3 or dist[i] > 1e-6:
                continue
            near = -dist[i]
            mx, my = np.array([x[i], y[i]]) + FOLD.n * (2 * near)
            under = FOLD.off(mx, my) and abs(mx) <= self.hw(my) + 0.01
            press[i] = min(PRESSED if under else 1.0, H.step(near / 0.05))
            sink[i] = -(clear - SIT) * (1 - H.step(near / 0.08))
        return press, sink, dist

    # ------------------------------------------------------------ the flap
    def flap_point(self, x, y):
        key = (round(x, 5), round(y, 5))
        if key not in self.flap_at:
            self.flap_at[key] = self.flap_place(x, y)
        return self.flap_at[key]

    def flap_place(self, x, y):
        s = max(0.0, FOLD.dist(x, y))
        foot = np.array([x, y]) - FOLD.n * s
        turn = math.pi * ROLL
        if s <= turn:
            m, lift = ROLL * math.sin(s / ROLL), ROLL * (1 - math.cos(s / ROLL))
        else:
            m = -(s - turn)
            lift = 2 * ROLL + 0.003 * (1 + wave(x, y)) * min(1.0, (s - turn) / 0.05)
        fx, fy = foot + FOLD.n * m
        clear = 0.030
        off = lift + GAP - (clear - SIT) * (1 - H.step(max(0.0, -m) / 0.08))
        p = self.fit.laid(fx, fy, self.fit.drawn.smooth_depth(fx, fy), 1.0, (fx, fy, off))
        if self.sked:
            p = np.array(H.held_in_sked(H.in_sked(list(p), self.fit.body)))
        if len(self.straps):
            # over a strap: as far out of the cover as the strap's highest point near it, and a little
            out = self.fit.laid(fx, fy, self.fit.drawn.smooth_depth(fx, fy), 1.0, (fx, fy, off + 0.01)) - \
                self.fit.laid(fx, fy, self.fit.drawn.smooth_depth(fx, fy), 1.0, (fx, fy, off))
            out = out / (np.linalg.norm(out) or 1.0)
            rel = self.straps - p
            high = rel @ out
            beside = np.linalg.norm(rel - np.outer(high, out), axis=1)
            share = np.clip((0.06 - beside) / 0.035, 0.0, 1.0)
            share = share * share * (3 - 2 * share)
            more = float(np.max((high + OVER_STRAP) * share * (high > -0.03), initial=0.0))
            # (not where the flap is tucked under him: the strap goes on round the sled there)
            if more > 0 and out[2] > 0.1 and p[2] > 0.02:
                p = p + out * more
        return p

    def flap(self, detail):
        mesh = Mesh()
        step = 0.0125 * detail
        # the lowest place the fold line reaches inside the bag's width
        y_from = min(FOLD_A[1] + (sx * self.hw(0.0) - FOLD_A[0]) * FOLD.t[1] / FOLD.t[0] for sx in (-1, 1)) - 0.01
        ys = list(np.arange(y_from, TOP - RIM - step * 0.5, step)) + [TOP - RIM, TOP - BIND, TOP]
        inner = max(4, int(round((2 * 0.446 - 2 * (RIM + HOOK)) / (0.015 * detail))))
        row = lambda y: columns(-self.hw(y), self.hw(y), inner)
        mixed = lambda p, q, t: (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        # (the roll is cut finer than the rest: a quarter turn each)
        marks = [math.pi * ROLL * f for f in ((0.25, 0.5, 0.75, 1.0) if detail == 1 else (0.5, 1.0) if detail == 2 else (1.0,))]
        names = bands(len(row(0.0)))
        for r in range(len(ys) - 1):
            lo, hi = row(ys[r]), row(ys[r + 1])
            across = {len(ys) - 2: "bind", len(ys) - 3: "band"}.get(r)
            for j, band in enumerate(names):
                poly = [(lo[j], ys[r]), (lo[j + 1], ys[r]), (hi[j + 1], ys[r + 1]), (hi[j], ys[r + 1])]
                poly = cut(poly, [FOLD.dist(*p) for p in poly], mixed)
                pieces = []
                for mark in marks:
                    if not poly:
                        break
                    pieces += fan(cut(poly, [mark - FOLD.dist(*p) for p in poly], mixed))
                    poly = cut(poly, [FOLD.dist(*p) - mark for p in poly], mixed)
                pieces += fan(poly)
                for piece in pieces:
                    self.flap_face(mesh, piece, band, across)
        return mesh

    def flap_face(self, mesh, piece, band, across):
        # (across: the closure's band along the cover's top edge, which this face is in)
        top_edge = across is not None and band in ("in", "hook")

        def uv(p, tex):
            x, y = p
            if tex is INSIDE:
                return (x / LINING_TILE, y / LINING_TILE)
            if tex is OUTSIDE:
                return (x / OUT_TILE, y / OUT_TILE)
            if top_edge:
                return edge_uv(x, TOP - y, across)
            return edge_uv(y, self.hw(y) - abs(x), band)

        shown = EDGE if (band != "in" or top_edge) else INSIDE
        under = EDGE if (band in ("bind", "band") or top_edge) else OUTSIDE
        for side, tex in ((0, shown), (1, under)):
            ids = [mesh.point((round(p[0], 5), round(p[1], 5), side), lambda p=p: self.flap_point(*p)) for p in piece]
            uvs = [uv(p, tex) for p in piece]
            # (drawn against the clock a face of the cover shows its outside: the lining is the other way round)
            if side == 0:
                ids, uvs = ids[::-1], uvs[::-1]
            mesh.face(ids, uvs, tex)

    # ------------------------------------------------------------ the bottom sheet beside him
    def panel(self, detail):
        mesh = Mesh()
        step = 0.0125 * detail
        y0 = self.cut_l - 0.08
        Ys = list(np.arange(y0, PANEL_TO - RIM - step * 0.5, step)) + [PANEL_TO - RIM, PANEL_TO - BIND, PANEL_TO]
        inner = max(4, int(round(0.58 / (0.015 * detail))))

        def edges(Y):
            l = float(np.interp(Y, self.ext_y, self.ext_l)) + 0.015 + (BORDER - 0.015) * H.step((Y - (self.cut_l - 0.05)) / 0.15)
            r = float(np.interp(Y, self.ext_y, self.ext_r)) - 0.015 - (BORDER - 0.015) * H.step((Y - (self.cut_r - 0.05)) / 0.12)
            return r, l

        def place(x, Y):
            r, l = edges(Y)
            e = min(l - x, x - r, PANEL_TO - Y)
            z = PANEL_UP + 0.0015 * (1 + wave(x * 0.7, Y * 0.7)) + CURL[1] * max(0.0, 1 - e / CURL[0]) ** 2
            p = [x, Y, z]
            return in_sled(p, self.fit.body) if self.sked else p

        names = bands(len(columns(-1.0, 1.0, inner)))
        for k in range(len(Ys) - 1):
            lo, hi = columns(*edges(Ys[k]), inner), columns(*edges(Ys[k + 1]), inner)
            across = {len(Ys) - 2: "bind", len(Ys) - 3: "band"}.get(k)
            for j, band in enumerate(names):
                top_edge = across is not None and band in ("in", "hook")

                def uv(x, Y, tex):
                    if tex is INSIDE:
                        return (x / LINING_TILE, Y / LINING_TILE)
                    if tex is OUTSIDE:
                        return (x / OUT_TILE, Y / OUT_TILE)
                    if top_edge:
                        return edge_uv(x, PANEL_TO - Y, across)
                    r, l = edges(Y)
                    return edge_uv(Y, min(l - x, x - r), band)

                quad = [(lo[j], Ys[k]), (lo[j + 1], Ys[k]), (hi[j + 1], Ys[k + 1]), (hi[j], Ys[k + 1])]
                shown = EDGE if (band != "in" or top_edge) else INSIDE
                under = EDGE if (band in ("bind", "band") or top_edge) else OUTSIDE
                for side, tex in ((0, shown), (1, under)):
                    ids = [mesh.point((round(x, 5), round(Y, 5), side), lambda x=x, Y=Y: place(x, Y)) for x, Y in quad]
                    uvs = [uv(x, Y, tex) for x, Y in quad]
                    if side == 1:
                        ids, uvs = ids[::-1], uvs[::-1]
                    mesh.face(ids, uvs, tex)
        return mesh

    # ------------------------------------------------------------ the blanket
    def panel_z(self, x, Y):
        """How high the bottom sheet lies at a place, or 0 (what he lies on) where it is not."""
        y0 = self.cut_l - 0.08
        r = float(np.interp(Y, self.ext_y, self.ext_r)) - 0.015 - (BORDER - 0.015) * H.step((Y - (self.cut_r - 0.05)) / 0.12)
        l = float(np.interp(Y, self.ext_y, self.ext_l)) + 0.015 + (BORDER - 0.015) * H.step((Y - (self.cut_l - 0.05)) / 0.15)
        if Y < y0 or Y > PANEL_TO or not (r <= x <= l):
            return 0.0
        e = min(l - x, x - r, PANEL_TO - Y)
        return PANEL_UP + 0.003 + CURL[1] * max(0.0, 1 - e / CURL[0]) ** 2

    def drape(self):
        """The blanket's height over what he lies on, on a grid (5 mm across, 1 cm along): (X, Ys, loose, close).
        close: a cloth lying on him (as the blanket lay until 2026-11-23); loose: the blanket as it is laid on him,
        resting on his shoulders, chest and arms, sagging a little between them and falling off his arms to the
        bottom sheet (to what he lies on beyond it)."""
        if hasattr(self, "_drape"):
            return self._drape
        X = np.arange(-0.75, 0.7501, 0.005)
        Ys = np.arange(BLANKET_SIDE - BLANKET_L - 0.04, BLANKET_SIDE + 0.03, 0.01)
        hull = np.zeros((len(Ys), len(X)))
        for k, Y in enumerate(Ys):
            for px, pz in self.fit.body.cut(Y, 0.021 if Y < 0.60 else 0.011):
                i = int(round((px + 0.75) / 0.005))
                # (as far out again as the measuring was coarse, and his skin is proud of it sideways)
                for j in range(max(0, i - 3), min(len(X), i + 4)):
                    hull[k, j] = max(hull[k, j], pz)

        def blur(g, sx, sy):
            for axis, s in ((1, sx), (0, sy)):
                r = int(s * 3) + 1
                kern = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2)
                kern /= kern.sum()
                g = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), kern, mode="valid"), axis, g)
            return g

        close = hull.copy()
        for _ in range(4):
            close = np.maximum(blur(close, 2.6, 1.3), hull)
        close = blur(close, 1.0, 0.7) + BLANKET_OFF

        # loose: over him a smooth cover of his outline that bridges the hollows (between arm and chest, below the
        # collar bones, between the thighs) ...
        top = hull.copy()
        for _ in range(8):
            top = np.maximum(blur(top, SPAN_X / 0.005, SPAN_Y / 0.01), hull)
        top = blur(top, 1.5, 1.0) + BLANKET_OFF
        # ... and off his outermost on each side (smooth along him) it falls to what lies beside him
        floor = np.array([[self.panel_z(x, Y) + 0.004 for x in X] for Y in Ys])
        on = hull > 0.02
        edge_r = H.smooth(np.array([X[np.argmax(row)] if row.any() else -0.05 for row in on]), 2.0)
        edge_l = H.smooth(np.array([X[len(X) - 1 - np.argmax(row[::-1])] if row.any() else 0.05 for row in on]), 2.0)
        loose = top.copy()
        for k in range(len(Ys)):
            for side, e in ((-1, edge_r[k]), (1, edge_l[k])):
                j0 = int(np.argmin(np.abs(X - e)))
                z0 = top[k, j0]
                reach = REACH * z0 + 0.015
                for j in range(len(X)):
                    out = (X[j] - e) * side
                    if out > 0:
                        loose[k, j] = floor[k, j] + (z0 - floor[k, j]) * (1 - H.step(out / reach))
        loose = np.maximum(blur(loose, 1.5, 1.5), floor)
        self._drape = (X, Ys, loose, close)
        return self._drape

    def cloth(self, px, Y, which=2):
        """How high the blanket lies at a place (which: 2 loose, 3 close)."""
        d = self.drape()
        X, Ys, S = d[0], d[1], d[which]
        f, g = (Y - Ys[0]) / 0.01, (px - X[0]) / 0.005
        a, b = min(max(int(f), 0), len(Ys) - 2), min(max(int(g), 0), len(X) - 2)
        u, v = f - a, g - b
        return (S[a, b] * (1 - v) + S[a, b + 1] * v) * (1 - u) + (S[a + 1, b] * (1 - v) + S[a + 1, b + 1] * v) * u

    def dip(self, px):
        """By how much the blanket's upper edge is lower at his throat than beside his neck."""
        return (BLANKET_SIDE - BLANKET_TOP) * (1 - H.step((abs(px) - 0.055) / 0.05))

    def blanket(self, detail):
        mesh = Mesh()
        X, Ys, loose, close = self.drape()
        step = 0.0125 * detail
        arcs = np.arange(-BLANKET_W / 2, BLANKET_W / 2 + 1e-6, step)
        rows = np.arange(BLANKET_SIDE - step * int(BLANKET_L / step), BLANKET_SIDE + 1e-6, step)
        mid = int(np.argmin(np.abs(X)))
        lines = {}

        def pad(s, t):
            out = 1.0
            for v, (a, m, b) in ((s, CELLS[0]), (t, CELLS[1])):
                lo, hi = (a, m) if v < m else (m, b)
                out *= H.step((min(v - lo, hi - v) - 0.03) / 0.025)
            return out

        def line(which, Y):
            """The cloth's line across him at a place along him, and the length along it from his middle."""
            key = (which, round(Y, 5))
            if key not in lines:
                S = (loose, close)[which]
                f = (Y - Ys[0]) / 0.01
                a = min(max(int(f), 0), len(Ys) - 2)
                z = S[a] + (S[a + 1] - S[a]) * (f - a)
                length = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(X), np.diff(z)))])
                lines[key] = (z, length - length[mid])
            return lines[key]

        def at(which, arc, Y):
            z, length = line(which, Y)
            px, pz = float(np.interp(arc, length, X)), float(np.interp(arc, length, z))
            i = min(max(int(np.searchsorted(length, arc)) - 1, 0), len(X) - 2)
            tx, tz = X[i + 1] - X[i], z[i + 1] - z[i]
            return px, pz, -tz / math.hypot(tx, tz), tx / math.hypot(tx, tz)

        grid = {}
        for k, Y in enumerate(rows):
            y_d = self.drawn_along(Y)
            let = self.let_out(y_d)
            for j, whole in enumerate(arcs):
                px, pz, nx, nz = at(0, whole, Y)
                d = FOLD.dist(whole / let, y_d)
                # laid loose where it is uncovered; beside the fold, where the cover comes down onto it, close
                w = H.step(d / LOOSE_FROM)
                if w < 1:
                    cx, cz, cnx, cnz = at(1, whole, Y)
                    px, pz, nx, nz = cx + (px - cx) * w, cz + (pz - cz) * w, cnx + (nx - cnx) * w, cnz + (nz - cnz) * w
                s_, t_ = (BLANKET_SIDE - Y) / BLANKET_L, (BLANKET_W / 2 - whole) / BLANKET_W
                # its upper edge dips at his throat, where the hood's strips are
                dip = self.dip(px) * H.step((Y - (BLANKET_SIDE - 0.06)) / 0.06)
                Y_at = Y - dip
                if dip > 1e-4:
                    pz = float(self.cloth(px, Y_at)) * w + float(self.cloth(px, Y_at, 3)) * (1 - w)
                # (a soft thing: its cells stand in it, and it lies in slow waves; where it hangs off his arm the
                # waves are folds down its fall)
                hang = H.step((abs(nx) - 0.35) / 0.4)
                up = PAD * pad(s_, t_) + 0.0025 * wave(whole * 1.3, Y * 1.3) + 0.001 * wave(whole * 3.1 + 2.0, Y * 2.9)
                up += 0.006 * hang * wave(0.4 + whole * 0.3, Y * 2.2)
                # (under the cover it lies closer to him; its upper hem is turned down onto him)
                up -= 0.006 * H.step(-d / 0.02) + 0.002 * H.step((Y - (BLANKET_SIDE - 0.02)) / 0.02)
                # (over his shoulders beside his neck it lies a little looser: his collar came through it there)
                up += 0.004 * H.step((Y - (BLANKET_SIDE - 0.06)) / 0.05) * H.step((abs(px) - 0.04) / 0.03)
                floor = self.panel_z(px, Y_at) + 0.003
                p = [px + nx * up, Y_at, max(pz + nz * up, floor)]
                if self.sked:
                    p = in_sled(p, self.fit.body, 0.008)
                grid[(k, j)] = (p, d, (s_, t_))
        for k in range(len(rows) - 1):
            for j in range(len(arcs) - 1):
                quad = [(k, j), (k, j + 1), (k + 1, j + 1), (k + 1, j)]
                if all(grid[q][1] < -0.03 for q in quad):
                    continue                  # under the cover that stays closed
                ids = [mesh.point(q, lambda q=q: grid[q][0]) for q in quad]
                mesh.face(ids, [grid[q][2] for q in quad], KIT)
        return mesh

    # ------------------------------------------------------------ the hood's padded strips under his chin
    def collar(self, detail):
        mesh = Mesh()
        y0, y1, count = COLLAR
        per = 4 if detail == 1 else 2
        rows = [y0 + (y1 - y0) * k / (count * per) for k in range(count * per + 1)]
        round_ = 22 if detail == 1 else 12 if detail == 2 else 8
        # One outline for all of it: his throat where it is narrowest, a little wider toward his chest, and as
        # high at every row as his throat is there. (Each row round what was measured at it, the lower strips
        # went out over the slope of his shoulders: seen from beside his neck they stood there as a row of tabs.)
        neck = [q for q in self.fit.body.cut((y0 + y1) / 2 + 0.005, 0.016) if abs(q[0]) < 0.09 and q[1] > 0.02]
        high = max(q[1] for q in neck if abs(q[0]) < 0.035)
        lines = []
        for k, Y in enumerate(rows):
            t = (k % per) / per
            # (at its lower edge it is drawn in to him, under the blanket's hem)
            off = COLLAR_OFF + COLLAR_PUFF * math.sin(math.pi * t) ** 0.7 if 0 < k < len(rows) - 1 else COLLAR_OFF * (0.4 if k == 0 else 1.0)
            here = max([q[1] for q in self.fit.body.cut(Y, 0.011) if abs(q[0]) < 0.035], default=high)
            tall = min(max(here / high, 0.85), 1.15)
            wider = 1.0 + 0.10 * (1 - k / (len(rows) - 1))
            pts = [(q[0] * wider, q[1] * tall) for q in neck]
            # (and round what of him is measured right beside his throat at this row: the slope up to his neck
            # came through the lower strips, a white patch of his shirt, seen in game)
            pts += [q for q in self.fit.body.cut(Y, 0.011) if abs(q[0]) < 0.078 and q[1] > 0.02]
            wide = max(abs(q[0]) for q in pts)
            ring = H.grown(pts + [(-wide, 0.0), (wide, 0.0)], off)
            # from what he lies on at his right, over his throat, to what he lies on at his left
            top = [q for q in ring if q[1] > PANEL_UP + 0.002]
            top.sort(key=lambda q: math.atan2(q[1] - 0.05, q[0]), reverse=True)
            top = np.array(top)
            length = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(top, axis=0), axis=1))])
            line = []
            for j in range(round_ + 1):
                at = length[-1] * j / round_
                px, pz = float(np.interp(at, length, top[:, 0])), float(np.interp(at, length, top[:, 1]))
                # Beside his throat the blanket comes up over the strips: what of them would stand through it
                # lies under it. (Seen in game from beside his neck: a row of tabs standing out of the blanket.)
                if Y < BLANKET_SIDE - self.dip(px) + 0.004:
                    cover = float(self.cloth(px, Y))
                    if pz < cover + 0.010:
                        pz = min(pz, cover - 0.006)
                line.append((px, Y, pz, at - length[-1] / 2))
            lines.append(line)
        for k in range(len(rows) - 1):
            for j in range(round_):
                quad = [(k, j), (k, j + 1), (k + 1, j + 1), (k + 1, j)]
                place = lambda q: (in_sled(list(lines[q[0]][q[1]][:3]), self.fit.body, 0.012) if self.sked else lines[q[0]][q[1]][:3])
                ids = [mesh.point(q, lambda q=q: place(q)) for q in quad]
                mesh.face(ids, [(lines[c][e][3] / OUT_TILE, rows[c] / OUT_TILE) for c, e in quad], OUTSIDE)
        return mesh

    def meshes(self, detail):
        return [("flap", self.flap(detail)), ("panel", self.panel(detail)), ("blanket", self.blanket(detail)),
                ("collar", self.collar(detail))]


# ---------------------------------------------------------------- the closure's picture and the two materials
TO_PAA = r"F:\Program Files (x86)\Steam\steamapps\common\Arma 3 Tools\ImageToPAA\ImageToPAA.exe"
COYOTE = 0.62         # the coyote band, against the kit's edge picture
BLANKET_DARKER = 0.56 # the blanket, against the kit's atlas (the game shows a cloth about twice as light as its picture)


def make_pictures():
    """hpmk_closure_co.paa: the kit's edge picture with its coyote band darker (in the game the kit's shows as
    cream: twice as light as the shell, where the photographs have a band a little lighter than the shell).
    hpmk_closure.rvmat, hpmk_blanket.rvmat: the kit's materials, dull (webbing and a fleece blanket do not shine)."""
    import re
    import subprocess
    import tempfile
    from pathlib import Path

    from PIL import Image

    data = Path(__file__).resolve().parents[1] / "addons/acme_hpmk/data"
    work = Path(tempfile.mkdtemp(prefix="hpmk_closure_"))
    subprocess.run(["hemtt", "utils", "paa", "convert", str(data / "hpmk_edge_co.paa"), str(work / "edge.png")], capture_output=True)
    pic = np.asarray(Image.open(work / "edge.png").convert("RGB")).astype(float)
    rows = pic.mean(axis=1)
    tan = (rows[:, 0] > 80) & (rows[:, 0] > rows[:, 2] * 1.3)
    pic[tan] *= COYOTE
    Image.fromarray(np.clip(pic, 0, 255).astype(np.uint8)).save(work / "hpmk_closure_co.png")
    out = data / "hpmk_closure_co.paa"
    subprocess.run([TO_PAA, str(work / "hpmk_closure_co.png"), str(out)], capture_output=True)
    print("wrote", out, "(%d rows of the coyote band darkened)" % int(tan.sum()))

    blanket_picture(data, work)

    def dull(source, name, note, shine, smdi=None):
        s = (data / source).read_text()
        s = re.sub(r"^//.*\n", "// " + note + "\n", s, count=1)
        s = re.sub(r"specular\[\] = \{[^}]*\};", "specular[] = {%s, %s, %s, 1};" % (shine[0], shine[0], shine[0]), s)
        s = re.sub(r"specularPower = [0-9.]+;", "specularPower = %s;" % shine[1], s)
        if smdi:
            s = re.sub(r'texture = "[^"]*_smdi\.paa";', 'texture = "%s";' % smdi, s)
        (data / name).write_text(s)
        print("wrote", data / name)

    dull("hpmk_edge.rvmat", "hpmk_closure.rvmat", "HRS-I closure on the worn shell: the edge band's relief, dull (tools/hpmk_opened.py).", (0.1, 12))
    dull("hpmk.rvmat", "hpmk_blanket.rvmat", "HPMK-I self-heating blanket on the casualty: dull, with a nap (tools/hpmk_opened.py).", (0.04, 8),
         "#(argb,8,8,3)color(1,0.05,0.12,1,SMDI)")
    # (its relief: the lining's nap, three times to the blanket's length; the atlas's relief is not laid out as this picture)
    s = (data / "hpmk_blanket.rvmat").read_text()
    a = s.index("class Stage1")
    b = s.index("class Stage2")
    stage = s[a:b].replace("hpmk_nohq.paa", "hpmk_in_nohq.paa").replace("aside[] = {1, 0, 0}; up[] = {0, 1, 0};", "aside[] = {3, 0, 0}; up[] = {0, 3, 0};")
    assert "hpmk_in_nohq.paa" in stage and "{3, 0, 0}" in stage
    (data / "hpmk_blanket.rvmat").write_text(s[:a] + stage + s[b:])


def blanket_picture(data, work):
    """hpmk_blanket_co.paa: the blanket's picture cut out of the kit's atlas, darker, with the cloudiness of a
    felted cloth (the atlas has it as flat as paper). The picture is square and the blanket is not (its length
    runs along the picture's width), so the printed label is drawn narrower by as much as the blanket stretches
    it, to read in its own proportions on him."""
    import subprocess

    from PIL import Image

    subprocess.run(["hemtt", "utils", "paa", "convert", str(data / "hpmk_co.paa"), str(work / "atlas.png")], capture_output=True)
    atlas = Image.open(work / "atlas.png").convert("RGB")
    cloth = atlas.crop((ATLAS[0], ATLAS[1], ATLAS[0] + ATLAS[2], ATLAS[1] + ATLAS[2])).resize((1024, 1024), Image.LANCZOS)
    pic = np.asarray(cloth).astype(float)
    # the label: the ink in the first cell
    x0, x1 = int(CELLS[0][0] * 1024) + 12, int(CELLS[0][1] * 1024) - 12
    y0, y1 = int(CELLS[1][0] * 1024) + 12, int(CELLS[1][1] * 1024) - 12
    cell = pic[y0:y1, x0:x1]
    ground = np.median(cell.reshape(-1, 3), axis=0)
    ink = np.abs(cell - ground).sum(axis=2) > 60
    ys, xs = np.nonzero(ink)
    bx0, bx1, by0, by1 = xs.min() - 6, xs.max() + 7, ys.min() - 6, ys.max() + 7
    label = Image.fromarray(cell[by0:by1, bx0:bx1].astype(np.uint8))
    narrow = max(1, int(round(label.width * BLANKET_W / BLANKET_L)))
    label = np.asarray(label.resize((narrow, label.height), Image.LANCZOS)).astype(float)
    cell[by0:by1, bx0:bx1] = ground
    at = (bx0 + bx1) // 2 - narrow // 2
    cell[by0:by1, at:at + narrow] = label
    pic[y0:y1, x0:x1] = cell
    print("   the label (%d x %d px) drawn %d px wide" % (bx1 - bx0, by1 - by0, narrow))
    cloth = pic * BLANKET_DARKER
    rng = np.random.default_rng(20261120)
    f = np.fft.fftfreq(1024)
    soft = lambda g, sg: np.real(np.fft.ifft2(np.fft.fft2(g) * np.exp(-2 * (np.pi * sg) ** 2 * (f[:, None] ** 2 + f[None, :] ** 2))))
    cloud, grain = soft(rng.normal(size=(1024, 1024)), 30.0), soft(rng.normal(size=(1024, 1024)), 1.2)
    cloth *= (1.0 + 0.05 * cloud / cloud.std() + 0.035 * grain / grain.std())[:, :, None]
    Image.fromarray(np.clip(cloth, 0, 255).astype(np.uint8)).save(work / "hpmk_blanket_co.png")
    out = data / "hpmk_blanket_co.paa"
    subprocess.run([TO_PAA, str(work / "hpmk_blanket_co.png"), str(out)], capture_output=True)
    print("wrote", out, "mean colour", cloth.reshape(-1, 3).mean(axis=0).round())


if __name__ == "__main__":
    import sys
    import tempfile
    from pathlib import Path
    if sys.argv[1:] == ["--blanket"]:
        blanket_picture(Path(__file__).resolve().parents[1] / "addons/acme_hpmk/data", Path(tempfile.mkdtemp(prefix="hpmk_blanket_")))
    else:
        make_pictures()
