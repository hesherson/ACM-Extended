from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding="utf-8", errors="replace")

def test_b66_version_stamp():
    assert_release_identity()
    post = txt("functions/fn_postInit.sqf")
    assert_release_identity()
    assert_release_identity()

def test_main_select_syringe_tag_is_persistent_and_left_of_native_syringe():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_lifetime import selector_contract
    selector_contract()
    from test_bounded_tag_contracts import require
    require(txt("functions/fn_skPendingTagRender.sqf"), "private _tagCenterX = _x + _w*0.36;")

def test_main_tag_dropdown_always_opens_below_and_is_wide():
    pending = txt("functions/fn_skPendingTagRender.sqf")
    assert 'private _menuY = _btnY + _btnH + 2*pixelH;' in pending
    assert '(safeZoneH * 1.05) min (safeZoneW * 0.38)' in pending
    # No branch that flips the pending menu above the button.
    assert '_menuY = _btnY - _menuH' not in pending

def test_runtime_font_fallback_prevents_invisible_tag_typing():
    pending = txt("functions/fn_skPendingTagRender.sqf")
    car = txt("functions/fn_skCarouselRender.sqf")
    for src in (pending, car):
        assert 'fileExists "\\acm_extended\\ui\\fonts\\QEPhillips\\QEPhillips96.fxy"' in src
        assert '"ACME_QEPhillips"' in src
        assert '"Caveat"' in src
        assert 'ctrlSetFont _tagFont;' in src
    assert '*0.027' in pending
    assert '*0.027' in car

def test_compact_and_promoted_tracks_are_distinct_and_promoted_is_wider():
    inject = txt("functions/fn_skInject.sqf")
    assert 'private _carCompactW = _toolbarW * 0.92;' in inject
    assert 'private _carExpandedW = (_toolbarW * 1.32) min (safeZoneH * 0.46);' in inject
    assert 'private _carBottom = _drawRowY - safeZoneH*0.030;' in inject

def test_promoted_syringes_are_larger_and_ad_hints_move_outward():
    car = txt("functions/fn_skCarouselRender.sqf")
    move = txt("functions/fn_skCarouselMove.sqf")
    assert 'then {0.435} else {0.150}' in car
    assert 'private _fullH = safeZoneH*0.435;' in move
    assert 'then {0.175} else {0.165}' in car
    assert 'private _dx=_rw*0.175;' in move
    assert 'private _hintPad = safeZoneH * (if (_expanded) then {0.018} else {0.010});' in car
    assert 'private _leftKeyX = (_rx - _keyW - _hintPad)' in car
    assert 'private _rightKeyX = (_rx + _rw + _hintPad)' in car

def test_edit_syringe_tag_moves_with_route_row():
    layout = txt("functions/fn_skDynamicLayout.sqf")
    car = txt("functions/fn_skCarouselRender.sqf")
    assert 'private _editRect = [_tx, _routeY + _th + _editGap, _tw, _th];' in layout
    assert '_d setVariable ["ACME_SK_EditTagBodyRect", _editRect];' in layout
    assert '_editBtn ctrlSetPosition _editRect;' in layout
    assert 'ACME_SK_EditTagBodyRect' in car
    assert 'ctrlPosition (_d displayCtrl 84151)' not in car

def test_carousel_hit_regions_end_above_draw_syringe():
    layout = txt("functions/fn_skDynamicLayout.sqf")
    car = txt("functions/fn_skCarouselRender.sqf")
    assert 'private _zoneBottom = (_drawRect select 1) - safeZoneH*0.018;' in layout
    assert 'private _zoneH = (_zoneBottom - _zoneY) max 0;' in layout
    assert 'max (safeZoneH*0.035)' not in layout
    assert 'private _hoverBottom = (_drawForBounds select 1) - safeZoneH*0.018;' in car
    assert 'private _hitH = (_hitBottom-_hitY) max 0;' in car
    assert 'private _activeH = (_activeHitBottom-_activeHitY) max 0;' in car

def test_untagged_hover_uses_last_two_simple_medication_pulls_only():
    from test_bounded_syringe_tooltips import tooltip_contract, test_untagged_tooltip_only_reveals_recent_or_written_marked_syringes, test_unlabelled_summary_uses_last_two_positions_and_localization_fallback
    tooltip_contract()
    for index, known in ((1, False), (2, True)):
        test_untagged_tooltip_only_reveals_recent_or_written_marked_syringes(5, index, known, False)
    test_unlabelled_summary_uses_last_two_positions_and_localization_fallback([['Old secret', 9], ['Other', 1.5], ['Ketamine', 2]], 'Unknown', 9, ['1.5mL of Other', '2mL of Ketamine label'])

def test_expanded_view_lingers_and_motion_is_smooth_longer_slide():
    move = txt("functions/fn_skCarouselMove.sqf")
    pick = txt("functions/fn_skCarouselPick.sqf")
    tick = txt("functions/fn_skUiTick.sqf")
    assert 'diag_tickTime + 0.95' in move
    assert 'diag_tickTime + 0.90' in pick
    assert 'private _motion = 0.180;' in move
    assert '_c ctrlCommit _motion;' in move
    assert '_now + 0.65' in tick

def test_patient_name_is_raised_farther_in_screen_to_head_gap():
    layout = txt("functions/fn_skDynamicLayout.sqf")
    assert 'private _headerCenterY = _screenTop + _available*0.18;' in layout
    assert 'private _maxY = _headTop - (_hr select 3) - safeZoneH*0.008;' in layout
