/*
 * Where the casualty is local: take them off the SKED and into the vehicle with ACE's own load (the
 * ace_loadPersonEvent handler, which picks the seat). If they are not in the vehicle 3 s later (no seat
 * after all), the pose guard puts them back on the SKED.
 * Arguments: 0: casualty, 1: vehicle, 2: rescuer.
 */
params ["_patient", "_vehicle", "_rescuer", "_litter"];
if (!local _patient || {!alive _patient} || {!isNull objectParent _patient}
    || {(_patient getVariable ["acme_sked_litter", objNull]) isNotEqualTo _litter}
    || {_patient getVariable ["acme_sked_loading", false]}) exitWith {};
_patient setVariable ["acme_sked_loading", true];
detach _patient;
["ace_loadPersonEvent", [_patient, _vehicle, _rescuer, [], false]] call CBA_fnc_localEvent;
[{
    _this setVariable ["acme_sked_loading", nil];
}, _patient, 3] call CBA_fnc_waitAndExecute;
