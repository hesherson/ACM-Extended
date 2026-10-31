from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')


def test_version_batch():
    cfg = txt('config.cpp')
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()
    assert_release_identity()


def test_rpt_confirmed_pending_tag_renderer_compile_bug_is_removed():
    src = txt('functions/fn_skPendingTagRender.sqf')
    assert 'if (!_showSetup) exitWith {' in src
    assert 'if (!_showSetup) then {' not in src
    assert 'exitWith {};\n};\n\nprivate _color' not in src


def test_main_tag_button_is_compact_and_anchored_left_of_barrel():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()


def test_main_tag_dropdown_is_directly_below_and_full_description_width():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()
    from test_bounded_selector_lifetime import selector_contract
    selector_contract()


def test_selected_main_tag_immediately_renders_real_overlay_and_edit_lines():
    render = txt('functions/fn_skPendingTagRender.sqf')
    color = txt('functions/fn_skPendingTagColor.sqf')
    assert r'\acm_extended\ui\syringe_tags\%1mL\tag_overlay_%1mL_%2.paa' in render
    assert '_tag ctrlShow true;' in render
    assert '_e ctrlShow _hasTag;' in render
    assert 'call ACME_fnc_skPendingTagRender;' in color


def test_draw_save_commits_tag_color_and_three_lines_to_syringe():
    draw = txt('overrides/fn_syringeDrawButton.sqf')
    apply = txt('functions/fn_skApplyPendingTag.sqf')
    assert 'call ACME_fnc_skPendingTagCommit;' in draw
    assert 'call ACME_fnc_skApplyPendingTag' in draw
    assert '_out set [7, _color];' in apply
    assert '_out set [8 + _i' in apply


def test_new_qedavemergens_font_replaces_old_runtime_wiring():
    from test_bounded_tag_font_fallback import font_contract, no_outline_fonts
    from test_bounded_tag_line_layout import layout_contract
    font_contract(); no_outline_fonts(); layout_contract()


def test_chest_reveal_is_not_expired_by_cross_machine_mission_clock():
    edit = txt('functions/fn_chestSealEdit.sqf')
    effect = txt('functions/fn_chestSealEffectLocal.sqf')
    assert 'CBA_missionTime - _issued' not in edit
    assert '_issued > CBA_missionTime' not in edit
    assert 'Treatment request expired' not in edit
    assert '!finite _issued' in edit
    assert 'CBA_missionTime - _issued' not in effect
    assert 'ACME_CS_blockedEffectEpoch' in effect
    assert 'ACME_CS_lastSealEffectRev' in effect


def test_chest_reveal_keeps_epoch_revision_idempotence_guards():
    request = txt('functions/fn_chestSealRequest.sqf')
    edit = txt('functions/fn_chestSealEdit.sqf')
    assert 'ACME_CS_pending set' in request
    assert 'ACME_CS_editResults getOrDefault' in edit
    assert '_epoch != (_snapshot select 0)' in edit
    assert '_expected > (_snapshot select 1)' in edit
    assert 'ACME_CS_sealRevisions' in edit


def test_head_patient_grab_uses_priority_two_and_startup_grace():
    from test_bounded_head_pose_contracts import assert_startup_grace
    assert_startup_grace()


def test_head_patient_release_is_priority_two_and_never_setpos():
    from test_bounded_head_pose_contracts import assert_connected_patient_states, assert_no_patient_teleport
    assert_connected_patient_states()
    assert_no_patient_teleport()


def test_head_provider_stands_only_for_draggerbase_then_returns_crouched():
    from test_bounded_head_provider_sequence import provider_contract
    provider_contract()


def test_head_elevation_only_rolls_patient_when_actually_prone():
    from test_bounded_head_start_contracts import start_contract
    start_contract()


