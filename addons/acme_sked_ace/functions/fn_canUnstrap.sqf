/*
 * Medical menu: is the casualty strapped into a SKED that is on the ground and not being moved?
 * Arguments: 0: medic, 1: patient. Returns: bool.
 */
params ["_medic", "_patient"];
private _litter = _patient getVariable ["acme_sked_litter", objNull];
[_medic, _litter] call acme_sked_fnc_canUnstrapLitter
