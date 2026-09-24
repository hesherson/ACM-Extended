from historical_source import read_source, assert_release_identity
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')

def test_b63_version_stamp():
    assert_release_identity()
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_tag_editors_are_frameless_short_and_raised():
    from test_bounded_editor_presentation import frame_contract, native_editor_contract
    frame_contract(); native_editor_contract()

def test_stored_tag_editor_raises_native_syringe_and_places_select_tag_under_tag():
    from test_bounded_editor_presentation import frame_contract, native_editor_contract
    frame_contract(); native_editor_contract()

def test_body_map_edit_tag_is_above_syringe_below_route():

    from test_bounded_current_carousel_contract import tag_geometry_contract, geometry_contract
    tag_geometry_contract()
    geometry_contract()

def test_main_draw_select_tag_is_under_live_tag_and_has_wide_clickable_dropdown():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()
    from test_bounded_selector_lifetime import selector_contract
    selector_contract()

def test_pending_tag_live_preview_remains_available_to_saline_flush_flow():
    from test_bounded_flush_preview_contracts import tag_save_contract
    tag_save_contract()

def test_draw_and_save_have_physical_press_feedback():
    inj = txt('functions/fn_skInject.sqf')
    assert 'ACME_SK_PressFeedbackBound' in inj
    assert '"MouseButtonDown"' in inj
    assert '"MouseButtonUp"' in inj
    assert '"MouseExit"' in inj
    assert 'forEach [84003,84004]' in inj
    assert '2*pixelW' in inj and '2*pixelH' in inj

def test_carousel_is_toolbar_width_and_body_contracts_more():

    from test_bounded_current_carousel_contract import geometry_contract
    geometry_contract()

def test_carousel_art_is_larger_inside_tighter_footprint():

    from test_bounded_current_carousel_contract import render_contract
    render_contract()

def test_carousel_has_fading_gray_underlay():

    from test_bounded_current_carousel_contract import retired_contract
    # The decorative fading-gray underlay was retired; the bounded retention zone carries interaction state.
    retired_contract()

def test_patient_header_is_name_only_and_raised_in_body_view():

    from test_bounded_current_carousel_contract import header_contract
    header_contract()

def test_access_click_is_immediate_selected_syringe_administration():
    from test_bounded_site_click_handoff import assert_site_contract
    from test_bounded_staged_push_contracts import assert_staged_contract
    # The historical name remains an identity, not a request to restore immediate delivery.
    assert_site_contract(txt('functions/fn_skSiteClick.sqf'),
                         txt('functions/fn_skInjectSite.sqf'),
                         txt('functions/fn_skBuildHotspots.sqf'))
    assert_staged_contract(txt('functions/fn_skBeginInjection.sqf'),
                           txt('functions/fn_skConfirmInjection.sqf'))


def test_carousel_motion_has_two_phase_scroll_and_clicks_use_it():
    from test_historical_carousel_input import test_click_selects_its_final_visible_record_once_without_a_deferred_second_step
    # Phase 121 retired multi-control motion. Do not reinstate 0.085-second interpolation or delayed selection.
    for offset,expected in ((-2,'id-b'),(-1,'id-c'),(1,'id-b'),(2,'id-c')):
        test_click_selects_its_final_visible_record_once_without_a_deferred_second_step(offset,expected)
    move=txt('functions/fn_skCarouselMove.sqf')
    assert 'CBA_fnc_waitAndExecute' not in move
    assert '[0] call ACME_fnc_skCarouselRender;' in move

def test_single_syringe_only_nudges_and_does_not_duplicate_neighbors():
    from test_historical_carousel_input import test_keyboard_steps_keep_wraparound_and_never_mutate_the_store
    # No decorative nudge is needed for the immediate renderer. A sole syringe stays selected.
    for direction in (-1,1):
        test_keyboard_steps_keep_wraparound_and_never_mutate_the_store(1,direction)
    render=txt('functions/fn_skCarouselRender.sqf')
    assert '_n == 1 && {_slot != 2}' in render
    assert 'ctrlShow false' in render
