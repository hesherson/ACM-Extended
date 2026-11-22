"""The HPMK-I laid out ready on an empty litter ("Stage HPMK"): addons/acme_hpmk/hpmk_staged_talon.p3d and
hpmk_staged_sked.p3d, from the kit's own model of the shell opened flat (addons/acme_hpmk/hpmk_open.p3d).

Asked for on 2026-11-20: "a 'Stage HPMK' as an option for the litter and skedco, where it can just lay a sheet out
over the top of the sked/litter, allowing for a patient to be laid on top and then wrapped into the HPMK as soon
as they are on the litter or sked."

The opened shell as drawn is flat, 2.15 m wide: the half he will lie on (its middle is the model's point 'liner')
and beside it the cover. Here it is laid over a litter as a cloth: the half he will lie on along the litter's
middle, its head end where his head will be, the cover hanging off his left side onto the ground. Every point
keeps its place across and along and its height over the sheet's underside (the creases, the folded blanket, the
hood); the underside follows the litter's top (measured from the litter's model) and comes down beside it in a
slope, as a tarp does.

The models have no collision shape (a casualty is laid on them) and are shown by acme_sked_fnc_stageHpmk as plain
objects fixed on the litter, like the strap models. Run again when a litter's model changes.

  python tools/build_hpmk_staged.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fit_hpmk_worn as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "addons/acme_hpmk/hpmk_open.p3d"
OUT = ROOT / "addons/acme_hpmk"
CELL = 0.01
ACROSS, ALONG = (-1.30, 2.10), (-1.80, 1.90)       # the ground round a litter that is looked at
LIES = 0.004          # the sheet's underside over what it lies on
GROUND = 0.012        # and over the ground beside the litter (ground is not flat)
SOFT = 3.5            # how gently the cloth comes down from an edge (cells)
# Where his head will be along each litter (the middle of his face, as he is measured lying on it), and the litter
LITTERS = (("talon", "addons/acme_talon/talon_open.p3d", 0.79), ("sked", "addons/acme_sked/sked_open.p3d", 0.72))
# And under a casualty who lies on it ("prep HPMK should put the blanket under the patient and show it actually
# underneath the patient", 2026-11-20): hpmk_under_ground.p3d (no litter, flat; its middle is his pelvis, his face
# 0.664 m along from it, as on the litters) and hpmk_under_talon.p3d. In these the half he lies on is pressed
# flat by him: as drawn its creases stand 4 to 8 cm high, the folded blanket 11 cm and the hood 13 cm, and his arms
# and legs lay sunk in them. The cover beside him keeps its creases.
UNDER = (("ground", None, 0.664), ("talon", "addons/acme_talon/talon_open.p3d", 0.79))
PRESSED = 0.14               # what is left of a crease's height under him
PRESSED_TO = (0.45, 0.62)    # across: pressed as far as the first, as drawn from the second on
# the closure's band as on the shell he wears (tools/hpmk_opened.py: the kit's own shows cream in the game)
SWAP = {rb"acme_hpmk\data\hpmk_edge_co.paa": (rb"acme_hpmk\data\hpmk_closure_co.paa", rb"acme_hpmk\data\hpmk_closure.rvmat")}


def point(lv, name):
    for tag, data in lv["tags"]:
        if tag == name:
            ids = np.nonzero(np.frombuffer(data, "u1", len(lv["pts"])))[0]
            return lv["pts"][ids[0]]
    raise KeyError(name)


def top_of(path):
    """The top of a litter's model over the ground round it: a grid of heights (across, along)."""
    lv = F.read(path)[0]
    P = lv["pts"]
    nx, ny = int((ACROSS[1] - ACROSS[0]) / CELL) + 1, int((ALONG[1] - ALONG[0]) / CELL) + 1
    top = np.zeros((nx, ny))
    for vs, fl, tex, mat in lv["faces"]:
        q = P[[v[0] for v in vs]]
        for k in range(1, len(q) - 1):
            a, b, c = q[0], q[k], q[k + 1]
            i0, i1 = int((min(a[0], b[0], c[0]) - ACROSS[0]) / CELL), int((max(a[0], b[0], c[0]) - ACROSS[0]) / CELL) + 1
            j0, j1 = int((min(a[2], b[2], c[2]) - ALONG[0]) / CELL), int((max(a[2], b[2], c[2]) - ALONG[0]) / CELL) + 1
            if i1 < 0 or j1 < 0 or i0 >= nx or j0 >= ny:
                continue
            high = max(a[1], b[1], c[1])
            top[max(i0, 0):min(i1 + 1, nx), max(j0, 0):min(j1 + 1, ny)] = np.maximum(top[max(i0, 0):min(i1 + 1, nx), max(j0, 0):min(j1 + 1, ny)], high)
    return top


