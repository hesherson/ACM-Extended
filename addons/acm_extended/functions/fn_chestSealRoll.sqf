// Physical front/back roll used by the chest-seal Flip button.
// This function owns ONLY the casualty. Provider theatre starts on the medic's client in fn_chestSealFlip.
params [
    ["_patient", objNull, [objNull]],
    ["_target", "front", [""]],
    ["_force", false, [false]],
    ["_provider", objNull, [objNull]],
    ["_preserveSuspendedHeadElevation", false, [false]]
];
if (isNull _patient || {!(_target in ["front", "back"])}) exitWith {};

if (!local _patient) exitWith {
    [_patient, "chestSealRoll", [_patient, _target, _force, _provider, _preserveSuspendedHeadElevation]] call ACME_fnc_ownerDispatch;
};

// Owner-authoritative final gate. A provider cannot force a physical patient animation merely because
// the casualty is prone, obtunded, or carries stale chest-procedure state.
if !([_patient] call ACME_fnc_chestSealCanPhysicalRoll) exitWith {};

// Outside this minigame a body roll must tear down head elevation normally. Inside it, Semi-Fowler is only
// suspended, so the front/back roll theatre must not destroy the logical posture we will restore on exit.
if !(_patient getVariable ["ACME_CS_ProcedureActive", false]) then {
    if (!_preserveSuspendedHeadElevation) then {
        [_patient] call ACME_fnc_headElevYieldForRoll;
    };
};

private _actual = [_patient, _patient getVariable ["ACME_CS_facing", "front"]] call ACME_fnc_chestSealActualSide;
_patient setVariable ["ACME_CS_facing", _actual, true];
if (!_force && {_actual isEqualTo _target}) exitWith {};

// Never invent a different diagram side when the body itself cannot be animated.
if ((!alive _patient) || {(lifeState _patient) isEqualTo "DEAD"} || {!isNull objectParent _patient}) exitWith {};

private _trans = if (_target isEqualTo "back") then {
    // posterior up -> patient rolls onto the front
    "AinjPpneMstpSnonWrflDnon_rolltofront"
} else {
    // anterior up -> patient rolls onto the back
    "AinjPpneMstpSnonWrflDnon_rolltoback"
};
private _hold = if (_target isEqualTo "back") then {
    missionNamespace getVariable ["ACME_uncon_faceDown", "ace_medical_engine_uncon_anim_1"]
} else {
    missionNamespace getVariable ["ACME_uncon_faceUp", "ACM_LyingState"]
};

// Ask for the smooth priority-1 transition first. ACM_LyingState is intentionally isolated and can swallow
// playMoveNow, so verify the requested roll actually began. If it did not, use ACE priority 2 once as a narrowly
// scoped state-graph repair. The token prevents an old fallback from overriding a newer flip.
private _token = format ["%1:%2:%3", clientOwner, CBA_missionTime, random 1];
private _rollTime = missionNamespace getVariable ["ACME_CS_rollTime", 1.85 / (call ACME_fnc_choreographyRate)];
if (!(_rollTime isEqualType 0) || {!finite _rollTime} || {_rollTime <= 0}) then {_rollTime = 1.85 / (call ACME_fnc_choreographyRate);};
private _leaseToken = [_patient, _trans, 1, "chest-seal-roll", _provider, _rollTime + 0.45, 3, _token] call ACME_fnc_patientAnimRequest;
if (_leaseToken == "") exitWith {_patient setVariable ["ACME_CS_rollUntil", -1, false];};
_patient setVariable ["ACME_CS_rollToken", _token, false];
_patient setVariable ["ACME_CS_rollUntil", CBA_missionTime + _rollTime, false];
[{
    params ["_p", "_tok", "_trans"];
    if (isNull _p || {!local _p} || {!alive _p} || {!isNull objectParent _p}) exitWith {};
    if ((_p getVariable ["ACME_CS_rollToken", ""]) != _tok) exitWith {};
    private _lock = _p getVariable ["ACME_patientAnimLock", []];
    if ((_lock param [0, ""]) != _tok) exitWith {};
    if !([_p] call ACME_fnc_chestSealCanPhysicalRoll) exitWith {};
    if ((toLower animationState _p) != (toLower _trans)) then {
        [_p, _trans, 2] call ACME_fnc_doAnim;
    };
}, [_patient, _token, _trans], 0.15] call CBA_fnc_waitAndExecute;

[{
    params ["_p", "_tok", "_hold", "_needsHold", "_target"];
    if (isNull _p || {!local _p}) exitWith {};
    if ((_p getVariable ["ACME_CS_rollToken", ""]) != _tok) exitWith {};
    _p setVariable ["ACME_CS_rollToken", "", false];
    _p setVariable ["ACME_CS_rollUntil", -1, false];
    private _lock = _p getVariable ["ACME_patientAnimLock", []];
    if ((_lock param [0, ""]) != _tok) exitWith {};
    [_p, _tok] call ACME_fnc_patientAnimRelease;
    if (!alive _p || {!isNull objectParent _p}) exitWith {};
    private _stillRollable = [_p] call ACME_fnc_chestSealCanPhysicalRoll;
    if (_needsHold && {_stillRollable}) then {
        ["ace_common_switchMove", [_p, _hold]] call CBA_fnc_globalEvent;
        // Cache only while the patient is still legitimately under the authored lying/unconscious pose.
        _p setVariable ["ACME_CS_facing", _target, true];
    };
    // The carrier is parked once when chest access begins.  Keep that world-space placement through
    // front/back flips instead of shuttling the vest around the casualty on every roll.
}, [_patient, _token, _hold, true, _target], _rollTime] call CBA_fnc_waitAndExecute;
