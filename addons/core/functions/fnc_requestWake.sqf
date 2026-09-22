#include "..\script_component.hpp"
/*
 * Canonical clinical wake request.
 *
 * ACE's WakeUp event is always attempted first. If the patient remains raw-flag
 * unconscious 0.15 s later while the same wake gate is still completely clear,
 * repair the stale low-level flag and emit WakeUp once more. This repairs a
 * state-machine/raw-flag split without bypassing anesthesia, paralysis, seizure,
 * arrest, traumatic knockout, or unstable physiology.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_ignoreKnockOut", false, [false]],
    ["_reason", "clinical", [""]]
];

if (isNull _patient || {!alive _patient} || {!local _patient}) exitWith {false};
if !([_patient, _ignoreKnockOut] call FUNC(canWake)) exitWith {false};

if (_ignoreKnockOut && {_patient getVariable [QGVAR(KnockOut_State), false]}) then {
    _patient setVariable [QGVAR(KnockOut_State), false, true];
};

if !([_patient, false] call FUNC(canWake)) exitWith {false};

[QACEGVAR(medical,WakeUp), _patient] call CBA_fnc_localEvent;

[{
    params ["_p", "_reason"];
    if (isNull _p || {!alive _p} || {!local _p}) exitWith {};
    if !(_p getVariable ["ACE_isUnconscious", false]) exitWith {};
    if !([_p, false] call ACM_core_fnc_canWake) exitWith {};

    [_p, false] call ACEFUNC(medical_status,setUnconsciousState);
    [QACEGVAR(medical,WakeUp), _p] call CBA_fnc_localEvent;

    _p setVariable [
        "ACME_consciousRepairCount",
        (_p getVariable ["ACME_consciousRepairCount", 0]) + 1,
        false
    ];
    _p setVariable ["ACME_consciousRepairLast", [serverTime, _reason], false];

    diag_log format [
        "[ACME CONSCIOUSNESS REPAIR] %1 cleared stale unconscious latch (%2)",
        netId _p,
        _reason
    ];
}, [_patient, _reason], 0.15] call CBA_fnc_waitAndExecute;

true
