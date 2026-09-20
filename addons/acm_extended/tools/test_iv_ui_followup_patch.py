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
    assert '_logo ctrlSetAngle [-90' in i
    assert 'ACME_fnc_ivTrayHover' in i
    assert "(_count min 5)" in h
    assert "_count > 5" in h
    assert "private _liveSlot = ctrlPosition _bg;" in h
    assert "private _artV = missionNamespace getVariable ['ACME_iv_trayArtV',0.66];" in h
    assert 'ACME_iv_trayIconBias", 0.40' in i
    assert "private _artOffset = {" in h
    assert "private _rectAtVisualCenter = {" in h
    assert "private _spriteX = _bx + (_bw * 0.5) + (_baseOff select 0);" in h
    assert "private _spriteY = _by + (_bh * 0.5) + (_baseOff select 1);" in h
    assert "private _fanW = _bw * _fanMul;" in h
    assert "private _fanH = _bh * _fanMul;" in h
    assert "[_anchorX,_anchorY,_fanW,_fanH,_ang,_artU,_artV] call _rectAtVisualCenter" in h
    assert "private _px = _sx + _sw - _pw - _insetX;" in h
    assert "private _py = _sy + _insetY;" in h
    assert "private _fanW = _sw * 0.88;" not in h
    assert "private _fanH = _sh * 0.70;" not in h
    assert "[-0.024, -0.060, -99]" in h
    assert "[ 0.024, -0.060, -81]" in h
    assert "UI Y increases downward" in h
    assert "1 - _iconBias" not in h
    assert "['band','pad']" in h
    assert 'playSound "ACME_NARSPEAR_Open"' in g
    assert 'class ivTrayHover {};' in c
