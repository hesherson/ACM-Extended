from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')


def test_b64_version_stamp():
    assert_release_identity()
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()


def test_qephillips_is_wired_as_the_tag_font_without_redistributing_font_files():
    from test_bounded_tag_font_fallback import font_contract, no_outline_fonts
    from test_bounded_tag_line_layout import layout_contract
    font_contract(); no_outline_fonts(); layout_contract()


def test_tag_edit_fields_have_no_black_rect_and_text_is_larger():
    from test_bounded_editor_presentation import frame_contract, native_editor_contract
    frame_contract(); native_editor_contract()


def test_main_draw_always_has_select_syringe_tag_left_of_native_syringe():
    inj = txt('functions/fn_skInject.sqf')
    pending = txt('functions/fn_skPendingTagRender.sqf')
    pick_flush = txt('functions/fn_skPickFlush.sqf')
    waste = txt('functions/fn_skWasteDraw.sqf')
    assert '_pendingTagBtn ctrlSetText "Select Syringe Tag";' in inj
    assert '_button ctrlSetText "Select Syringe Tag";' in pending
    assert 'private _btnX = _x - _btnW - _gap;' in pending
    assert '_button ctrlShow _showSetup;' in pending and '_button ctrlEnable _showSetup;' in pending
    assert '[10, _patient, _bodyPart, _flushClass]' in pick_flush
    assert 'ACME_fnc_skApplyPendingTag' in waste


def test_tag_dropdowns_remain_wide_clickable_and_same_color_reselectable():
    from test_bounded_tag_dropdowns import dropdown_contract, geometry_contract
    dropdown_contract()
    geometry_contract()


def test_edit_syringe_tag_is_attached_to_full_route_row():
    car = txt('functions/fn_skCarouselRender.sqf')
    assert '"Edit Syringe Tag"' in car
    assert 'private _ivRect = ctrlPosition (_d displayCtrl 84151);' in car
    assert 'private _imRect = ctrlPosition (_d displayCtrl 84154);' in car
    assert '_btnW = ((_imRect select 0) + (_imRect select 2)) - _btnX;' in car
    assert '_btnY = (_ivRect select 1) + (_ivRect select 3) + safeZoneH*0.004;' in car


def test_gradient_is_completely_removed():
    inj = txt('functions/fn_skInject.sqf')
    layout = txt('functions/fn_skDynamicLayout.sqf')
    setview = txt('functions/fn_skSetView.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    for s in (inj, layout, setview, car):
        assert '84482' not in s
        assert '84496' not in s
    assert 'center-weighted gray gradient' not in layout


def test_carousel_track_is_narrow_but_promoted_syringe_scale_is_restored():
    inj = txt('functions/fn_skInject.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    move = txt('functions/fn_skCarouselMove.sqf')
    assert 'private _carCompactW = _toolbarW * 0.90;' in inj
    assert 'private _carExpandedW = _toolbarW * 0.90;' in inj
    assert 'safeZoneH * (if (_expanded) then {0.390} else {0.145})' in car
    assert 'private _fullH = safeZoneH*0.390;' in move
    assert 'private _capW = _rw' not in car
    assert 'private _cap = _rw' not in car


def test_carousel_workspace_stays_between_edit_row_and_draw_row():
    inj = txt('functions/fn_skInject.sqf')
    layout = txt('functions/fn_skDynamicLayout.sqf')
    assert 'private _carBottom = _drawRowY - safeZoneH*0.018;' in inj
    assert 'private _editRowY = _routeY + _th + safeZoneH*0.004;' in layout
    assert 'private _zoneY = _editRowY + _th + safeZoneH*0.006;' in layout
    assert 'private _zoneBottom = _viewY - safeZoneH*0.016;' in layout


def test_carousel_hitboxes_cannot_cover_edit_or_draw_rows():
    car = txt('functions/fn_skCarouselRender.sqf')
    assert 'private _hoverTop =' in car
    assert 'private _hoverBottom = (_drawForBounds select 1) - safeZoneH*0.012;' in car
    assert 'private _hitY = (_y-_padY) max _hoverTop;' in car
    assert 'private _hitBottom = (_y+_h+_padY) min _hoverBottom;' in car
    assert 'private _activeHitBottom = (_centerY+_hitH/2) min _hoverBottom;' in car


def test_ad_arrow_key_hints_exist_scale_and_hide_in_editor():
    inj = txt('functions/fn_skInject.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    setview = txt('functions/fn_skSetView.sqf')
    for i in range(84700, 84704):
        assert str(i) in inj and str(i) in car and str(i) in setview
    assert 'ctrlSetText "A"' in inj and 'ctrlSetText "D"' in inj
    assert 'ctrlSetText "◀"' in inj and 'ctrlSetText "▶"' in inj
    assert 'private _hintScale = if (_expanded) then {1.20} else {1.0};' in car
    assert 'ctrlShow (!_editMode)' in car


def test_patient_name_uses_actual_screen_to_head_gap():
    layout = txt('functions/fn_skDynamicLayout.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    assert 'private _screenTop = safeZoneY + safeZoneH*0.004;' in layout
    assert 'private _headTop = (_bodyRect select 1) + (_bodyRect select 3)*0.055;' in layout
    assert 'safeZoneX + safeZoneW/2 - (_hr select 2)/2' in layout
    assert 'ctrlSetText (if (isNull _p) then {"Patient"} else {name _p})' in car


def test_carousel_motion_is_one_physical_slide_then_zero_duration_rebind():
    move = txt('functions/fn_skCarouselMove.sqf')
    pick = txt('functions/fn_skCarouselPick.sqf')
    assert 'private _motion = 0.135;' in move
    assert '_c ctrlCommit _motion;' in move
    assert 'private _scale = if (_to>=0' in move
    assert '[0] call ACME_fnc_skCarouselRender;' in move
    assert '[_motion] call ACME_fnc_skCarouselRender;' not in move
    assert '[_dir] call ACME_fnc_skCarouselMove;' in pick


def test_single_syringe_still_only_nudges_then_recenters():
    move = txt('functions/fn_skCarouselMove.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    assert 'if (_n == 1) exitWith' in move
    assert 'private _shift=_dir*_rw*0.075;' in move
    assert '_n == 1 && {_slot != 2}' in car


def test_body_map_current_syringe_remains_immediate_administration_source():
    site = txt('functions/fn_skSiteClick.sqf')
    inject = txt('functions/fn_skInjectSite.sqf')
    assert '[_part] call ACME_fnc_skInjectSite;' in site
    assert 'ACME_fnc_skSelectedIndex' in inject
