from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def read(rel): return (ROOT / rel).read_text(encoding='utf-8-sig', errors='ignore')

def test_normal_page_navigation_clears_infusion_editor_state():
    s=read('functions/fn_skPageNavigate.sqf')
    assert s.count('ACME_infusion_pendingContext = nil;') >= 2
    assert 'ACME_SK_RequestedView' in s
    done=read('functions/fn_infusionDone.sqf')
    assert 'ACME_infusion_pendingContext = nil;' in done

def test_transfusion_nav_uses_pulsing_backings():
    s=read('../circulation/functions/fnc_openTransfusionMenu.sqf')
    c=read('config.cpp')
    assert 'ctrlCreate ["RscText",86952]' in s
    assert 'ctrlCreate ["RscText",86953]' in s
    assert 'diag_tickTime * 220' in s
    assert 'class ACME_TX_PageButton: ACME_SK_PulseButton' in c

def test_clean_hub_has_no_iv_bruise_or_track():
    s=read('functions/fn_ivMinigameStickSuccess.sqf')
    r=read('functions/fn_ivMinigameRenderMarks.sqf')
    assert 'if (!_hitB && {' in s
    assert '_mkind in ["removed", "miss"]' in r
    assert '_mkind in ["hub", "removed", "miss"]' not in r

def test_rear_arm_mirrors_and_tip_is_cursor_exact():
    s=read('functions/fn_ivMinigameTick.sqf')
    assert '_viewNow find "_rear" >= 0' in s
    assert 'private _tipX = _ux;' in s
    assert 'private _tipY = _uy;' in s
    held=s[s.index('// needle held:'):]
    assert 'call ACME_fnc_ivNeedleTip' not in held.split('if (!isNull _heldC)',1)[0]

def test_ej_is_neck_trap_window():
    b=read('functions/fn_ivLimbBounds.sqf')
    d=read('functions/fn_ivSiteData.sqf')
    i=read('functions/fn_ivMinigameInit.sqf')
    assert '_v < 0.420' in b and '_v > 0.590' in b
    assert '0.560, 0.505' in d and '0.440, 0.505' in d
    assert '[0.045, 0.085]' in i

def test_tray_rotation_hover_splay_and_spear_sound():
    i=read('functions/fn_ivMinigameInit.sqf')
    h=read('functions/fn_ivTrayHover.sqf')
    g=read('functions/fn_ivMinigameGrabNeedle.sqf')
    c=read('config.cpp')
    assert 'iv_tray_%1g_0_ca.paa' in i
    assert 'ACME_fnc_ivTrayHover' in i
    assert "(_count min 5)" in h
    assert "_count > 5" in h
    assert "private _liveSlot = ctrlPosition _bg;" in h
    assert 'ACME_iv_trayIconBias", 0.66' in i
    assert 'private _iconX = _colX + (_slotW / 2) - (_iconW / 2);' in i
    assert "ctrlSetAngle" not in h
    assert "iv_tray_%1g_%2_ca.paa" in h
    assert "_c ctrlSetPosition [_bx,_by - _rise,_bw,_bh];" in h
    assert "private _px = _sx + _insetX;" in h
    assert "private _py = _sy + _insetY;" in h
    assert "_sx + _sw - _pw - _insetX" not in h
    assert "['band','pad']" in h
    assert 'playSound "ACME_NARSPEAR_Open"' in g
    assert 'class ivTrayHover {};' in c


def test_tray_catheter_canvas_is_square_in_physical_pixels():
    i=read('functions/fn_ivMinigameInit.sqf')
    assert 'private _iconW = _iconH * _af;' in i
    assert 'private _iconW = _iconH / _af;' not in i
    assert 'private _lIconW = _lIconH * _af;' in i
    assert 'private _lIconW = _lIconH / _af;' not in i

    # _af = pixelW / pixelH. Multiplication is the only mapping that gives
    # equal pixel width/height on both ordinary and 32:9 displays.
    for width,height in ((1920,1080),(2560,1440),(5120,1440)):
        pixel_w=1/width
        pixel_h=1/height
        af=pixel_w/pixel_h
        h_ui=.1
        w_ui=h_ui*af
        assert abs((w_ui/pixel_w)-(h_ui/pixel_h)) < 1e-9


def test_iv_tray_stock_fan_is_upward_only_and_plus_is_top_left():
    h=read('functions/fn_ivTrayHover.sqf')

    # Baked textures raise only the handle. Runtime offsets also rise monotonically.
    # Real PAA silhouettes and pixel-space tile containment are tested in test_iv_tray_geometry.py.
    assert "private _rise = _sh * 0.02 * (_i + 1);" in h
    assert "_c ctrlSetPosition [_bx,_by - _rise,_bw,_bh];" in h
    assert "ctrlSetAngle" not in h

    # The >5 marker is inset from the live tray tile's top-left, never its right edge.
    assert 'private _px = _sx + _insetX;' in h
    assert 'private _py = _sy + _insetY;' in h
    assert '_sx + _sw - _pw - _insetX' not in h
    assert "ctrlCreate ['RscStructuredText',-1]" in h
    assert "[14,[1,0.55,0.55,0.56]]" in h
