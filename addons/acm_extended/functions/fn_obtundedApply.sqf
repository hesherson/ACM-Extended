// Owner-local physical application of obtundation.
// B49: obtundation is no longer a forced collapse/posture system. It preserves whatever pose the casualty actually
// occupies. An already-down casualty stays down and gets a deliberately slow Get Up; an upright casualty stays
// upright. The only ragdoll left in this system is the probabilistic stumble when an obtunded player tries to sprint.
params ["_patient", "_on", ["_posture", "free"], ["_reason", "recover"], ["_wasOn", false], ["_wasPosture", ""], ["_token", -1], ["_manual", false]];
if (isNull _patient || {!local _patient}) exitWith {};

private _wasMedicalUncon = _patient getVariable ["ACE_isUnconscious", false];
// Reject a stale transition before it can alter a newer episode or any posture.
if (_token >= 0 && {(_patient getVariable ["ACME_obtunded_transitionToken", _token]) != _token}) exitWith {};
if (_on && {_patient getVariable ["ACE_isUnconscious", false]}
    && {!([_patient, false, "obtunded"] call ACM_core_fnc_requestWake)}) exitWith {
    [_patient, false, false, "", _token, true] call ACME_fnc_obtundedStateCommit;
};


[_patient, _on, _manual, _posture, _token, false] call ACME_fnc_obtundedStateCommit;
_patient setVariable ["ACME_obtunded_transitioning", false, true];
_patient setVariable ["ACME_obtunded_forcedBack", false, true];
_patient setVariable ["ACME_obtunded_treatmentHold", false, true];
_patient setVariable ["ACME_obtunded_collapseInFlight", -1, false];
_patient setVariable ["ACME_obtunded_poseRetryAt", 0, false];

// Retire the attachment helper from pre-B49 forced-posture builds without creating a new one. This keeps hot-loaded
// or saved casualties from remaining attached to an invisible legacy direction anchor.
private _legacyDirHolder = _patient getVariable ["ACME_obtunded_dirHolder", objNull];
if (!isNull _legacyDirHolder) then {
    if ((attachedTo _patient) isEqualTo _legacyDirHolder) then {detach _patient;};
    deleteVehicle _legacyDirHolder;
};
_patient setVariable ["ACME_obtunded_dirHolder", objNull, false];

if (_on) then {
    // If ACE had the casualty medically unconscious, wake the medical state but preserve the fact that they were
    // physically down. Do not play any ACME collapse or posture animation on top of the wake-up.
    if (_wasMedicalUncon) then {
        [_patient, true, true] call ACM_core_fnc_setWasTreated;
        [_patient, true, true] call ACM_core_fnc_setLyingState;
    };
    _patient setUnitPos "AUTO";
    if !(_patient getVariable ["ACME_obtunded_slowGetUp", false]) then {_patient setAnimSpeedCoef 1;};
} else {
    // Clearing the cognitive state never stands, rolls, or ragdolls the casualty. If they are still lying, the normal
    // Get Up action remains available. Clean up a temporary sprint-ragdoll engine state if one was active.
    _patient setUnitPos "AUTO";
    _patient setAnimSpeedCoef 1;
    if (_patient getVariable ["ACME_obtunded_sprintRagdollActive", false]) then {
        _patient setVariable ["ACME_obtunded_sprintRagdollActive", false, true];
        if (!(_patient getVariable ["ACE_isUnconscious", false])) then {_patient setUnconscious false;};
    };
    _patient setVariable ["ACME_obtunded_sprintRagdollToken", [], true];
};
