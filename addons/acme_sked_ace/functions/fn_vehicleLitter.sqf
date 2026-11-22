/*
 * Litter action: put the litter, casualty and all, on the cabin floor of a vehicle (a timer, then the server
 * does it), or take it out again.
 * Arguments: 0: player, 1: litter, 2: vehicle, 3: load <BOOL> (false: unload).
 */
params ["_player", "_litter", "_vehicle", "_load"];
// a rescuer who drags this litter lets go of it first
if ((_litter getVariable ["acme_drag_by", objNull]) isEqualTo _player) then {[_player, true] call acme_sked_fnc_dragStop;};
[[4, 6] select _load, [_player, _litter, _vehicle, _load], {
    (_this select 0) params ["_player", "_litter", "_vehicle", "_load"];
    [_player, ["vehicleLitterOut", "vehicleLitterIn"] select _load, _litter, _vehicle] call acme_sked_fnc_request;
}, {}, ["Unloading litter...", "Loading litter..."] select _load, {
    (_this select 0) params ["_player", "_litter", "_vehicle", "_load"];
    !isNull _litter && {alive _vehicle} && {_player distance _vehicle < 12}
        && {((_litter getVariable ["acme_sked_inVehicle", objNull]) isEqualTo _vehicle) isNotEqualTo _load}
}] call ace_common_fnc_progressBar;
