/*
 * SKED action: is there a casualty within 3 m who can be strapped in?
 * Arguments: 0: player, 1: SKED. Returns: bool.
 */
params ["_player", "_litter"];
[_player, _litter] call acme_sked_fnc_canHandleEmpty && {!isNull ([_litter, _player] call acme_sked_fnc_findCasualty)}
