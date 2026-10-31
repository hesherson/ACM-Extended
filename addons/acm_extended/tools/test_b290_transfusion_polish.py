"""Consume production native geometry for paired controls and common corner shape.

This verifies authored bounds and executes the existing pixel-slice renderer;
actual font rasterization and pointer acceptance still require Arma.
"""
from pathlib import Path
import re

import pytest

from source_scan import lex, matching, split_args
from test_b273_transfusion_layout import authored_place, fixed_layout, overlap
from test_b278_transfusion_geometry import test_corner_radius_uses_identical_whole_pixels_on_all_nine_slices as _verify_pixel_corners

ROOT = Path(__file__).resolve().parents[3]
FUN = ROOT / "addons/acm_extended/functions"


@pytest.mark.parametrize("aspect", [4 / 3, 16 / 9, 21 / 9, 32 / 9])
@pytest.mark.parametrize("pair", ["tabs", "infusion", "service", "prepare", "confirm_bag", "confirm_infusion"])
def test_each_authored_pair_has_equal_bounds_and_one_shared_gap(aspect, pair):
    fixed = fixed_layout()
    if pair == "tabs":
        left, right = fixed[86214], fixed[86144]
    elif pair == "infusion":
        left, right = fixed[86131], fixed[86172]
    elif pair == "service":
        left, right = authored_place(86170), authored_place(86143)
    elif pair == "prepare":
        left, right = authored_place(86141), authored_place(86121)
    else:
        occurrence = 0 if pair == "confirm_infusion" else 1
        left, right = authored_place(86197, occurrence), authored_place(86198, occurrence)
    canvas = min(aspect, 1.7777778)
    physical = [tuple(v * canvas if i in [0, 2] else v for i, v in enumerate(rect)) for rect in [left, right]]
    assert physical[0][1:] == pytest.approx(physical[1][1:])
    assert physical[1][0] - (physical[0][0] + physical[0][2]) == pytest.approx(canvas * .008)
    assert not overlap(*physical)


def frame_radii(source):
    tokens = lex(source)
    pairs = matching(tokens)
    for i, token in enumerate(tokens):
        if token.value != "ACME_fnc_transfusionRoundedFrame":
            continue
        assert tokens[i - 1].value == "call" and tokens[i - 2].value == "]"
        end = i - 2
        begin = pairs[end]
        args = split_args(tokens, begin + 1, end, pairs)
        assert len(args[3]) == 1 and args[3][0].kind == "number"
        yield float(args[3][0].value)


def test_every_live_frame_consumer_uses_the_same_corner_radius():
    radii = [radius for name in ["layoutTransfusionMenu", "updateTransfusionCards"]
             for radius in frame_radii((FUN / f"fn_{name}.sqf").read_text())]
    assert len(radii) == 6
    default = re.search(r'\["_radius",([\d.]+)\]', (FUN / "fn_transfusionRoundedFrame.sqf").read_text())
    assert set(radii) == {float(default.group(1))} == {.007}
    # The authored first-frame window must match the runtime window, too.
    dialog = (ROOT / "addons/circulation/TransfusionMenu_Dialog.hpp").read_text()
    corner = dialog.split("class Slice_0:", 1)[1].split("};", 1)[0]
    assert 'w = QUOTE(safeZoneH * 0.007 * pixelW / pixelH)' in corner
    assert 'h = QUOTE(safeZoneH * 0.007)' in corner


@pytest.mark.parametrize("width,height", [(1280, 960), (1920, 1080), (3440, 1440), (5120, 1440)])
def test_common_radius_produces_equal_pixel_corners_at_each_supported_aspect(width, height):
    _verify_pixel_corners(width, height)


def test_action_labels_keep_zero_pressed_offset_and_obsolete_remove_stays_hidden():
    styles = (ROOT / "addons/acm_extended/TransfusionMenu_Styles.hpp").read_text()
    dialog = (ROOT / "addons/circulation/TransfusionMenu_Dialog.hpp").read_text()
    config = (ROOT / "addons/acm_extended/config.cpp").read_text()
    def class_body(source, name):
        fragment = source[source.index(f"class {name}:"):]
        tokens = lex(fragment)
        start = next(i for i, token in enumerate(tokens) if token.value == "{")
        end = matching(tokens)[start]
        return fragment[tokens[start].offset:tokens[end].offset]
    bases = [class_body(styles, "ACME_TransfusionActionButton"),
             class_body(dialog, "StopTransfusionButton"),
             class_body(config, "ACME_InjectMedicationBagButton")]
    for base in bases:
        for key in ["offsetX", "offsetY", "offsetPressedX", "offsetPressedY", "borderSize"]:
            assert re.search(rf"\b{key}\s*=\s*0\s*;", base)
    layout = (FUN / "fn_layoutTransfusionMenu.sqf").read_text()
    assert 'forEach [86008,86091,86180,86181,86182];' in layout
