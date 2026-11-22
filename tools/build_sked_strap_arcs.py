#!/usr/bin/env python3
"""The SKED's straps that cross the casualty's arms and hands, pulled tight over a bare casualty.

The straps of the wrapped SKED are arches of one fixed shape in its model; for a bare casualty each is moved
down onto him (acmeStrapFitBare[] of the SKED's class). An arch that is low enough to lie on the belly is lower
still at its sides, where the arms are: it cut through forearms and wrists (seen in game 2026-11-19).

For these straps this tool makes models of their own for a bare casualty: the strap's own mesh, buckles and
textures (first LOD of sked_wrapped.p3d), each point moved up or down so that the strap's underside follows a
line pulled tight over the casualty's body and arms (tools/litter_body.py) from one side of the shell to the
other. The server hangs them on a SKED with a bare casualty and the SKED hides its own strap there
(acmeStrapArcBare[], acmeStrapArcSources[] of its class; acme_sked_ace, fn_strapArcs.sqf). A casualty in the
HPMK keeps the model's straps.

Axes as in the model file: x across, y up, z along (the head at +z).

  python tools/build_sked_strap_arcs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_talon_strap_arcs as talon  # noqa: E402
import litter_body  # noqa: E402
import strap_settle  # noqa: E402
import strap_texture  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "addons/acme_sked"
SOURCE = ROOT / "sked_wrapped.p3d"
# where the casualty's pelvis is along the SKED, and how high he lies in it (measured in game)
PELVIS, FLOOR = 0.056, 0.003
# The straps, and how far the model's own is moved for a bare casualty (acmeStrapFitBare[] in acme_sked's
# config.cpp): where the new strap leaves the shell it is exactly where the old one was.
STRAPS = {"strap_belly": -0.105}
# The leg straps. In the model they are one strap across the pelvis with two buckles; on a Skedco each goes round
# its own thigh: from its side of the shell over the top of the thigh, the buckle lying there, and down between
# the legs. The strap is cut in the middle and each half laid that way over the casualty (leg_loops()).
LOOPS = {"strap_pelvis": -0.105}
CROTCH = -0.235       # along the casualty, from his pelvis: where his legs have parted (from the scan)
SLANT_FROM = 0.19     # from the middle: outward of this a leg strap runs straight across, inward it slants to the crotch
DIVE = 0.012          # from the middle: where a leg strap goes down between the thighs
DIVE_TO = 0.03        # how low over the shell it ends there (out of sight)
BUCKLE_FROM = 0.165   # from the middle: where the outer end of a buckle comes to lie, on top of the thigh
# The harness over the chest (the strap across it and the two that cross from the shoulders) is not one strap
# across the SKED: it is moved down as the model's own is, and then every part of it that would be inside the
# casualty's body or arms is lifted onto the line pulled tight across him at that place.
HARNESS = {"strap_chest": -0.10}
LYING = 0.035         # webbing lower than this (after the move) lies on the shell under him and stays there
FIXED = 0.272         # from the middle: from here outward a strap is left as it is (it goes down into the shell)
WIDE_FIXED = 0.29     # the same for the harness over the chest: the upper arms lie further out
LIFT = 0.004          # how far the webbing's underside stays off the skin
# A casualty in the HPMK: the same straps pulled tight over the shell he wears (tools/build_hpmk_shell.py). The
# leg straps cannot go round each thigh there: the strap across the pelvis is one strap again, over the bag. The
# strap over the knees gets a model too (the bag is wider and higher there than bare legs).
STRAPS_HPMK = {"strap_pelvis": -0.105, "strap_belly": -0.105, "strap_knee": -0.12}
SHELL_OFF = 0.003     # how far the webbing's underside stays off the shell
# The strap over the feet and the chest harness are laid on the shell part by part (harness()), from where the
# SKED's own are for a bare casualty.
# (the strap over the feet stays where the SKED's own is: the bag is inside the foot cover it lies on, and the
# strap is only lifted where the bag over his shins is higher than it)
HARNESS_HPMK = {"strap_chest": -0.10, "strap_feet": 0.0}


SURFACE = {}


def on_the_bag(points, faces, keep=(), far=strap_settle.FAR, opened=False):
    """A strap's points, every part of its webbing brought down (or up) onto the cloth of the HPMK shell under
    it (strap_settle.py): the tight line it was laid on stands off the bag wherever the bag is lower than its
    highest place under the strap."""
    if ("sked", opened) not in SURFACE:
        SURFACE[("sked", opened)] = strap_settle.surface(True, opened)
    top = SURFACE[("sked", opened)]
    there = litter_body.TALON_PELVIS - PELVIS
    webbing = {v[0] for vs, flags, tex, mat in faces if b"web" in tex.lower() for v in vs}
    held = [points[i] for i in keep]
    out, lines = strap_settle.settle(
        points, lambda x, along: (lambda h: None if h is None else h + FLOOR)(top(x, along + there)), SHELL_OFF, webbing=webbing, far=far)
    for i, p in zip(keep, held):
        out[i] = p
    print("\n".join(lines))
    return out


def tight_line(fit, lo, hi, anchor_x, anchor_z):
    """The line of a strap pulled tight across the casualty between two places along the SKED, fixed at
    (-anchor_x, anchor_z) and (anchor_x, anchor_z): over his body and arms (fit "bare") or over the HPMK shell."""
    if fit == "bare":
        return litter_body.tight(lo - PELVIS, hi - PELVIS, anchor_x, anchor_z, LIFT, FLOOR)
    import build_hpmk_shell
    there = litter_body.TALON_PELVIS - PELVIS
    reach = anchor_x - 0.004
    # (where the bag is wider than the strap's fixing the strap presses it in)
    over = [(max(-reach, min(reach, x)), z + SHELL_OFF + FLOOR) for x, z in build_hpmk_shell.outline(lo + there, hi + there, sked=True)]
    return litter_body.hull(over + [(-anchor_x, anchor_z), (anchor_x, anchor_z)])


def main(fit="bare"):
    pts, nrm, recs, sels = talon.read_lod0(SOURCE)
    for name, moved in (STRAPS if fit == "bare" else STRAPS_HPMK).items():
        ids = sels[name]
        # from here outward the strap is left as it is (a strap that does not reach that far: its own end)
        fixed = min(FIXED if fit == "bare" else WIDE_FIXED, max(abs(pts[i][0]) for i in ids) - 0.004)
        # the strap's underside as modelled, by distance from the middle (each centimetre)
        # (of its webbing alone: a buckle's underside is another line, and the strap came out stepped with it)
        webbing = {v[0] for vs, flags, tex, mat in recs if b"web" in tex.lower() for v in vs} & set(ids)
        low = {}
        for i in webbing:
            k = round(abs(pts[i][0]) / 0.01)
            low[k] = min(low.get(k, 9.0), pts[i][1])
        keys = sorted(low)

        def under(x):
            k = abs(x) / 0.01
            a = max([j for j in keys if j <= k], default=keys[0])
            b = min([j for j in keys if j >= k], default=keys[-1])
            return low[a] if a == b else low[a] + (low[b] - low[a]) * (k - a) / (b - a)

        zs = [pts[i][2] for i in ids]
        line = tight_line(fit, min(zs), max(zs), fixed, under(fixed) + moved)
        points, normals, faces, where, modelled = [], [], [], {}, []
        for vs, flags, tex, mat in recs:
            if not all(v[0] in ids for v in vs):
                continue
            out = []
            for point, normal, u, v in vs:
                if point not in where:
                    x, y, z, pflags = pts[point]
                    modelled.append((x, y, z))
                    if abs(x) < fixed:
                        y += litter_body.height(line, x) - under(x)
                    else:
                        y += moved
                    where[point] = len(points)
                    points.append((x, y, z, pflags))
                normals.append(nrm[normal])
                out.append((where[point], len(normals) - 1, u, v))
            faces.append((out, flags, tex, mat))
        path = ROOT / ("sked_%s_%s.p3d" % (name, fit))
        if fit == "hpmk":
            points = on_the_bag(points, faces)
        # lifted onto him the webbing is longer: its weave is laid out again along it (strap_texture.py)
        faces, lines = strap_texture.retexture(modelled, points, faces)
        print("\n".join(lines))
        talon.write(path, points, normals, faces)
        print("wrote %s: %d points, %d faces, along %.3f..%.3f" % (path.name, len(points), len(faces), min(zs), max(zs)))
        print("   underside, as modelled and moved | pulled tight:",
              " ".join("%+.2f:%.3f|%.3f" % (x / 100, under(x / 100) + moved, litter_body.height(line, x / 100)) for x in range(-26, 27, 2)))


def harness(fit="bare"):
    pts, nrm, recs, sels = talon.read_lod0(SOURCE)
    for name, moved in (HARNESS if fit == "bare" else HARNESS_HPMK).items():
        ids = sorted(sels[name])
        # the line pulled tight across him, at every 2 cm along
        lines = {}

        def tight_at(z):
            k = round(z / 0.02)
            if k not in lines:
                # (over 8 cm of him: both edges of a strap 5 cm wide then get the same line)
                lines[k] = tight_line(fit, k * 0.02 - 0.04, k * 0.02 + 0.04, WIDE_FIXED, FLOOR)
            return lines[k]

        # for every point: the lowest point of the harness near it (within 1.5 cm across and along, and not more
        # than 3 cm under it: a strap that crosses under another is a layer of its own)
        cells = {}
        for i in ids:
            x, y, z, _ = pts[i]
            cells.setdefault((round(x / 0.015), round(z / 0.015)), []).append(i)
        lift = {}
        for i in ids:
            x, y, z, _ = pts[i]
            if abs(x) >= WIDE_FIXED or y + moved < LYING:
                lift[i] = 0.0
                continue
            cx, cz = round(x / 0.015), round(z / 0.015)
            low = y
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in cells.get((cx + dx, cz + dz), ()):
                        yj = pts[j][1]
                        if y - 0.03 <= yj < low and abs(pts[j][0] - x) <= 0.015 and abs(pts[j][2] - z) <= 0.015:
                            low = yj
            lift[i] = max(0.0, litter_body.height(tight_at(z), x) - (low + moved))
        # Smoothed, so that the webbing stays a band and does not crumple: every point takes the mean of what its
        # neighbours within 3 cm need at most (never less than it needs itself).
        def spread(values, pick):
            out = {}
            for i in ids:
                x, y, z, _ = pts[i]
                cx, cz = round(x / 0.015), round(z / 0.015)
                near = [values[j] for dx in range(-2, 3) for dz in range(-2, 3) for j in cells.get((cx + dx, cz + dz), ())
                        if (pts[j][0] - x) ** 2 + (pts[j][2] - z) ** 2 <= 0.0009 and abs(pts[j][1] - y) <= 0.04]
                out[i] = pick(near)
            return out

        still = {i for i in ids if abs(pts[i][0]) >= WIDE_FIXED or pts[i][1] + moved < LYING}
        lift = spread(spread(lift, max), lambda v: sum(v) / len(v))
        for i in still:
            lift[i] = 0.0
        points, normals, faces, where, modelled = [], [], [], {}, []
        idset = set(ids)
        for vs, flags, tex, mat in recs:
            if not all(v[0] in idset for v in vs):
                continue
            out = []
            for point, normal, u, v in vs:
                if point not in where:
                    x, y, z, pflags = pts[point]
                    where[point] = len(points)
                    modelled.append((x, y, z))
                    points.append((x, y + moved + lift[point], z, pflags))
                normals.append(nrm[normal])
                out.append((where[point], len(normals) - 1, u, v))
            faces.append((out, flags, tex, mat))
        path = ROOT / ("sked_%s_%s.p3d" % (name, fit))
        # (the strap over his feet lies on the SKED's foot cover, not on the bag)
        if fit == "hpmk" and name != "strap_feet":
            points = on_the_bag(points, faces, [where[i] for i in still if i in where], 0.16)
        faces, lines = strap_texture.retexture(modelled, points, faces)
        print("\n".join(lines))
        talon.write(path, points, normals, faces)
        raised = [v for v in lift.values() if v > 0.001]
        print("wrote %s: %d points, %d faces; %d points lifted, by up to %.3f m" % (path.name, len(points), len(faces), len(raised), max(raised, default=0)))


def leg_loops():
    import json
    import math
    pts, nrm, recs, sels = talon.read_lod0(SOURCE)
    scan = json.loads(litter_body.SCAN.read_text())
    first, step = scan["across_first"], scan["across_step"]

    def body(x, along):
        """The casualty's top at x across, within 3.5 cm of a place along him (-1: nothing of him)."""
        i = round((x - first) / step)
        return max((st["up"][i] for st in scan["stations"] if abs(st["along"] - along) <= 0.035), default=-1)

    for name, moved in LOOPS.items():
        ids = sels[name]
        idset = set(ids)
        # (of its webbing alone: a buckle's underside is another line, and the strap came out stepped with it)
        webbing = {v[0] for vs, flags, tex, mat in recs if b"web" in tex.lower() for v in vs} & set(ids)
        low = {}
        for i in webbing:
            k = round(abs(pts[i][0]) / 0.01)
            low[k] = min(low.get(k, 9.0), pts[i][1])
        keys = sorted(low)

        def under(ax):
            k = ax / 0.01
            a = max([j for j in keys if j <= k], default=keys[0])
            b = min([j for j in keys if j >= k], default=keys[-1])
            return low[a] if a == b else low[a] + (low[b] - low[a]) * (k - a) / (b - a)

        zs = [pts[i][2] for i in ids]
        centre = (min(zs) + max(zs)) / 2
        crotch = CROTCH + PELVIS

        def along(ax):
            if ax >= SLANT_FROM:
                return centre
            return centre + (crotch - centre) * min(1.0, (SLANT_FROM - ax) / (SLANT_FROM - DIVE))

        # the strap as modelled, by length along it from where it is fixed (FIXED) inward to its middle
        n = int(FIXED / 0.002)
        length = [0.0]
        for j in range(n):
            a, b = FIXED - j * 0.002, FIXED - (j + 1) * 0.002
            length.append(length[-1] + math.hypot(0.002, under(a) - under(b)))

        def modelled(ax):
            f = (FIXED - ax) / 0.002
            j = min(int(f), n - 1)
            return length[j] + (length[j + 1] - length[j]) * (f - j)

        # the buckles: everything of the strap that is not webbing, on each side
        hard = {1: [], -1: []}
        for vs, flags, tex, mat in recs:
            if all(v[0] in idset for v in vs) and b"web" not in tex.lower():
                for v in vs:
                    hard[1 if pts[v[0]][0] > 0 else -1].append(abs(pts[v[0]][0]))
        points, normals, faces, where, as_drawn = [], [], [], {}, []
        frames = {}
        for side in (1, -1):
            # the line pulled tight from the fixing over hand and thigh to where the strap goes down between the
            # legs, in (distance from the middle, height); the strap slants toward the crotch as it comes inward
            cloud = []
            for k in range(int(DIVE * 100), int(FIXED * 100)):
                ax = k / 100
                z = body(side * ax, along(ax) - PELVIS)
                if z < 0:
                    continue
                z = litter_body.skin(ax, z) + LIFT + FLOOR
                more = litter_body.ARM_MORE if ax >= litter_body.ARMS else 0.0
                cloud += [(max(ax - 0.005, DIVE), z), (min(ax + 0.005 + more, FIXED - 0.002), z)]
            line = litter_body.hull(cloud + [(FIXED, under(FIXED) + moved)])
            # from the fixing inward, in short steps, then straight down between the thighs
            path = [(0.0, FIXED, under(FIXED) + moved, centre)]
            nodes = list(reversed(line)) + [(line[0][0], DIVE_TO)]
            for (x1, h1), (x2, h2) in zip(nodes, nodes[1:]):
                steps = max(1, int(math.hypot(x2 - x1, h2 - h1) / 0.002))
                for j in range(1, steps + 1):
                    ax, h = x1 + (x2 - x1) * j / steps, h1 + (h2 - h1) * j / steps
                    a = along(ax)
                    u0, ax0, h0, a0 = path[-1]
                    path.append((u0 + math.sqrt((ax - ax0) ** 2 + (h - h0) ** 2 + (a - a0) ** 2), ax, h, a))
            total = path[-1][0]
            # where the buckle goes: its outer end on top of the thigh, itself as long as it is; the webbing
            # outside and inside of it is let out or taken in to reach
            b_out, b_in = modelled(max(hard[side])), modelled(min(hard[side]))
            to_out = next(u for u, ax, h, a in path if ax <= BUCKLE_FROM)
            to_in = to_out + (b_in - b_out)
            if to_in > total - 0.05:
                raise ValueError("no room for the buckle on the thigh")
            whole = modelled(0.0)

            def laid(s):
                if s <= b_out:
                    return s * to_out / b_out
                if s <= b_in:
                    return to_out + (s - b_out)
                return to_in + (s - b_in) * (total - to_in) / (whole - b_in)

            def at(u):
                """The place on the line at length u, and the strap's own axes there (along it, out of it, across it)."""
                u = min(max(u, 0.0), total)
                lo, hi = 0, len(path) - 1
                while hi - lo > 1:
                    m = (lo + hi) // 2
                    if path[m][0] <= u:
                        lo = m
                    else:
                        hi = m
                (u0, x0, h0, a0), (u1, x1, h1, a1) = path[lo], path[hi]
                f = 0.0 if u1 == u0 else (u - u0) / (u1 - u0)
                place = (side * (x0 + (x1 - x0) * f), h0 + (h1 - h0) * f, a0 + (a1 - a0) * f)
                # (the direction over a centimetre, so that the strap does not kink at every step of the scan)
                (ub, xb, hb, ab) = path[max(lo - 3, 0)]
                (ue, xe, he, ae) = path[min(hi + 3, len(path) - 1)]
                t = (side * (xe - xb), he - hb, ae - ab)
                d = math.sqrt(sum(c * c for c in t)) or 1.0
                t = tuple(c / d for c in t)
                dot = t[2]
                w = (-dot * t[0], -dot * t[1], 1 - dot * t[2])
                d = math.sqrt(sum(c * c for c in w)) or 1.0
                w = tuple(c / d for c in w)
                # out of the strap: square to both, and away from the casualty (the strap runs inward: to the
                # casualty's left side that is one way round, to his right the other)
                o = (t[1] * w[2] - t[2] * w[1], t[2] * w[0] - t[0] * w[2], t[0] * w[1] - t[1] * w[0])
                if side < 0:
                    o = tuple(-c for c in o)
                return place, t, o, w

            frames[side] = (laid, at, modelled)
            print("   %s leg: fixed at %.3f, over the thigh at %.3f, down between the legs at %.3f from the middle; %.3f m long (modelled %.3f); buckle from %.3f to %.3f along it"
                  % ("left" if side > 0 else "right", FIXED, max(h for x, h in line), line[0][0], total, whole, to_out, to_in))

        # The parts of a buckle are stiff: each (what hangs together of what is not webbing) is laid on the line as
        # a whole, by its middle, and not bent along it.
        parent = {}

        def find(a):
            while parent.setdefault(a, a) != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for vs, flags, tex, mat in recs:
            if all(v[0] in idset for v in vs) and b"web" not in tex.lower():
                for v in vs[1:]:
                    parent[find(v[0])] = find(vs[0][0])
        members = {}
        for q in list(parent):
            members.setdefault(find(q), []).append(q)
        stiff = {}
        for root, group in members.items():
            side = 1 if sum(pts[q][0] for q in group) >= 0 else -1
            middle = sum(frames[side][2](abs(pts[q][0])) for q in group) / len(group)
            for q in group:
                stiff[q] = (side, middle)

        def place(x, y, z, side, middle=None):
            """Where a point of the modelled strap comes to lie, and the strap's axes there. `middle`: the point
            belongs to a stiff part, which lies on the line by its middle (length along the modelled strap)."""
            ax = abs(x)
            if ax >= FIXED:
                return (x, y + moved, z), None
            up, off = y - under(ax), z - centre
            laid, at, modelled = frames[side]
            if middle is not None:
                p, t, o, w = at(laid(middle))
                run = modelled(ax) - middle
            else:
                p, t, o, w = at(laid(modelled(ax)))
                run = 0.0
            return (p[0] + run * t[0] + up * o[0] + off * w[0], p[1] + run * t[1] + up * o[1] + off * w[1],
                    p[2] + run * t[2] + up * o[2] + off * w[2]), (side, ax, t, o, w)

        def turned(normal, frame):
            nx, ny, nz = normal
            if not frame:
                return normal
            side, ax, t, o, w = frame
            # the normal in the modelled strap's own axes there (inward along it, out of it, along the SKED)
            slope = (under(ax + 0.004) - under(max(ax - 0.004, 0.0))) / (0.004 + min(ax, 0.004))
            d = math.hypot(1.0, slope)
            c1 = (nx * -side + ny * -slope) / d
            c2 = (nx * -side * slope + ny) / d
            return (c1 * t[0] + c2 * o[0] + nz * w[0], c1 * t[1] + c2 * o[1] + nz * w[1], c1 * t[2] + c2 * o[2] + nz * w[2])

        def strips(corners):
            """A face cut into strips a centimetre wide across the SKED (corners: lists x, y, z, normal, u, v)."""
            lo = math.floor(min(c[0] for c in corners) / 0.01)
            hi = math.ceil(max(c[0] for c in corners) / 0.01)
            for k in range(lo, hi):
                poly = corners
                for edge, keep in ((k * 0.01, 1), ((k + 1) * 0.01, -1)):
                    cut = []
                    for i, c in enumerate(poly):
                        d = poly[(i + 1) % len(poly)]
                        ci, di = (c[0] - edge) * keep >= -1e-9, (d[0] - edge) * keep >= -1e-9
                        if ci:
                            cut.append(c)
                        if ci != di:
                            f = (edge - c[0]) / (d[0] - c[0])
                            cut.append([c[j] + (d[j] - c[j]) * f for j in range(len(c))])
                    poly = cut
                    if len(poly) < 3:
                        break
                if len(poly) >= 3:
                    yield poly

        for vs, flags, tex, mat in recs:
            if not all(v[0] in idset for v in vs):
                continue
            if vs[0][0] in stiff:
                # a part of a buckle: its own points, shared between its faces
                out = []
                for point, normal, u, v in vs:
                    side, middle = stiff[point]
                    new, frame = place(*pts[point][:3], side, middle)
                    if point not in where:
                        where[point] = len(points)
                        points.append(new + (pts[point][3],))
                        as_drawn.append(pts[point][:3])
                    normals.append(turned(nrm[normal], frame))
                    out.append((where[point], len(normals) - 1, u, v))
                faces.append((out, flags, tex, mat))
                continue
            corners = [list(pts[point][:3]) + list(nrm[normal]) + [u, v] for point, normal, u, v in vs]
            for poly in strips(corners):
                side = 1 if sum(c[0] for c in poly) >= 0 else -1
                made = []
                for c in poly:
                    new, frame = place(c[0], c[1], c[2], side)
                    points.append(new + (0,))
                    as_drawn.append(tuple(c[0:3]))
                    normals.append(turned(tuple(c[3:6]), frame))
                    made.append((len(points) - 1, len(normals) - 1, c[6], c[7]))
                # (a face has three or four corners)
                if len(made) <= 4:
                    faces.append((made, flags, tex, mat))
                else:
                    for i in range(1, len(made) - 1):
                        faces.append(([made[0], made[i], made[i + 1]], flags, tex, mat))
        path = ROOT / ("sked_%s_bare.p3d" % name)
        faces, lines = strap_texture.retexture(as_drawn, points, faces)
        print("\n".join(lines))
        talon.write(path, points, normals, faces)
        print("wrote %s: %d points, %d faces" % (path.name, len(points), len(faces)))


if __name__ == "__main__":
    main()
    harness()
    leg_loops()
    main("hpmk")
    harness("hpmk")
