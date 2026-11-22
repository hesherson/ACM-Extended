"""The casualty on a litter as a surface, for fitting straps to him: tools/assets/litter_body_scan.json.

The scan is taken in the game with the casualty in the litter pose (acme_litter_side.rtm), bare: rays straight
down onto him every centimetre across and every two centimetres along, in his fire geometry (the only shape of
him a script can touch). It has to be taken again whenever the pose changes (scratch mission acme_fit_test.VR,
then tools/litter_body.py --take <the game's log>).

Axes of the scan: across (the casualty's left is +), along (from the pelvis toward the head), up (from what he
lies on). His arms and hands are in it: a strap fitted to it goes round body and arms together.

A strap that is pulled tight lies on the upper convex hull of what is under it, and runs straight from where it
leaves the body to where it is fixed: hull() gives that line.
"""
import json
import re
import sys
from pathlib import Path

SCAN = Path(__file__).with_name("assets") / "litter_body_scan.json"
# where the casualty's pelvis is along the Talon, and how high the Talon's deck is under him (measured in game)
TALON_PELVIS, TALON_DECK = 0.127, 0.145
# The fire geometry stands off the skin: a strap laid on it would float. Measured at the thighs: the leg strap of
# the Talon, built 1.0 cm under the fire geometry's top, lay flush on the skin with nothing coming through.
PROUD = 0.010
# Not so at the arms: there the skin is as far out as the fire geometry or a little further (seen in game: a strap
# built 6 mm under the fire geometry's top went into the forearm). From ARMS outward of the middle line the
# casualty is taken to be this much bigger than the scan, upward and sideways.
ARMS, ARM_MORE = 0.15, 0.008


def skin(x, z):
    """The height of the skin where the scan has z, at x across."""
    return z + ARM_MORE if abs(x) >= ARMS else z - PROUD


def take(log):
    rows = {}
    for line in Path(log).read_text(errors="replace").splitlines():
        m = re.search(r"ACMEFT\|scan\|(-?\d+)\|\[(.*)\]", line)
        if m:
            rows[int(m.group(1))] = [int(v) for v in m.group(2).split(",")]
    if not rows:
        raise SystemExit("no scan lines in " + str(log))
    width = len(next(iter(rows.values())))
    half = (width - 1) // 2
    scan = {"across_step": 0.01, "across_first": -half * 0.01,
            "stations": [{"along": round(j * 0.02 - TALON_PELVIS, 3),
                          "up": [(-1 if v < 0 else round(v / 1000 - TALON_DECK, 3)) for v in row]}
                         for j, row in sorted(rows.items())]}
    SCAN.write_text(json.dumps(scan))
    print("wrote", SCAN, len(rows), "stations of", width)


def outline(lo, hi, slack=0.02):
    """The casualty's top between two places along him (and a little beyond): [(across, up)], highest of all the
    stations there at each step across. Steps with nothing of him are left out."""
    scan = json.loads(SCAN.read_text())
    best = {}
    for st in scan["stations"]:
        if lo - slack <= st["along"] <= hi + slack:
            for i, v in enumerate(st["up"]):
                if v >= 0:
                    best[i] = max(best.get(i, -1), v)
    return [(round(scan["across_first"] + i * scan["across_step"], 3), v) for i, v in sorted(best.items())]


def hull(points):
    """The upper convex hull of points [(x, z)], from the leftmost to the rightmost."""
    pts = sorted(set(points))
    out = []
    for p in pts:
        while len(out) >= 2:
            (x1, z1), (x2, z2) = out[-2], out[-1]
            if (x2 - x1) * (p[1] - z1) - (z2 - z1) * (p[0] - x1) >= 0:
                out.pop()
            else:
                break
        out.append(p)
    return out


def tight(lo, hi, anchor_x, anchor_z, lift=0.0, floor=0.0):
    """The line of a strap pulled tight over the casualty between two places along him, fixed at (-anchor_x,
    anchor_z) and (anchor_x, anchor_z): [(x, z)] from left to right. z is over what he lies on; `floor` is added
    to every height of the casualty (the height of what he lies on, in the strap's own axes), `lift` is how far
    the strap stays off his skin."""
    body = [(x, skin(x, z) + lift + floor) for x, z in outline(lo, hi)]
    # (each step of the scan is a centimetre wide: the body reaches half a step further than its last ray)
    wide = []
    for x, z in body:
        wide += [(x - 0.005, z), (x + 0.005, z)]
    # Nothing of him may be further out than where the strap is fixed: the strap would have to come back in under
    # it, and the scan does not show what is under his widest place.
    beyond = max(abs(x) for x, z in wide) - anchor_x
    if beyond > 0.006:
        raise ValueError("between %.2f and %.2f the casualty reaches %.3f m beyond where the strap is fixed (%.3f)"
                         % (lo, hi, beyond + anchor_x, anchor_x))
    # (the fire geometry stands off the skin sideways too: what is left of it beyond the fixing is brought in)
    reach = anchor_x - 0.002
    wide += [(x + (ARM_MORE if x > 0 else -ARM_MORE), z) for x, z in wide if abs(x) >= ARMS]
    if max(abs(x) for x, z in wide) > reach:
        raise ValueError("between %.2f and %.2f an arm reaches the strap's fixing at %.3f" % (lo, hi, anchor_x))
    return hull(wide + [(-anchor_x, anchor_z), (anchor_x, anchor_z)])


