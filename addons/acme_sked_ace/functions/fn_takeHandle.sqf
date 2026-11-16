/*
 * SKED action: take a handle (the free one nearest the player).
 * Arguments: 0: player, 1: SKED.
 */
params ["_player", "_litter"];
[_player, "takeHandle", _litter] call acme_sked_fnc_request;
