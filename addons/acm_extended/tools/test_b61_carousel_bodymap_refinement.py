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

    from test_bounded_current_carousel_contract import geometry_contract
    geometry_contract()
    inj = txt('functions/fn_skInject.sqf')
    assert 'private _carExpandedW = (_toolbarW * 1.72) min (safeZoneH * 0.64);' in inj
    assert 'safeZoneW*0.84' not in inj

def test_open_close_syringe_menu_button_is_removed_and_draw_button_restored_low():
    from test_bounded_page_navigation import retired_toggle_contract
    retired_toggle_contract()

def test_body_shrink_is_stronger_and_route_row_clears_body():

    from test_bounded_current_carousel_contract import geometry_contract
    geometry_contract()
    inj = txt('functions/fn_skInject.sqf')
    layout = txt('functions/fn_skDynamicLayout.sqf')
    assert 'private _expandedH = safeZoneH * 0.14 / _fillV;' in inj
    assert 'if (_expanded) then {0.228} else {0.630}' in layout

def test_carousel_zoom_falloff_is_more_pronounced_but_active_remains_85_percent():

    from test_bounded_current_carousel_contract import render_contract, navigation_contract
    render_contract()
    navigation_contract()
    car = txt('functions/fn_skCarouselRender.sqf')
    assert '[0.34,0.66,1.0,0.66,0.34]' in car
    assert '[0.28,0.55,1.0,0.55,0.28]' in car
    assert '[0.06,0.24,0.85,0.24,0.06]' in car

def test_active_hover_target_is_larger_and_above_neighbor_targets():

    from test_bounded_current_carousel_contract import render_contract
    render_contract()
    car = txt('functions/fn_skCarouselRender.sqf')
    assert 'private _hitW = _fullW * 1.55; private _hitH = _fullH * 1.26;' in car
    assert 'private _padX = _w * 0.20; private _padY = _h * 0.11;' in car

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
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_lifetime import selector_contract
    selector_contract()

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
