// Semi-Fowler's requires a casualty who is physically down. A stale lying flag must never
// make an independently standing or crouching patient eligible.
params [["_patient", objNull, [objNull]], ["_medic", objNull, [objNull]]];
if (isNull _patient || {!alive _patient}) exitWith {false};
if !(_patient isKindOf "CAManBase") exitWith {false};
if (_patient isEqualTo _medic) exitWith {false};
if (_patient getVariable ["ACME_headElevated", false]) exitWith {false};
if (!isNull objectParent _patient || {!isNull attachedTo _patient}) exitWith {false};
if (_patient call ace_common_fnc_isBeingDragged || {_patient call ace_common_fnc_isBeingCarried}) exitWith {false};
// Do not start a new placement while the previous lay-flat/lift or another intervention still owns the casualty's
// animation. B165 could make headElevated=false before the old animation lease retired, allowing an immediate second
// click to lose its lift request and leave logical Semi-Fowler state with no visible posture.
private _animLock = _patient getVariable ["ACME_patientAnimLock", []];
if ((count _animLock) >= 5) then {
    private _until = _animLock param [4, -1];
    if (_until isEqualType 0 && {_until > serverTime}) exitWith {false};
};
private _stance = stance _patient;
if (_stance in ["STAND", "CROUCH"]) exitWith {false};
private _down = (_patient getVariable ["ACE_isUnconscious", false])
    || {lifeState _patient == "INCAPACITATED"}
    || {_patient getVariable ["ACM_core_Lying_State", false]};
_down && {_stance == "PRONE" || {!isAwake _patient}}
