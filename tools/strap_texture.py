"""Webbing that has been laid on a new line keeps its weave: the picture on a strap is mapped along it by the
length of the strap, so where a builder let the webbing out or lifted it onto a casualty (it only moved the
points, and the picture stretched with them: chevrons three times as long on the steep sides of a strap over
the HPMK, seen in game 2026-11-20) the mapping is laid out again, as many weaves to the metre as the modelled
strap has.

retexture(src_points, new_points, faces) -> faces with new (u, v), and report lines.

How: on every face of webbing the picture runs along the strap in one direction (the one in which its u or v
changes: whichever spans more over the whole strap). The face was stretched along that direction by some factor;
the coordinate's steps along the face's edges are to grow by that factor. The new coordinates are the ones
that come closest to that on all faces at once (least squares), with every piece of webbing held where it is
nearest the strap's middle, so buckles keep their place on it. A strap's loose end, a loop through a buckle
and layers lying on each other are all just faces to this. Hardware (another picture) is left as it is.
"""
import math
from collections import defaultdict

import numpy as np


def _factor(src, new, a):
    """How much a face (its first three corners) was stretched along the direction its coordinate a runs in."""
    e1, e2 = src[1] - src[0], src[2] - src[0]
    g11, g12, g22 = e1 @ e1, e1 @ e2, e2 @ e2
    det = g11 * g22 - g12 * g12
    if det < 1e-16:
        return 1.0
    # the gradient of a in the face: g = p e1 + q e2 with g.e1 = a1 - a0, g.e2 = a2 - a0
    b1, b2 = a[1] - a[0], a[2] - a[0]
    p, q = (b1 * g22 - b2 * g12) / det, (b2 * g11 - b1 * g12) / det
    g = p * e1 + q * e2
    was = np.linalg.norm(g)
    if was < 1e-6:
        return 1.0
    now = np.linalg.norm(p * (new[1] - new[0]) + q * (new[2] - new[0]))
    return float(min(8.0, max(0.125, now / was)))


def retexture(src, new, faces, is_web=lambda tex: b"web" in tex.lower()):
    """src, new: the points before and after (same order); faces: [(corners [(point, normal, u, v)], flags,
    texture, material)]. Returns (faces, report lines)."""
    src = np.array([p[:3] for p in src], float)
    new = np.array([p[:3] for p in new], float)
    faces = [([tuple(v) for v in vs], flags, tex, mat) for vs, flags, tex, mat in faces]
    web = [f for f, (vs, flags, tex, mat) in enumerate(faces) if is_web(tex)]
    if not web:
        return faces, []
    uv = np.array([(v[2], v[3]) for f in web for v in faces[f][0]])
    axis = 0 if np.ptp(uv[:, 0]) >= np.ptp(uv[:, 1]) else 1
    # One unknown for every corner of the picture: a point with the coordinates it has there. The picture repeats
    # every whole unit along the strap, so two corners at a point that differ by whole units are one corner.
    # (points at one place of the modelled strap are one point: a builder may give every face its own)
    same, ident = {}, []
    for i, q in enumerate(src):
        ident.append(same.setdefault(tuple(np.round(q, 5)), i))

    def corner(v):
        a = round(v[2 + axis], 4)
        whole = math.floor(a + 1e-9)
        return (ident[v[0]], round(v[3 - axis], 4), round(a - whole, 4)), whole

    key, rows, cols, want, weight = {}, [], [], [], []
    start, place = [], []
    lengths = [0.0, 0.0]
    for f in web:
        vs = faces[f][0]
        ids, wholes = [], []
        for v in vs:
            k, whole = corner(v)
            if k not in key:
                key[k] = len(key)
                start.append(v[2 + axis] - whole)
                place.append(src[v[0]])
            ids.append(key[k])
            wholes.append(whole)
        a = [v[2 + axis] for v in vs]
        k = _factor(src[[v[0] for v in vs[:3]]], new[[v[0] for v in vs[:3]]], a[:3])
        for i in range(len(vs)):
            j = (i + 1) % len(vs)
            rows.append(ids[i])
            cols.append(ids[j])
            want.append((a[i] - a[j]) * k - (wholes[i] - wholes[j]))
            weight.append(1.0)
            lengths[0] += abs(a[i] - a[j])
            lengths[1] += abs(a[i] - a[j]) * k
    n = len(key)
    start, place = np.array(start), np.array(place)
    # Where the picture has a seam (the webbing's edge and underside are mapped apart from its top), both sides
    # of the seam are moved alike: at a point, the corners keep their steps to each other.
    at_point = defaultdict(list)
    for (point, across, part), i in key.items():
        at_point[point].append(i)
    for ids in at_point.values():
        for i, j in zip(ids, ids[1:]):
            rows.append(i)
            cols.append(j)
            want.append(start[i] - start[j])
            weight.append(0.5)
    rows, cols, want, weight = np.array(rows), np.array(cols), np.array(want), np.array(weight)
    # the pieces that hang together in the picture: each is held at its corner nearest the strap's middle
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in zip(rows, cols):
        parent[find(i)] = find(j)
    held = {}
    for i in range(n):
        r = find(i)
        if r not in held or abs(place[i][0]) < abs(place[held[r]][0]):
            held[r] = i
    hold = np.array(sorted(held.values()))

    def times(x):
        return np.concatenate([weight * (x[rows] - x[cols]), 30.0 * x[hold]])

    def back(r):
        out = np.zeros(n)
        np.add.at(out, rows, weight * r[:len(rows)])
        np.add.at(out, cols, -weight * r[:len(rows)])
        np.add.at(out, hold, 30.0 * r[len(rows):])
        return out

    # least squares by conjugate gradients, from the mapping as it is
    b = np.concatenate([weight * want, 30.0 * start[hold]])
    x = start.copy()
    r = b - times(x)
    s = back(r)
    p = s.copy()
    gamma = s @ s
    for _ in range(20000):
        q = times(p)
        alpha = gamma / max(q @ q, 1e-30)
        x += alpha * p
        r -= alpha * q
        s = back(r)
        g2 = s @ s
        if g2 < 1e-16:
            break
        p = s + (g2 / gamma) * p
        gamma = g2
    miss = float(np.sqrt(np.mean((x[rows] - x[cols] - want) ** 2)))
    for f in web:
        vs, flags, tex, mat = faces[f]
        out = []
        for v in vs:
            k, whole = corner(v)
            a = float(x[key[k]]) + whole
            out.append((v[0], v[1], a, v[3]) if axis == 0 else (v[0], v[1], v[2], a))
        faces[f] = (out, flags, tex, mat)
    line = "   webbing: %d faces in %d pieces, the picture along %s; as laid it is %.2f times as long as modelled, and the picture with it (a step off by %.4f on average, the most a corner moved %.2f)" % (
        len(web), len(hold), "uv"[axis], lengths[1] / max(lengths[0], 1e-9), miss, float(np.abs(x - start).max()))
    return faces, [line]
