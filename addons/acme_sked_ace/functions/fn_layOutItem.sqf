/*
 * Self action: unroll the SKED from the inventory on the ground in front of the player, head end away.
 * Arguments: 0: player.
 */
params ["_player"];
[6, [_player], {
    (_this select 0) params ["_player"];
    [_player, "layOutItem"] call acme_sked_fnc_request;
}, {}, "Laying out SKED...", {"ACME_SKED_Item" in (items ((_this select 0) select 0))}] call ace_common_fnc_progressBar;
