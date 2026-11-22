"""What is seen of an airway adjunct on a casualty's face: addons/acm_extended/models/acme_face_npa.p3d,
acme_face_opa.p3d and acme_face_ett.p3d.

Asked for on 2026-11-20: "NPA, OPA and ET tube. all should physically show them on the face when applying any of
those and having them successfully established."

Each is drawn about the place where it enters him: the nostril's opening (NPA), the middle of his lips (OPA, ET
tube). Axes of the drawing: x to his right, y out of his face, z to the top of his head. What is inside him is
drawn a little way in, so nothing ends in the open when the place is a few millimetres off.
  NPA       the trumpet of a 28 Fr Rusch tube standing out of the nostril: a shallow cup 26 mm across, its
            bore in the middle, the green of the user's reference pictures (2026-11-20)
  OPA       a Guedel airway as in the user's reference: the white oval flange lying on the lips, in it the red
            oval of the bite block round the dark slot
  i-gel     as in the user's reference: the clear, wide stem out of the mouth, the green wings of size 4 on
            it, the clear 15 mm connector on top
  ET tube   a 7.5 mm tube out of the left corner of the mouth, bent toward the chin as the tube is made,
            its 15 mm connector, and the pilot line with its balloon lying on the cheek
They are shown by ACME_fnc_casualtyVisualTick as plain objects fixed to his head: no collision shape, no shadow.
Colours are about half as bright as the thing is: the game shows a bright colour burnt out in daylight
(measured with the HPMK's pictures).

  python tools/build_airway_adjuncts.py
"""
import math
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "addons/acm_extended/models"


def colour(r, g, b):
    return ("#(argb,8,8,3)color(%.3f,%.3f,%.3f,1.0,co)" % (r, g, b)).encode()


WHITE = colour(0.40, 0.41, 0.39)        # clear or white plastic
GREEN = colour(0.03, 0.36, 0.25)        # the NPA's rubber; the i-gel's size 4
CLEAR = colour(0.36, 0.38, 0.37)        # the i-gel's clear stem
RED = colour(0.36, 0.05, 0.04)          # size 4 bite block
BLUE = colour(0.08, 0.20, 0.40)         # the tube's connector, the pilot balloon
DARK = colour(0.03, 0.03, 0.03)         # an opening


NPA_FOLD_AT = 0.0050                    # the fold in the NPA's trumpet: so far below its middle,
NPA_FOLD_TO = (0.0, 0.25, -0.97)        # what is below it runs this way (down, a little out of the face),
NPA_FOLD_SOFT = 0.0018                  # the bend this long to each side of the fold
NPA_LIP = 0.0010                        # his upper lip: so far before the nostril's opening at most (6 mm and more below it)
NPA_SKIN = 0.0008                       # the trumpet's thickness where it lies on the lip


