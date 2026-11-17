#!/usr/bin/env python3
"""Build the supplied Hardigg chest with independent lid UVs and a lidless cabinet."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from build_medical_chest_variants import ATLAS_REGIONS, ATLAS_SIZE, DATA
from build_hardigg_abrasion import wear_maps
from build_hardigg_lid_artwork import add_lid_artwork, artwork, artwork_texture
from build_hardigg_wear import paint_finish

PREFIX = r"acm_extended\data\medical_chest\hardigg" + "\\"
REGIONS = {**ATLAS_REGIONS, "inside": (1320, 1632, 704, 704), "lid_trim": (1320, 2368, 704, 768)}
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
        if is_lid and y.min() > .139:
            region, u, v = "lid", (.263 - x) / .526, (.832 - z) / .832
        elif is_lid:
            region, u, v = "lid_trim", (x + .263) / .526, (.832 - z) / .832
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
    io = model_io(root / "acme_medchest_src/build/mc_p3d.py")
    model = work / "hardigg_source"
    subprocess.run([sys.executable, str(Path(__file__).with_name("build_hardigg_hardware.py")),
                    str(root), str(model)], check=True)
    closed = io.read_p3d(model / "medchest.p3d")
    for lod in closed:
        lod["props"]["autocenter"] = "0"
        if lod["res"] < 1000:
            paint_uv(lod)
            if lod["res"] == 1:
                carve_gouges(lod)
            add_lid_artwork(lod, variants)
        for face in lod["faces"]:
            for key in ("tex", "mat"):
                if face[key]:
                    face[key] = PREFIX + face[key].rsplit("\\", 1)[-1]
    cabinet = [split_lod(lod, False) for lod in closed]
    loose = [split_lod(lod, True) for lod in closed if lod["sels"].get("lid")]
    for name, lods in (("medchest", closed), ("medchest_open", cabinet), ("hardigg_lid", loose)):
        io.write_p3d(out / (name + ".p3d"), lods)
        check = io.read_p3d(out / (name + ".p3d"))
        if any(not lod["verts"] for lod in check):
            raise ValueError(f"Empty LOD in {name}")
        print(name, len(check), "LODs;", sum(len(lod["faces"]) for lod in check), "faces")
    cfg = (model / "model.cfg").read_text()
    cfg = cfg.replace('sections[] = {"camo"};', 'sections[] = {"camo", "lid_artwork"};', 1)
    lid_class = cfg.index("    class hardigg_lid:")
    cfg = cfg[:lid_class] + cfg[lid_class:].replace('sections[] = {"camo"};',
                                                  'sections[] = {"camo", "lid_artwork"};', 1)
    i = cfg.rfind("};")
    cfg = cfg[:i] + '    class medchest_open: medchest { sections[] = {"camo"}; };\n' + cfg[i:]
    (out / "model.cfg").write_text(cfg)
    for path in (root / "acme_medchest/data").glob("*.rvmat"):
        material = path.read_text().replace("acme_medchest\\data\\", PREFIX)
        if path.name == "case.rvmat":
            material = material.replace("{0.5, 0.5, 0.5, 1}", "{0.28, 0.28, 0.28, 1}")
            material = material.replace("specularPower = 85;", "specularPower = 34;")
            material = material.replace("fresnel(1.3,7)", "fresnel(1.38,0.4)")
        (out / path.name).write_text(material)


def make_atlas(source):
    canvas = Image.new("RGB", ATLAS_SIZE, (64, 69, 47))
    tile = source.convert("RGB")
    for x, y, w, h in REGIONS.values():
        canvas.paste(tile.resize((w, h), Image.Resampling.LANCZOS), (x, y))
    return canvas


def blackout_lid(image):
    for region in ("lid", "lid_trim"):
        x, y, w, h = REGIONS[region]
        tile = np.asarray(image.crop((x, y, x+w, y+h)), dtype=np.float32)
        luminance = tile @ np.array([.2126, .7152, .0722])
        matte = 14 + luminance * .285
        black = np.stack((matte * .97, matte, matte * 1.03), -1).clip(0, 255).astype(np.uint8)
        image.paste(Image.fromarray(black), (x, y))


def yellow_stencil():
    patch = Image.new("RGBA", ATLAS_SIZE)
    mask = Image.new("L", (1000, 1600))
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 130)
    draw = ImageDraw.Draw(mask)
    draw.text((100, 826), "MED CHEST", font=font, fill=234, stroke_width=1)
    values = np.asarray(mask).copy()
    noise = np.random.default_rng(240).random(values.shape)
    values[noise < .13] = 0
    values = (values * (.66 + noise * .34)).astype(np.uint8)
    dust = mask.filter(ImageFilter.GaussianBlur(6)).point(lambda a: a * .22)
    color = Image.new("RGBA", mask.size, (236, 185, 53, 0))
    color.putalpha(dust)
    core = Image.new("RGBA", mask.size, (243, 195, 52, 0))
    core.putalpha(Image.fromarray(values))
    color.alpha_composite(core)
    patch.paste(color, REGIONS["lid"][:2])
    return patch


def build_textures(root, out, work, hemtt, variants):
    textures = root / "acme_medchest_src/textures_png"
    folder = DATA / "variants"

    def convert(src, dst):
        dst.unlink(missing_ok=True)
        subprocess.run([hemtt, "utils", "paa", "convert", str(src), str(dst)], check=True)

    def export(image, name):
        png = work / (name + ".png")
        image.save(png)
        convert(png, out / (name + ".paa"))

    for name in ("alu_co", "alu_smdi", "black_co", "detail_co"):
        convert(textures / (name + ".png"), out / (name + ".paa"))
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
                tinted = np.clip(tile * np.array([.61, .76, .64]), 0, 255)
                base.paste(Image.fromarray(tinted.astype(np.uint8)), (x, y))
        if index == 11:
            blackout_lid(base)
            overlay = yellow_stencil()
        else:
            texture = folder / ("chest_0_open_ca.paa" if index == 0 else f"chest_{index}_ca.paa")
            png = work / texture.with_suffix(".png").name
            convert(texture, png)
            with Image.open(png) as image:
                overlay = image.convert("RGBA")
        base.paste(finish, mask=finish.getchannel("A"))
        paint_finish(overlay, index, REGIONS["lid"])
        base.paste(overlay, mask=overlay.getchannel("A"))
        export(base, f"case_{index}_co")
        export(artwork_texture(variants[index]), f"lid_artwork_{index}_ca")
    shutil.copyfile(out / "case_0_co.paa", out / "case_co.paa")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Extracted acme_medchest_b2 folder")
    parser.add_argument("--output", type=Path, default=DATA / "hardigg")
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--hemtt", default="hemtt")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)
    variants = [artwork(index) for index in range(12)]
    build_models(args.source.resolve(), args.output, args.work, variants)
    build_textures(args.source, args.output, args.work, args.hemtt, variants)


if __name__ == "__main__":
    main()
