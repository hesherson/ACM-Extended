#!/usr/bin/env python3
"""Make the tow strap of the SKED models a part that can move, and long enough to reach a rescuer's hip.

A dragged SKED is pulled by its strap, and the strap goes up from the SKED's head end to the rescuer's left hip
(acme_sked_ace, fn_dragStrapAim.sqf, by the animations "strap_pitch" and "strap_yaw" of model.cfg). The models
had the strap lying flat in front of the SKED, 0.95 m long, with no named selection in their visual LODs.
(The engine's rope was tried first, for real sag: measured 2026-11-18, a rope whose ends hang on attached things
stays where it was made.)

For sked_open.p3d and sked_wrapped.p3d this
  - names the strap "tow_strap" in every visual LOD, and in the memory LOD (where its end is the point "tow",
    so the game can say where the moved strap ends): every point further forward than the head end, and every
    face made of such points only;
  - makes it 1.55 times as long, in every LOD (the memory point "tow" at its end moves with it), so that it is
    1.45 m: from the head end on the ground to a hip 0.9 m up and 1.2 m ahead.
Running it again changes nothing.

  python tools/build_sked_strap_selection.py
"""
from pathlib import Path
from struct import pack, pack_into, unpack_from

ROOT = Path(__file__).resolve().parents[1] / "addons/acme_sked"
NAME = b"tow_strap"
# how far forward the head end of each model is (its memory point "head_end"), and a little more
MODELS = {"sked_open.p3d": 1.24, "sked_wrapped.p3d": 1.07}
LONGER = 1.55
SHORT = 1.2          # a strap shorter than this has not been made longer yet


def rework(path, limit):
    model = bytearray(path.read_bytes())
    assert model[:4] == b"MLOD"
    # is the strap still its first length? (the furthest point of the first LOD)
    points = unpack_from("<I", model, 24)[0]
    furthest = max(unpack_from("<3f", model, 40 + 16 * i)[2] for i in range(points))
    stretch = (furthest - limit) < SHORT
    out = bytearray(model[:12])
    cursor = 12
    named = 0
    for _ in range(unpack_from("<I", model, 8)[0]):
        start = cursor
        assert model[cursor:cursor + 4] == b"P3DM"
        points, normals, faces = unpack_from("<3I", model, cursor + 12)
        first = cursor + 28
        forward = []
        for i in range(points):
            z = unpack_from("<f", model, first + 16 * i + 8)[0]
            forward.append(z > limit)
            if stretch and z > limit:
                pack_into("<f", model, first + 16 * i + 8, limit + (z - limit) * LONGER)
        cursor = first + points * 16 + normals * 12
        in_face = []
        for _ in range(faces):
            n = unpack_from("<I", model, cursor)[0]
            in_face.append(all(forward[unpack_from("<I", model, cursor + 4 + 16 * j)[0]] for j in range(n)))
            cursor = model.index(0, cursor + 72) + 1
            cursor = model.index(0, cursor) + 1
        assert model[cursor:cursor + 4] == b"TAGG"
        cursor += 4
        last = None
        have = False
        while True:
            tag = cursor
            end = model.index(0, cursor + 1)
            name = bytes(model[cursor + 1:end])
            size = unpack_from("<I", model, end + 1)[0]
            cursor = end + 5 + size
            if name == NAME:
                have = True
            if name == b"#EndOfFile#":
                last = tag
                break
        resolution = unpack_from("<f", model, cursor)[0]
        cursor += 4
        if (resolution < 1000 or abs(resolution - 1e15) < 1e9) and not have and any(forward):
            data = bytes(1 if f else 0 for f in forward) + bytes(1 if f else 0 for f in in_face)
            out += model[start:last] + b"\x01" + NAME + b"\0" + pack("<I", len(data)) + data + model[last:cursor]
            named += 1
        else:
            out += model[start:cursor]
    assert cursor == len(model)
    path.write_bytes(out)
    return named, stretch, furthest


def main():
    for name, limit in MODELS.items():
        named, stretched, furthest = rework(ROOT / name, limit)
        print("%s: strap named in %d LODs; %s (it reached %.2f m forward)" % (name, named, "made longer" if stretched else "length left alone", furthest))


if __name__ == "__main__":
    main()
