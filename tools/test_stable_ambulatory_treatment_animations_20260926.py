#!/usr/bin/env python3
"""Stable B177: standing/crouched ambulatory presentation uses medicUp and a frozen stethoscope contact reach."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_ambulatory_patient_gate_is_conscious_on_foot_and_standing_or_crouched():
    s = read("addons/acm_extended/functions/fn_patientUpright.sqf")
    assert 'getVariable ["ACE_isUnconscious", false]' in s
    assert 'getVariable ["ace_medical_unconscious", false]' in s
    assert 'isNull objectParent _patient' in s
    assert '(stance _patient) in ["STAND", "CROUCH"]' in s
    assert '"PRONE"' not in s
    assert 'ACME_headElevated' in s
    assert 'ACME_headElev_Suspended' in s


def test_conscious_prone_patient_keeps_normal_provider_pose_but_no_patient_settle():
    upright = read("addons/acm_extended/functions/fn_patientUpright.sqf")
    settle = read("addons/acm_extended/functions/fn_treatmentPatientSettle.sqf")
    roll = read("addons/acm_extended/functions/fn_chestSealCanPhysicalRoll.sqf")

    assert '"PRONE"' not in upright
    assert '(stance _patient) in ["STAND", "CROUCH", "PRONE"]' in settle
    assert 'if (_independentlyConscious) exitWith {};' in settle
    assert 'A manual prone stance is NEVER permission to seize a conscious player' in roll
    assert 'if (_unconscious) exitWith {true};' in roll


def test_medicup_map_uses_real_kneeling_empty_hands_family_and_runtime_fallback():
    init = read("addons/acm_extended/functions/fn_initChestSealProcedureRuntime.sqf")
    choose = read("addons/acm_extended/functions/fn_poseUprightState.sqf")

    for idx in (0, 1, 2, 3, 4, 5):
        assert f"AinvPknlMstpSnonWnonDnon_medicUp{idx}" in init
    assert "AinvPercMstp" not in init.split("ACME_poseUprightStates", 1)[1].split("];", 1)[0]
    for mode in ("chestSealWorkspace", "chestSeal", "ncdSeat", "pulse", "inspect", "response", "airway"):
        assert f'["{mode}"' in init
    assert 'isClass (configFile >> "CfgMovesMaleSdr" >> "States" >> _candidate)' in choose
    assert '[_normal, false]' in choose


def test_treatment_pose_selects_ambulatory_provider_presentation_only():
    s = read("addons/acm_extended/functions/fn_treatmentPoseStart.sqf")
    assert 'private _ambulatoryPatient = [_patient] call ACME_fnc_patientUpright;' in s
    assert 'call ACME_fnc_poseUprightState' in s
    assert 'AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown' in s
    assert 'private _ambulatoryContact = false;' in s
    assert '_ambulatoryContact];' in s
    assert '_medic setUnitPos "MIDDLE";' in s
    assert '["MIDDLE", "UP"] select' not in s
    assert 'private _recoverAmbulatoryHold = (_state param [16,false]) || {_state param [19,false]};' in s


def test_stethoscope_freezes_putdown_reach_and_resumes_authored_exit():
    init = read("addons/acm_extended/functions/fn_initChestSealProcedureRuntime.sqf")
    begin = read("addons/acm_extended/functions/fn_beginStethoscopeAction.sqf")
    close = read("addons/acm_extended/functions/fn_stethoscopeClose.sqf")
    seq = read("addons/acm_extended/functions/fn_headElevMedicSeq.sqf")

    assert 'ACME_uprightStethoscopeHoldAt = 0.55;' in init
    assert '[_medic, "stethoscope", -1, _patient] call ACME_fnc_treatmentPoseStart' in begin
    assert '_poseStateAtClose param [19,false]' in close
    assert '["lower", "contactexit"] select _ambulatoryContact' in close
    assert '"contactexit"' in seq
    assert '[_u] call ace_common_fnc_isPlayer' in seq
    assert "ACE_player" not in seq
    contact = seq.split('if (_mode == "contactexit") then {', 1)[1].split('} else {', 1)[0]
    assert '[_u, _second, 1] call ACME_fnc_doAnim;' in contact
    assert '_first' not in contact


def test_nar_spear_temporarily_hands_off_from_workspace_and_returns():
    gesture = read("addons/acm_extended/functions/fn_treatmentGesture.sqf")
    ncd = read("addons/acm_extended/functions/fn_chestSealApplyNCD.sqf")
    assert '_existingMode == "chestSealWorkspace"' in gesture
    assert '_mode == "ncdSeat"' in gesture
    assert '[_medic, _mode, _window, _patient] call ACME_fnc_treatmentPoseStart;' in gesture
    assert 'call ACME_fnc_chestSealProviderHoldStart' in gesture
    assert '[_medic,"ncdSeat",2.0,_patient] call ACME_fnc_treatmentGesture;' in ncd


def test_chest_seal_placement_reasserts_selected_pose_not_hardcoded_down_pose():
    seal = read("addons/acm_extended/functions/fn_chestSealApply.sqf")
    assert 'private _poseMain = _state param [2, "AinvPknlMstpSnonWnonDnon_medic3"];' in seal
    assert '(toLowerANSI animationState _m) != (toLowerANSI _poseMain)' in seal
    assert '[_m, _poseMain, 1] call ACME_fnc_doAnim;' in seal


def test_upright_helpers_remain_registered():
    cfg = read("addons/acm_extended/config.cpp")
    assert "class patientUpright {};" in cfg
    assert "class poseUprightState {};" in cfg


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B177 ambulatory treatment animation regression: PASS")
