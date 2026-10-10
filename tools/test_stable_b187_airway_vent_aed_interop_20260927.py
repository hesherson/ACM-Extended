#!/usr/bin/env python3
"""Stable B188: airway removal tears down Ventway custody and Ventway CPR ventilation does not deadlock the AED."""
from build_contract import assert_current_build as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_airway_loss_helper_is_registered_and_owner_routed():
    cfg = read("addons/acm_extended/config.cpp")
    dispatch = read("addons/acm_extended/functions/fn_ownerDispatch.sqf")
    helper = read("addons/acm_extended/functions/fn_ventAirwayLoss.sqf")

    assert "class ventAirwayLoss {};" in cfg
    assert 'case "ventAirwayLoss": {_args call ACME_fnc_ventAirwayLoss;};' in dispatch
    assert '[_patient, "ventAirwayLoss", [_patient, _medic, _reason]] call ACME_fnc_ownerDispatch;' in helper


def test_igel_removal_disconnects_ventway_before_clearing_oral_airway():
    s = read("addons/airway/functions/fnc_removeAirwayItem.sqf")
    branch = s.split("} else {", 1)[1]

    check = branch.index('if (_airway == "SGA"')
    disconnect = branch.index('call ACME_fnc_ventAirwayLoss;', check)
    clear = branch.index('_patient setVariable [QGVAR(AirwayItem_Oral), "", true];', disconnect)

    assert check < disconnect < clear
    assert '"i-gel removed"' in branch


def test_extubation_disconnects_ventway_before_ett_state_is_cleared():
    s = read("addons/acm_extended/functions/fn_ownerDispatch.sqf")
    block = s.split('case "ettExtubate": {', 1)[1].split('case "laryngoConsequence"', 1)[0]

    disconnect = block.index('[_patient, _medic, "ETT removed"] call ACME_fnc_ventAirwayLoss;')
    remove = block.index('[_patient, false, false, false, false, true, false] call ACME_fnc_ettAirwayStateCommit;')

    assert disconnect < remove
    assert 'setVariable ["ACME_vent_connected", false' not in block
    assert 'setVariable ["ACME_vent_driving", false' not in block


def test_airway_loss_stops_clinical_ventilation_immediately_and_requests_full_custody_return():
    s = read("addons/acm_extended/functions/fn_ventAirwayLoss.sqf")

    clear = s.index('[_patient, _custody, false] call ACME_fnc_ventPatientClear;')
    request = s.index('["ACME_ventCustodyRequest", ["airwayLoss", _medic, _patient]] call CBA_fnc_serverEvent;')
    assert clear < request

    for state in (
        "ACME_vent_onPatient",
        "ACME_vent_connected",
        "ACME_vent_driving",
        "ACME_vent_circuit",
        "ACME_vent_configured",
    ):
        assert state in s


def test_server_airway_loss_return_is_not_blocked_by_ventilator_procedure_gate():
    s = read("addons/acm_extended/functions/fn_ventCustodyRequest.sqf")
    block = s.split('if (_op == "airwayLoss") exitWith {', 1)[1].split('if (_op == "attach") exitWith {', 1)[0]

    assert 'ACME_fnc_procedureAllowed' not in block
    assert '_r set ["recipient", _medic];' in block
    assert '_r set ["phase", "returning"];' in block
    assert '_patient setVariable ["ACME_vent_recovering", true, true];' in block
    assert '"ACME_ventPatientClear"' in block
    assert "ACME_fnc_ventCustodyTick" in block


def test_ventway_patient_bvm_sentinel_does_not_count_as_aed_motion():
    analyze = read("addons/circulation/functions/fnc_AED_AnalyzeRhythm.sqf")
    motion = read("addons/circulation/functions/fnc_AED_MotionDetected.sqf")

    for s in (analyze, motion):
        assert 'private _bvmProvider' in s
        assert '_bvmProvider isNotEqualTo _patient' in s
        assert 'private _realBvmMotion' in s

    # The old predicate treated the patient sentinel as a living bagger forever.
    assert 'alive (_patient getVariable ["ACM_breathing_BVM_provider", objNull])' not in analyze
    assert 'alive (_patient getVariable [QEGVAR(breathing,BVM_provider), objNull])' not in motion


def test_real_cpr_and_real_bvm_still_block_aed_analysis_as_motion():
    analyze = read("addons/circulation/functions/fnc_AED_AnalyzeRhythm.sqf")
    motion = read("addons/circulation/functions/fnc_AED_MotionDetected.sqf")

    assert 'ace_medical_CPR_provider' in analyze
    assert 'QACEGVAR(medical,CPR_provider)' in motion
    assert '|| {_realBvmMotion}' in analyze
    assert '|| {_realBvmMotion}) then {' in motion


def test_manual_charge_and_shock_eligibility_are_not_gated_by_ventway_bvm_sentinel():
    charge = read("addons/circulation/functions/fnc_AED_CanManualCharge.sqf")
    shock = read("addons/circulation/functions/fnc_AED_CanAdministerShock.sqf")

    for s in (charge, shock):
        assert "BVM_provider" not in s
        assert "ACME_vent" not in s


def test_build_identity_is_b187_stable():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B188 airway/vent/AED interoperability regression: PASS")
