#include "..\script_component.hpp"
/* Adopt restored/locality-transferred ocular state without exposing native writes to ACME. */
params ["_patient", ["_newPeriod",false], ["_retire",false]];
if (isNil QGVAR(activePatients)) then {GVAR(activePatients) = [];};
if (_retire) exitWith {GVAR(activePatients) = GVAR(activePatients) - [_patient];};
if (isNull _patient || {!local _patient}) exitWith {};
["cleanup",[_patient]] call FUNC(shieldSource);
[_patient] call FUNC(shieldRecover);
if (!alive _patient) exitWith {};

private _eyes = _patient getVariable [QGVAR(eyeInjuries),[1,1]];
private _structural = (_eyes isEqualType [] && {count _eyes == 2}
    && {(_eyes findIf {!(_x isEqualType 0) || {!finite _x}}) == -1}
    && {({_x < 0.999} count _eyes) > 0})
    || {_patient getVariable [QGVAR(ocularPermanent),false]}
    || {(_patient getVariable [QGVAR(eyeShieldItem),""]) != ""};
private _needs = _structural || {GET_DUST_INJURY(_patient) > 0};
if (!_needs) exitWith {GVAR(activePatients) = GVAR(activePatients) - [_patient];};

if (_newPeriod && {_structural}) then {
    _patient setVariable [QGVAR(structuralLastTick),CBA_missionTime,false];
};
GVAR(activePatients) pushBackUnique _patient;
if (_structural) then {[_patient] call FUNC(structuralTick);};
