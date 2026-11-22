"""Fit separate thin cloth and laminated-paper meshes to the lid's molded face."""

from collections import defaultdict
from dataclasses import dataclass
import math
import random

import numpy as np
from PIL import Image
from build_hardigg_sheet import SHEETS, sheet, strips
from build_hardigg_tape import SCALE, lift, tape_image
from build_hardigg_wear import inventory_card, lid_tape

ATLAS_SIZE = 2048
TILE_SIZE = 512
FRONT_SCALE = np.array((.526 / 1000, .832 / 1600))
CARD_CENTER = (528, 785)
CARD_ANGLE = 1
TEXTURE = "lid_artwork_0_ca.paa"


def rotated(points, angle, center):
    cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return points @ np.array(((cosine, -sine), (sine, cosine))) + center


@dataclass
class Piece:
    center: tuple
    angle: float
    image: Image.Image
    damage: str
    tile: tuple
    over_card: bool = False
    size: tuple = None                                       # in lid pixels; the image holds SCALE texels for each
    maps: dict = None                                        # tape: its normal map, specular map and relief
    card: tuple = None                                       # the sheet a strip holds: centre, turn, half size


def artwork(index, glyphs, handwriting, quantity):
    """Lay the pieces of one chest design out on its own atlas, SCALE texels for each lid pixel."""
    rng = random.Random(36400 + index * 31)
    images = []
    spec = SHEETS.get(index)
    for order, (pos, length, width, angle, color, label, damage) in enumerate(lid_tape(index)):
        if spec:                                             # tape that lay where the inventory sheet is now
            pos = spec.get("moved", {}).get(order, pos)
        tape = tape_image(length, width, rng, color, label, glyphs, damage)
        images.append((pos, angle, tape["image"], damage, False, (length, width), tape, None))
    if spec:
        made = sheet(index)
        centre, turn = spec["place"]
        card = (centre, turn, made["size"][0] / 2 + 6, made["size"][1] / 2 + 4)
        images.insert(0, (centre, turn, made["image"], "sleeve", False, made["size"], made, None))
        # Independently modeled strips overlap the sheet and follow the lid ribs.
        for offset, length, width, angle, damage, colour in strips(index):
            center = tuple(rotated(np.array(offset), turn, centre))
            tape = tape_image(round(length), width, rng, colour, "", glyphs, damage)
            images.append((center, turn + angle, tape["image"], damage, True, (round(length), width), tape, card))
    x = y = 12
    row_height = 0
    pieces = []
    for pos, angle, image, damage, over_card, size, maps, card in images:
        width, height = (round(n * SCALE) for n in size)
        if x + width + 12 > ATLAS_SIZE:
            x, y, row_height = 12, y + row_height + 12, 0
        if y + height + 12 > ATLAS_SIZE:
            raise ValueError(f"Lid artwork of finish {index} exceeds its atlas")
        pieces.append(Piece(pos, angle, image, damage, (x, y, width, height), over_card, size, maps, card))
        row_height = max(row_height, height)
        x += width + 12
    return pieces


def artwork_texture(pieces):
    canvas = Image.new("RGBA", (ATLAS_SIZE, ATLAS_SIZE))
    for piece in pieces:
        x, y, width, height = piece.tile
        image = piece.image.resize((width, height), Image.Resampling.LANCZOS)
        canvas.paste(image, (x, y))
    return canvas


class LidSurface:
    """Project along +Y onto a particular visual LOD of the actual lid."""

    CELL = .022

    def __init__(self, lod):
        self.cells = defaultdict(list)
        positions = np.asarray(lod["verts"])
        for face in lod["faces"]:
            ids = face["v"]
            if not all(i in lod["sels"]["lid"] and i in lod["sels"]["camo"] for i in ids):
                continue
            polygon = positions[ids]
            if polygon[:, 1].min() <= .139:
                continue
            for corner in range(1, len(polygon) - 1):
                triangle = polygon[[0, corner, corner + 1]]
                points = triangle[:, [0, 2]]
                a, b = points[1:] - points[0]
                determinant = a[0] * b[1] - a[1] * b[0]
                if abs(determinant) < 1e-10:
                    continue
                inverse = np.array(((b[1], -b[0]), (-a[1], a[0]))) / determinant
                depth = triangle[:, 1]
                low, high = np.floor(np.array((points.min(axis=0), points.max(axis=0))) / self.CELL).astype(int)
                for x in range(low[0], high[0] + 1):
                    for z in range(low[1], high[1] + 1):
                        self.cells[x, z].append((points[0], inverse, depth))
        # Batch all candidate triangles in each cell for the per-point query.
        self.cells = {key: tuple(np.asarray(values) for values in zip(*rows)) for key, rows in self.cells.items()}

    def depth(self, x, z):
        origin, inverse, depth = self.cells[math.floor(x / self.CELL), math.floor(z / self.CELL)]
        weights = (inverse @ (np.array((x, z)) - origin)[..., None])[..., 0]
        bary = np.column_stack((1 - weights.sum(axis=1), weights))
        valid = (bary >= -1e-6).all(axis=1)
        if not valid.any():
            raise ValueError(f"Artwork projects outside the lid at {x:.4f}, {z:.4f}")
        return float((bary[valid] * depth[valid]).sum(axis=1).max())


