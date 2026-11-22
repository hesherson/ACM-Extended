#!/usr/bin/env python3
"""Build the supplied Hardigg chest with independent lid UVs and a lidless cabinet."""
import argparse
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

from build_medical_chest_variants import ATLAS_REGIONS, ATLAS_SIZE, DATA
from build_hardigg_abrasion import wear_maps
from build_hardigg_lid_artwork import add_lid_artwork, artwork, artwork_texture
from build_hardigg_wear import paint_finish
import build_hardigg_fittings as fittings
import build_hardigg_surface as surface
import build_hardigg_tape as tape
import build_medical_chest_inserts as inserts
from build_medical_chest_stencils import stencil_glyphs

PREFIX = r"acm_extended\data\medical_chest\hardigg" + "\\"
REGIONS = {
    **ATLAS_REGIONS, "inside": (1320, 1632, 704, 704),
    "lid_left": (1320, 2368, 112, 704), "lid_right": (1444, 2368, 112, 704),
    "lid_top": (1570, 2368, 454, 112), "lid_bottom": (1570, 2492, 454, 112),
}
LID_ORIGIN = np.array((0.0, .1175, .416))
GOUGES = ((.14, .241), (-.15, .416), (.16, .559), (-.13, .603),
          (.178, .721), (-.177, .721), (.218, .779), (-.218, .779),
          (.201, .752), (-.228, .726), (.173, .531), (-.177, .366))


