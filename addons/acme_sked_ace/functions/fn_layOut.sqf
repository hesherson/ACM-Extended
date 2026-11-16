/*
 * Lay out a SKED from its bag or rolled up, on the ground.
 * Arguments: 0: player, 1: the bag or the rolled SKED.
 */
params ["_player", "_pack"];
[6, [_player, _pack], {
    (_this select 0) params ["_player", "_pack"];
    [_player, "layOut", _pack] call acme_sked_fnc_request;
}, {}, "Laying out SKED...", {!isNull ((_this select 0) select 1)}] call ace_common_fnc_progressBar;
