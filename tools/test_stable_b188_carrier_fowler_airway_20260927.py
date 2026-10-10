#!/usr/bin/env python3
"""Stable B188: manual plate carrier and Semi-Fowler share one physical custody/animation lifecycle."""
from build_contract import assert_current_build as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_manual_carrier_head_elev_support_helper_is_registered_and_nonduplicating():
    cfg = read("addons/acm_extended/config.cpp")
    helper = read("addons/acm_extended/functions/fn_manualPlateCarrierHeadElevSupport.sqf")

    assert "class manualPlateCarrierHeadElevSupport {};" in cfg
    assert 'getVariable ["ACME_chestAccess_vestLoadout", []]' in helper
    assert 'getVariable ["ACME_chestAccess_vestProp", objNull]' in helper
    assert 'setVariable ["ACME_headElev_manualCarrierBorrowed", true, true]' in helper
    assert 'setVariable ["ACME_headElev_propObj", _prop, true]' in helper

    # Borrowing must not remove another vest or spawn a second prop.
    assert "removeVest" not in helper
    assert "createSimpleObject" not in helper
    assert "createVehicle" not in helper


def test_manual_carrier_eligibility_uses_unambiguous_hemtt_safe_alive_checks():
    s = read("addons/acm_extended/functions/fn_manualPlateCarrierCanToggle.sqf")
    assert 'if (!(alive _medic)) exitWith {false};' in s
    assert 'if (!([_medic] call ace_common_fnc_isAwake)) exitWith {false};' in s
    # B208 permits corpse equipment access; only a living, awake patient blocks removal.
    assert 'if (!(alive _patient)) exitWith {false};' not in s
    assert 'private _awake = alive _patient && {' in s
    assert '!alive _medic || {!([_medic] call ace_common_fnc_isAwake)}' not in s


def test_manual_removal_still_uses_patient_grab_and_release_before_success():
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    commit = read("addons/acm_extended/functions/fn_manualPlateCarrierCommit.sqf")

    assert '"ACME_HeadElevPatientGrab"' in acquire
    assert '"ACME_HeadElevPatientRelease"' in acquire
    assert 'call ACME_fnc_patientAnimRequest' in acquire

    wait = commit.split('[_patient, _medic, _lease, true, "manualplatecarrier", _lease]', 1)[1]
    condition = wait.split('[{', 1)[1].split('}, {', 1)[0]
    assert '(count _saved) == 2' in condition
    assert '(vest _p) == ""' in condition
    assert '(_p getVariable ["ACME_chestAccess_vestBusy", ""]) == ""' in condition


def test_semi_fowler_start_borrows_manual_carrier_instead_of_unsupported_hold():
    s = read("addons/acm_extended/functions/fn_headElevateStart.sqf")
    borrow = s.index('ACME_fnc_manualPlateCarrierHeadElevSupport')
    manual = s.index('private _manual = !_hasBag && {!_hasCarrier} && {!_manualCarrierSupport};')
    assert borrow < manual
    assert '(_patient getVariable ["ACME_manualPlateCarrierState", ""]) == "off"' in s
    assert 'if (!_manualCarrierSupport) then {' in s


def test_semi_fowler_lift_reuses_existing_manual_prop_after_patient_lifts():
    s = read("addons/acm_extended/functions/fn_headElevApplyTilt.sqf")
    assert 'private _prop = _patient getVariable ["ACME_headElev_propObj", objNull];' in s
    assert 'if (isNull _prop) then {' in s
    assert '_prop setVariable ["ACME_chestFixedPark", nil, false];' in s
    assert '[_patient] call ACME_fnc_headElevPropApply;' in s

    # Placement remains delayed until after the authored lift starts.
    assert '_liftTime + 0.1] call CBA_fnc_waitAndExecute;' in s


def test_chest_access_watchdog_does_not_pull_borrowed_carrier_out_from_under_patient():
    s = read("addons/acm_extended/functions/fn_chestAccessVestPark.sqf")
    assert 'ACME_headElev_manualCarrierBorrowed' in s
    assert 'ACME_headElevated' in s
    assert 'ACME_headElev_Suspended' in s
    assert 'call ACME_fnc_headElevPropApply' in s


