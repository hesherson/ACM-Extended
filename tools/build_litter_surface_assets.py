"""Build the patient HPMK shells and repair the carry bag fabric geometry."""

import argparse
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent / "addons"
FABRIC = r"acme_sked\data\sked_cordura.rvmat"
PIPING = "#(rgb,8,8,3)color(0.25,0.191,0.103,1,CO)"


def shell_model(io, exposed):
    """Give the empty field shell a filled profile. Use visual LODs only."""
    folder = ROOT / "acme_hpmk"
    source = io.read_p3d(folder / "hpmk_closed.p3d")
    result = []
    for lod in source:
        if lod["res"] >= 1000:
            continue
        lod["props"]["autocenter"] = "0"
        positions = np.asarray(lod["verts"])

        def height(p):
            x, y, z = p.T
            center = np.clip(1 - (x / (.44 + .08 * np.exp(-((y - .26) / .38)**2)))**2, 0, 1)**1.1
            upper = np.exp(-((y - .26) / .43)**4) * .285
            lower = np.exp(-((y + .56) / .51)**4) * .16
            coverage = np.clip((.23 - y) / .18, 0, 1) if exposed else 1
            envelope = center * np.maximum(upper, lower) * coverage
            loft = np.clip((z + .069) / .030, 0, 1)
            return z + .038 + envelope * loft

        eps = .0002
        base = height(positions)
        grad = [(height(positions + np.eye(3)[i]*eps) - height(positions - np.eye(3)[i]*eps)) / (2*eps)
                for i in range(3)]
        positions[:, 2] = base
        lod["verts"] = list(map(tuple, positions))
        normals = np.asarray(lod["normals"])
        lod["normals"] = []
        # Update the smooth vertex normals through the loft deformation.
        for face in lod["faces"]:
            refs = []
            for point, normal in zip(face["v"], normals[face["n"]]):
                nx, ny, nz = normal
                dz = nz / max(grad[2][point], .1)
                vector = np.array((nx - grad[0][point]*dz, ny - grad[1][point]*dz, dz))
                refs.append(len(lod["normals"]))
                lod["normals"].append(tuple(vector / max(np.linalg.norm(vector), 1e-8)))
            face["n"] = refs
        result.append(lod)
    io.write_p3d(folder / ("hpmk_patient_exposed.p3d" if exposed else "hpmk_patient_wrapped.p3d"), result)


def fix_fabric_uv(lod):
    """Give narrow bindings and folded returns a stable texture tangent."""
    positions = np.array(lod["verts"])
    for face in lod["faces"]:
        if face["mat"] != FABRIC:
            continue
        p = positions[face["v"]]
        v = np.array(face["uv"])
        area = np.linalg.norm(np.cross(p[1:-1] - p[0], p[2:] - p[0]), axis=1).sum()
        u, w = v[1:-1] - v[0], v[2:] - v[0]
        uv_area = abs(u[:, 0] * w[:, 1] - u[:, 1] * w[:, 0]).sum()
        if area < 1e-9 or uv_area > area * .071:
            continue
        along = max(p - p[0], key=np.linalg.norm)
        along /= np.linalg.norm(along)
        normal = np.cross(p[1] - p[0], p[2] - p[0])
        across = np.cross(normal, along)
        across /= max(np.linalg.norm(across), 1e-10)
        offset = p - p.mean(axis=0)
        new = np.column_stack((offset @ along, offset @ across)) * .56
        # Sample a clean patch on the existing Cordura body island, inside its stitch lines.
        face["uv"] = list(map(tuple, new + (.225, .757)))


def bag_space(point, slung, vector=False):
    x, y, z = point
    if slung:
        return (-x, -y, z) if vector else (-x - .035, -y - .223, z - .836)
    return (z, x, y) if vector else (z - .435, x, y + .136)


def pack_space(point, slung):
    x, y, z = point
    return (-x - .035, -y - .223, z + .836) if slung else (y, z - .136, x + .435)


