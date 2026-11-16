/*
 * Pick up a SKED (in its bag, or rolled) into the inventory.
 * Arguments: 0: player, 1: the bag or the rolled SKED.
 */
params ["_player", "_pack"];
if !(_player canAdd "ACME_SKED_Item") exitWith {
    ["No room for the SKED (it needs a backpack)."] call ace_common_fnc_displayTextStructured;
};
[_player, "pickUp", _pack] call acme_sked_fnc_request;
