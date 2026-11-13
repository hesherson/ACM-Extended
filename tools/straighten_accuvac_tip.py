"""Straighten the ACCUVAC Yankauer's three visible mesh LODs in the editable MLOD."""

import argparse
from collections import defaultdict
from math import atan2, cos, dist, sin
from pathlib import Path
from struct import pack_into, unpack_from


# Vertex ranges for the wand mesh in the shipped ACCUVAC source model.
# The separate hose, pump, lid, handle, and physical LODs are untouched.
WAND_RINGS = {0: (4812, 5304, 12), 1: (3354, 3525, 8), 2: (1621, 1657, 6)}
REFERENCE = (-0.188156, -0.1342, -0.285825)


def lods(model):
    assert model[:4] == b"MLOD"
    cursor = 12
    for _ in range(unpack_from("<I", model, 8)[0]):
        assert model[cursor:cursor + 4] == b"P3DM"
        point_count, normal_count, face_count = unpack_from("<3I", model, cursor + 12)
        point_offset = cursor + 28
        normal_offset = point_offset + point_count * 16
        cursor = normal_offset + normal_count * 12
        normals_by_point = defaultdict(set)
        for _ in range(face_count):
            vertex_count = unpack_from("<I", model, cursor)[0]
            assert vertex_count in (3, 4)
            for j in range(vertex_count):
                point, normal = unpack_from("<2I", model, cursor + 4 + 16 * j)
                normals_by_point[point].add(normal)
            cursor = model.index(0, cursor + 72) + 1
            cursor = model.index(0, cursor) + 1
        assert model[cursor:cursor + 4] == b"TAGG"
        cursor += 4
        selections = {}
        while True:
            end = model.index(0, cursor + 1)
            name = bytes(model[cursor + 1:end])
            size = unpack_from("<I", model, end + 1)[0]
            cursor = end + 5 + size
            if name == b"#EndOfFile#":
                break
            if name == b"yankauer_tip":
                selections[name] = [i for i, value in enumerate(model[end + 5:cursor]) if value]
        cursor += 4  # LOD resolution
        yield point_offset, normal_offset, normals_by_point, selections
    assert cursor == len(model)


def straighten(model):
    tip = None
    for lod, (points, normals, normals_by_point, selections) in enumerate(lods(model)):
        if b"yankauer_tip" in selections:
            assert tip is not None
            for index in selections[b"yankauer_tip"]:
                pack_into("<3f", model, points + 16 * index, *tip)
        if lod not in WAND_RINGS:
            continue
        first, last, step = WAND_RINGS[lod]
        rings = [range(i, min(i + step, last)) for i in range(first, last, step)]
        ring_points = [[unpack_from("<3f", model, points + 16 * i) for i in ring] for ring in rings]
        centers = [tuple(sum(axis) / len(axis) for axis in zip(*ring)) for ring in ring_points]
        base = centers[0]
        straight_angle = atan2(REFERENCE[2] - base[2], REFERENCE[0] - base[0])
        run = 0.0
        rotations = {}
        for i, (ring, coordinates, center) in enumerate(zip(rings, ring_points, centers)):
            if i:
                run += dist(centers[i - 1], center)
            if center[0] >= -0.20937:
                continue
            target = (base[0] + cos(straight_angle) * run, base[1], base[2] + sin(straight_angle) * run)
            if i == len(centers) - 1 and tip is not None:
                target = tip
            before = centers[i - 1]
            after = centers[min(i + 1, len(centers) - 1)]
            if dist(before, after) > 0.00001:
                angle = straight_angle - atan2(after[2] - before[2], after[0] - before[0])
            rotated_cos, rotated_sin = cos(angle), sin(angle)
            for index, point in zip(ring, coordinates):
                x, y, z = [coordinate - origin for coordinate, origin in zip(point, center)]
                pack_into("<3f", model, points + 16 * index,
                          target[0] + x * rotated_cos - z * rotated_sin, target[1] + y,
                          target[2] + x * rotated_sin + z * rotated_cos)
                for normal in normals_by_point[index]:
                    rotations.setdefault(normal, angle)
            if lod == 0 and i == len(centers) - 1:
                tip = target
        # In this model, each vertex normal belongs only to the transformed wand
        # or only to the unchanged mesh. Do not modify a shared boundary normal.
        untouched_normals = set().union(*(indices for index, indices in normals_by_point.items()
                                         if index < first or index >= last))
        for index, angle in rotations.items():
            assert index not in untouched_normals
            position = normals + 12 * index
            x, y, z = unpack_from("<3f", model, position)
            pack_into("<3f", model, position, x * cos(angle) - z * sin(angle), y, x * sin(angle) + z * cos(angle))
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    args.target.write_bytes(straighten(bytearray(args.source.read_bytes())))