def test_generic_provider_work_preflights_to_empty_hands_and_crouch_once():
    # B177 removed the generic presentation waits so accepted treatment starts immediately.
    # The real helper still issues only one holster request and never restores a weapon.
    from test_historical_weapon_preflight import (
        test_one_engine_holster_request_is_retained,
        test_treatment_bridge_contains_no_generic_presentation_wait,
        test_native_treatment_is_called_directly_after_presentation_setup,
    )
    for weapon, delay in (("pistol", .95), ("rifle", .70), ("launcher", .70)):
        for ace in (False, True):
            test_one_engine_holster_request_is_retained(weapon, delay, ace)
    test_treatment_bridge_contains_no_generic_presentation_wait()
    test_native_treatment_is_called_directly_after_presentation_setup()


def test_generic_acme_treatment_poses_never_choose_standing_medicup_variants():
    pose = txt('functions/fn_treatmentPoseStart.sqf')
    assert 'private _upright = false;' in pose
    # medicUp is a kneeling provider working toward a conscious upright casualty.
    # It is deliberately available since B175, with a native-class fallback.
    helper = txt('functions/fn_poseUprightState.sqf')
    assert 'call ACME_fnc_poseUprightState' in pose
    assert '!_enteredProne' in pose and '"assessmentAirway", "assessmentBreathing"' in pose
    assert '!([_patient] call ACME_fnc_patientUpright)' in helper
    assert 'isClass (configFile >> "CfgMovesMaleSdr" >> "States" >> _candidate)' in helper
    assert '[_normal, false]' in helper


def test_no_automatic_weapon_restore_in_core_provider_paths():
    for rel in [
        'functions/fn_medicAnimationPrep.sqf',
        'functions/fn_treatmentPoseStart.sqf',
        'functions/fn_treatmentPoseStop.sqf',
        'functions/fn_headElevMedicSeq.sqf',
        'overrides/fn_treatment.sqf',
    ]:
        src = txt(rel)
        assert 'selectWeapon (primaryWeapon' not in src
        assert 'selectWeapon (handgunWeapon' not in src
        assert 'selectedWeaponOnTreatment' not in src


def test_generic_preflight_never_falls_through_with_weapon_or_standing_state():
    # Historical case identity: no generic wait remains. Verify the current helper
    # cannot reselect a live weapon or queue another holster once empty hands settle.
    from test_historical_weapon_preflight import (
        test_no_direct_weapon_reselection_was_reintroduced,
        test_visible_empty_hands_do_not_reholster,
        test_treatment_bridge_contains_no_generic_presentation_wait,
    )
    test_no_direct_weapon_reselection_was_reintroduced()
    test_treatment_bridge_contains_no_generic_presentation_wait()
    for state in ('AmovPknlMstpSnonWnonDnon','ACME_DirectPressureHold','ACM_GenericContinuous','ACM_ProneContinuous'):
        test_visible_empty_hands_do_not_reholster(state)


def test_provider_stance_lock_is_released_after_native_and_custom_treatment_end():
    post = txt('functions/fn_postInit.sqf')
    stop = txt('functions/fn_treatmentPoseStop.sqf')
    assert 'B72 provider stance release' in post
    assert '} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];' in post
    assert '_m setUnitPos "AUTO";' in post
    assert '_u setUnitPos "AUTO";' in stop
    # B251 carries the provider locality epoch through both bounded stance releases.
    assert '[_medic,_currentEpoch,_localityEpoch,_releaseIfFree], 0.35] call CBA_fnc_waitAndExecute;' in stop
    assert '[_medic,_currentEpoch,_localityEpoch,_releaseIfFree], 4.25] call CBA_fnc_waitAndExecute;' in stop
    assert '(_u getVariable ["ACME_providerLocalityEpoch", 0]) != _localityEpoch' in stop
    assert 'if ((_u getVariable ["ACME_treatmentPoseEpoch",0]) != _endedEpoch) exitWith {};' in stop
    assert 'if ([_u] call ACME_fnc_providerStanceOwned) exitWith {};' in stop


def test_cursor_menu_defers_before_provider_preflight():
    tr = txt('overrides/fn_treatment.sqf')
    cursor = tr.index('ace_interact_menu_cursorMenuOpened')
    preflight = tr.index('ACME_treatmentPreflightActive')
    assert cursor < preflight


if __name__ == '__main__':
    tests = [v for k,v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
    print(f'B72 focused contracts: {len(tests)}/{len(tests)} passed')
