from historical_source import read_source, assert_release_identity
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')

def test_b59_version_and_registration():
    cfg = txt('config.cpp')
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()
    for fn in ('skStoreEnsureIds','skSelectStored','skSelectedIndex','skAfterStoredRemoval','skBodySyringeRender','skBodySyringeMove'):
        assert f'class {fn} {{}};' in cfg

def test_drawn_list_is_fully_replaced_in_body_map():
    inj = txt('functions/fn_skInject.sqf')
    refresh = txt('functions/fn_skRefreshDrawn.sqf')
    rows = txt('functions/fn_skListRefresh.sqf')
    view = txt('functions/fn_skSetView.sqf')
    assert 'ctrlCreate ["ACME_SK_StyledList", 84133]' not in inj
    assert 'ctrlCreate ["ACME_SK_StyledLabel", 84134]' not in inj
    assert 'LBSelChanged", {_this call ACME_fnc_skPickDrawn}' not in inj
    assert 'the Drawn list is retired' in refresh
    assert '[84133,84302,"drawn"]' not in rows
    assert 'forEach [84133,84134,84302]' not in view

def test_body_map_has_compact_three_slot_mini_carousel():
    inj = txt('functions/fn_skInject.sqf')
    render = txt('functions/fn_skBodySyringeRender.sqf')
    assert 'ACME_SK_BodyPreviewRect' in inj
    assert '84500 + (_slot * 10)' in inj
    assert 'for "_slot" from 0 to 2' in inj
    for idc in ('84540','84541','84542'):
        assert idc in inj
    assert 'previous / selected / next' in render
    assert 'private _sc = [0.62,1.0,0.62]' in render
    assert 'private _al = [0.30,1.0,0.30]' in render
    assert 'SELECTED SYRINGE' in render

def test_body_and_full_carousel_share_stable_id_selection():
    from test_historical_syringe_identity import test_selection_follows_identity_after_store_reordering, test_missing_selected_identity_requires_explicit_fallback
    for order in ('[_c,_a,_b]','[_b,_c,_a]','[_a,_b,_c]'):
        test_selection_follows_identity_after_store_reordering(order)
    for fallback in (True,False):
        test_missing_selected_identity_requires_explicit_fallback(fallback)
    assert 'call ACME_fnc_skCarouselRender;' in txt('functions/fn_skBodySyringeRender.sqf')
    assert 'ACME_fnc_skSelectedIndex' in txt('functions/fn_skCarouselRender.sqf')

def test_ad_keys_drive_both_views_without_stealing_tag_typing():
    from test_historical_carousel_input import test_current_keyboard_route_is_body_only_and_legacy_bridge_uses_the_same_move, test_keydown_hold_and_keyup_preserve_existing_repeat_cadence, test_any_edit_control_keeps_ad_typing_and_cancels_an_existing_hold
    # One tandem Body Map replaced the separate carousel page. Both entry paths delegate to the same navigation.
    for view in ('syringe','body'):
        test_current_keyboard_route_is_body_only_and_legacy_bridge_uses_the_same_move(view)
    for key,expected in ((30,'id-c'),(32,'id-b')):
        test_keydown_hold_and_keyup_preserve_existing_repeat_cadence(key,expected)
        test_any_edit_control_keeps_ad_typing_and_cancels_an_existing_hold(84460,key)

def test_view_buttons_make_carousel_to_body_workflow_explicit():
    from test_bounded_page_navigation import bindings_contract, labels_contract
    bindings_contract()
    labels_contract()

def test_body_preview_renders_real_fill_tag_and_summary():
    body = txt('functions/fn_skBodySyringeRender.sqf')
    assert '(_amt + _nsMl) / (_size max 0.01)' in body
    assert 'ACME_SK_CarouselTravel10' in body
    assert 'syringe_%1_plunger_ca.paa' in body
    assert 'tag_overlay_%1mL_%2.paa' in body
    assert '_entry param [8 + _ln, ""]' in body
    assert 'ACME_fnc_skSyringeSummary' in body
    assert 'displayCtrl 84001' in body and 'displayCtrl 84002' in body

def test_flush_body_map_path_is_not_broken_by_syringe_preview():
    body = txt('functions/fn_skBodySyringeRender.sqf')
    move = txt('functions/fn_skBodySyringeMove.sqf')
    hot = txt('functions/fn_skBuildHotspots.sqf')
    assert 'ACME_SK_SelFlush' in body
    assert 'Saline Flush 10 mL' in body
    assert 'syringe_flush_10_barrel_ca.paa' in body
    assert 'ACME_SK_SelFlush' in move
    assert 'private _deliveryReady = (_flush != "") || {_syringeIndex >= 0};' in hot

def test_consumption_keeps_nearest_syringe_and_clears_target_state():
    after = txt('functions/fn_skAfterStoredRemoval.sqf')
    inject = txt('functions/fn_skInjectSite.sqf')
    assert '(_oldIndex min ((count _store) - 1)) max 0' in after
    assert 'ACME_SK_SiteIdx", -1' in after
    assert 'ACME_SK_EpiDoseChoice", 0' in after
    assert 'ACME_SK_SelFlush", ""' in after
    assert '[_storeIdx] call ACME_fnc_skAfterStoredRemoval' in inject
    assert 'Choose a prepared syringe in Syringe Menu first.' in inject

def test_self_interaction_uses_stable_syringe_id_not_array_identity():
    menu = txt('functions/fn_skSyringeSelfMenu.sqf')
    opened = txt('functions/fn_skOpenStoredSyringe.sqf')
    assert 'private _id = _e param [11,"",[""]]' in menu
    assert '[_id]' in menu
    assert 'ACME_SK_OpenCarouselId' in opened
    assert 'ACME_fnc_skSelectStored' in opened
    assert 'ACME_SK_OpenCarouselIndex' not in opened

def test_carousel_hides_draw_ui_sections_and_uses_native_scale():
    rows = txt('functions/fn_skListRefresh.sqf')
    inj = txt('functions/fn_skInject.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    assert 'private _visible = !_carousel;' in rows
    assert 'ACME_SK_CarouselNativeRect' in inj
    assert 'ACME_SK_CarouselNativeRect' in car
    assert '(_amt+_nsMl)/(_size max 0.01)' in car
    assert 'private _sc=[0.55,0.75,1.0,0.75,0.55]' in car

def test_life_reset_clears_store_and_stable_selection():
    from test_historical_syringe_identity import test_personal_lifecycle_clears_kit_and_selection_but_not_patient_equipment
    assert 'call ACME_fnc_registerSyringeLifecycleRuntime;' in txt('functions/fn_postInit.sqf')
    for event in ('Killed','Respawn'):
        test_personal_lifecycle_clears_kit_and_selection_but_not_patient_equipment(event)


def test_no_user_facing_drawn_list_wording_remains():
    kit = txt('functions/fn_syringeKitDraw.sqf')
    compound = txt('functions/fn_skCompoundBegin.sqf')
    assert 'Narc Box Drawn list' not in kit
    assert 'Stored in the Syringe Menu.' in kit
    assert 'Drawn list' not in compound
    assert 'Syringe Menu' in compound
