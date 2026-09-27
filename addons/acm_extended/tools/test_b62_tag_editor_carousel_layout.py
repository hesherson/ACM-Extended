from historical_source import read_source, assert_release_identity
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')

def test_b62_version_stamp_and_functions():
    cfg = txt('config.cpp')
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()
    assert_release_identity()
    assert 'class skTagEditOpen {};' in cfg
    assert 'class skTagEditDone {};' in cfg

def test_main_draw_select_tag_is_beside_native_syringe_not_left_list():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()
    from test_bounded_selector_lifetime import selector_contract
    selector_contract()

def test_both_tag_dropdowns_have_single_click_fallback_and_none():
    from test_bounded_tag_dropdowns import dropdown_contract
    dropdown_contract()

def test_carousel_button_is_edit_tag_and_editor_button_is_select_tag():
    from test_bounded_tag_dropdowns import captions_contract
    captions_contract()

def test_dedicated_edit_tag_mode_uses_native_draw_size_and_auto_focuses_first_line():
    from test_bounded_tag_focus import assert_native_editor_contract
    assert_native_editor_contract()
    assert 'ctrlSetText "Done"' in txt('functions/fn_skInject.sqf')

def test_tag_edits_do_not_repaint_on_every_keypress_and_fields_are_transparent():
    commit = txt('functions/fn_skTagCommit.sqf')
    render = txt('functions/fn_skCarouselRender.sqf')
    pending = txt('functions/fn_skPendingTagRender.sqf')
    assert 'if !(uiNamespace getVariable ["ACME_SK_TagEditMode",false]) then {call ACME_fnc_skRefreshDrawn;};' in commit
    assert 'ctrlSetBackgroundColor [0,0,0,0]' in render
    assert 'ctrlSetBackgroundColor [0,0,0,0]' in pending

def test_wide_carousel_retention_zone_spans_route_to_draw_workspace():

    from test_bounded_current_carousel_contract import geometry_contract
    geometry_contract()
    inj = txt('functions/fn_skInject.sqf')
    tick = txt('functions/fn_skUiTick.sqf')
    assert 'ctrlCreate ["ACME_SK_HotspotButton", 84481]' in inj
    assert 'ACME_SK_CarouselZoneHover' in tick

def test_compact_syringes_are_larger_and_carousel_is_tighter_on_ultrawide():

    from test_bounded_current_carousel_contract import geometry_contract, render_contract
    geometry_contract()
    render_contract()

def test_body_moves_down_and_shrinks_more_during_promoted_carousel():

    from test_bounded_current_carousel_contract import geometry_contract
    geometry_contract()
    inj = txt('functions/fn_skInject.sqf')
    assert 'private _expandedRect = [_uiX + _uiW/2 - _expandedW/2, safeZoneY + safeZoneH*0.055, _expandedW, _expandedH];' in inj

def test_active_syringe_still_85_percent_and_hover_is_100_percent_with_bigger_target():

    from test_bounded_current_carousel_contract import render_contract
    render_contract()
    render = txt('functions/fn_skCarouselRender.sqf')
    assert '0.85' in render
    assert 'if (!_editMode && {_off == _hoverOffset}) then {_alpha = 1;};' not in render
    assert 'private _hitW = _fullW * 1.55; private _hitH = _fullH * 1.26;' in render

def test_edit_mode_disables_neighbor_selection_and_injection_hotspots():
    # Dedicated center and neighbor gates replaced the older shared hitbox.
    from test_bounded_body_input_gates import editor_input_contract
    editor_input_contract()

def test_hover_tooltip_remains_exact_three_written_tag_lines():
    from test_bounded_syringe_tooltips import tooltip_contract, test_tagged_active_tooltip_is_exactly_three_written_lines_not_a_medication_summary
    tooltip_contract()
    for lines in (['First', 'Second', 'Third'], ['', '', 'Only third'], ['', '', '']):
        test_tagged_active_tooltip_is_exactly_three_written_lines_not_a_medication_summary(lines, 4)
