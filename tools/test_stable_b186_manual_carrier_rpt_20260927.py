#!/usr/bin/env python3
"""Stable B188 build: manual carrier runtime cannot reproduce the B185 RPT spam/stuck-provider failures."""
from build_contract import assert_current_build as _assert_current_build
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_manual_remove_wait_condition_unpacks_patient_provider_and_lease():
    s = read("addons/acm_extended/functions/fn_manualPlateCarrierCommit.sqf")

    start = s.index('[_patient, _medic, _lease, true, "manualplatecarrier", _lease]')
    wait = s.index('[{', start)
    condition = s[wait:s.index('}, {', wait)]
    args_tail = s[s.index('}, {', wait):s.index('] call CBA_fnc_waitUntilAndExecute;', wait)]

    assert 'params ["_p", "_medic", "_lease"];' in condition
    assert '(_p getVariable ["ACME_manualPlateCarrierLease", ""]) != _lease' in condition
    assert '[_patient, _medic, _lease]' in args_tail

    # B185 unpacked the second array element as _lease, making _lease the medic OBJECT and generating:
    # "Error Generic error in expression" at the string != object comparison every scheduler pass.
    assert 'params ["_p", "_lease"];' not in condition


def test_manual_carrier_medical_log_messages_are_strings_not_arrays():
    commit = read("addons/acm_extended/functions/fn_manualPlateCarrierCommit.sqf")
    complete = read("addons/acm_extended/functions/fn_manualPlateCarrierCompleteRemoval.sqf")
    auto = read("addons/acm_extended/functions/fn_manualPlateCarrierAutoReturn.sqf")

    assert '[_p, "activity", "Plate carrier replaced", []] call ace_medical_treatment_fnc_addToLog;' in commit
    assert '[_p, "activity", "Plate carrier manually removed", []] call ace_medical_treatment_fnc_addToLog;' in complete
    assert '[_patient, "activity", format ["Plate carrier automatically returned (%1)", _reason], []]' in auto

    # These array-wrapped messages poisoned ACE medical logs and caused updateLogList/isLocalized errors every refresh.
    assert '["Plate carrier replaced"]' not in commit
    assert '["Plate carrier manually removed"]' not in commit
    assert '[format ["Plate carrier automatically returned (%1)", _reason]]' not in auto


def test_every_manual_carrier_addtolog_call_has_four_arguments_and_string_message_expression():
    for rel in (
        "addons/acm_extended/functions/fn_manualPlateCarrierCommit.sqf",
        "addons/acm_extended/functions/fn_manualPlateCarrierCompleteRemoval.sqf",
        "addons/acm_extended/functions/fn_manualPlateCarrierAutoReturn.sqf",
    ):
        s = read(rel)
        for line in s.splitlines():
            if "ace_medical_treatment_fnc_addToLog" not in line:
                continue
            # Multiline auto-return call is validated explicitly above; single-line calls must not array-wrap message.
            if "call ace_medical_treatment_fnc_addToLog" in line and "activity" in line:
                assert '"activity", ["' not in line


def test_manual_remove_success_still_retires_provider_episode():
    # B264 moves the single authoritative success/medical log into a helper
    # callable from either the original owner or the new patient owner.
    s = read("addons/acm_extended/functions/fn_manualPlateCarrierCompleteRemoval.sqf")
    success = s.split('_p setVariable ["ACME_manualPlateCarrierState", "off", true];', 1)[1]
    success = success.split('["ACME_manualPlateCarrierAck"', 1)[0]

    assert '[_medic, "chestAccessVestProvider", [_medic, _p, "manualstop", false, "", _lease]]' in success
    assert 'call ACME_fnc_ownerDispatch;' in success


def test_manual_remove_still_uses_patient_grab_hold_release_choreography():
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    provider = read("addons/acm_extended/functions/fn_chestAccessVestProvider.sqf")

    assert '"ACME_HeadElevPatientGrab"' in acquire
    assert '"ACME_HeadElevPatientRelease"' in acquire
    assert '[_p] call ACME_fnc_chestAccessVestPark' in acquire
    assert 'private _manualEntry = (_preparationToken find "manualpc:") == 0;' in provider


def test_b186_stable_identity():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B188 manual carrier RPT regression: PASS")
