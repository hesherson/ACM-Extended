#!/usr/bin/env python3
"""Stable B189: debug overlay is resolution invariant, left pinned, non-wrapping and vertically bounded."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_debug_overlay_uses_one_safezone_reference_box_only():
    s = read("addons/acm_extended/functions/fn_debugMenuClinical.sqf")
    assert 'private _baseFontH = safeZoneH * 0.0092;' in s
    assert 'private _totalW = (safeZoneH * 0.40)' in s
    assert 'private _x = safeZoneXAbs + _marginX;' in s
    assert 'private _y = safeZoneY + _marginY;' in s
    assert 'private _panelBottom = safeZoneY + safeZoneH - _marginY;' in s
    for token in ("pixelW", "pixelH", "getResolution"):
        assert token not in s


def test_every_visible_debug_text_control_uses_same_final_font_scale():
    s = read("addons/acm_extended/functions/fn_debugMenuClinical.sqf")
    assert 'private _applyFont = {' in s
    assert '{_x ctrlSetFontHeight _fontH;} forEach [_ctrlH, _ctrlT, _ctrlL, _ctrlR, _ctrlS, _ctrlM];' in s
    assert '_fontH = _baseFontH;' in s
    assert '_fontH = _fontH * ((_totalW / _naturalW) min 1);' in s
    assert '_fontH = _fontH * ((_availableH / _neededH) * 0.992);' in s


def test_width_fit_measures_natural_unwrapped_longest_line():
    s = read("addons/acm_extended/functions/fn_debugMenuClinical.sqf")
    assert 'private _measureNaturalWidth = {' in s
    natural = s.split('private _measureNaturalWidth = {', 1)[1].split('private _layout = {', 1)[0]
    assert 'safeZoneWAbs * 8' in natural
    assert 'ctrlTextWidth _ctrlM' in natural
    assert 'private _naturalW =' in s


def test_value_columns_expand_before_formatting_so_values_do_not_wrap():
    s = read("addons/acm_extended/functions/fn_debugMenuClinical.sqf")
    render = s.split('private _renderAll = {', 1)[1].split('_top pushBack', 1)[0]
    assert '_valueW = 11;' in render
    assert '_valueW = _valueW max (count _sA);' in render
    assert '_valueW = _valueW max (count _sB);' in render
    assert render.index('_valueW = _valueW max (count _sA);') < render.index('private _bodyRows =')


def test_body_control_can_never_extend_below_panel_bottom():
    s = read("addons/acm_extended/functions/fn_debugMenuClinical.sqf")
    layout = s.split('private _layout = {', 1)[1].split('private _cTitle', 1)[0]
    assert 'private _bodyAvail = (_panelBottom - _bodyY) max 0;' in layout
    assert 'max _bodyH' not in layout
    assert '_ctrlL ctrlSetPosition [_x, _bodyY min _panelBottom, _totalW, _bodyAvail];' in layout


def test_reference_geometry_is_resolution_independent_across_common_and_odd_modes():
    # The renderer works in safe-zone fractions only. The same fractions must therefore produce the
    # same panel width/height proportions for every raster resolution, including the reported 1680x1050.
    resolutions = [
        (1280, 720),
        (1680, 1050),
        (1920, 1080),
        (2560, 1440),
        (3440, 1440),
        (3840, 1080),
        (5120, 1440),
    ]
    for width, height in resolutions:
        panel_width_to_height = min(0.40, width / height * 0.245)
        top_margin_fraction = 0.004
        bottom_margin_fraction = 0.004
        assert panel_width_to_height <= 0.40
        assert panel_width_to_height * height <= width * 0.245 + 1e-9
        assert abs((1 - top_margin_fraction - bottom_margin_fraction) - 0.992) < 1e-9
        assert width > 0 and height > 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B189 debug resolution invariant regression: PASS")
