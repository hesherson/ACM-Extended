#!/usr/bin/env python3
"""The shadow volumes of the SKED models, made flat.

The shadow volume of sked_open.p3d and sked_wrapped.p3d was a closed hull round the whole model, 7 cm (open) and
36 cm (wrapped) high. The deck of the SKED is a sheet 2 mm thick that lies INSIDE that hull, so the engine drew
the whole deck in its own shadow whatever the sun did; only the head and foot ends, which stick out of the hull,
were lit (reported from the game 2026-11-18). A shadow volume has to lie inside what is seen.

This scales the hull's heights so that it is a slab 1.5 mm thick at the bottom of the deck: the SKED still
throws its outline on the ground, and nothing of it lies in its own shadow. The points are rewritten in place;
the faces are untouched.

  python tools/build_sked_shadow.py
"""
import struct
from pathlib import Path
from struct import unpack_from

ROOT = Path(__file__).resolve().parents[1] / "addons/acme_sked"
THICK = 0.0015


def flatten(path):
    data = bytearray(path.read_bytes())
    cursor = 12
    done = []
    for _ in range(unpack_from("<I", data, 8)[0]):
        points, normals, faces = unpack_from("<3I", data, cursor + 12)
        p0 = cursor + 28
        cursor = p0 + points * 16 + normals * 12
        for _ in range(faces):
            end = data.index(0, cursor + 72)
            cursor = data.index(0, end + 1) + 1
        cursor += 4
        while True:
            end = data.index(0, cursor + 1)
            name = bytes(data[cursor + 1:end])
            cursor = end + 5 + unpack_from("<I", data, end + 1)[0]
            if name == b"#EndOfFile#":
                break
        res = unpack_from("<f", data, cursor)[0]
        cursor += 4
        # shadow volumes: resolutions 10000 to 20000
        if 9999 < res < 20001:
            ys = [unpack_from("<f", data, p0 + 16 * i + 4)[0] for i in range(points)]
            low, high = min(ys), max(ys)
            if high - low > THICK * 1.01:
                for i, y in enumerate(ys):
                    struct.pack_into("<f", data, p0 + 16 * i + 4, low + (y - low) * THICK / (high - low))
                done.append((res, points, low, high))
    path.write_bytes(data)
    return done


def main():
    for name in ("sked_open.p3d", "sked_wrapped.p3d"):
        for res, points, low, high in flatten(ROOT / name):
            print("%s: shadow volume %g, %d points, was %.3f to %.3f high, now %.4f thick" % (name, res, points, low, high, THICK))


if __name__ == "__main__":
    main()
