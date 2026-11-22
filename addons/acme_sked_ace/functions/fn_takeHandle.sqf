/*
 * SKED action: take a handle (the free one nearest the player).
 * Arguments: 0: player, 1: SKED, 2: which end (-1 either, 0 the head end, 1 the foot end; default -1).
 */
params ["_player", "_litter", ["_end", -1]];
[_player, ["takeHandle", "takeHandleHead", "takeHandleFoot"] select (((_end + 1) max 0) min 2), _litter] call acme_sked_fnc_request;
