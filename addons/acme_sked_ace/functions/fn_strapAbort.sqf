/*
 * ACE treatment callback when the timer is broken off: the casualty is free again.
 * Arguments: 0: medic (and the rest of the ACE callback arguments, unused).
 */
params ["_medic"];
(_medic getVariable ["acme_sked_strapTarget", []]) params [["_patient", objNull], ["_litter", objNull]];
_medic setVariable ["acme_sked_strapTarget", nil];
if (isNull _patient || {isNull _litter}) exitWith {};
[_medic, "strapAbort", _patient, _litter] call acme_sked_fnc_request;
