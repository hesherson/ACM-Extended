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
    inj = txt('functions/fn_skInject.sqf')
    layout = txt('functions/fn_skDynamicLayout.sqf')
    tick = txt('functions/fn_skUiTick.sqf')
    assert 'ctrlCreate ["ACME_SK_HotspotButton", 84481]' in inj
    assert 'private _zoneY = _routeY + _th + safeZoneH*0.006;' in layout
    assert 'private _zoneBottom = _viewY - safeZoneH*0.008;' in layout
    assert '_zone ctrlSetPosition [_carX,_zoneY,_carW,_zoneH];' in layout
    assert 'ACME_SK_CarouselZoneHover' in tick
    assert '_hover || {_zoneHover}' in tick

def test_compact_syringes_are_larger_and_carousel_is_tighter_on_ultrawide():
    inj = txt('functions/fn_skInject.sqf')
    render = txt('functions/fn_skCarouselRender.sqf')
    assert '(safeZoneW * 0.40) min (safeZoneH * 1.08)' in inj
    assert '(safeZoneW * 0.46) min (safeZoneH * 1.22)' in inj
    assert 'safeZoneH*0.132' in inj
    assert 'safeZoneH*0.405' in inj
    assert 'if (_expanded) then {0.94} else {0.98}' in render
    assert '[0.24,0.48,1.0,0.48,0.24]' in render

def test_body_moves_down_and_shrinks_more_during_promoted_carousel():
    inj = txt('functions/fn_skInject.sqf')
    layout = txt('functions/fn_skDynamicLayout.sqf')
    assert 'safeZoneH * 0.26 / _fillV' in inj
    assert 'safeZoneH*0.032' in inj
    assert 'safeZoneH*0.100' in inj
    assert 'if (_expanded) then {0.455} else {0.748}' in layout

def test_active_syringe_still_85_percent_and_hover_is_100_percent_with_bigger_target():
    render = txt('functions/fn_skCarouselRender.sqf')
    assert '0.85' in render
    assert '_scale = _scale * 1.10; _alpha = 1;' in render
    assert '_fullW * 1.45' in render
    assert '_fullH * 1.20' in render

def test_edit_mode_disables_neighbor_selection_and_injection_hotspots():
    # Dedicated center and neighbor gates replaced the older shared hitbox.
    from test_bounded_body_input_gates import editor_input_contract
    editor_input_contract()

def test_hover_tooltip_remains_exact_three_written_tag_lines():
    from test_bounded_syringe_tooltips import tooltip_contract, test_tagged_active_tooltip_is_exactly_three_written_lines_not_a_medication_summary
    tooltip_contract()
    for lines in (['First', 'Second', 'Third'], ['', '', 'Only third'], ['', '', '']):
        test_tagged_active_tooltip_is_exactly_three_written_lines_not_a_medication_summary(lines, 4)
