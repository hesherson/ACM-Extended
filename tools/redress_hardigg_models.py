#!/usr/bin/env python3
"""Bring chest models that the generator wrote before B370 up to date, without building the shell again.

It does what build_hardigg_medical_chest.py now does after the shell is built: unfold the inside tile, move
the fittings to their atlas, pick the rusty latches, model the tape and the inventory sheets again, split the
loose lid off, and bolt the open cabinets.

  python tools/redress_hardigg_models.py <acme_medchest_b2 folder> --models <folder with B369 p3d files>
      [--output <hardigg data folder>] [--work <folder>] [--hemtt hemtt]

--models must hold models as B369 left them (not fitted). With --work the lid artwork textures are written too.
"""
import argparse
from pathlib import Path

import build_hardigg_fittings as fittings
import build_hardigg_lid_artwork as art
import build_hardigg_medical_chest as chest
import build_hardigg_surface as surface
import build_hardigg_tape as tape
import build_medical_chest_inserts as inserts
from build_medical_chest_stencils import stencil_glyphs


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="Extracted acme_medchest_b2 folder")
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=inserts.OUTPUT)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--hemtt", default="hemtt")
    parser.add_argument("--only", help="Finish numbers, comma separated; the open cabinets are left alone then")
    args = parser.parse_args()
    io, kit, geo = inserts.load_source(args.source.resolve())
    glyphs = stencil_glyphs(surface.ASSETS / "hardigg_stencil.png")
    only = [int(n) for n in args.only.split(",")] if args.only else None

    for index in (range(12) if only is None else only):
        suffix = f"_{index}" if index else ""
        pieces = art.artwork(index, glyphs, None, None)
        closed = io.read_p3d(args.models / f"medchest{suffix}.p3d")
        for place, lod in enumerate(closed):
            if lod["res"] >= 1000:
                continue
            lod = inserts._drop(lod, lambda face: "lid_artwork" in face["tex"].lower())
            surface.inner_uv(lod)
            surface.moulded(lod)
            lod = fittings.fit(lod, geo, kit, record=index == 0 and lod["res"] == 1)
            fittings.weather(lod, geo, index)
            first = len(lod["faces"])
            art.add_lid_artwork(lod, (pieces,))
            for face in lod["faces"][first:]:
                face["tex"] = chest.PREFIX + f"lid_artwork_{index}_ca.paa"
                face["mat"] = chest.PREFIX + f"lid_artwork_{index}.rvmat"
            closed[place] = lod
        closed = [fittings.rig(lod) for lod in closed]
        io.write_p3d(args.output / f"medchest{suffix}.p3d", closed)
        io.write_p3d(args.output / f"hardigg_lid{suffix}.p3d",
                     [chest.split_lod(lod, True) for lod in closed if lod["sels"].get("lid")])
        print(f"finish {index}:", [sum(len(f["v"]) - 2 for f in lod["faces"]) for lod in closed[:3]], "triangles")
        if args.work:
            tape.export(pieces, index, args.output, args.work, args.hemtt, art.artwork_texture(pieces))

    for name in (("medchest_open.p3d", "medchest_open_4.p3d") if only is None else ()):
        lods = io.read_p3d(args.models / name)
        for place, lod in enumerate(lods):
            if lod["res"] >= 1000:
                continue
            surface.inner_uv(lod)
            surface.moulded(lod)
            lod = fittings.fit(lod, geo, kit)
            lods[place] = fittings.bolted(lod, geo, kit) if lod["res"] == 1 else lod
        lods = [fittings.rig(lod) for lod in lods]
        io.write_p3d(args.output / name, lods)
        print(name, [sum(len(f["v"]) - 2 for f in lod["faces"]) for lod in lods[:3]], "triangles")


if __name__ == "__main__":
    main()
