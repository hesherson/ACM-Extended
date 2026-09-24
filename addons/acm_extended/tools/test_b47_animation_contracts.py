from historical_source import read_source, assert_release_identity
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
def txt(rel): return read_source(ROOT / rel, errors='ignore')

def block(src, name):
    m = re.search(r'class\s+' + re.escape(name) + r'\b[^\{]*\{', src)
    assert m, name
    i = m.end(); depth = 1
    while i < len(src) and depth:
        if src[i] == '{': depth += 1
        elif src[i] == '}': depth -= 1
        i += 1
    return src[m.start():i]

def test_version_batch():
    assert_release_identity()
    assert_release_identity()

def test_exact_requested_motion_wrappers():
    from test_historical_pose_lifecycle import WRAPPERS, test_work_wrappers_keep_authored_entry_exit_and_weapon_restrictions
    for args in WRAPPERS:
        test_work_wrappers_keep_authored_entry_exit_and_weapon_restrictions(*args)

def test_check_response_five_seconds_custom_pose():
    b = block(txt('config.cpp'),'CheckResponse')
    assert 'treatmentTime = 5;' in b
    assert "'response', 5" in b
    assert 'ace_medical_treatment_fnc_checkResponse' in b
    assert "'response'] call ACME_fnc_treatmentPoseStop" in b
    for k in ['animationMedic = ""','animationMedicProne = ""']:
        assert k in b

def test_check_airway_medic4_old_custom_pose():
    c = txt('config.cpp'); b = block(c,'CheckAirway')
    assert 'ACME_fnc_airwayMedicPose' in b
    assert 'ACM_airway_fnc_checkAirway' in b
    assert "'airway'] call ACME_fnc_treatmentPoseStop" in b
    f = txt('functions/fn_airwayMedicPose.sqf')
    assert 'checkairway' in f.lower() and '"airway", 2.5' in f

def test_inspect_chest_six_seconds():
    b = block(txt('config.cpp'),'ACME_InspectChest')
    assert 'treatmentTime = 6;' in b
    assert 'callbackStart = "_this call ACME_fnc_inspectChestPoseStart"' in b
    assert '[_medic, "inspect", 6, _patient]' in txt('functions/fn_inspectChestPoseStart.sqf')

def test_shared_pose_timing_and_clean_exit():
    from test_historical_pose_lifecycle import test_selected_assessment_states_are_crouch_authored_not_standing_substitutes, test_ordinary_cleanup_remains_bounded_and_releases_temporary_stance
    for mode,main in [('roll','AinvPknlMstpSnonWnonDnon_medic4'),('inspect','ACME_ChestInspectWork'),('pulse','ACME_StethoscopeWork')]:
        test_selected_assessment_states_are_crouch_authored_not_standing_substitutes(mode,main)
    for stance in ('STAND','CROUCH'):
        test_ordinary_cleanup_remains_bounded_and_releases_temporary_stance(stance)
    # Entry owns weapon handling; stopping must not reselect or repeatedly holster a weapon.
    assert 'selectWeapon' not in txt('functions/fn_treatmentPoseStop.sqf')

def test_stethoscope_hold_is_minigame_owned():
    from test_historical_pose_lifecycle import (
        test_owner_freeze_uses_current_mode_timeline_despite_frame_overshoot,
        test_duplicate_hold_reuses_one_observer_worker_and_release_is_idempotent,
    )
    for duration in (3,12):
        test_owner_freeze_uses_current_mode_timeline_despite_frame_overshoot('stethoscope',.421,duration)
    test_duplicate_hold_reuses_one_observer_worker_and_release_is_idempotent()
    b = txt('functions/fn_beginStethoscopeAction.sqf')
    assert '[_medic, "stethoscope", _poseEpoch, true] call ACME_fnc_treatmentPoseStop' in b

def test_tsp_animate_rewrite_optional_sling_support():
    # The current preflight deliberately uses ACE/engine holstering, not TSP sling callbacks.
    c = txt('config.cpp')
    assert 'class medicAnimationPrep {};' in c
    req = c.split('requiredAddons[] = {',1)[1].split('};',1)[0]
    assert 'tsp_animate' not in req
    from test_historical_weapon_preflight import test_one_engine_holster_request_is_retained_across_repeated_controllers, test_engine_fallback_has_same_provider_and_switchweapon_contract
    test_one_engine_holster_request_is_retained_across_repeated_controllers('pistol',0.95,True)
    test_engine_fallback_has_same_provider_and_switchweapon_contract()

def test_roll_uses_shared_medic4_pose_for_2_5_seconds():
    r = txt('functions/fn_rollProviderStart.sqf')
    assert '["ACME_rollProviderDuration", 2.2]' in r
    assert '[_medic, "roll", _duration, _patient] call ACME_fnc_treatmentPoseStart' in r
    assert '[_unit, "roll", _epoch] call ACME_fnc_treatmentPoseStop' in r
    f = txt('functions/fn_chestSealFlip.sqf')
    assert 'ACME_fnc_rollProviderStart' in f

def test_specific_pose_wins_over_generic_roll():
    p = txt('functions/fn_postInit.sqf')
    assert 'private _poseOwned = (_medic getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []' in p
    assert 'private _isStethoscope = toLower _classname == "usestethoscope"' in p
    assert '{!_poseOwned} && {!_isStethoscope}' in p

def test_auscultate_indentation_normalized():
    s = txt('overrides/fn_updateActions.sqf')
    assert "if (_actionClass == 'usestethoscope')" in s
    assert "private _indent = missionNamespace getVariable ['ACME_menuChildIndent', '        ']" in s
    assert "format ['%1%2', _indent, _baseName]" in s
    assert "_baseName = 'Auscultate Chest'" in s
