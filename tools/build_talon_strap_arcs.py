#!/usr/bin/env python3
"""The two straps of the Talon II, closed over a casualty: the litter's own straps and buckles, pulled over him.

The Talon's model has its straps buckled flat on the deck; a casualty lies on top of them and nothing holds him
(seen in game 2026-11-18). These models are those same straps (their mesh, their buckles, their textures, taken
from the first LOD of talon_open.p3d) bent into an arch over the casualty: for each of the two straps one model
for a bare casualty and one for a casualty in the HPMK. The server hangs them on the litter (acme_sked_ace,
fn_strapArcs.sqf), and the litter hides the strap on its deck that was "taken up" (model.cfg of acme_talon:
sources "strap_legs_over" and "strap_chest_over").

How a strap is bent: it lies flat from sleeve to sleeve (x -0.241..0.241 m, 0.145 m up) with the buckle in the
middle. The middle part with the buckle stays as long as it is; the webbing on both sides is let out (as the
real strap is, through its adjuster) to reach round the casualty. The arch is a rounded box: widest at the
casualty's arms, tucked in again where the strap goes into the sleeve of the pole.

Axes as in the model file: x across, y up, z along (the head at +z).

  python tools/build_talon_strap_arcs.py
"""
import math
import struct
import sys
from pathlib import Path
from struct import unpack_from

sys.path.insert(0, str(Path(__file__).resolve().parent))
import strap_settle  # noqa: E402
import strap_texture  # noqa: E402
ROOT = Path(__file__).resolve().parents[1] / "addons/acme_talon"
SOURCE = ROOT / "talon_open.p3d"
END = 0.241           # where a strap leaves the sleeve of the pole, from the middle
FLAT = 0.145          # how high it lies on the deck
RIGID = 0.07          # the middle part (buckle and adjusters) that is not let out, from the middle
WIDE = 0.282          # the arch at its widest, from the middle: outside the casualty's arms
# the straps: the number in the names of their bones (tr2a.., tl2a..: over the thighs; tr3a.., tl3a..: the chest)
STRAPS = {"legs": "2", "chest": "3"}
# for each fit: how high each strap is in the middle, and how square the arch is (the HPMK is a bag: flat, wide)
# A strap over bare legs is cinched onto them: THIGH is one thigh where that strap crosses it, as an ellipse
# (its middle from the litter's middle line and over the model's ground, half its width, half its height).
THIGH = (0.105, 0.232, 0.088, 0.082)
SKIN = 0.004          # how far the webbing's underside stays off the skin
# The other strap crosses the belly and both forearms: over a bare casualty it is pulled tight over all three,
# along the line tools/litter_body.py gives for that stretch of him (from where to where along the litter).
BELLY = ("tight", 0.215, 0.277)
# Over a casualty in the HPMK both straps are pulled tight over the shell he wears (tools/build_hpmk_shell.py),
# each over the stretch of him it crosses (from where to where along the litter).
SHELL_OFF = 0.003     # how far the webbing's underside stays off the shell
FITS = {"bare": ({"legs": THIGH, "chest": BELLY}, 3.2),
        "hpmk": ({"legs": ("shell", -0.215, -0.165), "chest": ("shell", 0.215, 0.277)}, 5.0)}
PARTS = "abcdefght"


def read_lod0(path):
    data = path.read_bytes()
    cursor = 12
    points, normals, faces = unpack_from("<3I", data, cursor + 12)
    p0 = cursor + 28
    pts = [unpack_from("<3fI", data, p0 + 16 * i) for i in range(points)]
    n0 = p0 + points * 16
    nrm = [unpack_from("<3f", data, n0 + 12 * i) for i in range(normals)]
    cursor = n0 + normals * 12
    recs = []
    for _ in range(faces):
        n = unpack_from("<I", data, cursor)[0]
        vs = [unpack_from("<IIff", data, cursor + 4 + 16 * j) for j in range(n)]
        flags = unpack_from("<I", data, cursor + 68)[0]
        end = data.index(0, cursor + 72)
        tex = data[cursor + 72:end]
        end2 = data.index(0, end + 1)
        mat = data[end + 1:end2]
        cursor = end2 + 1
        recs.append((vs, flags, tex, mat))
    cursor += 4
    sels = {}
    while True:
        end = data.index(0, cursor + 1)
        name = data[cursor + 1:end].decode("latin1")
        size = unpack_from("<I", data, end + 1)[0]
        blob = data[end + 5:end + 5 + size]
        cursor = end + 5 + size
        if name == "#EndOfFile#":
            break
        if size >= points and not name.startswith("#"):
            sels[name] = {i for i in range(points) if blob[i]}
    return pts, nrm, recs, sels


