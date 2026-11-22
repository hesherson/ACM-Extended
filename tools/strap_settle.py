"""A litter's strap, laid on the HPMK shell the casualty wears so that its webbing lies on the cloth.

The builders lay a strap on the line pulled tight across the bag at the strap's place (the hull of the bag there,
over the strap's whole width, or over 8 cm of him for the chest harness). Where the bag is lower than that line
(it slopes along him under a strap 5 cm wide, or the line bridges from one high place to the next), the strap
stood in the air over it: "all of the straps don't sit flush" (the user, 2026-11-20, of pictures of a casualty in
the HPMK on both litters). Here every point of a strap is moved up or down so that the underside of the webbing
at that place lies just over the bag's own surface under it.

surface(sked) -> height(x, along): the bag's top there in the scan's axes (over what he lies on), or None
settle(points, height, off, ...) -> points
"""
import math
from pathlib import Path

import numpy as np

ASSETS = Path(__file__).with_name("assets")
CELL = 0.005
FAR = 0.07            # a part of a strap further than this from the cloth is not lying on the bag


def surface(sked, opened=False):
    """The top of the fitted shell (tools/fit_hpmk_worn.py leaves it as a preview OBJ in the scan's axes) as a
    function of the place: the highest of its faces over each 5 mm cell and its neighbours. opened: the shell
    with its cover folded back off his chest."""
    path = ASSETS / ("hpmk_worn%s%s_preview.obj" % ("_open" if opened else "", "_sked" if sked else ""))
    v, faces = [], []
    for line in open(path):
        t = line.split()
        if t and t[0] == "v":
            v.append([float(a) for a in t[1:4]])
        elif t and t[0] == "f":
            faces.append([int(a) - 1 for a in t[1:]])
    v = np.array(v)
    x0, y0 = v[:, 0].min() - CELL, v[:, 1].min() - CELL
    nx, ny = int((v[:, 0].max() - x0) / CELL) + 3, int((v[:, 1].max() - y0) / CELL) + 3
    top = np.full((nx, ny), -9.0)
    for face in faces:
        for k in range(1, len(face) - 1):
            a, b, c = v[face[0]], v[face[k]], v[face[k + 1]]
            i0, i1 = int((min(a[0], b[0], c[0]) - x0) / CELL), int((max(a[0], b[0], c[0]) - x0) / CELL) + 1
            j0, j1 = int((min(a[1], b[1], c[1]) - y0) / CELL), int((max(a[1], b[1], c[1]) - y0) / CELL) + 1
            d = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    px, py = x0 + i * CELL, y0 + j * CELL
                    if abs(d) < 1e-12:
                        continue
                    s = ((px - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (py - a[1])) / d
                    t = ((b[0] - a[0]) * (py - a[1]) - (px - a[0]) * (b[1] - a[1])) / d
                    # (a little over the face's edges: a cell's corner between two faces belongs to both)
                    if s >= -0.02 and t >= -0.02 and s + t <= 1.02:
                        z = a[2] + s * (b[2] - a[2]) + t * (c[2] - a[2])
                        if z > top[i, j]:
                            top[i, j] = z

    def height(x, along):
        i, j = int(round((x - x0) / CELL)), int(round((along - y0) / CELL))
        if i < 1 or j < 1 or i >= nx - 1 or j >= ny - 1:
            return None
        h = top[i - 1:i + 2, j - 1:j + 2].max()
        return None if h < -8 else float(h)

    return height


def settle(points, height, off, inside=0.19, outside=0.25, webbing=None, far=FAR):
    """points: [(x, up, along, flags)] of one strap in its model's axes; height(x, along): the bag's top there in
    the same axes (or None); off: how far the webbing's underside stays off the cloth. Between `inside` and
    `outside` from the middle the move fades out: there the strap leaves the bag for where it is fixed.
    webbing: the indices of the points of webbing (what is measured against the cloth; all points if None).
    Returns (points, lines of a report)."""
    n = len(points)
    P = np.array([p[:3] for p in points], float)
    web = set(range(n)) if webbing is None else set(webbing)
    cells = {}
    for i in range(n):
        cells.setdefault((round(P[i, 0] / 0.015), round(P[i, 2] / 0.015)), []).append(i)

    def near(i, reach, layer):
        x, y, z = P[i]
        cx, cz = round(x / 0.015), round(z / 0.015)
        r = int(math.ceil(reach / 0.015))
        return [j for dx in range(-r, r + 1) for dz in range(-r, r + 1) for j in cells.get((cx + dx, cz + dz), ())
                if (P[j, 0] - x) ** 2 + (P[j, 2] - z) ** 2 <= reach * reach and abs(P[j, 1] - y) <= layer]

    need = np.zeros(n)
    gap_before = []
    for i in range(n):
        x, y, z = P[i]
        if abs(x) >= outside:
            continue
        h = height(x, z)
        if h is None:
            continue
        # the underside of the strap here: its lowest point of webbing close by, in the same layer (a strap that
        # crosses under another is a layer of its own)
        low = min([P[j, 1] for j in near(i, 0.015, 0.03) if j in web and P[j, 1] <= y] or [y])
        fade = 1.0 if abs(x) <= inside else (outside - abs(x)) / (outside - inside)
        # (a part that is nowhere near the cloth does not lie on the bag: a strap on its way down to where it is
        # fixed, or passing under him. It is left alone; taken along, a shoulder strap went up 37 cm.)
        if abs(h + off - low) > far:
            continue
        need[i] = (h + off - low) * fade
        if i in web and abs(x) <= inside:
            gap_before.append(low - h)
    # Smoothed, so that the webbing stays a band: every point takes the mean, over 2 cm, of what its neighbours
    # within 1.5 cm need at most; and where that still leaves a point in the cloth, it and its neighbours are
    # raised by what is missing. (With the most over 3 cm the webbing stood 6 to 12 mm off the cloth nearly
    # everywhere: off the highest place within 3 cm.)
    most = np.array([max([need[j] for j in near(i, 0.015, 0.04)] or [need[i]]) for i in range(n)])
    move = np.array([np.mean([most[j] for j in near(i, 0.02, 0.04)] or [most[i]]) for i in range(n)])
    short = np.maximum(need - move, 0.0)
    short[need == 0.0] = 0.0
    move = move + np.array([max([short[j] for j in near(i, 0.015, 0.04)] or [0.0]) for i in range(n)])
    move[np.abs(P[:, 0]) >= outside] = 0.0
    out = [(p[0], p[1] + float(move[i]), p[2]) + tuple(p[3:]) for i, p in enumerate(points)]
    gap_after = []
    for i in web:
        x, y, z = P[i]
        h = height(x, z)
        if h is not None and abs(x) <= inside:
            low = min([P[j, 1] + move[j] for j in near(i, 0.015, 0.03) if j in web and P[j, 1] <= y] or [y + move[i]])
            gap_after.append(low - h)

    def spread(g):
        g = np.array(g) * 1000
        return "in the cloth at %d, off it by <6 mm at %d, 6-12 mm at %d, more at %d (most %.0f mm) of %d places" % (
            (g < -1).sum(), ((g >= -1) & (g < 6)).sum(), ((g >= 6) & (g < 12)).sum(), (g >= 12).sum(), g.max(), len(g)) if len(g) else "nowhere over the bag"

    return out, ["   its webbing over the bag, as laid on the tight line: " + spread(gap_before), "   settled on the cloth (moved by %+.0f to %+.0f mm): %s" % (move.min() * 1000, move.max() * 1000, spread(gap_after))]
