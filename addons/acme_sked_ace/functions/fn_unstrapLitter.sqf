/*
 * SKED action: take the casualty out of the SKED.
 * Arguments: 0: player, 1: SKED.
 */
params ["_player", "_litter"];
// a rescuer who drags this litter lets go of it first
if ((_litter getVariable ["acme_drag_by", objNull]) isEqualTo _player) then {[_player, true] call acme_sked_fnc_dragStop;};
[8, [_player, _litter], {
    (_this select 0) params ["_player", "_litter"];
    [_player, "unstrap", _litter] call acme_sked_fnc_request;
}, {}, "Unstrapping...", {
    (_this select 0) params ["_player", "_litter"];
    [_player, _litter] call acme_sked_fnc_canUnstrapLitter
}] call ace_common_fnc_progressBar;