class Arch:
    """Half of the arch from its top outward and down to the sleeve, by length along it."""

    def __init__(self, top, square):
        e = 2 / square
        # the angle below the widest point at which the arch is back in at the sleeve
        low = -math.acos((END / WIDE) ** (1 / e))
        drop = abs(math.sin(low)) ** e
        # the height of the widest point, such that the arch ends at the height of the flat strap
        mid = (FLAT + drop * top) / (1 + drop)
        rise = top - mid
        steps = 4000
        self.table = []
        s = 0.0
        last = None
        for i in range(steps + 1):
            a = math.pi / 2 + (low - math.pi / 2) * i / steps
            x = WIDE * abs(math.cos(a)) ** e
            z = mid + rise * math.copysign(abs(math.sin(a)) ** e, a)
            if last:
                s += math.hypot(x - last[0], z - last[1])
            last = (x, z)
            self.table.append((s, x, z))
        self.length = s
        self.let_out = (self.length - RIGID) / (END - RIGID)

    def at(self, flat):
        """Where a point of the flat strap, this far from the middle, is on the arch: (x, z, tangent)."""
        s = flat if flat <= RIGID else RIGID + (flat - RIGID) * self.let_out
        s = min(max(s, 0.0), self.length)
        lo, hi = 0, len(self.table) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if self.table[m][0] <= s:
                lo = m
            else:
                hi = m
        (s0, x0, z0), (s1, x1, z1) = self.table[lo], self.table[hi]
        f = 0 if s1 == s0 else (s - s0) / (s1 - s0)
        d = math.hypot(x1 - x0, z1 - z0) or 1.0
        return x0 + (x1 - x0) * f, z0 + (z1 - z0) * f, ((x1 - x0) / d, (z1 - z0) / d)


class Cinched(Arch):
    """Half of a strap pulled tight over two legs, from its middle outward and down to the sleeve: level from
    the middle to the top of the thigh (it bridges the gap between the legs, and the buckle lies there), round
    the outside of the thigh, and from where it leaves the thigh straight to the sleeve."""

    def __init__(self, thigh):
        cx, cz, rx, rz = thigh
        rx, rz = rx + SKIN, rz + SKIN
        steps = 4000
        line = [(cx * i / 200, cz + rz) for i in range(200)]
        left = False
        for i in range(steps + 1):
            a = math.pi / 2 - math.pi * i / steps
            x, z = cx + rx * math.cos(a), cz + rz * math.sin(a)
            # the direction the strap runs here, and the direction from here to the sleeve
            tx, tz = rx * math.sin(a), -rz * math.cos(a)
            ex, ez = END - x, FLAT - z
            line.append((x, z))
            # it leaves the thigh where the straight way to the sleeve no longer cuts into it
            if i and tx * ez - tz * ex >= 0:
                left = True
                break
        if not left:
            raise ValueError("the thigh is wider than the litter: no way from it to the sleeve")
        x0, z0 = line[-1]
        line += [(x0 + (END - x0) * i / 200, z0 + (FLAT - z0) * i / 200) for i in range(1, 201)]
        self.table = []
        s = 0.0
        last = None
        for x, z in line:
            if last:
                s += math.hypot(x - last[0], z - last[1])
            last = (x, z)
            self.table.append((s, x, z))
        self.length = s
        self.let_out = (self.length - RIGID) / (END - RIGID)


class Tight(Arch):
    """Half of a strap pulled tight over the casualty's body and arms (tools/litter_body.py), from its middle
    outward and down to the sleeve. The two halves of a strap are bent alike, so the line is the higher of the
    casualty's two sides at every place."""

    def __init__(self, back, front):
        import litter_body
        line = litter_body.tight_half(back - litter_body.TALON_PELVIS, front - litter_body.TALON_PELVIS, END, FLAT, SKIN, FLAT)
        self.lay(line)

    def lay(self, line):
        self.table = [(0.0,) + line[0]]
        s = 0.0
        for (x1, z1), (x2, z2) in zip(line, line[1:]):
            # (in short steps: at() looks the place up between two entries of the table)
            n = max(1, int(math.hypot(x2 - x1, z2 - z1) / 0.0005))
            for i in range(1, n + 1):
                s += math.hypot(x2 - x1, z2 - z1) / n
                self.table.append((s, x1 + (x2 - x1) * i / n, z1 + (z2 - z1) * i / n))
        print("   the line:", " ".join("%.3f:%.3f" % q for q in line))
        self.length = s
        self.let_out = (self.length - RIGID) / (END - RIGID)


