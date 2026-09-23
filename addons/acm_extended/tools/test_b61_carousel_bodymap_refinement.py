from historical_source import read_source, assert_release_identity
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')

def test_b61_version_stamp():
    assert_release_identity()
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_ultrawide_carousel_width_is_capped_and_moved_lower():
    inj = txt('functions/fn_skInject.sqf')
    assert '(safeZoneW * 0.48) min (safeZoneH * 1.30)' in inj
    assert '(safeZoneW * 0.62) min (safeZoneH * 1.55)' in inj
    assert 'safeZoneH*0.795' in inj
    assert 'safeZoneH*0.515' in inj
    assert 'safeZoneW*0.84' not in inj

def test_open_close_syringe_menu_button_is_removed_and_draw_button_restored_low():
    inj = txt('functions/fn_skInject.sqf')
    setview = txt('functions/fn_skSetView.sqf')
    render = txt('functions/fn_skCarouselRender.sqf')
    assert 'ctrlCreate ["ACME_SK_StyledButton", 84170]' not in inj
    assert 'displayCtrl 84170' not in setview
    assert 'displayCtrl 84170' not in render
    assert 'safeZoneH / 1.08' in inj
    assert '< Draw Syringe' in setview

def test_body_shrink_is_stronger_and_route_row_clears_body():
    inj = txt('functions/fn_skInject.sqf')
    layout = txt('functions/fn_skDynamicLayout.sqf')
    assert 'safeZoneH * 0.32 / _fillV' in inj
    assert 'if (_expanded) then {0.472} else {0.748}' in layout
    assert 'safeZoneH*0.36' in inj

def test_carousel_zoom_falloff_is_more_pronounced_but_active_remains_85_percent():
    car = txt('functions/fn_skCarouselRender.sqf')
    move = txt('functions/fn_skCarouselMove.sqf')
    assert '[0.38,0.66,1.0,0.66,0.38]' in car
    assert '[0.32,0.56,1.0,0.56,0.32]' in car
    assert '[0.12,0.38,0.85,0.38,0.12]' in car
    assert '_scale = _scale * 1.075; _alpha = 1;' in car
    assert 'private _activeScale = if (_hover) then {1.075} else {1};' in car
    assert '_rw*0.17' in move

def test_active_hover_target_is_larger_and_above_neighbor_targets():
    inj = txt('functions/fn_skInject.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    assert 'ctrlCreate ["ACME_SK_HotspotButton", 84480]' in inj
    assert '_fullW * 1.25' in car
    assert '_fullH * 1.10' in car
    assert '_w * 0.08' in car and '_h * 0.06' in car

def test_hover_tooltip_is_exact_three_tag_lines():
    # Only the dedicated active hitbox owns text; neighboring click targets stay silent.
    from test_bounded_syringe_tooltips import tooltip_contract, test_tagged_active_tooltip_is_exactly_three_written_lines_not_a_medication_summary, test_neighbor_tooltip_clearing_is_separate_from_active_content
    tooltip_contract()
    test_tagged_active_tooltip_is_exactly_three_written_lines_not_a_medication_summary(['First', 'Mixed Case', 'Third'], 0)
    test_neighbor_tooltip_clearing_is_separate_from_active_content()

def test_color_dropdown_can_reselect_same_row_for_multiple_syringes():
    inj = txt('functions/fn_skInject.sqf')
    stored = txt('functions/fn_skTagColor.sqf')
    pending = txt('functions/fn_skPendingTagColor.sqf')
    assert inj.count('lbSetCurSel -1') >= 2
    assert 'ctrlSetFocus _l' in inj
    assert '_c lbSetCurSel -1' in stored
    assert '_ctrl lbSetCurSel -1' in pending

def test_main_draw_page_has_changeable_tag_selector():
    inj = txt('functions/fn_skInject.sqf')
    render = txt('functions/fn_skPendingTagRender.sqf')
    assert 'Select Tag: None' in inj
    assert 'Select Tag: %1' in render
    assert 'Select or change' in inj
    assert 'None - No syringe tag' in inj
    assert 'ACME_SK_PendingTagColor' in render

def test_body_map_no_longer_prints_current_medication_details_at_top():
    car = txt('functions/fn_skCarouselRender.sqf')
    setview = txt('functions/fn_skSetView.sqf')
    assert car.count('(_d displayCtrl 84001) ctrlSetText "";') >= 3
    assert '(_display displayCtrl 84001) ctrlSetText "";' in setview
    assert 'ctrlSetText _sum' not in car

def test_ad_and_click_still_promote_carousel_without_manual_open_button():
    from test_historical_carousel_input import test_keydown_hold_and_keyup_preserve_existing_repeat_cadence, test_center_click_toggles_browsing_but_keeps_a_staged_target_promoted
    for key,expected in ((30,'id-c'),(32,'id-b')):
        test_keydown_hold_and_keyup_preserve_existing_repeat_cadence(key,expected)
    for pending in (False,True):
        test_center_click_toggles_browsing_but_keeps_a_staged_target_promoted(pending)
    assert 'Open Syringe Menu' not in txt('functions/fn_skInject.sqf')
