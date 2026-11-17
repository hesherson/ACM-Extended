"""Fit separate thin cloth and laminated-paper meshes to the lid's molded face."""

from collections import defaultdict
from dataclasses import dataclass
import math
import random

import numpy as np
from PIL import Image

from build_hardigg_wear import inventory_card, lid_tape, tape_material

ATLAS_SIZE = 2048
TILE_SIZE = 512
FRONT_SCALE = np.array((.526 / 1000, .832 / 1600))
CARD_CENTER = (528, 889)
CARD_ANGLE = 2
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


def artwork(index):
    """Allocate one padded atlas tile per chest design, all sharing one model section."""
    rng = random.Random(36400 + index * 31)
    images = [(pos, angle, tape_material(length, width, rng, color, label), damage, False)
              for pos, length, width, angle, color, label, damage in lid_tape(index)]
    if index == 2:
        images.insert(0, (CARD_CENTER, CARD_ANGLE, inventory_card(), "sleeve", False))
        # Independently modeled strips overlap the sleeve and follow the lid ribs.
        for offset, length, width, angle, damage in (
            ((-6, -210), 479, 41, 1, "fold"), ((4, 207), 472, 42, -1, "split"),
            ((-248, -1), 385, 40, 90, "lift"), ((246, -5), 385, 43, -89, "fold"),
        ):
            center = tuple(rotated(np.array(offset), CARD_ANGLE, CARD_CENTER))
            images.append((center, CARD_ANGLE + angle,
                           tape_material(length, width, rng, (127, 129, 119), ""), damage, True))
    offset_x, offset_y = index % 4 * TILE_SIZE, index // 4 * TILE_SIZE
    x = y = 12
    row_height = 0
    pieces = []
    for pos, angle, image, damage, over_card in images:
        width, height = (round(n * .64) for n in image.size)
        if x + width + 12 > TILE_SIZE:
            x, y, row_height = 12, y + row_height + 12, 0
        if y + height + 12 > TILE_SIZE:
            raise ValueError(f"Lid artwork tile {index} exceeds its atlas allocation")
        pieces.append(Piece(pos, angle, image, damage, (offset_x + x, offset_y + y, width, height), over_card))
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
    width, height = piece.image.size
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
            across = v
            if split and column < tear_end:
                # A tapering gap with uneven fibers, cut into the actual mesh.
                opening = .14 * (1 - u / columns[tear_end]) * (1 + .25 * math.sin(u * 61))
                across += (-1 if row <= middle else 1) * opening * (1 - abs(v * 2 - 1))
            px = (u - .5) * width
            py = (across - .5) * height
            if tape:
                px += (math.sin(v * 26 + u * 6) + math.sin(v * 67)) * 2.3 * abs(2*u-1)**8
                py += (math.sin(u * 57 + v) + math.sin(u * 103 - v * 3)) * 1.35 * abs(2*v-1)**4
            distance = .00075
            if tape:
                wrinkle = max(0, math.sin(u * 38 + v * 5 + .4 * math.sin(v * 9)))**7
                distance += .0011 * wrinkle * (.35 + .65 * math.sin(v * math.pi))
                tip = max(0, (u - .82) / .18)
                if piece.damage == "lift":
                    distance += .009 * tip**2 * (.28 + .72 * v)
                if piece.damage == "fold":
                    roll = tip * (1 - .58 * v)
                    px -= .12 * width * roll**2
                    distance += .007 * roll**1.5
                if split:
                    distance += .003 * max(0, 1 - 2*u) * math.exp(-((v-.5)/.21)**2)
            else:
                crease = v - .54 + .034 * (u - .5)
                distance += .0028 * math.exp(-(crease / .047)**2)
                distance += .0020 * v**8 * abs(2*u-1)**6
            design_x, design_y = rotated(np.array((px, py)), piece.angle, piece.center)
            x, z = np.array((.263, .832)) - np.array((design_x, design_y)) * FRONT_SCALE
            if piece.over_card:
                card_x, card_y = rotated(np.array((design_x, design_y)), -CARD_ANGLE,
                                         -np.array(rotated(np.array(CARD_CENTER), -CARD_ANGLE, (0, 0))))
                if abs(card_x) < 257 and abs(card_y) < 217:
                    distance += .0026 + .0020 * math.exp(-((card_y + .034*card_x - 17) / 21)**2)
            points.append((x, surface.depth(x, z) + distance, z))
            uv.append(((atlas_x + .65 + u * (atlas_w - 1.3)) / ATLAS_SIZE,
                       1 - (atlas_y + .65 + v * (atlas_h - 1.3)) / ATLAS_SIZE))

    stride = len(rows)
    for i in range(len(columns) - 1):
        for j in range(stride - 1):
            if split and i < tear_end and j == middle:
                continue
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
    return [points[i] for i in used], [uv[i] for i in used], [tuple(indices[i] for i in face) for face in faces]


def add_lid_artwork(lod, variants):
    surface = LidSurface(lod)
    selected = lod["sels"].setdefault("lid_artwork", set())
    for pieces in variants:
        for piece in pieces:
            points, uv, faces = piece_mesh(piece, surface, round(lod["res"]))
            start = len(lod["verts"])
            lod["verts"].extend(points)
            vertices = set(range(start, start + len(points)))
            selected.update(vertices)
            lod["sels"]["lid"].update(vertices)
            for ids in faces:
                a, b, c = np.array([points[i] for i in ids[:3]])
                normal = np.cross(b - a, c - a)
                length = np.linalg.norm(normal)
                if length < 1e-11:
                    continue
                normal_index = len(lod["normals"])
                lod["normals"].append(tuple(normal / length))
                lod["faces"].append(dict(v=[start + i for i in ids], n=[normal_index] * len(ids),
                                         uv=[uv[i] for i in ids], tex=TEXTURE, mat=""))
