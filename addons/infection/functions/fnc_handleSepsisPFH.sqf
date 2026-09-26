#include "..\script_component.hpp"
/*
 * 1.3.0 sepsis adjunct. This is a single owner-local tick, not a PFH creator.
 * Stage progression/regression remains in the main infection worker.
 */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
if ((_patient getVariable [QGVAR(Infection_Stage), 0]) < 3) exitWith {};

private _next = _patient getVariable [QGVAR(Sepsis_NextPain), 0];
if (CBA_missionTime >= _next) then {
    [_patient, 0.12] call ACEFUNC(medical,adjustPainLevel);
    _patient setVariable [QGVAR(Sepsis_NextPain), CBA_missionTime + 60, false];
};
