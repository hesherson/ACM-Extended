#!/usr/bin/env python3
"""The Talon II cut into four models, one for each segment of the litter, for its fold animation.

Why: the litter's fold is authored on 253 bones (soft skinned deck and straps). The engine's model compiler has
room for 255 entries in a shape's table of bones, and it needs one entry for every bone in every section
(texture + material), more when a section has many bones: talon_open.p3d needs 833. Binarize says so 68 000
times ("SubSkeletonIndex out of bounds", only seen when it is run by hand) and the faces beyond entry 254 are
tied to the wrong bones: in the game the fold was a tangle of spikes, although every bone was where the rig
puts it (measured with a probe point on each bone, 2026-11-18). The open litter at rest shows nothing of this,
because at rest every bone's matrix is the same.

Each segment by itself has 57 to 92 bones and compiles without that error; two segments together do not. So
the fold is shown by four models side by side, each with the whole skeleton and all the animations (model.cfg:
talon_fold_1..4 inherit talon_open) and the faces of one segment. acme_sked_ace puts them in place of the
litter for the seconds of the fold or the unfold (fn_talonTransition.sqf).

A face belongs to the segment with the lowest number among the bones of its corners (segments 1 to 4, foot end
to head end). Each model: those faces of the first LOD with the points they use, and the memory LOD (the axes).

  python tools/build_talon_fold_parts.py
"""
import re
from pathlib import Path
from struct import pack, unpack_from

ROOT = Path(__file__).resolve().parents[1] / "addons/acme_talon"


def segment(bone):
    """1 to 4, foot end to head end, from the bone's name."""
    m = re.fullmatch(r"(?:d(\d)[ab]\d\d|(?:c|n|p|sp|sv)[rl](\d)|f(\d)|t[rl](\d)[a-ht])", bone)
    if m:
        return int(next(g for g in m.groups() if g))
    if bone in ("bfl", "bfr", "hfl", "hfr", "body"):
        return 1
    if bone in ("bhl", "bhr", "hhl", "hhr"):
        return 4
    raise SystemExit("no segment for bone " + bone)


def main():
    data = (ROOT / "talon_open.p3d").read_bytes()
    text = (ROOT / "model.cfg").read_text()
    at = text.index("Talon_Skeleton")
    bones = {b for b, _ in re.findall(r'"(\w+)",\s*"(\w*)"', text[text.index("skeletonBones[] = {", at):text.index("};", at)])}
    cursor = 12
    lods = []
    for _ in range(unpack_from("<I", data, 8)[0]):
        start = cursor
        points, normals, faces = unpack_from("<3I", data, cursor + 12)
        p0 = cursor + 28
        n0 = p0 + points * 16
        cursor = n0 + normals * 12
        recs = []
        for _ in range(faces):
            f0 = cursor
            n = unpack_from("<I", data, cursor)[0]
            vs = [unpack_from("<IIff", data, cursor + 4 + 16 * j) for j in range(n)]
            end = data.index(0, cursor + 72)
            cursor = data.index(0, end + 1) + 1
            recs.append((vs, data[f0 + 68:cursor]))
        cursor += 4
        taggs = []
        while True:
            end = data.index(0, cursor + 1)
            name = data[cursor + 1:end].decode("latin1")
            size = unpack_from("<I", data, end + 1)[0]
            taggs.append((name, data[cursor:cursor + 1], data[end + 5:end + 5 + size]))
            cursor = end + 5 + size
            if name == "#EndOfFile#":
                break
        res = unpack_from("<f", data, cursor)[0]
        cursor += 4
        lods.append(dict(start=start, end=cursor, points=points, normals=normals, p0=p0, n0=n0, recs=recs, taggs=taggs, res=res))
    vis = lods[0]
    assert vis["res"] == 1.0, "the first LOD is not resolution 1: is this the real talon_open.p3d?"
    mem = next(l for l in lods if abs(l["res"] - 1e15) < 1e9)
    P = vis["points"]
    of_point = [[] for _ in range(P)]
    for name, _, blob in vis["taggs"]:
        if name in bones and len(blob) >= P:
            for i in range(P):
                if blob[i]:
                    of_point[i].append(name)
    seg_of = []
    for vs, _ in vis["recs"]:
        segs = [segment(n) for v in vs for n in of_point[v[0]]]
        assert segs, "a face with no bone"
        seg_of.append(min(segs))
    total = 0
    for part in (1, 2, 3, 4):
        keep = [k for k, s in enumerate(seg_of) if s == part]
        used = sorted({v[0] for k in keep for v in vis["recs"][k][0]})
        remap = {old: new for new, old in enumerate(used)}
        lod = bytearray(b"P3DM" + pack("<6I", 28, 256, len(used), vis["normals"], len(keep), 0))
        for old in used:
            lod += data[vis["p0"] + 16 * old:vis["p0"] + 16 * old + 16]
        lod += data[vis["n0"]:vis["n0"] + vis["normals"] * 12]
        for k in keep:
            vs, tail = vis["recs"][k]
            lod += pack("<I", len(vs))
            for j in range(4):
                lod += pack("<IIff", remap[vs[j][0]], vs[j][1], vs[j][2], vs[j][3]) if j < len(vs) else pack("<IIff", 0, 0, 0.0, 0.0)
            lod += tail
        lod += b"TAGG"
        part_bones = set()
        for name, active, blob in vis["taggs"]:
            if name == "#EndOfFile#":
                continue
            if name.startswith("#"):
                if name == "#Property#":
                    lod += active + name.encode("latin1") + b"\0" + pack("<I", len(blob)) + blob
                continue
            pts = bytes(blob[old] for old in used)
            if not any(pts):
                continue
            if name in bones:
                part_bones.add(name)
            new = pts + bytes(blob[P + k] if P + k < len(blob) else 0 for k in keep)
            lod += active + name.encode("latin1") + b"\0" + pack("<I", len(new)) + new
        lod += b"\x01#EndOfFile#\0" + pack("<I", 0) + pack("<f", 1.0)
        out = ROOT / ("talon_fold_%d.p3d" % part)
        out.write_bytes(data[:8] + pack("<I", 2) + bytes(lod) + data[mem["start"]:mem["end"]])
        total += len(keep)
        print("wrote %s: %d faces, %d points, %d bones" % (out.name, len(keep), len(used), len(part_bones)))
    assert total == len(vis["recs"])
    print("all", total, "faces of the first LOD are in a part")


if __name__ == "__main__":
    main()
