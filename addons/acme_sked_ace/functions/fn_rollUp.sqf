/*
 * Roll up an empty laid out SKED: into its bag in the inventory, or rolled up on the ground if there is no room.
 * Arguments: 0: player, 1: SKED.
 */
params ["_player", "_litter"];
[8, [_player, _litter], {
    (_this select 0) params ["_player", "_litter"];
    [_player, "rollUp", _litter] call acme_sked_fnc_request;
}, {}, "Rolling up SKED...", {
    (_this select 0) params ["_player", "_litter"];
    [_player, _litter] call acme_sked_fnc_canHandleEmpty
}] call ace_common_fnc_progressBar;