def model_io(source):
    spec = importlib.util.spec_from_file_location("medchest_mlod", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def carve_gouges(lod):
    """Indent small, tapered pockets in the flat exterior plastic without altering its perimeter."""
    face_wear = []
    for sign in (-1, 1):
        candidates = []
        for index, face in enumerate(lod["faces"]):
            ids = face["v"]
            if len(ids) != 3 or not set(ids) <= lod["sels"]["camo"]:
                continue
            positions = np.array([lod["verts"][j] for j in ids])
            if np.min(positions[:, 1] * sign) < .145:
                continue
            normal = np.cross(positions[1] - positions[0], positions[2] - positions[0])
            if normal[1] * sign > .000006:
                candidates.append((index, positions))
        for target in GOUGES:
            if not candidates:
                break
            k = min(range(len(candidates)), key=lambda j:
                    np.linalg.norm(candidates[j][1].mean(axis=0)[[0, 2]] - target))
            index, points = candidates.pop(k)
            center = points.mean(axis=0)
            face = lod["faces"][index]
            outer = face["v"]
            edges = (points[1:] - points[0]).T
            solve = np.linalg.pinv(edges)
            longest = max((points[(i + 1) % 3] - points[i] for i in range(3)), key=np.linalg.norm)
            direction = longest / np.linalg.norm(longest)
            offsets = points - center
            along = (offsets @ direction)[:, None] * direction
            # Keep the elongated cut inside its original triangle even on a thin bevel.
            shape = along + (offsets - along) * .36
            weight = shape @ solve.T
            weight = np.column_stack((-weight.sum(axis=1), weight))
            scale = min(.23, .018 / np.linalg.norm(longest), .25 / max(-weight.min(), 1e-6))
            rim = center + shape * scale
            bottom = center + (rim - center) * .38
            # Interpolate both UVs and the original smooth normals on the outer lip.
            cut_uv = dict(zip(outer, face["uv"]))
            original_uv = np.asarray(face["uv"])
            weights = (np.concatenate((rim, bottom)) - points[0]) @ solve.T
            new_uv = original_uv[0] + weights @ (original_uv[1:] - original_uv[0])
            plane = np.cross(edges[:, 0], edges[:, 1])
            widths = np.linalg.norm(np.cross(rim[1:] - rim[0], direction), axis=1)
            bottom -= min(.00064, np.max(widths) * .23) * plane / np.linalg.norm(plane)
            selected = []
            for ring in (rim, bottom):
                ids = list(range(len(lod["verts"]), len(lod["verts"]) + 3))
                lod["verts"].extend(map(tuple, ring))
                for vertices in lod["sels"].values():
                    if set(outer) <= vertices:
                        vertices.update(ids)
                selected.append(ids)
            inner, floor = selected
            cut_uv.update(zip(inner + floor, map(tuple, new_uv)))
            source_normals = np.asarray([lod["normals"][i] for i in face["n"]])
            smooth = source_normals[0] + weights[:3] @ (source_normals[1:] - source_normals[0])
            smooth /= np.linalg.norm(smooth, axis=1, keepdims=True)
            lip_normal = len(lod["normals"])
            lod["normals"].extend(map(tuple, smooth))
            cut_normals = dict(zip(outer + inner, face["n"] + list(range(lip_normal, lip_normal + 3))))
            fragments = []
            for outside, inside in ((outer, inner), (inner, floor)):
                for i in range(3):
                    j = (i + 1) % 3
                    a, b, c, d = outside[i], outside[j], inside[j], inside[i]
                    pa, pb, pc, pd = np.array([lod["verts"][k] for k in (a, b, c, d)])
                    # On a narrow bevel, the first diagonal can cross the concave lip.
                    if np.cross(pb-pa, pc-pa) @ plane > 0 and np.cross(pc-pa, pd-pa) @ plane > 0:
                        fragments.extend(((a, b, c), (a, c, d)))
                    else:
                        fragments.extend(((a, b, d), (b, c, d)))
            fragments.append(tuple(floor))
            # Flat normals across the tiny cut make its edges catch the light.
            for i, ids in enumerate(fragments):
                coords = np.array([lod["verts"][j] for j in ids])
                normal = np.cross(coords[1] - coords[0], coords[2] - coords[0])
                if normal @ plane <= 0:
                    raise ValueError("A gouge fragment inverted the shell surface")
                if i < 6:
                    normals = [cut_normals[j] for j in ids]
                else:
                    normal /= np.linalg.norm(normal)
                    normals = [len(lod["normals"])] * 3
                    lod["normals"].append(tuple(normal))
                fragment = {**face, "v": list(ids), "n": normals, "uv": [cut_uv[j] for j in ids]}
                if i == 0:
                    lod["faces"][index] = fragment
                else:
                    face_wear.append(fragment)
    lod["faces"].extend(face_wear)


def paint_uv(lod):
    lid = lod["sels"]["lid"]
    for face in lod["faces"]:
        if not face["tex"].lower().endswith(r"\case_co.paa"):
            continue
        points = np.array([lod["verts"][i] for i in face["v"]])
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        axis = int(np.argmax(abs(normal)))
        center = points.mean(axis=0)
        is_lid = set(face["v"]) <= lid
        x, y, z = points.T
        # The outer depth band includes the rib crowns, sides and groove transitions.
        # Every patch in it uses the same front coordinates as the neighboring flat panel.
        on_rib_panel = abs(center[0]) < .205 and .064 < center[2] < .768
        front_facing = normal[1] > .69 * np.linalg.norm(normal)
        if is_lid and y.min() > .139 and (on_rib_panel or front_facing):
            region, u, v = "lid", (.263 - x) / .526, (.832 - z) / .832
        elif is_lid and (normal[1] >= 0 or (center[1] > .088 and axis != 1)):
            # Unwrap the shoulder on a diagonal across its depth and inward roll.
            # The two components increase together from the seam towards the face.
            if abs(normal[0]) > abs(normal[2]):
                region = "lid_right" if center[0] > 0 else "lid_left"
                u, v = (y - .074 + .265 - abs(x)) / .133, (.832 - z) / .832
            else:
                region = "lid_top" if center[2] > .416 else "lid_bottom"
                end = .832 - z if center[2] > .416 else z - .018
                u, v = (.263 - x) / .526, (y - .074 + end) / .133
        elif is_lid:
            region, u, v = "inside", (x + .263) / .526, (.832 - z) / .832
        elif axis == 1 and normal[1] < 0 and center[1] < -.13:
            region, u, v = "back", (x + .263) / .526, (.832 - z) / .832
        elif axis == 0 and abs(center[0]) > .217 and normal[0] * center[0] > 0:
            region = "right" if center[0] < 0 else "left"
            u, v = (.161 - y) / .322, (.832 - z) / .832
        elif axis == 2 and (center[2] > .775 or center[2] < .055):
            region = "top" if normal[2] > 0 else "bottom"
            u, v = (x + .263) / .526, (.161 - y) / .322
        else:
            region, u, v = "inside", (x + .263) / .526, (.832 - z) / .832
        left, top, width, height = REGIONS[region]
        face["uv"] = list(zip((left + 3 + np.clip(u, 0, 1) * (width - 6)) / ATLAS_SIZE[0],
                              1 - (top + 3 + np.clip(v, 0, 1) * (height - 6)) / ATLAS_SIZE[1]))


def fix_plaque_uv(lod):
    # The plaque occupies the left half of the detail atlas below drawers 1–4.
    for face in lod["faces"]:
        if face["tex"].endswith("detail_co.paa") and all(
            0 <= u <= .5 and 1 - 1248/2048 <= v <= 1 - 768/2048 for u, v in face["uv"]
        ):
            face["uv"] = [(.5 - u, v) for u, v in face["uv"]]


def rounded_shadow(kit, geo, source):
    vertices, faces, selections = [], [], {}

    def add(part, bone=""):
        start = len(vertices)
        vertices.extend(part.v)
        if bone:
            selections.setdefault(bone, set()).update(range(start, len(vertices)))
        for polygon in part.f:
            a, *others = [start + i for i in polygon]
            for b, c in zip(others, others[1:]):
                faces.append(dict(v=[a, b, c], n=[0, 0, 0], uv=[(0, 0)] * 3, tex="", mat=""))

    add(kit.rbox((-.263, -.153, .018), (.263, .073, .831), .028, 3))
    add(kit.rbox((-.262, .075, .018), (.262, .152, .831), .028, 3), "lid")
    for height in (.150, .333, .517, .700):
        add(kit.rbox((-.176, .141, height-.021), (.176, .160, height+.021), .008, 2), "lid")
    for side in (-1, 1):
        x = side * .24
        add(kit.cyl((x-.012, -.120, .036), (x+.012, -.120, .036), .035, n=10))
    for index in range(1, 9):
        low, high = geo.drawer_z(index)
        add(kit.rbox((-.216, -.120, low), (.216, .068, high), .003, 2), f"drawer{index}")
    return {**source, "verts": vertices, "faces": faces, "sels": selections, "sharp": [],
            "normals": [(0., 0., 1.)]}


def split_lod(lod, loose):
    lid = lod["sels"].get("lid", set())
    keep = sorted(lid if loose else set(range(len(lod["verts"]))) - lid)
    if not keep:
        raise ValueError("A physical or visual LOD lost all its points")
    index = {old: new for new, old in enumerate(keep)}
    faces = []
    for f in lod["faces"]:
        if all(i in index for i in f["v"]):
            faces.append({**f, "v": [index[i] for i in f["v"]]})
    sels = {}
    for name, points in lod["sels"].items():
        if loose and name not in ("camo", "lid_artwork", "Component02"):
            continue
        selected = {index[i] for i in points if i in index}
        if selected:
            sels["Component01" if loose and name == "Component02" else name] = selected
    verts = [lod["verts"][i] for i in keep]
    if loose:
        verts = list(map(tuple, np.asarray(verts) - LID_ORIGIN))
    mass = [lod["mass"][i] for i in keep] if lod["mass"] is not None else None
    return {**lod, "verts": verts, "faces": faces, "sels": sels, "mass": mass,
            "sharp": [(index[a], index[b]) for a, b in lod["sharp"] if a in index and b in index]}


def build_models(root, out, work, variants):
    source = root / "acme_medchest_src/build"
    io = model_io(source / "mc_p3d.py")
    sys.path.insert(0, str(source))
    import mc_geo as geo
    import mc_kit as kit
    model = work / "hardigg_source"
    subprocess.run([sys.executable, str(Path(__file__).with_name("build_hardigg_hardware.py")),
                    str(root), str(model)], check=True)
    closed = io.read_p3d(model / "medchest.p3d")
    for index, lod in enumerate(closed):
        if lod["res"] == io.LOD_SHADOW:
            lod = closed[index] = rounded_shadow(kit, geo, lod)
        lod["props"]["autocenter"] = "0"
        if lod["res"] < 1000:
            paint_uv(lod)
            surface.inner_uv(lod)
            surface.moulded(lod)
            fix_plaque_uv(lod)
            if lod["res"] == 1:
                carve_gouges(lod)
        if math.isclose(lod["res"], io.LOD_MEMORY, rel_tol=1e-6):
            lod["sels"]["chest_actions"] = {len(lod["verts"])}
            lod["verts"].append((0., .167, .416))
        for face in lod["faces"]:
            for key in ("tex", "mat"):
                if face[key]:
                    face[key] = PREFIX + face[key].rsplit("\\", 1)[-1]
        if lod["res"] < 1000:
            # Latches, handles, wheels and feet go on their own atlas; the first LOD records their relief.
            closed[index] = fittings.fit(lod, geo, kit, record=lod["res"] == 1)
    closed = [fittings.rig(lod) for lod in closed]              # latch hinges to where the real drum is
    cabinet = [split_lod(lod, False) for lod in closed]
    cabinet = [fittings.bolted(lod, geo, kit) if lod["res"] == 1 else lod for lod in cabinet]
    for lod in cabinet:
        if math.isclose(lod["res"], io.LOD_MEMORY, rel_tol=1e-6):
            lod["verts"][next(iter(lod["sels"]["chest_actions"]))] = (0., .081, .416)
    cabinet = inserts.padlocked(io, kit, geo, cabinet)
    io.write_p3d(out / "medchest_open.p3d", cabinet)
    io.write_p3d(out / "medchest_open_4.p3d", inserts.four_drawer(io, kit, geo, cabinet))
    for index, pieces in enumerate(variants):
        textured = [deepcopy(lod) if lod["res"] < 1000 else lod for lod in closed]
        for lod in textured:
            if lod["res"] < 1000:
                fittings.weather(lod, geo, index)
                first_art = len(lod["faces"])
                add_lid_artwork(lod, (pieces,))
                for face in lod["faces"][first_art:]:
                    face["tex"] = PREFIX + f"lid_artwork_{index}_ca.paa"
                    face["mat"] = PREFIX + f"lid_artwork_{index}.rvmat"
        loose = [split_lod(lod, True) for lod in textured if lod["sels"].get("lid")]
        suffix = f"_{index}" if index else ""
        io.write_p3d(out / f"medchest{suffix}.p3d", textured)
        io.write_p3d(out / f"hardigg_lid{suffix}.p3d", loose)
        print(f"Hardigg finish {index}: {len(pieces)} fitted artwork pieces")
    cfg = (model / "model.cfg").read_text()
    cfg = cfg.replace('sections[] = {"camo"};', 'sections[] = {"camo", "lid_artwork"};', 1)
    lid_class = cfg.index("    class hardigg_lid:")
    cfg = cfg[:lid_class] + cfg[lid_class:].replace('sections[] = {"camo"};',
                                                  'sections[] = {"camo", "lid_artwork"};', 1)
    i = cfg.rfind("};")
    derived = ['    class medchest_open: medchest { sections[] = {"camo"}; };',
               '    class medchest_open_4: medchest { sections[] = {"camo"}; };']
    for index in range(1, len(variants)):
        derived.extend((f"    class medchest_{index}: medchest {{}};",
                        f"    class hardigg_lid_{index}: hardigg_lid {{}};"))
    cfg = cfg[:i] + "\n".join(derived) + "\n" + cfg[i:]
    (out / "model.cfg").write_text(cfg)
    for path in (root / "acme_medchest/data").glob("*.rvmat"):
        material = path.read_text().replace("acme_medchest\\data\\", PREFIX)
        if path.name == "case.rvmat":
            material = material.replace("{0.5, 0.5, 0.5, 1}", "{0.28, 0.28, 0.28, 1}")
            material = material.replace("specularPower = 85;", "specularPower = 34;")
            material = material.replace("fresnel(1.3,7)", "fresnel(1.38,0.4)")
        (out / path.name).write_text(material)


def make_atlas(source):
    canvas = Image.new("RGB", ATLAS_SIZE, (43, 63, 50))
    pixels = np.asarray(source.convert("RGB"), dtype=np.float32)
    luminance = pixels @ np.array([.2126, .7152, .0722])
    contrast = (luminance - np.median(luminance)) * .64
    colors = np.clip(np.array([43, 63, 50]) + contrast[..., None], 0, 255)
    tile = Image.fromarray(colors.astype(np.uint8))
    for x, y, w, h in REGIONS.values():
        canvas.paste(tile.resize((w, h), Image.Resampling.LANCZOS), (x, y))
    return canvas


def blackout_lid(image):
    for region in ("lid", "lid_left", "lid_right", "lid_top", "lid_bottom"):
        x, y, w, h = REGIONS[region]
        tile = np.asarray(image.crop((x, y, x+w, y+h)), dtype=np.float32)
        luminance = tile @ np.array([.2126, .7152, .0722])
        matte = 14 + luminance * .285
        black = np.stack((matte * .97, matte, matte * 1.03), -1).clip(0, 255).astype(np.uint8)
        image.paste(Image.fromarray(black), (x, y))


def build_textures(root, out, work, hemtt, variants, glyphs):
    textures = root / "acme_medchest_src/textures_png"

    def convert(src, dst):
        dst.unlink(missing_ok=True)
        subprocess.run([hemtt, "utils", "paa", "convert", str(src), str(dst)], check=True)

    def export(image, name):
        png = work / (name + ".png")
        image.save(png)
        convert(png, out / (name + ".paa"))

    for name in ("alu_co", "alu_smdi", "black_co"):
        convert(textures / (name + ".png"), out / (name + ".paa"))
    # The detail atlas also carries the four drawer fronts and the padlock faces.
    export(inserts.paint_detail(textures / "detail_co.png"), "detail_co")
    with Image.open(textures / "case_nohq.png") as image:
        specular, normal, finish = wear_maps(REGIONS, ATLAS_SIZE, image)
    export(specular, "case_smdi")
    export(normal, "case_nohq")
    with Image.open(textures / "case_co.png") as source:
        olive = make_atlas(source)
    for index in range(12):
        base = olive.copy()
        if index == 8:
            for region in ("back", "right", "left", "top", "bottom", "inside"):
                x, y, w, h = REGIONS[region]
                tile = np.asarray(base.crop((x, y, x+w, y+h)), dtype=np.float32)
                tinted = np.clip(tile * np.array([.80, .89, .84]), 0, 255)
                base.paste(Image.fromarray(tinted.astype(np.uint8)), (x, y))
        if index == 11:
            blackout_lid(base)
        overlay = Image.new("RGBA", ATLAS_SIZE)
        base.paste(finish, mask=finish.getchannel("A"))
        paint_finish(overlay, index, REGIONS, glyphs)
        base.paste(overlay, mask=overlay.getchannel("A"))
        export(base, f"case_{index}_co")
        tape.export(variants[index], index, out, work, hemtt, artwork_texture(variants[index]))
    shutil.copyfile(out / "case_0_co.paa", out / "case_co.paa")
    # The shell textures proper come from the mesh-driven surface builder. It keeps the markings painted above
    # and replaces the base plastic, wear, normal, specular and ambient shadow maps.
    fittings.build(out, work / "fittings", hemtt)
    import build_hardigg_surface
    build_hardigg_surface.build(out, work / "surface", hemtt, glyphs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Extracted acme_medchest_b2 folder")
    parser.add_argument("--output", type=Path, default=DATA / "hardigg")
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--hemtt", default="hemtt")
    parser.add_argument("--stencil", type=Path, default=Path(__file__).with_name("assets") / "hardigg_stencil.png")
    parser.add_argument("--handwriting", type=Path, help="No longer used: build_hardigg_sheet.py has its own fonts")
    parser.add_argument("--quantity-font", type=Path, help="No longer used")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)
    glyphs = stencil_glyphs(args.stencil)
    variants = [artwork(index, glyphs, args.handwriting, args.quantity_font) for index in range(12)]
    build_models(args.source.resolve(), args.output, args.work, variants)
    build_textures(args.source, args.output, args.work, args.hemtt, variants, glyphs)


if __name__ == "__main__":
    main()
