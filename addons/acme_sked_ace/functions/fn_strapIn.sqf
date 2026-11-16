/*
 * ACE treatment callback: strap the casualty into the nearest laid out SKED.
 * Arguments: 0: medic, 1: patient (and the rest of the ACE callback arguments, unused).
 */
params ["_medic", "_patient"];
private _litter = [_patient] call acme_sked_fnc_findLitter;
if (isNull _litter) exitWith {};
[_medic, "strap", _patient, _litter] call acme_sked_fnc_request;
