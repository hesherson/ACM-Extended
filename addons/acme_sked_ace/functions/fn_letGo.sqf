/*
 * Self action: let go of the handle (sets the SKED down first if it is lifted and too few would be left,
 * or if this rescuer leads).
 * Arguments: 0: player.
 */
params ["_player"];
[_player, "letGo"] call acme_sked_fnc_request;
