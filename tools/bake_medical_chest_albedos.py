#!/usr/bin/env python3
"""Bake the crate body and fit a separate, uniquely mapped paint layer to the lid.

Supply the native olive albedo as PNG and the stock model's visual LOD dumps.
Each dump is an array of LODs with Points, UV, and Sections containing Texture
and Faces. Indices refer to render vertices with their native per-vertex UV.
"""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image

from build_medical_chest_variants import (
    ATLAS_REGIONS, DATA, fitted_faces, generic_open_atlas, paint_projections, visual_model,
)

OLIVE = "portablecabinet_01_olive_co.paa"


def triangles(lod):
    faces = []
    for section in lod["Sections"]:
        if section["Texture"].rsplit("\\", 1)[-1].lower() != OLIVE:
            continue
        for face in section["Faces"]:
            faces.extend((face[0], face[i], face[i+1]) for i in range(1, len(face)-1))
    return np.asarray(faces)


def stamp_triangle(mapping, native_uv, art_uv):
    """Map covered native pixel centers back to the source artwork."""
    height, width = mapping.shape[:2]
    low = np.maximum(np.floor(native_uv.min(axis=0)).astype(int), (0, 0))
    high = np.minimum(np.ceil(native_uv.max(axis=0)).astype(int) + 1, (width, height))
    if np.any(high <= low):
        return
    a, b, c = native_uv
    ab, ac = b - a, c - a
    area = ab[0] * ac[1] - ab[1] * ac[0]
    if abs(area) < 1e-5:
        return
    y, x = np.mgrid[low[1]:high[1], low[0]:high[0]]
    x, y = x - a[0], y - a[1]
    u = (x * ac[1] - y * ac[0]) / area
    v = (ab[0] * y - ab[1] * x) / area
    w = 1 - u - v
    inside = (u >= -1e-5) & (v >= -1e-5) & (w >= -1e-5)
    tile = mapping[low[1]:high[1], low[0]:high[0]]
    tile[inside] = w[inside, None] * art_uv[0] + u[inside, None] * art_uv[1] + v[inside, None] * art_uv[2]


def project_artwork(mapping, lod, surface, regions):
    faces = triangles(lod)
    points = np.asarray(lod["Points"])[faces]
    uv = np.asarray(lod["UV"])[faces] * np.array(mapping.shape[:2][::-1]) - .5
    normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    for selected, region, (u, v), _ in paint_projections(points, normals, surface):
        if region not in regions:
            continue
        x, y, w, h = ATLAS_REGIONS[region]
        source = np.stack((x + u.clip(0, 1) * (w - 1), y + v.clip(0, 1) * (h - 1)), axis=2)
        for i in np.flatnonzero(selected):
            stamp_triangle(mapping, uv[i], source[i])


def texture_mapping(closed_lods, size):
    width, height = size
    mapping = np.full((height, width, 2), -1, dtype=np.float32)
    # The stock lid repeats mirrored UV islands. Bake only the crate body.
    for lod in reversed(closed_lods):
        project_artwork(mapping, lod, "closed", ATLAS_REGIONS.keys() - {"lid"})
    return mapping


def bake(base, atlas, mapping):
    covered = mapping[:, :, 0] >= 0
    sample = mapping[covered]
    u, v = sample.T
    x, y = sample.astype(int).T
    u, v = (u - x)[:, None], (v - y)[:, None]
    atlas = np.asarray(atlas)
    paint = ((atlas[y, x] * (1-u) + atlas[y, x+1] * u) * (1-v)
             + (atlas[y+1, x] * (1-u) + atlas[y+1, x+1] * u) * v)
    rgb = np.array(base)
    alpha = paint[:, 3:4] / 255
    rgb[covered] = np.rint(rgb[covered] * (1-alpha) + paint[:, :3] * alpha).astype(np.uint8)
    return Image.fromarray(rgb)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--olive", type=Path, required=True)
    parser.add_argument("--closed-uv", type=Path, required=True)
    parser.add_argument("--closed-mesh", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--hemtt", default="hemtt")
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    folder = DATA / "variants"

    def convert(src, dst):
        dst.unlink(missing_ok=True)
        subprocess.run([args.hemtt, "utils", "paa", "convert", str(src), str(dst)], check=True)

    def decode(src):
        png = args.work / src.with_suffix(".png").name
        convert(src, png)
        with Image.open(png) as texture:
            return texture.convert("RGBA")

    with Image.open(args.olive) as texture:
        olive = texture.convert("RGB")
    mapping = texture_mapping(json.loads(args.closed_uv.read_text()), olive.size)
    if (mapping[:, :, 0] >= 0).sum() < 1000:
        raise ValueError("The stock UV dumps did not cover the cabinet texture")
    shell_eight = decode(folder / "chest_8_shell_co.paa").convert("RGB")
    if shell_eight.size != olive.size:
        raise ValueError("The stock and tinted finishes must share the same UV atlas")
    closed_lid_faces = tuple(fitted_faces(args.closed_mesh, "closed", {"lid"}))
    if not closed_lid_faces:
        raise ValueError("The stock closed mesh did not have any paintable lid faces")
    for number in range(11):
        art = folder / f"chest_{number}_ca.paa"
        artwork = decode(art) if number else generic_open_atlas(art, args.work, args.hemtt)
        base = shell_eight if number == 8 else olive
        png = args.work / f"chest_{number}_baked_co.png"
        bake(base, artwork, mapping).save(png)
        convert(png, folder / png.with_suffix(".paa").name)
        lid_art = art.name if number else "chest_0_open_ca.paa"
        texture = f"acm_extended\\data\\medical_chest\\variants\\{lid_art}"
        (folder / f"chest_{number}_closed_lid.p3d").write_bytes(visual_model(closed_lid_faces, texture))


if __name__ == "__main__":
    main()
