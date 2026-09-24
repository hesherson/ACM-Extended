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
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()

def test_runtime_font_fallback_prevents_invisible_tag_typing():
    from test_bounded_tag_font_fallback import font_contract, no_outline_fonts
    from test_bounded_tag_line_layout import layout_contract
    font_contract(); no_outline_fonts(); layout_contract()

def test_compact_and_promoted_tracks_are_distinct_and_promoted_is_wider():

    from test_bounded_current_carousel_contract import geometry_contract
    geometry_contract()

def test_promoted_syringes_are_larger_and_ad_hints_move_outward():

    from test_bounded_current_carousel_contract import render_contract, hint_contract
    render_contract()
    hint_contract()

def test_edit_syringe_tag_moves_with_route_row():
    layout = txt("functions/fn_skDynamicLayout.sqf")
    car = txt("functions/fn_skCarouselRender.sqf")
    assert 'private _editRect = [_tx, _routeY + _th + _editGap, _tw, _th];' in layout
    assert '_d setVariable ["ACME_SK_EditTagBodyRect", _editRect];' in layout
    assert '_editBtn ctrlSetPosition _editRect;' in layout
    assert 'ACME_SK_EditTagBodyRect' in car
    assert 'ctrlPosition (_d displayCtrl 84151)' not in car

def test_carousel_hit_regions_end_above_draw_syringe():

    from test_bounded_current_carousel_contract import geometry_contract, render_contract
    geometry_contract()
    render_contract()

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
    # Navigation commits immediately, then the promoted view lingers. Hover/retention refreshes
    # the collapse deadline without reintroducing decorative multi-control interpolation.
    assert 'diag_tickTime + 1.35' in move
    assert 'ACME_SK_CarouselExpanded",true' in pick
    assert '_motion' not in move
    assert 'ctrlCommit' not in move
    assert '_now + 0.90' in tick

def test_patient_name_is_raised_farther_in_screen_to_head_gap():

    from test_bounded_current_carousel_contract import header_contract
    header_contract()
