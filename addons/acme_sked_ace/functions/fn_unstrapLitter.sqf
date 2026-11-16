/*
 * SKED action: take the casualty out of the SKED.
 * Arguments: 0: player, 1: SKED.
 */
params ["_player", "_litter"];
[8, [_player, _litter], {
    (_this select 0) params ["_player", "_litter"];
    [_player, "unstrap", _litter] call acme_sked_fnc_request;
}, {}, "Unstrapping...", {
    (_this select 0) params ["_player", "_litter"];
    [_player, _litter] call acme_sked_fnc_canUnstrapLitter
}] call ace_common_fnc_progressBar;
