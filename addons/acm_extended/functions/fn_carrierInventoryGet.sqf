/* A single worn carrier can have one live custody container, in either chest workspace. */
params ["_patient"];
if (isNull _patient) exitWith {objNull};
private _cargo = _patient getVariable ["ACME_carrierCargo", objNull];
if (isNull _cargo || {_cargo getVariable ["ACME_carrierClosing", false]}
    || {!((_cargo getVariable ["ACME_carrierPatient", objNull]) isEqualTo _patient)}) exitWith {objNull};
_cargo
