"""Regenerate the supplied Hardigg shell with four latch channels per long side."""

import argparse
from pathlib import Path
import runpy
import sys


def bumper_spans(geo, loop, lid):
    """Leave room for the centered latch channels and recessed handles."""
    stations = loop.s_of
    latch = geo.LATCH_HW
    handle = geo.HANDLE_HW
    end = geo.END_LATCH_X
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
    stop = end + latch if lid else handle
    spans.extend(((stations("right", cursor), stations("top", stop)),
                  (stations("top", end - latch), stations("left", cursor)),
                  (stations("left", lower), stations("bottom", end - latch)),
                  (stations("bottom", stop), stations("right", lower))))
    if not lid:
        spans.extend(((stations("top", -handle), stations("top", end + latch)),
                      (stations("bottom", end + latch), stations("bottom", -handle))))
    return spans


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build = args.source / "acme_medchest_src/build"
    sys.path.insert(0, str(build))
    import mc_geo as geo

    geo.LATCH_Z = (.724, .506, .344, .126)
    geo.bumper_spans = lambda loop, lid: bumper_spans(geo, loop, lid)
    sys.argv = [str(build / "build.py"), str(args.output)]
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
