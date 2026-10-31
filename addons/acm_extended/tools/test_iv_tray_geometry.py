"""Measure the shipped PAA pixels, including every stock pose.

These checks catch aspect/centering/fan-bound regressions that string assertions
missed. They validate geometry and source art, not Arma's runtime UI renderer.
"""
from functools import lru_cache
from pathlib import Path
import math
import re

import numpy as np
import pytest

from paa import parse_paa, read_paa

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(None)
def silhouette(gauge, pose):
    path = ROOT / f"ui/iv/tray/iv_tray_{gauge}g_{pose}_ca.paa"
    _, alpha = read_paa(path)
    return alpha > 127


def bounds(mask):
    ys, xs = mask.nonzero()
    return np.array([xs.min(), ys.min(), xs.max() + 1, ys.max() + 1])


@pytest.mark.parametrize("gauge", [14, 16, 18, 20])
def test_rest_pose_preserves_original_catheter_proportions(gauge):
    path = ROOT / f"ui/iv/{gauge}g/base/iv_catheter_{gauge}g_base_frame_00_ready_ca.paa"
    _, alpha = read_paa(path)
    x0, y0, x1, y1 = bounds(alpha > 127)
    original_ratio = (y1 - y0) / (x1 - x0)
    x0, y0, x1, y1 = bounds(silhouette(gauge, 0))
    # Original vertical art became horizontal by a rigid quarter turn.
    assert (x1 - x0) / (y1 - y0) == pytest.approx(original_ratio, rel=.04)
    assert (x0 + x1) / 2 == pytest.approx(256, abs=2)
    assert (y0 + y1) / 2 == pytest.approx(256, abs=2)


@pytest.mark.parametrize("gauge", [14, 16, 18, 20])
def test_shipped_fan_rotates_up_from_tip_without_changing_length(gauge):
    previous_top = bounds(silhouette(gauge, 0))[1]
    rest_bottom = bounds(silhouette(gauge, 0))[3]
    principal_lengths = []
    for pose in range(5):
        mask = silhouette(gauge, pose)
        ys, xs = mask.nonzero()
        covariance = np.cov(xs, ys)
        values, vectors = np.linalg.eigh(covariance)
        vector = vectors[:, -1]
        if vector[0] < 0:
            vector *= -1
        angle = math.degrees(math.atan2(-vector[1], vector[0]))
        assert angle == pytest.approx(pose * 4, abs=.6)
        principal_lengths.append(math.sqrt(values[-1]))
        x0, y0, x1, y1 = bounds(mask)
        assert min(x0, y0) > 1 and max(x1, y1) < 511
        assert y1 <= rest_bottom + 1
        if pose:
            assert y0 < previous_top
        previous_top = y0
        # Tip stays in the same region, while the handle moves upward.
        assert mask[250:263, 30:40].any()
        kind, mips = parse_paa(ROOT / f"ui/iv/tray/iv_tray_{gauge}g_{pose}_ca.paa")
        assert kind == 0xFF05
        assert [(w & 0x7FFF, h) for w, h, _ in mips] == [(s, s) for s in (512, 256, 128, 64, 32, 16, 8, 4)]
    assert max(principal_lengths) / min(principal_lengths) < 1.025


def tray_dimensions(slot_w, slot_h, aspect, bias):
    # Pull production limits from SQF so this test follows changed dimensions.
    init = (ROOT / "functions/fn_ivMinigameInit.sqf").read_text()
    width_limit, height_limit = map(float, re.search(
        r"private _iconH = .*?_slotW \* ([\d.]+).*?_slotH \* ([\d.]+)", init
    ).groups())
    height = min(slot_h * 2.45, slot_w * width_limit / aspect, slot_h * height_limit)
    width = height * aspect
    # B233: user removed fan and vertical bias. Tile center is invariant.
    assert 'private _iconY = _ry + (_slotH / 2) - (_iconH / 2);' in init
    return slot_w / 2 - width / 2, slot_h / 2 - height / 2, width, height


@pytest.mark.parametrize("screen", [(1920, 1080), (2560, 1440), (3440, 1440), (5120, 1440)])
@pytest.mark.parametrize("bias", [0, .34, .66, 1])
def test_actual_pixels_stay_inside_tile_for_every_pose_and_saved_bias(screen, bias):
    # Test full-screen normalized coordinates AND Arma's 4:3 reference-space pixel ratio.
    # Scale cancels in the invariant; use a large tile to expose rounding issues.
    for pw, ph in ((1 / screen[0], 1 / screen[1]), (.75 / 1080, 1 / 1080)):
        aspect = pw / ph
        sw, sh = .25, .25 * aspect * .92
        bx, by, bw, bh = tray_dimensions(sw, sh, aspect, bias)
        assert bw / pw == pytest.approx(bh / ph)
        # Only the centered resting needle is rendered; old fan assets stay available but hidden.
        u0, v0, u1, v1 = bounds(silhouette(14, 0)) / 512
        assert 0 <= bx + u0 * bw < bx + u1 * bw <= sw
        assert 0 <= by + v0 * bh < by + v1 * bh <= sh
        assert bx + bw/2 == pytest.approx(sw/2)
        assert by + bh/2 == pytest.approx(sh/2)
