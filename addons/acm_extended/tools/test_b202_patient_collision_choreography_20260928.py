from historical_source import assert_release_identity as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="strict")


def test_moving_patient_leases_own_collision_relaxation():
    req = read("addons/acm_extended/functions/fn_patientAnimRequest.sqf")
    rel = read("addons/acm_extended/functions/fn_patientAnimRelease.sqf")

    assert 'if (_moving) then {[_patient, false] call ACME_fnc_headElevCollision;};' in req
    assert 'if (!_moving && {_oldSpeedToken != ""}) then {[_patient, true] call ACME_fnc_headElevCollision;};' in req
    assert '[_patient, true] call ACME_fnc_headElevCollision;' in rel
    for anim in (
        "ACME_HeadElevPatientGrab",
        "ACME_HeadElevPatientRelease",
        "AinjPpneMstpSnonWrflDnon_rolltofront",
        "AinjPpneMstpSnonWrflDnon_rolltoback",
    ):
        assert anim in req


def test_collision_restore_is_deferred_and_invalidated_by_new_motion():
    s = read("addons/acm_extended/functions/fn_headElevCollision.sqf")

    assert "ACME_headElev_collisionEpoch" in s
    assert "CBA_fnc_execNextFrame" in s
    assert 'if ((_p getVariable ["ACME_headElev_collisionEpoch", -1]) != _epoch) exitWith {};' in s
    assert '["ace_common_setMass", [_patient, 1e-12]] call CBA_fnc_globalEvent;' in s


def test_new_cpr_or_bvm_waits_for_inflight_carrier_restore():
    treatment = read("addons/core/overrides/fnc_treatment.sqf")

    assert 'private _restoreInFlight = (_chestBusy find "restore:access:") == 0;' in treatment
    assert "private _needsPhysicalPrep = _restoreInFlight" in treatment
    assert treatment.index("private _restoreInFlight") < treatment.index("if (_needsChestAccess")


def test_naloxone_remains_no_roll():
    actions = read("addons/core/ACE_Medical_Treatment_Actions.hpp")
    block = actions.split("class Naloxone: Paracetamol {", 1)[1].split("class FentanylLozenge: Paracetamol {", 1)[0]
    assert "ACM_rollToBack = 0;" in block
    assert "ACME_neverRollToBack = 1;" in block


def test_b203_keeps_public_stable_version_1241():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    config = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
