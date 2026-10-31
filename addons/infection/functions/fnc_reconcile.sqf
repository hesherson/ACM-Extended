#include "..\script_component.hpp"
/* Re-enroll durable infection on its owner without restarting progression clocks.
 * Arguments: patient, new owner/clinical period (unused here), retire membership.
 * Only this component mutates its own runtime registry.
 */
params ["_patient", "", ["_retire", false]];

if (_retire) exitWith {
    if (!isNil QGVAR(activePatients)) then {
        GVAR(activePatients) = GVAR(activePatients) - [_patient];
    };
};
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};

private _needs = (_patient getVariable [QGVAR(Infection_Stage), 0]) > 0
    || {(_patient getVariable [QGVAR(Infection_EligibleTime), -1]) != -1}
    || {_patient getVariable [QGVAR(Sepsis_Permanent), false]};
if (!_needs) exitWith {
    if (!isNil QGVAR(activePatients)) then {
        GVAR(activePatients) = GVAR(activePatients) - [_patient];
    };
};

if (isNil QGVAR(activePatients)) then {GVAR(activePatients) = [];};
GVAR(activePatients) pushBackUnique _patient;
[_patient] call FUNC(handleInfectionPFH);
