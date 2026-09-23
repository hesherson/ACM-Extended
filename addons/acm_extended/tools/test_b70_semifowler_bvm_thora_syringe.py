from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')


def test_b70_version_stamp():
    assert_release_identity()
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()


def test_semifowler_patient_uses_exact_grab_release_without_helper_positioning():
    from test_bounded_head_pose_contracts import assert_connected_patient_states, assert_no_patient_teleport
    assert_connected_patient_states()
    assert_no_patient_teleport()


def test_semifowler_provider_runs_requested_full_duration_sequence_and_finishes_unarmed():
    seq = txt('functions/fn_headElevMedicSeq.sqf')
    assert 'private _dragger = "DraggerBase";' in seq
    assert 'private _toUnarmed = "AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon";' in seq
    assert 'private _unarmed = "AmovPknlMstpSnonWnonDnon";' in seq
    assert 'addEventHandler ["AnimDone"' in seq
    assert 'private _doneEH' in seq
    assert '[_u, _toUnarmed, 0] call ACME_fnc_doAnim;' in seq
    assert '[_u, _unarmed, 0] call ACME_fnc_doAnim;' in seq
    assert 'ACME_fnc_doAnimHeld' not in seq
    assert 'ACME_fnc_animQueue' not in seq


def test_provider_weapon_preflight_is_one_clear_only_and_never_tsp_or_auto_redraw():
    from test_historical_weapon_preflight import test_current_weapon_paths_do_not_invoke_optional_sling_or_direct_reselection, test_one_engine_holster_request_is_retained_across_repeated_controllers, test_pose_direct_pressure_exception_stays_scoped_and_does_not_restore_a_weapon
    test_current_weapon_paths_do_not_invoke_optional_sling_or_direct_reselection()
    for weapon,delay in [('pistol',0.95),('rifle',0.70),('launcher',0.70)]:
        test_one_engine_holster_request_is_retained_across_repeated_controllers(weapon,delay,True)
    # Established DP theatre intentionally clears logical selection without replaying a holster.
    test_pose_direct_pressure_exception_stays_scoped_and_does_not_restore_a_weapon()


def test_all_bvm_variants_are_class_routed_to_breathing():
    menu = txt('functions/fn_menuActionInfo.sqf')
    for cls in ['usebvm', 'usebvm_oxygen', 'usebvm_vehicleoxygen', 'usebvm_portableoxygen']:
        assert cls in menu
    assert 'exitWith {["airway", "ventilation", false]};' in menu
    groups = txt('functions/fn_postInit.sqf')
    assert '"Use BVM"' in groups
    assert '"Use BVM with Oxygen"' in groups


def test_adjust_thoracostomy_requires_actual_existing_procedure_and_is_in_chest():
    can = txt('functions/fn_thoraCanOpen.sqf')
    cfg = txt('config.cpp')
    dead = txt('overrides/fn_canTreatCached.sqf')
    menu = txt('functions/fn_menuActionInfo.sqf')
    groups = txt('functions/fn_postInit.sqf')
    assert 'params ["_medic", "_patient", ["_existingOnly", false' in can
    assert 'if (_existingOnly && {!_completed}) exitWith {false};' in can
    assert 'private _partial =' in can
    assert "[_medic, _patient, true] call ACME_fnc_thoraCanOpen" in cfg
    assert 'case "ACME_AdjustThoracostomy": {[_caller, _target, true] call ACME_fnc_thoraCanOpen};' in dead
    assert '"acme_adjustthoracostomy"' in menu
    assert '["airway", "chest", false]' in menu
    assert '"Adjust Thoracostomy"' in groups


def test_main_select_syringe_tag_is_deferred_self_healing_and_always_rendered_on_draw_page():
    cfg = txt('config.cpp')
    inject = txt('functions/fn_skInject.sqf')
    open_draw = txt('functions/fn_skOpenDraw.sqf')
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    render = txt('functions/fn_skPendingTagRender.sqf')
    assert 'class skPendingTagEnsure {};' in cfg
    assert 'ACME_SK_PendingTagReady", false' in inject
    assert 'ACME_SK_PendingTagReady", true' in open_draw
    assert 'call ACME_fnc_skPendingTagEnsure;' in open_draw
    assert 'ctrlCreate ["ACME_SK_StyledButton", 84610]' in ensure
    assert 'Select Syringe Tag' in ensure
    assert 'call ACME_fnc_skPendingTagEnsure;' in render
    assert 'private _showSetup = (_view == "syringe");' in render
    assert '_button ctrlShow true;' in render


def test_main_tag_text_fields_stay_hidden_until_real_color_exists():
    render = txt('functions/fn_skPendingTagRender.sqf')
    assert 'private _hasTag = !(_color in ["", "none"]);' in render
    assert '_e ctrlShow _hasTag;' in render
    assert '_e ctrlEnable _hasTag;' in render


def test_syringe_can_return_last_hundredth_to_exact_endpoint():
    compound = txt('functions/fn_skCompoundBegin.sqf')
    tick = txt('functions/fn_skUiTick.sqf')
    assert '(_fill - _floorMl) <= 0.015' in compound
    assert '_fill = _floorMl;' in compound
    assert '_newY = _floorY;' in compound
    assert '_drawnNow <= 0.015' in tick
    assert 'ACM_circulation_SyringeDraw_DrawnAmount = 0;' in tick


def test_edit_tag_stays_visible_during_ad_and_center_click_toggles_carousel():
    move = txt('functions/fn_skCarouselMove.sqf')
    pick = txt('functions/fn_skCarouselPick.sqf')
    # Movement may hide editors/list/done/hitbox, but not the persistent Edit Syringe Tag button 84470.
    assert '[84460,84461,84462,84470,84471,84472,84480]' not in move
    assert '[84460,84461,84462,84471,84472,84480]' in move
    assert 'call ACME_fnc_skCarouselToggle;' in pick


def test_b69_chest_seal_spacing_is_retained():
    gen = txt('functions/fn_chestSealGenHoles.sqf')
    assert 'ACME_CS_minHoleSep", 0.052' in gen
    assert 'for "_try" from 1 to 48 do {' in gen