class Over(Tight):
    """Half of a strap pulled tight over the HPMK shell the casualty wears, from its middle outward and down to
    the sleeve (the shell is wider than the litter: the strap comes up outside it)."""

    def __init__(self, back, front):
        import build_hpmk_shell
        import litter_body
        line = litter_body.over_half(build_hpmk_shell.outline(back, front), END, FLAT, SHELL_OFF, FLAT)
        self.lay(line)


def write(path, points, normals, faces):
    b = bytearray(b"MLOD" + struct.pack("<II", 257, 1) + b"P3DM" + struct.pack("<6I", 28, 256, len(points), len(normals), len(faces), 0))
    for p in points:
        b += struct.pack("<3fI", *p)
    for n in normals:
        b += struct.pack("<3f", *n)
    for vs, flags, tex, mat in faces:
        b += struct.pack("<I", len(vs))
        for j in range(4):
            b += struct.pack("<IIff", *(vs[j] if j < len(vs) else (0, 0, 0.0, 0.0)))
        b += struct.pack("<I", flags) + tex + b"\0" + mat + b"\0"
    b += b"TAGG" + b"\x01#Property#\0" + struct.pack("<I", 128)
    b += b"autocenter".ljust(64, b"\0") + b"0".ljust(64, b"\0")
    b += b"\x01#EndOfFile#\0" + struct.pack("<I", 0) + struct.pack("<f", 1.0)
    path.write_bytes(b)


SURFACE = {}


def main():
    pts, nrm, recs, sels = read_lod0(SOURCE)
    for fit, (tops, square) in FITS.items():
        for strap, number in STRAPS.items():
            ids = set()
            for side in ("tr", "tl"):
                for part in PARTS:
                    ids |= sels.get(side + number + part, set())
            fit_to = tops[strap]
            if isinstance(fit_to, tuple):
                arch = Tight(*fit_to[1:]) if fit_to[0] == "tight" else Over(*fit_to[1:]) if fit_to[0] == "shell" else Cinched(fit_to)
            else:
                arch = Arch(fit_to, square)
            points, normals, faces, where, flat = [], [], [], {}, []
            for vs, flags, tex, mat in recs:
                if not all(v[0] in ids for v in vs):
                    continue
                out = []
                for point, normal, u, v in vs:
                    x, y, z, pflags = pts[point]
                    side = -1.0 if x < 0 else 1.0
                    ax, az, (tx, tz) = arch.at(abs(x))
                    # the strap's own frame there: along the webbing (toward +x) and out of it
                    t = (tx, side * tz)
                    n = (-t[1], t[0])
                    if point not in where:
                        off = y - FLAT
                        where[point] = len(points)
                        points.append((side * ax + off * n[0], az + off * n[1], z, pflags))
                        flat.append((x, y, z))
                    nx, ny, nz = nrm[normal]
                    normals.append((nx * t[0] + ny * n[0], nx * t[1] + ny * n[1], nz))
                    out.append((where[point], len(normals) - 1, u, v))
                faces.append((out, flags, tex, mat))
            name = "talon_strap_%s_%s.p3d" % (strap, fit)
            settled = []
            if fit == "hpmk":
                # on the bag: every part of the webbing down onto the cloth under it (strap_settle.py)
                top = SURFACE.setdefault("wide", strap_settle.surface(False))
                webbing = {v[0] for vs, flags, tex, mat in faces if b"web" in tex.lower() for v in vs}
                points, settled = strap_settle.settle(
                    points, lambda x, along: (lambda h: None if h is None else h + FLAT)(top(x, along)), SHELL_OFF, webbing=webbing)
            # the webbing is let out: its weave is laid out again along the longer line (strap_texture.py)
            faces, lines = strap_texture.retexture(flat, points, faces)
            write(ROOT / name, points, normals, faces)
            print("wrote %s: %d points, %d faces, top %.3f, half the arch %.3f m, webbing let out %.2f times"
                  % (name, len(points), len(faces), arch.table[0][2], arch.length, arch.let_out))
            print("\n".join(settled + lines))


if __name__ == "__main__":
    main()
