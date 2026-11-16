/*
 * Server: a strapped casualty went into a vehicle. The SKED is stowed with them (deleted here, made again
 * round them when they are unloaded); the squeezed HPMK-I shell stays on.
 * Arguments: 0: casualty.
 */
params ["_patient"];
if (!isServer || {isNull objectParent _patient}) exitWith {};
private _litter = _patient getVariable ["acme_sked_litter", objNull];
if (isNull _litter) exitWith {};
[_litter, true] call acme_sked_fnc_srvRelease;
deleteVehicle _litter;
