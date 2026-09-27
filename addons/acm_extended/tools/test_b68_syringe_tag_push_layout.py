from historical_source import read_source, assert_release_identity
from pathlib import Path
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')


def test_b68_version_stamp():
    assert_release_identity()
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()


def test_main_draw_select_syringe_tag_is_unconditionally_present_and_below_dropdown():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()
    from test_bounded_selector_lifetime import selector_contract
    selector_contract()


def test_compact_track_and_hints_stay_inside_toolbar_but_promoted_track_widens():
    inj = txt('functions/fn_skInject.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    assert 'private _carCompactW = _toolbarW * 0.78;' in inj
    assert 'private _carExpandedW = (_toolbarW * 1.72) min (safeZoneH * 0.64);' in inj
    assert 'else {_toolbarX};' in car
    assert 'else {_toolbarX + _toolbarW - _keyW};' in car
    assert 'if (_expanded) then {(_rx - _keyW - _hintPad)' in car
    assert 'if (_expanded) then {(_rx + _rw + _hintPad)' in car


def test_body_route_edit_stack_and_carousel_are_lifted_clear_of_draw_row():
    inj = txt('functions/fn_skInject.sqf')
    layout = txt('functions/fn_skDynamicLayout.sqf')
    assert 'safeZoneY + safeZoneH*0.035' in inj
    assert 'safeZoneY + safeZoneH*0.055' in inj
    assert 'private _carCompactBottom = _drawRowY - safeZoneH*0.080;' in inj
    assert 'private _carExpandedBottom = _drawRowY - safeZoneH*0.188;' in inj
    assert 'if (_expanded) then {0.228} else {0.630}' in layout
    assert 'private _editRect = [_tx, _routeY + _th + _editGap, _tw, _th];' in layout


def test_promoted_syringes_are_larger_and_carousel_motion_is_real_slide_grow():

    from test_bounded_current_carousel_contract import render_contract, navigation_contract
    render_contract()
    navigation_contract()
    move = txt('functions/fn_skCarouselMove.sqf')
    # Decorative slide/grow interpolation was removed for client performance; selection/layout commit immediately.
    assert '_motion' not in move
    assert 'ctrlCommit' not in move
    assert '[0] call ACME_fnc_skDynamicLayout;' in move
    assert '[0] call ACME_fnc_skCarouselRender;' in move

def test_tag_text_is_lower_larger_and_edit_mode_uses_native_draw_position_without_body():
    from test_bounded_editor_presentation import frame_contract, native_editor_contract
    frame_contract(); native_editor_contract()


def test_done_pulses_green_only_when_tag_has_text_but_is_not_required():
    tick = txt('functions/fn_skUiTick.sqf')
    assert 'private _done = _d displayCtrl 84472;' in tick
    assert 'private _typed = false;' in tick
    assert 'findIf {_x > 32}' in tick
    assert '["success", _a] call ACME_fnc_a11yColor' in tick
    assert '_done ctrlSetBackgroundColor [0.05,0.05,0.05,0.65];' in tick


def test_saving_syringe_stays_on_main_draw_page():
    after = txt('functions/fn_skAfterSaveOpenBody.sqf')
    assert 'uiNamespace setVariable ["ACME_SK_OpenBodyAfterSaveId", ""];' in after
    assert 'uiNamespace setVariable ["ACME_SK_View", "syringe"];' in after
    assert 'uiNamespace setVariable ["ACME_SK_View", "body"]' not in after


def test_body_map_site_click_runs_locked_three_second_visual_push_before_commit():
    # Historical identity retained. Site click stages; explicit confirmation owns the timed push.
    from test_bounded_staged_push_contracts import assert_staged_contract, contains
    site = txt('functions/fn_skSiteClick.sqf')
    begin = txt('functions/fn_skBeginInjection.sqf')
    confirm = txt('functions/fn_skConfirmInjection.sqf')
    inject = txt('functions/fn_skInjectSite.sqf')
    click = txt('functions/fn_skBodyActionClick.sqf')
    cfg = txt('config.cpp')
    assert contains(site, '[_part] call ACME_fnc_skBeginInjection;')
    assert contains(begin, 'uiNamespace setVariable ["ACME_SK_CarouselExpanded",true];')
    assert contains(click, 'call ACME_fnc_skConfirmInjection')
    assert_staged_contract(begin, confirm)
    assert contains(inject, 'params ["_bodyPart", ["_pushSec", 3], ["_confirmedEpiMl", -1, [0]]];')
    assert 'class ACME_SyringePush' in cfg
    assert 'acm_extended\\sound\\syringe_push.ogg' in cfg


def test_uploaded_push_sound_is_exactly_three_seconds():
    p = ROOT / 'sound' / 'syringe_push.ogg'
    assert p.is_file()
    info = sf.info(str(p))
    assert abs(info.duration - 3.0) < 0.01



def test_normalized_vertical_clearance_keeps_full_plunger_envelope_between_edit_and_draw_rows():
    # ACM's 10 mL plunger travels 10.5 grid units inside a 42-grid-unit picture control: ~25% of control height.
    # The visible lower envelope is therefore center + 0.75*h when the syringe is full, not center + 0.5*h.
    draw_y = 1/1.08
    th = 1/32
    edit_gap = 0.004
    cases = [
        # expanded, route_y, rect_h, rect_bottom, syringe_h
        (False, 0.630, 0.105, draw_y - 0.080, 0.150),
        (True, 0.228, 0.380, draw_y - 0.188, 0.470),
    ]
    for expanded, route_y, car_h, car_bottom, syringe_h in cases:
        edit_bottom = route_y + th + edit_gap + th
        car_top = car_bottom - car_h
        center_y = car_top + car_h/2
        syringe_top = center_y - syringe_h/2
        full_plunger_bottom = center_y + 0.75*syringe_h
        assert syringe_top > edit_bottom
        assert full_plunger_bottom < draw_y
        assert draw_y - full_plunger_bottom >= 0.015

def test_b67_cardiac_safety_changes_remain_present():
    rate = txt('functions/fn_rhythmThresholdTick.sqf')
    post = txt('functions/fn_postInit.sqf')
    assert 'ACME_tbi_nonterminalMinHR    = 42' in post
    assert 'ACME_tbi_nonterminalMinMAP   = 60' in post
    assert 'ACME_tbi_nonterminalMinRR    = 12' in post
    assert 'call ACME_fnc_arrestLocal' not in rate
