/*
 * Self action: set the SKED down.
 * Arguments: 0: SKED.
 */
params ["_player", "_litter"];
[_player, "setDown", _litter] call acme_sked_fnc_request;
