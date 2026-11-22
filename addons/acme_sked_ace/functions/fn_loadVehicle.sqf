/*
 * Put the strapped casualty into a vehicle, in their SKED. The detach and the load both happen where the
 * casualty is local (acme_sked_loadLocal), so the pose guard does not put them back on the SKED half way;
 * the GetInMan handler then stows the SKED with them.
 * Arguments: 0: player, 1: SKED, 2: vehicle.
 */
params ["_player", "_litter", "_vehicle"];
// a rescuer who drags this litter lets go of it first
if ((_litter getVariable ["acme_drag_by", objNull]) isEqualTo _player) then {[_player, true] call acme_sked_fnc_dragStop;};
[6, [_player, _litter, _vehicle], {
    (_this select 0) params ["_player", "_litter", "_vehicle"];
    private _patient = _litter getVariable ["acme_sked_patient", objNull];
    if (isNull _patient) exitWith {};
    [_player, "loadVehicle", _litter, _vehicle] call acme_sked_fnc_request;
}, {}, "Loading SKED...", {
    (_this select 0) params ["_player", "_litter", "_vehicle"];
    alive _vehicle && {_player distance _vehicle < 12} && {[_player, _litter] call acme_sked_fnc_canUnstrapLitter}
}] call ace_common_fnc_progressBar;
