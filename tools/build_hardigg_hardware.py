"""Regenerate the supplied Hardigg shell with four latch channels per long side."""

import argparse
from itertools import product
from pathlib import Path
import runpy
import sys


def bumper_spans(geo, loop, lid):
    """Leave room for the centered latch channels and recessed handles."""
    stations = loop.s_of
    latch = geo.LATCH_HW
    handle = geo.HANDLE_HW
    cuts = [(z - latch, z + latch) for z in geo.LATCH_Z]
    if not lid:
        cuts.extend((z - handle, z + handle) for z in geo.HANDLE_Z)
    spans = []
    cursor = min(a for a, _ in cuts)
    for low, high in sorted(cuts):
        if low - cursor > geo.WS:
            spans.extend(((stations("right", cursor), stations("right", low)),
                          (stations("left", low), stations("left", cursor))))
        cursor = max(cursor, high)

    lower = min(a for a, _ in cuts)
    stop = latch if lid else handle + .012
    spans.extend(((stations("right", cursor), stations("top", stop)),
                  (stations("top", -stop), stations("left", cursor)),
                  (stations("left", lower), stations("bottom", -stop)),
                  (stations("bottom", stop), stations("right", lower))))
    return spans


def refine_depth(geo, part, cuts):
    """Add horizontal samples on the cabinet side walls before molding the pockets."""
    def clip(points, y, keep_above):
        result = []
        for a, b in zip(points[-1:] + points[:-1], points):
            inside_a = a[1] >= y if keep_above else a[1] <= y
            inside_b = b[1] >= y if keep_above else b[1] <= y
            if inside_a != inside_b:
                t = (y - a[1]) / (b[1] - a[1])
                result.append((a[0] + t * (b[0] - a[0]), y, a[2] + t * (b[2] - a[2])))
            if inside_b:
                result.append(b)
        return result

    points, faces = [], []
    for face in part.f:
        polygon = [part.v[i] for i in face]
        pieces = []
        for cut in cuts:
            if min(p[1] for p in polygon) < cut < max(p[1] for p in polygon):
                pieces.append(clip(polygon, cut, False))
                polygon = clip(polygon, cut, True)
        for panel in (*pieces, polygon):
            start = len(points)
            points.extend(panel)
            if len(panel) <= 4:
                faces.append(tuple(range(start, start + len(panel))))
            else:
                faces.extend((start, start + j, start + j + 1) for j in range(1, len(panel) - 1))
    return geo.Part(points, faces).weld()


def recess_handles(geo):
    shell_skin, frames, loop_type = geo.shell_skin, geo.frames, geo.K.XLoop

    class PocketLoop(loop_type):
        def corner_lines(self, count):
            yield from super().corner_lines(count)
            offsets = (-.078, -.065, 0, .065, .078)
            for side, offset in product(("top", "bottom"), offsets):
                yield self.s_of(side, offset)
            for side, z, offset in product(("left", "right"), geo.HANDLE_Z, offsets):
                yield self.s_of(side, z + offset)

    def skin(lid, lod):
        part, seam = shell_skin(lid, lod)
        if lid:
            return part, seam
        part = refine_depth(geo, part, (-.116, -.104, -.053, .006, .021))

        def pocket(cross, y):
            u = geo.K.sstep((.078 - abs(cross)) / .015)
            v = geo.K.sstep((y + .116) / .012) * geo.K.sstep((.021 - y) / .015)
            return u * v

        def indent(x, y, z):
            if abs(x) >= geo.HX - .003:
                depth = max(pocket(z - center, y) for center in geo.HANDLE_Z)
                x -= .022 * depth if x > 0 else -.022 * depth
            if z >= geo.ZT - .003 or z <= geo.ZB + .003:
                z += (-.014 if z > geo.ZC else .014) * pocket(x, y)
            return x, y, z

        part.v = [indent(*point) for point in part.v]
        return part, seam

    def hardware_frames():
        latches, handles = frames()
        recessed = []
        for origin, across, along, normal in handles:
            sink = .021 if normal[0] else .016
            recessed.append((tuple(p - sink * n for p, n in zip(origin, normal)), across, along, normal))
        return latches, recessed

    geo.K.XLoop = PocketLoop
    geo.shell_skin = skin
    geo.frames = hardware_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build = args.source / "acme_medchest_src/build"
    sys.path.insert(0, str(build))
    import mc_geo as geo

    geo.LATCH_Z = (.724, .506, .344, .126)
    geo.END_LATCH_X = 0.0
    geo.bumper_spans = lambda loop, lid: bumper_spans(geo, loop, lid)
    recess_handles(geo)
    sys.argv = [str(build / "build.py"), str(args.output)]
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
