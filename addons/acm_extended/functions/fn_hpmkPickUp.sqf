// pick up a dropped HPMK blanket, the one shed when a wrapped patient got up. it deletes the world object and
// returns a reusable HPMK to the inventory of the picker.
// it is called from the "Pick Up HPMK" ACE object action, which is registered per-client in fn_postInit and gated
// on ACME_hpmk_dropped.
// call it as [_blanket, _player] call ACME_fnc_hpmkPickUp.
params ["_blanket", "_player"];
if (isNull _blanket) exitWith {};
if !(_blanket getVariable ["ACME_hpmk_dropped", false]) exitWith {};

// consume it immediately, so a second interactor, or a double-click, cannot pick the same blanket twice. the
// interaction condition reads this flag, so clearing it removes the action before the object is deleted a frame
// later on the server.
_blanket setVariable ["ACME_hpmk_dropped", false, true];

// return a reusable HPMK to the picker. additem is fine on the local player.
if (!isNull _player && {alive _player}) then { _player addItem "ACME_HPMK"; };

// the blanket is a server-owned global object, from a createvehicle in the server-only blanket tick, so delete it
// on the server.
[_blanket] remoteExec ["ACME_fnc_remoteDeleteVehicle", 2];

if (!isNil "ace_common_fnc_displayTextStructured") then {
    ["HPMK picked up.", 2, _player] call ace_common_fnc_displayTextStructured;
};