class Model:
    """Points, and faces wound against the clock as seen from the side they show to."""

    def __init__(self):
        self.pts, self.faces = [], []

    def add(self, p):
        self.pts.append(np.array(p, float))
        return len(self.pts) - 1

    def ring(self, centre, axis, across, rx, ry, sides):
        """A ring of points round a centre, in the plane across the axis; 'across' is where its first point is."""
        axis = np.array(axis, float) / np.linalg.norm(axis)
        u = np.array(across, float)
        u = u - axis * (u @ axis)
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        return [self.add(np.array(centre) + u * (rx * math.cos(2 * math.pi * k / sides)) + v * (ry * math.sin(2 * math.pi * k / sides))) for k in range(sides)]

    def band(self, a, b, tex, smooth=True):
        """The wall between two rings that go the same way round, seen from outside (ring b further along the axis)."""
        n = len(a)
        for k in range(n):
            self.faces.append(([a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]], tex, smooth))

    def cap(self, ring, tex, outward=True):
        """A ring closed, seen from the axis' end (or from its start)."""
        c = self.add(np.mean([self.pts[i] for i in ring], axis=0))
        n = len(ring)
        for k in range(n):
            ids = [c, ring[k], ring[(k + 1) % n]]
            self.faces.append((ids if outward else ids[::-1], tex, False))

    def tube(self, path, radius, sides, tex, across=(1, 0, 0), ends=(True, True)):
        """A tube along a line of points; radius a number or one for each point."""
        path = [np.array(p, float) for p in path]
        rings = []
        for i, p in enumerate(path):
            ahead = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
            r = radius[i] if isinstance(radius, (list, tuple)) else radius
            rings.append(self.ring(p, ahead, across, r, r, sides))
        for a, b in zip(rings, rings[1:]):
            self.band(a, b, tex)
        if ends[0]:
            self.cap(rings[0], tex, outward=False)
        if ends[1]:
            self.cap(rings[-1], tex, outward=True)
        return rings

    def level(self, res, first):
        P = np.array(self.pts)
        # a normal for each point of the smooth faces (the mean of its faces'), one of its own for each flat face
        smooth = np.zeros((len(P), 3))
        flat = []
        for ids, tex, is_smooth in self.faces:
            q = P[ids]
            c = np.cross(q[1] - q[0], q[2] - q[0])
            if len(ids) == 4:
                c = c + np.cross(q[2] - q[0], q[3] - q[0])
            if is_smooth:
                for i in ids:
                    smooth[i] += c
            flat.append(c / (np.linalg.norm(c) or 1.0))
        smooth /= np.maximum(np.linalg.norm(smooth, axis=1), 1e-12)[:, None]
        nrm, faces = [], []
        for k, (ids, tex, is_smooth) in enumerate(self.faces):
            q = P[ids]
            if np.linalg.norm(np.cross(q[1] - q[0], q[2] - q[0])) < 1e-10:
                continue
            corners = []
            for i in ids:
                out = smooth[i] if is_smooth else flat[k]
                nrm.append((-out[0], -out[2], -out[1]))        # the file keeps normals pointing inward; (x, up, forward)
                corners.append([i, len(nrm) - 1, 0.5, 0.5])
            faces.append([corners, 0, tex, b""])
        tags = []
        if first:
            tags.append(("#Property#", b"autocenter".ljust(64, b"\0") + b"0".ljust(64, b"\0")))
        tags.append(("#Property#", b"lodnoshadow".ljust(64, b"\0") + b"1".ljust(64, b"\0")))
        tags.append(("#EndOfFile#", b""))
        return dict(pts=[(p[0], p[2], p[1]) for p in P], flags=[0] * len(P), nrm=nrm, faces=faces, tags=tags, res=res)


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


def npa(sides):
    m = Model()
    # out of the nostril: forward and down
    a = np.array([0.0, 0.62, -0.78])
    a /= np.linalg.norm(a)
    # the tube in the nostril, its neck, and the trumpet's back out to the rim (3 to 8 mm before the nostril).
    # (Measured on four of the game's faces, 2026-11-21: on the narrow noses a tube 14 mm long and 8.4 mm thick
    # came out through the side of the nose, and a trumpet 26 mm across reached the tip: shorter, thinner, 23 mm.)
    stations = [(-0.010, 0.0034), (0.0000, 0.0042), (0.0030, 0.0058), (0.0040, 0.0078), (0.0050, 0.0096), (0.0064, 0.0113), (0.0080, 0.0115)]
    rings = [m.ring(a * s, a, (1, 0, 0), r, r, sides) for s, r in stations]
    for p, q in zip(rings, rings[1:]):
        m.band(p, q, GREEN)
    # the rim, and the cup inside it down to the bore
    cup = [m.ring(a * s, a, (1, 0, 0), r, r, sides) for s, r in ((0.0080, 0.0105), (0.0066, 0.0090), (0.0056, 0.0078), (0.0050, 0.0060), (0.0044, 0.0036))]
    m.band(rings[-1], cup[0], GREEN, smooth=False)
    for p, q in zip(cup, cup[1:]):
        m.band(p, q, GREEN)
    deep = m.ring(a * -0.004, a, (1, 0, 0), 0.0032, 0.0032, sides)
    m.band(cup[-1], deep, DARK)
    m.cap(deep, DARK, outward=True)
    # The trumpet's lower back would stand in his upper lip (it leans back as it goes down). It is soft: where it
    # meets the lip it is folded, and runs down before the lip instead ("squash the bottom of the NPA so that it
    # doesn't clip into the face. just make it fold up", 2026-11-20). The fold: across the trumpet NPA_FOLD_AT below
    # its middle, what is below turned forward round that line until it runs along NPA_FOLD_TO, over a soft bend.
    t = np.array([0.0, -a[2], a[1]])            # across the axis, down and back: where the trumpet goes into the lip
    t = t if t[2] < 0 else -t
    hinge = a * 0.0030 + t * NPA_FOLD_AT
    to = np.array(NPA_FOLD_TO, float)
    to /= np.linalg.norm(to)
    whole = math.atan2(np.cross(t, to)[0], t @ to)
    for i, q in enumerate(m.pts):
        if q @ a < 0.0025:                      # (the tube in his nose stays as it is)
            continue
        along = (q - hinge) @ t
        k = min(1.0, max(0.0, (along + NPA_FOLD_SOFT) / (2 * NPA_FOLD_SOFT)))
        angle = whole * k * k * (3 - 2 * k)
        if angle == 0.0:
            continue
        c, sn = math.cos(angle), math.sin(angle)
        d = q - hinge
        m.pts[i] = hinge + np.array([d[0], d[1] * c - d[2] * sn, d[1] * sn + d[2] * c])
    # (At the fold itself his lip still showed through the cup, in game: below the nostril nothing of the trumpet is
    # nearer his face than NPA_LIP, its back there, the cup's face NPA_SKIN before that.)
    front = {i for ring in cup for i in ring}
    for ring in rings[2:] + cup:
        for i in ring:
            q = m.pts[i]
            k = min(1.0, max(0.0, (-0.003 - q[2]) / 0.003))
            least = (-0.004 + (NPA_LIP + 0.004) * k) + (NPA_SKIN if i in front else 0.0)
            if k > 0.0 and q[1] < least:
                q[1] = least
    return m