def piece_mesh(piece, surface, detail):
    width, height = piece.size or piece.image.size
    tape = piece.damage != "sleeve"
    step = (10, 19, 34)[detail - 1]
    # The molded ribs run horizontally. The sleeve needs the same vertical fit as
    # the tape, but can span long horizontal stretches with fewer vertices.
    along = step if tape else step * 3
    columns = np.linspace(0, 1, max((12, 8, 5)[detail - 1], math.ceil(width / along)) + 1)
    rows = np.linspace(0, 1, max((6, 4, 3)[detail - 1], math.ceil(height / step)) + 1)
    middle = (len(rows) - 1) // 2
    split = piece.damage == "split"
    tear_end = np.searchsorted(columns, .52)
    points, uv, faces = [], [], []
    atlas_x, atlas_y, atlas_w, atlas_h = piece.tile

    for column, u in enumerate(columns):
        for row, v in enumerate(rows):
            # A ripped tip is a tear in the picture of the strip (build_hardigg_tape.py), not a gap in the mesh.
            px = (u - .5) * width
            py = (v - .5) * height
            distance = .0011
            if tape:
                wrinkle = max(0, math.sin(u * 38 + v * 5 + .4 * math.sin(v * 9)))**7
                distance += .0006 * wrinkle * math.sin(v * math.pi)
                if piece.maps and "relief" in piece.maps:    # the swell under each pucker of the strip
                    distance += lift(piece.maps["relief"], u, v)
                tip = max(0, (u - .82) / .18)
                if piece.damage == "lift":
                    distance += .009 * tip**2 * (.28 + .72 * v)
                if piece.damage == "fold":
                    roll = tip * (1 - .58 * v)
                    px -= .12 * width * roll**2
                    distance += .007 * roll**1.5
                if split:
                    distance += .0018 * max(0, 1 - 2*u) * math.exp(-((v-.5)/.21)**2)
            else:
                place, slope, rise = piece.maps["fold"] if piece.maps else (.54, .034, .00038)
                crease = v - place + slope * (u - .5)
                distance += rise * math.exp(-(crease / .047)**2)
            design_x, design_y = rotated(np.array((px, py)), piece.angle, piece.center)
            x, z = np.array((.263, .832)) - np.array((design_x, design_y)) * FRONT_SCALE
            if piece.over_card:                              # raised where it lies on the sheet it holds
                centre, turn, half_w, half_h = piece.card
                card_x, card_y = rotated(np.array((design_x, design_y)), -turn,
                                         -np.array(rotated(np.array(centre), -turn, (0, 0))))
                if abs(card_x) < half_w and abs(card_y) < half_h:
                    distance += .0012
            points.append((x, surface.depth(x, z) + distance, z))
            uv.append(((atlas_x + .65 + u * (atlas_w - 1.3)) / ATLAS_SIZE,
                       1 - (atlas_y + .65 + v * (atlas_h - 1.3)) / ATLAS_SIZE))

    stride = len(rows)
    for i in range(len(columns) - 1):
        for j in range(stride - 1):
            a = i * stride + j
            b = a + stride
            faces.extend(((a, a + 1, b), (a + 1, b + 1, b)))

    # A thin modeled edge and a backing keep the lifted ends visible at grazing angles.
    front_count = len(points)
    positions = np.asarray(points)
    edges = set()
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1]):
            if (b, a) in edges:
                edges.remove((b, a))
            else:
                edges.add((a, b))
    backing = positions.copy()
    backing[:, 1] -= .00042 if tape else .00058
    points.extend(map(tuple, backing))
    uv += uv.copy()
    if tape and detail < 3:
        for a, b, c in faces.copy():
            if max(a, b, c) // stride >= len(columns) * .8 or (split and min(a, b, c) // stride < tear_end):
                faces.append((c + front_count, b + front_count, a + front_count))
    faces.extend((b, a, a + front_count, b + front_count) for a, b in sorted(edges))
    used = sorted({i for face in faces for i in face})
    indices = {old: new for new, old in enumerate(used)}
    front = 2 * (len(columns) - 1) * (stride - 1)            # the faces of the face of the piece come first
    return ([points[i] for i in used], [uv[i] for i in used], [tuple(indices[i] for i in face) for face in faces],
            front)


def add_lid_artwork(lod, variants):
    surface = LidSurface(lod)
    selected = lod["sels"].setdefault("lid_artwork", set())
    for pieces in variants:
        for piece in pieces:
            points, uv, faces, front = piece_mesh(piece, surface, round(lod["res"]))
            start = len(lod["verts"])
            lod["verts"].extend(points)
            vertices = set(range(start, start + len(points)))
            selected.update(vertices)
            lod["sels"]["lid"].update(vertices)
            # The face of a piece is smooth, so that its normal map can do the creasing; edges and backing are flat.
            positions = np.asarray(points)
            flat, smooth = {}, np.zeros((len(points), 3))
            for k, ids in enumerate(faces):
                a, b, c = positions[list(ids[:3])]
                normal = np.cross(b - a, c - a)
                length = np.linalg.norm(normal)
                if length < 1e-11:
                    continue
                flat[k] = normal / length
                if k < front:
                    smooth[list(ids)] += normal
            first_normal = len(lod["normals"])
            lengths = np.linalg.norm(smooth, axis=1, keepdims=True)
            lod["normals"].extend(map(tuple, np.where(lengths > 0, smooth / np.maximum(lengths, 1e-20), (0., 1., 0.)).tolist()))
            for k, ids in enumerate(faces):
                if k not in flat:
                    continue
                if k < front:
                    normals = [first_normal + i for i in ids]
                else:
                    normals = [len(lod["normals"])] * len(ids)
                    lod["normals"].append(tuple(flat[k]))
                lod["faces"].append(dict(v=[start + i for i in ids], n=normals,
                                         uv=[uv[i] for i in ids], tex=TEXTURE, mat=""))
