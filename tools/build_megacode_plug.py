"""The plug at the laptop end of the Megacode Kelly cable: addons/acm_extended/models/megacode_plug.p3d.

The cable is an engine rope, and a rope cannot be given an end shape or an end direction. What makes its end read as
plugged into the laptop is this small connector: fixed on the laptop with its origin on the laptop's back face, it
runs out along +y (the laptop's own forward, which faces the manikin after the spawn turns the laptop round), and the
rope is anchored a few millimetres inside its tail, so the cable comes out of the plug rather than out of the air.

Axes are the game's model axes (x right, y forward, z up); Model from build_airway_adjuncts writes them in the file's
order. The origin stays where it is drawn (autocenter 0), which is what lets the script put it on the port point.

    y  -0.006 .. 0.010   metal shell, its back end inside the laptop's case
    y   0.010 .. 0.028   moulded boot
    y   0.028 .. 0.042   strain relief, tapering to the cable

Run: python tools/build_megacode_plug.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_airway_adjuncts import Model, colour, write  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "addons" / "acm_extended" / "models" / "megacode_plug.p3d"

SHELL = colour(0.42, 0.43, 0.45)
BOOT = colour(0.055, 0.058, 0.062)
RING = colour(0.16, 0.17, 0.19)

# (y, radius) stations along the plug; the rope is anchored at y = 0.036 by the script (ACME_megacode_plugLength).
SHELL_STATIONS = [(-0.006, 0.0058), (0.010, 0.0058)]
COLLAR_STATIONS = [(0.010, 0.0074), (0.013, 0.0074)]
BOOT_STATIONS = [(0.013, 0.0068), (0.026, 0.0066), (0.028, 0.0058)]
RELIEF_STATIONS = [(0.028, 0.0052), (0.035, 0.0043), (0.042, 0.0035)]


def plug(sides):
    m = Model()
    for stations, tex in ((SHELL_STATIONS, SHELL), (COLLAR_STATIONS, RING), (BOOT_STATIONS, BOOT), (RELIEF_STATIONS, BOOT)):
        m.tube([(0.0, y, 0.0) for y, _ in stations], [r for _, r in stations], sides, tex, across=(0, 0, 1))
    return m


def main():
    levels = [plug(sides).level(res, i == 0) for i, (res, sides) in enumerate(((1.0, 16), (2.0, 10), (3.0, 6)))]
    write(OUT, levels)
    print(OUT, "points", [len(lv["pts"]) for lv in levels], "faces", [len(lv["faces"]) for lv in levels])


if __name__ == "__main__":
    main()
