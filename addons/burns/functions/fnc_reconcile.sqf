#include "..\script_component.hpp"
/*
 * Native burn-state owner boundary for clinical restore, locality transfer and
 * reset. Retiring a runtime must never clear durable anatomy or evacuation.
 */
params ["_patient", ["_newPeriod",false], ["_retire",false]];

if (_retire || {isNull _patient} || {!local _patient} || {!alive _patient}) exitWith {
    if (!isNil QGVAR(activePatients)) then {
        GVAR(activePatients) = GVAR(activePatients) - [_patient];
    };
};

private _active = GVAR(burnsEnabled) && {
    (_patient getVariable [QGVAR(SystemicBurden),_patient getVariable [QGVAR(BurnBurden),0]]) > 0
    || {(_patient getVariable [QGVAR(AirwayInflammation),0]) > 0.001}
    || {_patient getVariable [QGVAR(AirwayBurned),false]}
    || {_patient getVariable [QGVAR(PermanentInjury),false]}
};

if (!_active) exitWith {
    // A clean restore can replace anatomy without carrying derived drives.
    // Recompute/neutralize those once, without making settled burns active.
    [_patient] call FUNC(tickPatient);
    if (!isNil QGVAR(activePatients)) then {
        GVAR(activePatients) = GVAR(activePatients) - [_patient];
    };
};

if (_newPeriod) then {
    _patient setVariable [QGVAR(LastTickLocal),CBA_missionTime,false];
};
if (isNil QGVAR(activePatients)) then {GVAR(activePatients) = [];};
GVAR(activePatients) pushBackUnique _patient;
[_patient] call FUNC(tickPatient);