def test_manual_removal_of_elevated_patient_resumes_semi_fowler_when_done():
    # B264 extracted the actual once-per-lease commit to one owner worker, so
    # the old callback and a newly migrated patient owner share this code.
    complete = read("addons/acm_extended/functions/fn_manualPlateCarrierCompleteRemoval.sqf")
    block = complete.split('_p setVariable ["ACME_manualPlateCarrierState", "off", true];', 1)[1]

    assert 'ACME_headElevated' in block
    assert 'ACME_headElev_Suspended' in block
    assert '[_p, "borrow"] call ACME_fnc_manualPlateCarrierHeadElevSupport;' in block
    assert 'setVariable ["ACME_headElev_ResumePending", true, true]' in block
    assert 'call ACME_fnc_headElevTryResume' in block


def test_manual_lease_does_not_deadlock_semi_fowler_resume():
    s = read("addons/acm_extended/functions/fn_headElevTryResume.sqf")
    assert 'private _manualLease = _patient getVariable ["ACME_manualPlateCarrierLease", ""];' in s
    assert 'private _blockingChestLeases = (keys _chestLeases) select {_x != _manualLease};' in s
    assert '(count _blockingChestLeases) > 0' in s


def test_borrowed_resume_replays_provider_and_patient_semi_fowler_choreography():
    s = read("addons/acm_extended/functions/fn_headElevResume.sqf")
    provider = s.index('[_provider, "headElevMedicStart", [_provider, _patient]] call ACME_fnc_ownerDispatch;')
    patient = s.index('private _resumed = [_patient] call ACME_fnc_headElevApplyTilt;')
    assert provider < patient
    assert 'ACME_headElev_manualCarrierBorrowed' in s


def test_lower_head_releases_borrowed_support_back_to_manual_park_not_chest():
    restore = read("addons/acm_extended/functions/fn_headElevVestRestore.sqf")
    helper = read("addons/acm_extended/functions/fn_manualPlateCarrierHeadElevSupport.sqf")

    assert 'if (_patient getVariable ["ACME_headElev_manualCarrierBorrowed", false]) exitWith {' in restore
    assert '[_patient, "release"] call ACME_fnc_manualPlateCarrierHeadElevSupport;' in restore
    assert '[_patient] call ACME_fnc_chestAccessVestPark;' in helper


def test_wake_getup_transport_auto_return_cancels_borrowed_semi_fowler_before_revesting():
    auto = read("addons/acm_extended/functions/fn_manualPlateCarrierAutoReturn.sqf")
    getup = read("addons/core/functions/fnc_getUp.sqf")
    runtime = read("addons/acm_extended/functions/fn_registerManualPlateCarrierRuntime.sqf")

    stop = auto.index('[objNull, _patient, true, true] call ACME_fnc_headElevateStop;')
    lease = auto.index('private _leases = _patient getVariable ["ACME_chestAccess_leases", createHashMap];')
    restore = auto.index('[_patient, true, _provider, "access", true] call ACME_fnc_chestAccessVestRestore;')
    assert stop < lease < restore

    assert '[_patient, "getup"] call ACME_fnc_manualPlateCarrierAutoReturn;' in getup
    assert '"ace_dragging_setupDrag"' in runtime
    assert '"ace_dragging_setupCarry"' in runtime
    assert '_awake || {_transported} || {_moved} || {_externalVest}' in runtime


def test_airway_removal_still_disconnects_ventilator():
    igel = read("addons/airway/functions/fnc_removeAirwayItem.sqf")
    dispatch = read("addons/acm_extended/functions/fn_ownerDispatch.sqf")

    assert '[_patient, _medic, "i-gel removed"] call ACME_fnc_ventAirwayLoss;' in igel
    extubate = dispatch.split('case "ettExtubate": {', 1)[1].split('case "laryngoConsequence"', 1)[0]
    assert '[_patient, _medic, "ETT removed"] call ACME_fnc_ventAirwayLoss;' in extubate


def test_build_identity_is_b188_stable():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B188 carrier/Semi-Fowler/airway regression: PASS")