def opa(sides):
    m = Model()
    a = np.array([0.0, 1.0, -0.12])
    a /= np.linalg.norm(a)
    # the bite block between the teeth, and the flange before the lips
    block = [m.ring(a * s, a, (1, 0, 0), rx, ry, sides) for s, rx, ry in ((-0.024, 0.0085, 0.0048), (-0.002, 0.0100, 0.0056), (0.0030, 0.0100, 0.0056))]
    m.band(block[0], block[1], RED)
    m.band(block[1], block[2], RED)
    m.cap(block[0], RED, outward=False)
    flange = [m.ring(a * s, a, (1, 0, 0), rx, ry, sides) for s, rx, ry in ((0.0030, 0.0200, 0.0150), (0.0042, 0.0208, 0.0157), (0.0056, 0.0200, 0.0150))]
    m.band(block[2], flange[0], WHITE, smooth=False)       # its back (toward the lips: inner ring to outer shows that way)
    m.band(flange[0], flange[1], WHITE)
    m.band(flange[1], flange[2], WHITE)
    # (in the flange's face the red of the bite block, round the slot)
    red = m.ring(a * 0.0056, a, (1, 0, 0), 0.0108, 0.0066, sides)
    m.band(flange[2], red, WHITE, smooth=False)
    hole = m.ring(a * 0.0056, a, (1, 0, 0), 0.0062, 0.0026, sides)
    m.band(red, hole, RED, smooth=False)
    deep = m.ring(a * -0.006, a, (1, 0, 0), 0.0056, 0.0026, sides)
    m.band(hole, deep, DARK)
    m.cap(deep, DARK, outward=True)
    return m


def igel(sides):
    m = Model()
    a = np.array([0.0, 1.0, -0.10])
    a /= np.linalg.norm(a)
    # the stem (wide: it is its own bite block), from between the teeth to 3.4 cm before the lips
    stem = [m.ring(a * s, a, (1, 0, 0), rx, ry, sides) for s, rx, ry in ((-0.022, 0.0120, 0.0075), (0.0, 0.0125, 0.0080), (0.034, 0.0125, 0.0085))]
    m.band(stem[0], stem[1], CLEAR)
    m.band(stem[1], stem[2], CLEAR)
    m.cap(stem[0], CLEAR, outward=False)
    # the green plate on its end, with a wing to each side
    plate = [m.ring(a * s, a, (1, 0, 0), rx, ry, sides) for s, rx, ry in ((0.034, 0.0185, 0.0105), (0.039, 0.0185, 0.0105))]
    m.band(stem[2], plate[0], GREEN, smooth=False)
    m.band(plate[0], plate[1], GREEN, smooth=False)
    # the 15 mm connector, clear, open
    neck = [m.ring(a * s, a, (1, 0, 0), 0.0075, 0.0075, sides) for s in (0.039, 0.058)]
    m.band(plate[1], neck[0], GREEN, smooth=False)
    m.band(neck[0], neck[1], CLEAR)
    bore = m.ring(a * 0.058, a, (1, 0, 0), 0.0060, 0.0060, sides)
    m.band(neck[1], bore, CLEAR, smooth=False)
    deep = m.ring(a * 0.040, a, (1, 0, 0), 0.0056, 0.0056, sides)
    m.band(bore, deep, DARK)
    m.cap(deep, DARK, outward=True)
    return m


