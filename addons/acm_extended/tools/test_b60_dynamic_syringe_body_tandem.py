from historical_source import read_source, assert_release_identity
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')

def test_b60_version_and_new_functions_registered():
    cfg = txt('config.cpp')
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()
    for fn in (
        'skApplyPendingTag','skPendingTagReset','skPendingTagCommit','skPendingTagColor',
        'skPendingTagRender','skAfterSaveOpenBody','skDynamicLayout','skCarouselHover','skCarouselPick'
    ):
        assert f'class {fn} {{}};' in cfg

def test_body_and_carousel_have_compact_and_expanded_geometry():

    from test_bounded_current_carousel_contract import geometry_contract
    geometry_contract()

def test_ad_expands_carousel_and_auto_collapse_is_hover_aware():
    from test_historical_carousel_input import test_keydown_hold_and_keyup_preserve_existing_repeat_cadence, test_expanded_view_collapse_respects_existing_retention_conditions
    for key,expected in ((30,'id-c'),(32,'id-b')):
        test_keydown_hold_and_keyup_preserve_existing_repeat_cadence(key,expected)
    for guard in ('pointer','zone','tag-focus','color','held','pending','editor','busy','none'):
        test_expanded_view_collapse_respects_existing_retention_conditions(guard)

def test_active_syringe_is_85_percent_then_100_percent_on_hover():

    from test_bounded_current_carousel_contract import render_contract
    render_contract()
    car = txt('functions/fn_skCarouselRender.sqf')
    # Compact center is 85% opacity; hover is opacity-only and never changes geometry.
    assert '[0.06,0.24,0.85,0.24,0.06]' in car
    assert 'private _activeScale = 1;' in car
    assert 'if (!_editMode && {_off == _hoverOffset}) then {_alpha = 1;};' in car

def test_same_five_carousel_controls_are_used_in_both_layouts():
    inj = txt('functions/fn_skInject.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    assert 'for "_slot" from 0 to 4' in inj
    assert '84400 + (_slot * 10)' in inj
    assert 'ACME_SK_CarouselRect' in car
    assert 'if (_expanded)' in car
    # B59's separate lower mini-carousel is explicitly retired.
    assert 'ctrlCreate ["RscPicture", 84500' not in inj

def test_clicking_visible_syringe_selects_stable_record_and_expands():
    from test_historical_carousel_input import test_click_selects_its_final_visible_record_once_without_a_deferred_second_step, test_navigation_clears_existing_site_dose_and_discard_transients_without_touching_contents
    # The pick delegates to the shared identity-preserving move, not an inline index writer.
    for offset,expected in ((-2,'id-b'),(-1,'id-c'),(1,'id-b'),(2,'id-c')):
        test_click_selects_its_final_visible_record_once_without_a_deferred_second_step(offset,expected)
    test_navigation_clears_existing_site_dose_and_discard_transients_without_touching_contents()

def test_preparation_has_optional_none_tag_and_three_invisible_editors():
    from test_bounded_tag_line_layout import pending_contract
    pending_contract()

def test_all_requested_tag_colors_are_available_during_preparation():
    inj = txt('functions/fn_skInject.sqf')
    colors = [
        'yellow_induction','orange_benzodiazepine','blue_opioid','blue_stripe_reversal',
        'red_paralytic','red_stripe_reversal','violet_vasopressor','violet_stripe_hypotensive',
        'green_anticholinergic','gray_local_anesthetic','salmon_antiemetic','white_saline_flush'
    ]
    for color in colors:
        assert color in inj

def test_pending_tag_is_applied_to_every_narcbox_save_path():
    from source_scan import lex
    from test_historical_syringe_identity import test_actual_save_attaches_pending_tag_without_changing_source_funding
    # Waste Draw only stages a flush now; metadata is attached when Save funds it.
    for rel in ('functions/fn_skCompoundCommit.sqf','functions/fn_skFlushSave.sqf',
                'functions/fn_epinephrineDrawCardiac.sqf','functions/fn_epinephrinePrepare.sqf',
                'overrides/fn_syringeDrawButton.sqf'):
        tokens=lex(txt(rel))
        assert any(a.value=='call' and b.value=='ACME_fnc_skApplyPendingTag' for a,b in zip(tokens,tokens[1:])),rel
    for kind in ('compound','flush'):
        test_actual_save_attaches_pending_tag_without_changing_source_funding(kind)

def test_save_returns_to_large_body_and_compact_carousel():

    from test_bounded_current_carousel_contract import save_contract
    save_contract()
    after = txt('functions/fn_skAfterSaveOpenBody.sqf')
    compound = txt('functions/fn_skCompoundSave.sqf')
    waste = txt('functions/fn_skWasteDraw.sqf')
    direct = txt('overrides/fn_syringeDrawButton.sqf')
    # Saving now stays on Draw Syringe; it must not force Body Map open.
    assert 'ACME_SK_View", "body"' not in after
    assert '[true] call ACME_fnc_skAfterSaveOpenBody' in compound
    assert '[true] call ACME_fnc_skAfterSaveOpenBody' in waste
    assert 'call ACME_fnc_skAfterSaveOpenBody' in direct

def test_total_solution_volume_drives_stored_plunger_position():
    car = txt('functions/fn_skCarouselRender.sqf')
    assert '(_amt + _nsMl) / (_size max 0.01)' in car
    assert 'ACME_SK_CarouselTravel10' in car
    assert 'syringe_%1_plunger_ca.paa' in car

def test_tag_editing_does_not_steal_ad_typing_and_holds_expanded_view():
    from test_historical_carousel_input import test_any_edit_control_keeps_ad_typing_and_cancels_an_existing_hold, test_keyup_in_tag_mode_cancels_hold_even_without_an_intervening_tick, test_expanded_view_collapse_respects_existing_retention_conditions
    # Any CT_EDIT owns typing, including push seconds; do not restore a narrow hardcoded IDC list.
    for focus in (84460,84461,84462,84601,84602,84603,84830):
        for key in (30,32):
            test_any_edit_control_keeps_ad_typing_and_cancels_an_existing_hold(focus,key)
    for key in (30,32):
        test_keyup_in_tag_mode_cancels_hold_even_without_an_intervening_tick(key)
    test_expanded_view_collapse_respects_existing_retention_conditions('editor')

def test_body_hitboxes_wait_for_layout_animation_to_finish():
    hot = txt('functions/fn_skBuildHotspots.sqf')
    assert 'ACME_SK_LayoutBusyUntil' in hot
    assert '_layoutReady' in hot

def test_store_still_expires_on_death_and_respawn():
    from test_historical_syringe_identity import test_personal_lifecycle_clears_kit_and_selection_but_not_patient_equipment
    assert 'call ACME_fnc_registerSyringeLifecycleRuntime;' in txt('functions/fn_postInit.sqf')
    for event in ('Killed','Respawn'):
        test_personal_lifecycle_clears_kit_and_selection_but_not_patient_equipment(event)
