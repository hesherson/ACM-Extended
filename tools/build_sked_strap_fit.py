#!/usr/bin/env python3
"""Make the straps over the casualty of the wrapped SKED parts that can be moved up and down.

The straps were modelled as arches of one fixed height: 8 to 15 cm of air over a bare casualty, and inside the
HPMK in places when he is wrapped in one (seen in game 2026-11-18). Now each strap, with its buckle, is a named
selection, and model.cfg moves each one down or up by its own distance: source "strap_fit", 0 for a bare casualty
and 1 for one in the HPMK (acme_sked_ace, fn_strapFit.sqf). A strap that is moved down runs into the shell's rim
and under the ground with its ends, where it is not seen.

What a strap is: a piece of the model that is not shell, hangs together by shared points, lies over the casualty,
reaches at least 0.15 m high and is no longer than 0.6 m along the SKED (the buckles are many such pieces). Which of the five selections it goes to depends on where its middle is along
the SKED:  strap_feet, strap_knee, strap_pelvis, strap_belly, strap_chest.
A point that the shell uses too stays where it is. Running the tool again changes nothing.

  python tools/build_sked_strap_fit.py [--report]      (--report: say what would be named, write nothing)
"""
import sys
from collections import defaultdict
from pathlib import Path
from struct import pack, unpack_from

MODEL = Path(__file__).resolve().parents[1] / "addons/acme_sked/sked_wrapped.p3d"
SHELL = "sked_hdpe"
# from where to where along the SKED (forward, m) the middle of a strap is, for each selection
BANDS = [("strap_feet", -0.84, -0.60), ("strap_knee", -0.60, -0.20), ("strap_pelvis", -0.20, 0.05),
         ("strap_belly", 0.05, 0.20), ("strap_chest", 0.20, 0.70)]
HIGH = 0.15


def rework(path, write):
    model = path.read_bytes()
    assert model[:4] == b"MLOD"
    out = bytearray(model[:12])
    cursor = 12
    for lod in range(unpack_from("<I", model, 8)[0]):
        start = cursor
        points, normals, faces = unpack_from("<3I", model, cursor + 12)
        first = cursor + 28
        pts = [unpack_from("<3f", model, first + 16 * i) for i in range(points)]
        cursor = first + points * 16 + normals * 12
        face_points, face_shell = [], []
        for _ in range(faces):
            n = unpack_from("<I", model, cursor)[0]
            face_points.append([unpack_from("<I", model, cursor + 4 + 16 * j)[0] for j in range(n)])
            end = model.index(0, cursor + 72)
            end2 = model.index(0, end + 1)
            face_shell.append(SHELL in model[end + 1:end2].decode("latin1").lower())
            cursor = end2 + 1
        assert model[cursor:cursor + 4] == b"TAGG"
        cursor += 4
        names = set()
        last = None
        while True:
            tag = cursor
            end = model.index(0, cursor + 1)
            name = bytes(model[cursor + 1:end])
            size = unpack_from("<I", model, end + 1)[0]
            data = model[end + 5:end + 5 + size]
            cursor = end + 5 + size
            names.add(name)
            if name == b"tow_strap":
                tow = {i for i in range(points) if data[i]}
            if name == b"#EndOfFile#":
                last = tag
                break
        resolution = unpack_from("<f", model, cursor)[0]
        cursor += 4
        if resolution >= 1000 or b"strap_chest" in names:
            out += model[start:cursor]
            continue
        tow = locals().get("tow", set())
        shell_points = {p for f, s in zip(face_points, face_shell) if s for p in f}
        # pieces that hang together, of what is not shell
        parent = list(range(points))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for f, s in zip(face_points, face_shell):
            if not s:
                for p in f[1:]:
                    parent[find(p)] = find(f[0])
        pieces = defaultdict(set)
        for f, s in zip(face_points, face_shell):
            if not s:
                pieces[find(f[0])].update(f)
        chosen = defaultdict(set)
        for ids in pieces.values():
            if ids & tow:
                continue
            top = max(pts[i][1] for i in ids)
            back = min(pts[i][2] for i in ids)
            front = max(pts[i][2] for i in ids)
            middle = (back + front) / 2
            wide = max(abs(pts[i][0]) for i in ids)
            # (longer than 0.6 m: the webbing that runs along the SKED's edges, not a strap over the casualty)
            if top < HIGH or wide > 0.36 or front - back > 0.6:
                continue
            for name, lo, hi in BANDS:
                if lo <= middle < hi:
                    chosen[name].update(ids - shell_points)
        added = b""
        for name, _, _ in BANDS:
            ids = chosen.get(name, set())
            in_face = [all(p in ids for p in f) for f in face_points]
            print("   LOD %g  %-13s %5d points %5d faces  top %.3f  forward %.2f..%.2f" % (
                resolution, name, len(ids), sum(in_face), max((pts[i][1] for i in ids), default=0),
                min((pts[i][2] for i in ids), default=0), max((pts[i][2] for i in ids), default=0)))
            data = bytes(1 if i in ids else 0 for i in range(points)) + bytes(1 if f else 0 for f in in_face)
            added += b"\x01" + name.encode() + b"\0" + pack("<I", len(data)) + data
        out += model[start:last] + added + model[last:cursor]
    assert cursor == len(model)
    if write:
        path.write_bytes(out)


if __name__ == "__main__":
    rework(MODEL, "--report" not in sys.argv)
