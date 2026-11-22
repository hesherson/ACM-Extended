"""Write a model source file (MLOD P3D) of several levels of detail whose points are bound to bones by weight.

A level is a dict: res (its resolution number), points [(x, y, z)] in the model's own axes (x right, y up, z
forward), normals [(x, y, z)], faces [([(point, normal, u, v), ...3 or 4], texture, material)], weights
{bone: {point: weight 0..1}}, props {name: value}. Faces are given so that cross(p1 - p0, p2 - p0) points out of
the surface (as the game's own sources have it).
"""
import struct


def weight_byte(w):
    """How a source file stores a weight: 0 none, 1 all of it, otherwise 256 - 255 w."""
    if w <= 0.002:
        return 0
    if w >= 0.998:
        return 1
    return max(2, min(255, int(round(256 - 255 * w))))


def write(path, levels):
    b = bytearray(b"MLOD" + struct.pack("<II", 257, len(levels)))
    for level in levels:
        points, normals, faces = level["points"], level["normals"], level["faces"]
        b += b"P3DM" + struct.pack("<6I", 28, 256, len(points), len(normals), len(faces), 0)
        for p in points:
            b += struct.pack("<3fI", p[0], p[1], p[2], 0)
        for n in normals:
            b += struct.pack("<3f", *n)
        for vs, tex, mat in faces:
            b += struct.pack("<I", len(vs))
            for j in range(4):
                b += struct.pack("<IIff", *(vs[j] if j < len(vs) else (0, 0, 0.0, 0.0)))
            b += struct.pack("<I", 0) + tex.encode("latin1") + b"\0" + mat.encode("latin1") + b"\0"
        b += b"TAGG"
        for bone, by_point in level.get("weights", {}).items():
            blob = bytearray(len(points) + len(faces))
            for point, w in by_point.items():
                blob[point] = weight_byte(w)
            # a face belongs to a selection when all its points do
            for f, (vs, tex, mat) in enumerate(faces):
                if all(blob[v[0]] for v in vs):
                    blob[len(points) + f] = 1
            b += b"\x01" + bone.encode("latin1") + b"\0" + struct.pack("<I", len(blob)) + blob
        for name, value in level.get("props", {}).items():
            b += b"\x01#Property#\0" + struct.pack("<I", 128)
            b += name.encode("latin1").ljust(64, b"\0") + str(value).encode("latin1").ljust(64, b"\0")
        b += b"\x01#EndOfFile#\0" + struct.pack("<I", 0) + struct.pack("<f", level["res"])
    with open(path, "wb") as f:
        f.write(b)
