#!/usr/bin/env python3
"""Stable B177: thoracostomy preparation is providerless and cannot strand medic4."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_thoracostomy_uses_patient_only_chest_access_preparation():
    open_fn = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    assert '[_patient, _medic, _lease, true, "thoracostomy", _lease] call ACME_fnc_chestAccessVestEvent;' in open_fn
    assert 'private _releaseProvider = {' not in open_fn
    assert 'if (_treatmentClass == "thoracostomy") exitWith {' in acquire
    block = acquire.split('if (_treatmentClass == "thoracostomy") exitWith {',1)[1].split('if (_context == "chestseal") then {',1)[0]
    assert 'call ACME_fnc_chestAccessVestProvider' not in block
    assert '_patientArgs call _beginPatient;' in block
    assert 'call CBA_fnc_waitAndExecute;' in block

def test_menu_close_and_preparing_banner_are_owned_until_ready_or_abort():
    open_fn = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    assert 'ACME_chestAccessPreflightActive", true' in open_fn
    assert 'ace_medical_gui_menuDisplay' in open_fn
    assert '_menuDisplay closeDisplay 1;' in open_fn
    assert 'closeDialog 0;' in open_fn
    assert '[true, _medic, _patient, _lease] call ACME_fnc_chestAccessPreparing;' in open_fn
    assert 'ACME_chestAccess_readyLease' in open_fn
    assert 'ACME_chestAccess_readyServer' in open_fn
    assert 'CBA_fnc_waitUntilAndExecute' in open_fn

def test_cancel_timeout_and_close_release_one_lease_and_clear_preflight():
    open_fn = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    close_fn = read("addons/acm_extended/functions/fn_thoraClose.sqf")
    assert 'private _releaseLease = {' in open_fn
    assert '[_p, _m, _lease, false, "thoracostomy"] call ACME_fnc_chestAccessVestEvent;' in open_fn
    assert 'Chest-access preparation timed out' in open_fn
    assert '[_p, _m, _lease, _finish, _release, true] call _abort;' in open_fn
    for src in (open_fn, close_fn):
        assert 'ACME_chestAccessPreflightActive", false' in src
        assert 'ACME_chestAccessPreflightToken", ""' in src
        assert 'ACME_chestAccessPreflightCancel", false' in src
    assert '[_patient, _medic, _lease, false, "thoracostomy"] call ACME_fnc_chestAccessVestEvent;' in close_fn

def test_close_keeps_only_legacy_stale_provider_recovery():
    close_fn = read("addons/acm_extended/functions/fn_thoraClose.sqf")
    assert 'Hot-load/backward compatibility only: current thoracostomy never starts this provider animation.' in close_fn
    assert '[_medic, _patient, "stop", false, _oldToken] call ACME_fnc_chestAccessVestProvider;' in close_fn

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B177 thoracostomy providerless preparation: PASS")
