/*
 * Self action: lift the SKED (this rescuer leads).
 * Arguments: 0: player.
 */
params ["_player"];
[_player, "lift", _player getVariable ["acme_sked_bearing", objNull]] call acme_sked_fnc_request;
