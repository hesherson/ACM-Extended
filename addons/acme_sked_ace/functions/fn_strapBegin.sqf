/*
 * ACE treatment callback at the start of the timer: the casualty is laid on the nearest laid out litter while
 * the timer runs. The litter is remembered on the medic for the end of the timer.
 * Arguments: 0: medic, 1: patient (and the rest of the ACE callback arguments, unused).
 */
params ["_medic", "_patient"];
// (for fn_strapAnim.sqf: no animation of an earlier treatment, and none given again before a second is over)
_medic setVariable ["acme_strap_move", nil];
_medic setVariable ["acme_strap_animAt", CBA_missionTime];
private _litter = [_patient] call acme_sked_fnc_findLitter;
if (isNull _litter) exitWith {};
_medic setVariable ["acme_sked_strapTarget", [_patient, _litter]];
[_medic, "strapBegin", _patient, _litter] call acme_sked_fnc_request;
