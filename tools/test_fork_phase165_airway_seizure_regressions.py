#!/usr/bin/env python3
"""RC21: head-tilt, Semi-Fowler auscultation, and multiplayer seizure presentation regressions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_head_tilt_launcher_bypasses_generic_async_preflight():
    s = read("addons/core/overrides/fnc_treatment.sqf")
    direct = s.index('_nativeContinuousClass == "beginheadtiltchinlift"')
    generic = s.index('private _bypass = _medic getVariable ["ACME_treatmentPreflightBypass"')
    assert direct < generic
    assert '_this call ACM_core_fnc_treatmentNative' in s[direct:s.index('if (_nativeContinuousClass in ["usebvm"', direct)]

def test_head_tilt_releases_its_exact_continuous_epoch():
    s = read("addons/airway/functions/fnc_beginHeadTiltChinLift.sqf")
    assert 'private _ownedEpoch = missionNamespace getVariable [QGVAR(HeadTiltEpoch), -1];' in s
    assert '[_medic, _patient, _ownedEpoch, "ACM_airway_HeadTilt_State"]' in s

def test_manual_semifowler_is_suspended_not_cancelled_for_other_maneuvers():
    s = read("addons/acm_extended/functions/fn_headElevSuspend.sqf")
    assert '[_patient] call ACME_fnc_headElevHoldClear;' in s
    assert 'exitWith {[objNull, _patient] call ACME_fnc_headElevateStop;};' not in s

def test_semifowler_chest_ready_waits_for_actual_face_up_body():
    s = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    block = s.split("// No worn carrier:", 1)[1].split("private _commitRemoval", 1)[0]
    assert '_patient setVariable [_readyVar, -1, true];' in block
    assert 'ACME_fnc_chestSealActualSide' in block
    assert '_actual == "front"' in block
    assert 'CBA_fnc_waitUntilAndExecute' in block

def test_auscultation_trusts_exact_completed_chest_prep():
    s = read("addons/breathing/functions/fnc_useStethoscope.sqf")
    assert 'ACME_chestAccess_readyLease' in s
    assert 'ACME_chestAccess_readyServer' in s
    assert '_entryReady = true;' in s
    assert 'setVariable ["ACME_CS_facing", "front", true]' in s

def test_seizure_gestures_have_explicit_multiplayer_sync():
    cfg = read("addons/acm_extended/config.cpp")
    owner = read("addons/acm_extended/functions/fn_ownerInit.sqf")
    sync = read("addons/acm_extended/functions/fn_seizureGestureSync.sqf")
    advance = read("addons/acm_extended/functions/fn_seizureGestureAdvance.sqf")
    assert "class seizureGestureSync {};" in cfg
    assert '"ACME_seizureGestureSync"' in owner
    assert 'CBA_fnc_globalEvent' in advance
    assert '_patient switchGesture [_next,0,1,false];' not in advance
    assert 'switchGesture [_gesture, 0, 1, false]' in sync
    assert '!hasInterface && {!local _patient}' in sync

def test_seizure_visuals_are_suppressed_in_vehicles():
    motion = read("addons/acm_extended/functions/fn_seizureMotion.sqf")
    advance = read("addons/acm_extended/functions/fn_seizureGestureAdvance.sqf")
    sync = read("addons/acm_extended/functions/fn_seizureGestureSync.sqf")
    assert '_on && {!isNull objectParent _patient}' in motion
    assert "ACME_seizure_vehicleVisualSuppressed" in motion
    assert '!isNull objectParent _patient' in advance
    assert '!isNull objectParent _patient' in sync
    assert '[_patient,false] call ACME_fnc_seizureMotion;' in motion

def test_debug_and_tbi_still_share_authoritative_seizure_driver():
    debug = read("addons/acm_extended/functions/fn_debugInduceSeizure.sqf")
    tox = read("addons/acm_extended/functions/fn_lidoToxTick.sqf")
    assert '[_patient,true] call ACME_fnc_seizureMotion;' in debug
    assert '[_patient, true] call ACME_fnc_seizureMotion;' in tox
    assert 'private _tbiPreHern' in tox

def test_cric_and_rc19_steth_lifetimes_are_unchanged():
    steth = read("addons/acm_extended/functions/fn_beginStethoscopeAction.sqf")
    cric = read("addons/airway/functions/fnc_establishSurgicalAirway.sqf")
    assert 'ACM_core_ContinuousAction_Session", [_patient, _epoch]' in steth
    assert "SurgicalAirway_InProgress_Session" not in cric

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS rc21: airway + Semi-Fowler + seizure multiplayer regressions")
