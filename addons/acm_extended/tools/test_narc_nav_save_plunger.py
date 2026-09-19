from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return (ROOT/rel).read_text(encoding='utf-8', errors='ignore')

def test_save_is_in_place_and_immediate():
    s=read('functions/fn_skCompoundSave.sqf')
    assert 'closeDialog 0' not in s
    assert 'ACME_fnc_skOpenDraw' not in s
    assert '[] call ACME_fnc_skCompoundBegin;' in s
    assert '0.45] call CBA_fnc_waitAndExecute;' in s

def test_size_switch_is_in_place():
    p=read('functions/fn_skPickSize.sqf')
    a=read('functions/fn_skApplySize.sqf')
    assert 'closeDialog 0' not in p
    assert 'ACME_fnc_skOpenDraw' not in p
    assert 'ACME_fnc_skApplySize' in p
    assert 'for "_id" from 84010 to 84021' in a
    assert 'ACM_circulation_SyringeDraw_Ctrl_LimitTop' in a

def test_three_page_navigation_and_dual_buttons():
    i=read('functions/fn_skInject.sqf')
    sv=read('functions/fn_skSetView.sqf')
    nav=read('functions/fn_skPageNavigate.sqf')
    assert '84152' in i and '84157' in i
    assert '"< Transfuse"' in i and '"Body Map >"' in i
    assert '"< Narc Box"' in sv and '"Transfuse >"' in sv
    assert 'ACM_circulation_fnc_openTransfusionMenu' in nav
    assert 'ACME_SK_RequestedView' in nav

def test_push_uses_frame_interpolation():
    c=read('functions/fn_skConfirmInjection.sqf')
    r=read('functions/fn_skCarouselRender.sqf')
    assert 'ACME_SK_PushAnimPFH' in c
    assert 'private _e = _t * _t * (3 - (2 * _t));' in c
    assert 'ctrlCommit _pushSec' not in c
    assert 'if !(_normalPushAnimActive && {_slot == 2})' in r

def test_chrom_duplicate_reference_restored():
    t=read('functions/fn_visualFxTick.sqf')
    assert '_acmKetChrom ppEffectEnable false;' in t
    assert 'former dose/HR-synchronous contribution numerically below' in t


def test_plunger_drag_stays_sticky_to_actual_control_and_releases_on_second_click():
    compound=read('functions/fn_skCompoundBegin.sqf')
    waste=read('functions/fn_skWasteBegin.sqf')
    toggle=read('functions/fn_skWasteToggleMove.sqf')
    end=read('functions/fn_skWasteEnd.sqf')
    assert 'setMousePosition [_plungerX + (_plungerW / 2), _mouseYClamped];' in compound
    assert 'setMousePosition [_plungerX + (_plungerW / 2), _mouseYClamped];' in waste
    assert 'setMousePosition [_px + (_pw / 2), _py + (_ph / 2)];' in toggle
    assert 'Click again to release the plunger' in toggle
    assert 'ACME_SK_PlungerReleaseEH' not in toggle
    assert 'displayAddEventHandler ["MouseButtonDown"' not in toggle
    assert 'ACME_SK_PlungerReleaseEH' not in end


def test_nav_buttons_are_narrow_and_action_spans_both():
    inj=read('functions/fn_skInject.sqf')
    body=read('functions/fn_skBodyActionRender.sqf')
    assert 'private _navW = _tw * 0.72;' in inj
    assert 'private _actionW = ((_vr select 0) + (_vr select 2)) - _actionX;' in body

def test_push_duration_uses_separate_suggestion_and_blank_default():
    body=read('functions/fn_skBodyActionRender.sqf')
    start=read('functions/fn_hardcorePushStart.sqf')
    assert '_durHint ctrlSetText _suggested;' in body
    assert '_durEdit ctrlSetText _suggested;' not in body
    assert '_validPushTime' in body
    assert 'private _dur = 3;' in start
    assert 'if (_raw != "") then {' in start
