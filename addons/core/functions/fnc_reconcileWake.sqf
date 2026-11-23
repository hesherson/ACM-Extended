#include "..\script_component.hpp"
/* Complete a clinically permitted wake without guessing the medical state.
 * This is the sole desynchronization repair; callers never manufacture vitals.
 * Return true only after ACE's unconscious flag actually clears.
 */
params [["_patient", objNull, [objNull]], ["_reason", "clinical", [""]]];
if (isNull _patient || {!local _patient} || {!alive _patient}
    || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {false};
if !([_patient] call FUNC(canWake)) exitWith {false};
if !(_patient getVariable ["ACE_isUnconscious", false]) exitWith {true};
if (isNil QACEGVAR(medical,STATE_MACHINE)
    || {isNil "CBA_statemachine_fnc_getCurrentState"}
    || {isNil "CBA_statemachine_fnc_manualTransition"}) exitWith {false};

private _machine = ACEGVAR(medical,STATE_MACHINE);
if (isNull _machine) exitWith {false};
private _state = [_patient, _machine] call CBA_statemachine_fnc_getCurrentState;
// Unknown/unregistered, arrest, fatal-injury and dead states are NOT awake states.
if !(_state in ["Default", "Injured", "Unconscious"]) exitWith {false};

if (_state == "Unconscious") then {
    [_patient, _machine, "Unconscious", "Injured", {
        [_this, false] call ACEFUNC(medical_status,setUnconsciousState);
    }, "ACMEWakeRepair"] call CBA_statemachine_fnc_manualTransition;
} else {
    // The machine is already awake; only the stale flag/status/animation needs repair.
    [_patient, false] call ACEFUNC(medical_status,setUnconsciousState);
};

private _awake = !(_patient getVariable ["ACE_isUnconscious", false]);
if (_awake) then {
    _patient setVariable ["ACME_consciousRepairCount",
        (_patient getVariable ["ACME_consciousRepairCount", 0]) + 1, false];
    _patient setVariable ["ACME_consciousRepairLast", [serverTime, _reason, _state], false];
    if ((!isNil "ACME_fnc_debugEnabled" && {call ACME_fnc_debugEnabled})) then {diag_log format ["[ACME CONSCIOUSNESS REPAIR] %1: %2 (%3)", netId _patient, _reason, _state];};
};
_awake