def blur(g, s):
    r = int(s * 3) + 1
    kern = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2)
    kern /= kern.sum()
    for axis in (0, 1):
        g = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), kern, mode="valid"), axis, g)
    return g


def draped(top):
    """A cloth laid over that: never under it, coming down from its edges gently."""
    hard = np.where(top > 0.001, top + LIES, GROUND)
    cloth = hard.copy()
    for _ in range(6):
        cloth = np.maximum(blur(cloth, SOFT), hard)
    return np.maximum(blur(cloth, 1.2), hard - 0.001)


def at(grid, x, a):
    fx = min(max((x - ACROSS[0]) / CELL, 0.0), grid.shape[0] - 1.001)
    fa = min(max((a - ALONG[0]) / CELL, 0.0), grid.shape[1] - 1.001)
    i, j = int(fx), int(fa)
    u, v = fx - i, fa - j
    return (grid[i, j] * (1 - u) + grid[i + 1, j] * u) * (1 - v) + (grid[i, j + 1] * (1 - u) + grid[i + 1, j + 1] * u) * v


def main():
    source = F.read(SOURCE)
    marks = next(lv for lv in source if abs(lv["res"] - 1e15) < 1e12)
    liner, head, ground = point(marks, "liner"), point(marks, "head"), point(marks, "ground")
    for name, litter, head_at, under in [v + (False,) for v in LITTERS] + [v + (True,) for v in UNDER]:
        if litter is None:
            cloth = np.full((int((ACROSS[1] - ACROSS[0]) / CELL) + 1, int((ALONG[1] - ALONG[0]) / CELL) + 1), GROUND)
        else:
            cloth = draped(top_of(ROOT / litter))
        dx, da = np.gradient(cloth, CELL)
        levels = []
        for lv in source:
            if lv["res"] >= 1000 or len(lv["pts"]) == 0:
                # No collision shape and no points to aim at: a cloth to lie on. And no shape that casts a shadow:
                # the kit's is a slab 1 cm over the ground, and where the sheet's creases lie lower than that they
                # were in its shadow, a dark patch with straight edges on the sheet (seen in game). A sheet lying
                # flat casts no shadow worth having.
                continue
            P = lv["pts"]
            pts = np.zeros_like(P)
            slope = np.zeros((len(P), 2))
            kept = np.ones(len(P))
            for i, (x, y, z) in enumerate(P):
                X, A = x - liner[0], z - head[2] + head_at
                kept[i] = 1.0 if not under else PRESSED + (1 - PRESSED) * min(max((X - PRESSED_TO[0]) / (PRESSED_TO[1] - PRESSED_TO[0]), 0.0), 1.0)
                pts[i] = (X, at(cloth, X, A) + (y - ground[1]) * kept[i], A)
                slope[i] = (at(dx, X, A), at(da, X, A))
            # every normal turned as the sheet under its point was tilted
            by_normal = {}
            for vs, fl, tex, mat in lv["faces"]:
                for v in vs:
                    by_normal.setdefault(v[1], v[0])
            nrm = lv["nrm"].copy()
            for k, i in by_normal.items():
                n = lv["nrm"][k]
                # (a pressed crease is as much flatter)
                n = np.array([n[0] * kept[i], n[1], n[2] * kept[i]])
                t = np.array([n[0] - slope[i, 0] * n[1], n[1], n[2] - slope[i, 1] * n[1]])
                nrm[k] = t / (np.linalg.norm(t) or 1.0)
            faces = [[vs, fl] + list(SWAP.get(tex, (tex, mat))) for vs, fl, tex, mat in lv["faces"]]
            tags = [t for t in lv["tags"] if t[0] != "#EndOfFile#" and t[0] != "#Property#" and (t[0].startswith("#") or lv["res"] < 1000)]
            if not levels:
                tags.append(("#Property#", b"autocenter".ljust(64, b"\0") + b"0".ljust(64, b"\0")))
            tags.append(("#Property#", b"lodnoshadow".ljust(64, b"\0") + b"1".ljust(64, b"\0")))
            tags.append(("#EndOfFile#", b""))
            levels.append(dict(pts=pts, flags=lv["flags"], nrm=nrm, faces=faces, tags=tags, res=lv["res"]))
        name = ("hpmk_under_%s.p3d" if under else "hpmk_staged_%s.p3d") % name
        F.write(OUT / name, levels)
        first = levels[0]["pts"]
        print("wrote %s: %d levels, %d points in the first; across %.2f..%.2f, along %.2f..%.2f, up %.3f..%.3f" % (
            name, len(levels), len(first), first[:, 0].min(), first[:, 0].max(), first[:, 2].min(), first[:, 2].max(), first[:, 1].min(), first[:, 1].max()))


if __name__ == "__main__":
    main()
