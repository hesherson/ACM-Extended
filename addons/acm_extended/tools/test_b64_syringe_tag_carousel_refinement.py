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

    from test_bounded_current_carousel_contract import tag_geometry_contract
    tag_geometry_contract()
    pending = txt('functions/fn_skPendingTagRender.sqf')
    pick_flush = txt('functions/fn_skPickFlush.sqf')
    flush_save = txt('functions/fn_skFlushSave.sqf')
    # Current selector is centered under the native tag face, not forced to the syringe's left edge.
    assert 'private _tagCenterX = _x + _w*0.36;' in pending
    assert '[10, _patient, _bodyPart, _flushClass]' in pick_flush
    # Medicated-flush tag metadata is committed at Save, not at each Draw.
    assert 'ACME_fnc_skApplyPendingTag' in flush_save

def test_tag_dropdowns_remain_wide_clickable_and_same_color_reselectable():
    from test_bounded_tag_dropdowns import dropdown_contract, geometry_contract
    dropdown_contract()
    geometry_contract()


def test_edit_syringe_tag_is_attached_to_full_route_row():

    from test_bounded_current_carousel_contract import tag_geometry_contract
    tag_geometry_contract()

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

    from test_bounded_current_carousel_contract import geometry_contract, render_contract
    geometry_contract()
    render_contract()

def test_carousel_workspace_stays_between_edit_row_and_draw_row():

    from test_bounded_current_carousel_contract import geometry_contract
    geometry_contract()

def test_carousel_hitboxes_cannot_cover_edit_or_draw_rows():

    from test_bounded_current_carousel_contract import render_contract, geometry_contract
    render_contract()
    geometry_contract()

def test_ad_arrow_key_hints_exist_scale_and_hide_in_editor():

    from test_bounded_current_carousel_contract import hint_contract
    hint_contract()

def test_patient_name_uses_actual_screen_to_head_gap():

    from test_bounded_current_carousel_contract import header_contract
    header_contract()

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
    from test_bounded_site_click_handoff import assert_site_contract
    from test_bounded_staged_push_contracts import assert_staged_contract
    # The historical name remains an identity, not a request to restore immediate delivery.
    assert_site_contract(txt('functions/fn_skSiteClick.sqf'),
                         txt('functions/fn_skInjectSite.sqf'),
                         txt('functions/fn_skBuildHotspots.sqf'))
    assert_staged_contract(txt('functions/fn_skBeginInjection.sqf'),
                           txt('functions/fn_skConfirmInjection.sqf'))
