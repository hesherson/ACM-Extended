/*
 * ACE treatment callback: take the casualty out of the SKED.
 * Arguments: 0: medic, 1: patient (and the rest of the ACE callback arguments, unused).
 */
params ["_medic", "_patient"];
private _litter = _patient getVariable ["acme_sked_litter", objNull];
if (isNull _litter) exitWith {};
[_medic, "unstrap", _litter] call acme_sked_fnc_request;