def tight_half(lo, hi, anchor_x, anchor_z, lift=0.0, floor=0.0):
    """Half of the line of a strap pulled tight over the casualty, from its middle (x = 0) outward and down to
    where it is fixed (anchor_x, anchor_z); the same on both sides (the higher of his two sides at every place).
    Where his arm lies further out than the fixing, the strap comes up outside the arm first: [(x, z)], x not
    always growing."""
    best = {}
    for x, z in outline(lo, hi):
        k = round(abs(x) * 100)
        best[k] = max(best.get(k, -1), z)
    pts = []
    for k, z in sorted(best.items()):
        z = skin(k / 100, z) + lift + floor
        pts += [(max(k / 100 - 0.005, 0.0), z), (k / 100 + 0.005, z)]
    # (sideways the arm is taken 3 cm bigger than the scan: with 0.8 cm the strap's upright part beside the
    # forearm was still inside the arm's skin, and with 2 cm the thick of the forearm still showed through it)
    out = max(x for x, z in pts) - 0.005 + 0.030 + lift
    if out > anchor_x - 0.004:
        # round the outside of the arm: straight up from just over the fixing
        # (as high as the arm's outermost part is, so that the strap is upright beside the arm)
        up = max(z for x, z in pts if x > out - 0.03)
        side = [(out, anchor_z + 0.02), (out, up)]
        line = hull([(-x, z) for x, z in pts] + pts + side + [(-x, z) for x, z in side])
        half = [q for q in line if q[0] >= 0]
        # (upright beside the arm down to just over the fixing, then in to it)
        half = [(0.0, height(line, 0.0))] + half + [(out, anchor_z + 0.02), (anchor_x, anchor_z)]
    else:
        line = hull([(-x, z) for x, z in pts] + pts + [(anchor_x, anchor_z), (-anchor_x, anchor_z)])
        half = [(0.0, height(line, 0.0))] + [q for q in line if q[0] > 0]
    return half


def over_half(points, anchor_x, anchor_z, lift=0.0, floor=0.0):
    """Half of the line of a strap pulled tight over a shape given by points [(x, z)] of its surface (z over what
    the casualty lies on), from its middle (x = 0) outward and down to where it is fixed (anchor_x, anchor_z); the
    same on both sides (the higher of the two at every place). Where the shape is wider than the fixing the strap
    comes up outside it first. `floor` is added to every height of the shape, `lift` is how far the strap stays
    off it: [(x, z)], x not always growing."""
    best = {}
    for x, z in points:
        k = round(abs(x) * 200)
        best[k] = max(best.get(k, -9.0), z)
    pts = [(k / 200, z + lift + floor) for k, z in sorted(best.items())]
    out = max(x for x, z in pts) + lift
    if out > anchor_x - 0.004:
        up = max(z for x, z in pts if x > out - 0.03)
        side = [(out, anchor_z + 0.02), (out, up)]
        line = hull([(-x, z) for x, z in pts] + pts + side + [(-x, z) for x, z in side])
        half = [q for q in line if q[0] >= 0]
        half = [(0.0, height(line, 0.0))] + half + [(out, anchor_z + 0.02), (anchor_x, anchor_z)]
    else:
        line = hull([(-x, z) for x, z in pts] + pts + [(anchor_x, anchor_z), (-anchor_x, anchor_z)])
        half = [(0.0, height(line, 0.0))] + [q for q in line if q[0] > 0]
    return half


def height(line, x):
    """The height of a line [(x, z)] at x (the ends carried on level)."""
    if x <= line[0][0]:
        return line[0][1]
    for (x1, z1), (x2, z2) in zip(line, line[1:]):
        if x <= x2:
            return z1 + (z2 - z1) * (x - x1) / (x2 - x1) if x2 > x1 else max(z1, z2)
    return line[-1][1]


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--take":
        take(sys.argv[2])
    else:
        for name, lo, hi in (("Talon legs", -0.342, -0.292), ("Talon chest", 0.094, 0.144)):
            print(name, " ".join("%+.2f:%.3f" % p for p in tight(lo, hi, 0.241, 0.0)))
