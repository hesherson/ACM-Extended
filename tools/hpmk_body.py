"""The casualty in the litter pose as measured in the game, for building the HPMK shell round him:
tools/assets/hpmk_body_scan.json (scratch mission acme_hpmkm_test.VR; python tools/hpmk_body.py --take <log>).

In the file, all in the Talon II's own axes (x across, y along toward the head, z up), metres:
  frame   where the casualty's own origin is and his own three axes
  scan    his top under rays straight down, bare: {along: [up at each step across]}; scanU: in a combat uniform
  side    how far out he reaches at heights over the deck, to his right and to his left; sideU: in a uniform
  hscan, hside: the same over his head, finer
-1: nothing of him there. It has to be taken again when the litter pose changes.
"""
import json
import re
import sys
from pathlib import Path

FILE = Path(__file__).with_name("assets") / "hpmk_body_scan.json"


def take(log):
    out = {"frame": None, "bones": {}, "scan": {}, "scanU": {}, "side": {}, "sideU": {}, "hscan": {}, "hside": {}}
    nums = lambda s: [float(v.strip('"')) for v in s.split(",")]
    for line in Path(log).read_text(errors="replace").splitlines():
        m = re.search(r"ACMEHM\|(\w+)\|(.*)$", line)
        if not m:
            continue
        kind, rest = m.group(1), m.group(2).split("|")
        vecs = [nums(r.strip("[]")) for r in rest if r.startswith("[")]
        if kind == "frame":
            out["frame"] = vecs
        elif kind == "bone":
            out["bones"][rest[0]] = vecs
        elif kind in ("scan", "scanU", "hscan"):
            out[kind][rest[0]] = [-1 if v < 0 else v / 1000 for v in vecs[0]]
        elif kind in ("side", "sideU", "hside"):
            out[kind][rest[0]] = [[-1 if v < 0 else v / 1000 for v in row] for row in vecs]
    out["grid"] = {"scan": [0.02, -0.34, 0.01], "hscan": [0.01, -0.20, 0.005], "side": [0.02, 0.10, 0.01], "hside": [0.01, 0.10, 0.01]}
    FILE.write_text(json.dumps(out))
    print("wrote", FILE, {k: len(v) for k, v in out.items() if isinstance(v, dict)})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--take":
        take(sys.argv[2])