def ett(sides):
    m = Model()
    # The tube: from inside the mouth out between the lips, a little to his left of their middle (his left: -x),
    # in the arc it is made in (radius 14 cm), which outside the mouth turns toward his chin. ("the et tube is not
    # even in the mouth ... sit centered, with an allowance for the et tube to sit on the side of the mouth a
    # little bit", 2026-11-21: it left at the corner of the closed mouth, above the gap of the open one.)
    start = np.array([-0.004, -0.025, 0.0])
    R = 0.14
    line = []
    for k in range(9):
        s = 0.105 * k / 8                    # along the tube, 2.5 cm of it inside
        t = max(s - 0.025, 0.0) / R          # the arc begins at the lips
        p = start + np.array([-0.006 * min(s / 0.05, 1.0), min(s, 0.025), 0.0])
        if t > 0:
            p = p + np.array([0.0, R * math.sin(t), -R * (1 - math.cos(t))])
        line.append(p)
    m.tube(line, 0.0050, sides, WHITE, ends=(True, False))
    end, ahead = line[-1], line[-1] - line[-2]
    ahead /= np.linalg.norm(ahead)
    # the connector: a collar on the tube's end, the 15 mm fitting, open
    stations = [(-0.004, 0.0052), (-0.003, 0.0105), (0.0, 0.0105), (0.0005, 0.0075), (0.018, 0.0075)]
    rings = [m.ring(end + ahead * s, ahead, (1, 0, 0), r, r, sides) for s, r in stations]
    for p, q in zip(rings, rings[1:]):
        m.band(p, q, BLUE, smooth=False)
    bore = m.ring(end + ahead * 0.018, ahead, (1, 0, 0), 0.0060, 0.0060, sides)
    m.band(rings[-1], bore, BLUE, smooth=False)
    deep = m.ring(end + ahead * 0.004, ahead, (1, 0, 0), 0.0056, 0.0056, sides)
    m.band(bore, deep, DARK)
    m.cap(deep, DARK, outward=True)
    # the pilot line: off the tube 3 cm outside the lips, over the left cheek, down beside the jaw; its balloon
    off = line[5]
    pilot = [off + np.array(d) for d in ((0, 0, 0), (-0.012, -0.004, -0.004), (-0.030, -0.020, -0.012), (-0.046, -0.044, -0.026), (-0.056, -0.070, -0.040))]
    m.tube(pilot, 0.0011, max(sides // 2, 4), WHITE)
    tip, way = pilot[-1], pilot[-1] - pilot[-2]
    way /= np.linalg.norm(way)
    balloon = [tip + way * s for s in (0.0, 0.004, 0.012, 0.020, 0.024, 0.030)]
    m.tube(balloon, [0.0012, 0.0050, 0.0062, 0.0050, 0.0026, 0.0026], max(sides // 2, 5), BLUE)
    return m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, make in (("npa", npa), ("opa", opa), ("igel", igel), ("ett", ett)):
        levels = [make(sides).level(res, res == 1.0) for res, sides in ((1.0, 14), (2.0, 8), (3.0, 5))]
        write(OUT / ("acme_face_%s.p3d" % name), levels)
        P = np.array(levels[0]["pts"])
        print("wrote acme_face_%s.p3d: %s faces by level; across %.3f..%.3f, out %.3f..%.3f, up %.3f..%.3f" % (
            name, [len(lv["faces"]) for lv in levels], P[:, 0].min(), P[:, 0].max(), P[:, 2].min(), P[:, 2].max(), P[:, 1].min(), P[:, 1].max()))


if __name__ == "__main__":
    main()
