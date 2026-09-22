// Single entry point for the awake-but-impaired obtunded state.
// B49 deliberately stops treating obtundation as a forced body posture. Entering the state no longer ragdolls,
// forces prone, or parks the casualty supine. Their actual current body position is preserved. If they are already
// down they may use Get Up, but that movement is intentionally very slow (handled in the ACM getUp override).
// _this is [_unit, _on, _manual, _posture, _reason]. _posture is accepted for backward compatibility only.
params ["_unit", "_on", ["_manual", false], ["_posture", "free"], ["_reason", "recover"]];
if (isNull _unit) exitWith {};
if (_on && {!isPlayer _unit}) exitWith {};

// Automatic physiology still obeys the master switch. Manual/debug/Zeus entry is allowed with the master off so
// the debug state actually exercises the same visual stack the player sees in normal use.
if (_on && {!_manual} && {!(missionNamespace getVariable ["ACME_sys_obtunded", false])}) exitWith {};

// Obtundation is an awake state. Never bypass the central wake gate.
if (_on && {_unit getVariable ["ACE_isUnconscious", false]}
    && {!([_unit, false] call ACM_core_fnc_canWake)}) exitWith {};

private _curOn  = _unit getVariable ["ACME_obtunded", false];
private _curPos = _unit getVariable ["ACME_obtunded_posture", ""];
private _newPos = if (_on) then {"free"} else {""};
if (_curOn isEqualTo _on && {(!_on) || {_curPos isEqualTo _newPos}}) exitWith {};

private _token = (_unit getVariable ["ACME_obtunded_transitionToken", 0]) + 1;
[_unit, _on, _manual, _newPos, _token, true] call ACME_fnc_obtundedStateCommit;
_unit setVariable ["ACME_obtunded_forcedBack", false, true];
_unit setVariable ["ACME_obtunded_treatmentHold", false, true];
["ACME_obtundedApply", [_unit, _on, _newPos, _reason, _curOn, _curPos, _token, _manual], _unit] call CBA_fnc_targetEvent;
