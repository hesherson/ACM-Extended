#!/usr/bin/env python3
"""RC22: CBA wait payload and native stethoscope callback-shape regressions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_chest_preflight_condition_unpacks_full_cba_payload():
    s = read("addons/core/overrides/fnc_treatment.sqf")
    start = s.index('params ["_m","_p","_args","_tok","_leaseId","_classKey","_launch","_finish","_abort"];')
    block = s[start:start + 1800]
    assert 'params ["_m","_p","_args","_tok","_leaseId","_classKey","_launch","_finish","_abort"];' in block
    assert 'getVariable ["ACME_chestAccessPreflightToken",""]) != _tok' in block

def test_removal_provider_wait_unwraps_nested_call_args():
    s = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    start = s.index("// _this is [_args,_beginPatient]")
    block = s[start:start + 700]
    assert 'params ["_callArgs","_begin"];' in block
    assert '_callArgs param [1,objNull,[objNull]]' in block
    assert '_callArgs param [8,"",[""]]' in block
    assert 'params ["_m","_token"];' not in block

def test_restore_no_longer_starts_a_second_provider_medic4():
    s = read("addons/acm_extended/functions/fn_chestAccessVestRestore.sqf")
    assert '"chestAccessVestProvider", [_medic, _patient, "start"' not in s
    assert "Provider exit is owned by the minigame/action that is closing." in s

def test_native_stethoscope_callback_accepts_classname_slot():
    s = read("addons/breathing/functions/fnc_useStethoscope.sqf")
    assert 'params ["_medic", "_patient", ["_bodyPart", "Body"]];' in s
    assert '["_entryReady", false, [false]]' not in s
    assert 'private _slot3 = _this param [3, false];' in s
    assert 'if (_slot3 isEqualType true)' in s
    assert 'private _slot4 = _this param [4, false];' in s

def test_rc19_stethoscope_lifetime_still_present():
    s = read("addons/acm_extended/functions/fn_beginStethoscopeAction.sqf")
    assert '["session", [_patient, _epoch]]' in s
    assert 'call ACM_core_fnc_setContinuousActionState' in s
    assert "_args call _onStart;" in s
    assert 'findDisplay _dialogID' in s

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS rc22: chest wait payload + steth callback-shape regressions")
