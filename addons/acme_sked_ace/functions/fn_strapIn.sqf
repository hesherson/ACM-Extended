/*
 * ACE treatment callback: strap the casualty into the nearest laid out SKED.
 * Arguments: 0: medic, 1: patient (and the rest of the ACE callback arguments, unused).
 */
params ["_medic", "_patient"];
// The litter the casualty was laid on while the timer ran, if there is one.
(_medic getVariable ["acme_sked_strapTarget", []]) params [["_laid", objNull], ["_litter", objNull]];
_medic setVariable ["acme_sked_strapTarget", nil];
if (isNull _litter || {_laid isNotEqualTo _patient}) then {_litter = [_patient] call acme_sked_fnc_findLitter;};
if (isNull _litter) exitWith {};
[_medic, "strap", _patient, _litter] call acme_sked_fnc_request;