def add_pocket_seams(lod, slung):
    positions = np.array([pack_space(p, slung) for p in lod["verts"]])
    surfaces = []
    for f in lod["faces"]:
        if f["mat"] != FABRIC:
            continue
        polygon = positions[f["v"]]
        if polygon[:, 1].max() < .12:
            continue
        for corner in range(1, len(polygon) - 1):
            p = polygon[[0, corner, corner + 1]]
            plane = p[:, [0, 2]]
            axes = (plane[1:] - plane[0]).T
            if abs(np.linalg.det(axes)) > 1e-8:
                surfaces.append((plane[0], np.linalg.inv(axes), p[:, 1]))
    origin, axes, depth = (np.asarray(values) for values in zip(*surfaces))

    def face_depth(x, z):
        relative = (axes @ (np.array((x, z)) - origin)[..., None])[..., 0]
        weights = np.column_stack((1 - relative.sum(axis=1), relative))
        inside = (weights >= -1.e-6).all(axis=1)
        return np.max((weights[inside] * depth[inside]).sum(axis=1))

    normal = len(lod["normals"])
    lod["normals"].append(bag_space((0, 1, 0), slung, True))
    trim = "#(rgb,8,8,3)color(0.34,0.27,0.17,1,CO)"
    # Two raised folded bindings wrap each flap edge, over the curved pouch face.
    for z in (.648, .337):
        for height, thickness in ((z, .004), (z + .006, .0016)):
            start = len(lod["verts"])
            xs = np.linspace(-.10, .10, 20 if lod["res"] <= 1 else 9)
            for x in xs:
                for dz in (-thickness, 0, thickness):
                    y = face_depth(x, height+dz) + (.0032 if dz == 0 else .0012)
                    lod["verts"].append(bag_space((x, y, height+dz), slung))
            for i in range(len(xs) - 1):
                for j in range(2):
                    a = start + i * 3 + j
                    lod["faces"].append(dict(v=[a, a+1, a+4, a+3], n=[normal]*4,
                                             uv=[(0, 0), (0, 1), (1, 1), (1, 0)], tex=trim, mat=""))


def add_collar(lod, slung):
    """Raised stitched welt follows the upper attachment rim of the roll bag."""
    count = 38 if lod["res"] <= 1 else 20
    start = len(lod["verts"])
    normals = len(lod["normals"])
    for index in range(count):
        angle = index * math.tau / count
        base = np.array((.132 * 1.074 * math.copysign(abs(math.sin(angle))**(2/2.6), math.sin(angle)),
                         -.112 * 1.074 * math.copysign(abs(math.cos(angle))**(2/2.6), math.cos(angle)), .722))
        outward = np.array((base[0], base[1], 0.0))
        outward /= np.linalg.norm(outward)
        for corner in range(5):
            roll = corner * math.tau / 5
            n = outward * math.cos(roll) + (0, 0, math.sin(roll))
            lod["verts"].append(bag_space(base + n * .004, slung))
            lod["normals"].append(bag_space(n, slung, True))
    for index in range(count):
        for corner in range(5):
            nxt, ring = ((index + 1) % count) * 5, index * 5
            end = (corner + 1) % 5
            ids = [ring + corner, ring + end, nxt + end, nxt + corner]
            a, b, c = (np.asarray(lod["verts"][start + i]) for i in ids[:3])
            if np.cross(b-a, c-a) @ lod["normals"][normals + ids[0]] < 0:
                ids.reverse()
            lod["faces"].append(dict(v=[start+i for i in ids], n=[normals+i for i in ids],
                                     uv=[(0, 0), (0, 1), (1, 1), (1, 0)], tex=PIPING, mat=""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_io", type=Path, help="Directory containing the supplied mc_p3d.py module")
    parser.add_argument("source", type=Path, help="Folder containing the original Sked pack models")
    args = parser.parse_args()
    sys.path.insert(0, str(args.model_io.resolve()))
    import mc_p3d

    for exposed in (False, True):
        shell_model(mc_p3d, exposed)
    for role in ("pack", "slung"):
        name = f"sked_{role}.p3d"
        model = mc_p3d.read_p3d(args.source / name)
        for lod in model:
            if lod["res"] < 1000:
                fix_fabric_uv(lod)
            if lod["res"] <= 2:
                add_collar(lod, role == "slung")
            if lod["res"] <= 1:
                add_pocket_seams(lod, role == "slung")
        mc_p3d.write_p3d(ROOT / "acme_sked" / name, model)


if __name__ == "__main__":
    main()
