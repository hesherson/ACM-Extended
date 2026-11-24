/* B397: the player stages one of their Prepared IV Sets (a bag spiked with its line, ACME_PreparedIVSet) on a free
 * hook of an IV stand, ready for any provider to connect to a casualty later (fn_ivStandInit.sqf, "Connect staged
 * bag"). The set is a magazine whose ammo is its ledger token (the bag's records travel with it): it goes from the
 * player's gear into the stand's hidden holder exactly as it would into a crate, and the player's own list of
 * prepared sets is reconciled from what they still hold (fn_inventoryLedgerReconcile.sqf).
 * [stand, set id] call ACME_fnc_ivStandStage; returns true when the set left the player. */
params [["_stand", objNull, [objNull]], ["_setId", "", [""]]];
private _player = call ACME_fnc_controlledProvider;
if (isNull _stand || {isNull _player} || {_setId == ""} || {!local _player}) exitWith {false};
private _say = {[_this, 2] call ace_common_fnc_displayTextStructured;};
if (_player getVariable ["ACME_persistenceFrozen", false]) exitWith {"Equipment is being saved. Try again in a moment." call _say; false};
if ("prepared" in (_player getVariable ["ACME_inventoryIncomingKinds", []])) exitWith {"Your prepared sets are still being sorted. Try again in a moment." call _say; false};
private _staged = _stand getVariable ["ACME_ivStand_staged", [[], []]];
private _slots = _stand getVariable ["ACME_ivStand_slots", [objNull, objNull]];
if (([0, 1] findIf {isNull (_slots select _x) && {(_staged select _x) isEqualTo []}}) < 0) exitWith {"Both hooks on this stand are in use." call _say; false};
private _set = (_player getVariable ["ACME_preparedIVSets", []]) param [(_player getVariable ["ACME_preparedIVSets", []]) findIf {(_x select 0) == _setId}, []];
if (_set isEqualTo []) exitWith {false};
// the magazine that carries this set: the held token whose ledger record is this set
private _token = -1;
private _class = "";
{
    private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1", _x select 0], []];
    if (count _record > 8 && {(_record select 1) == _setId}) exitWith {_token = _x select 0; _class = _record select 8;};
} forEach ([_player, "prepared"] call ACME_fnc_inventoryLedgerNative);
if (_token < 0 || {_class == ""}) exitWith {"That set is not in your gear." call _say; false};

// what the bag on the hook looks like: the set's (first) bag, its fluid and size
_set params ["", ["_bagClass", ""], ["_action", ""], "", "", "", ["_label", ""]];
private _cfg = configFile >> "ace_medical_treatment" >> "IV" >> _action;
private _type = toLowerANSI (getText (_cfg >> "type") + " " + _action + " " + _bagClass);
private _fluid = switch (true) do {
    case ((_type find "blood") >= 0): {"blood"};
    case ((_type find "plasmalyte") >= 0): {"plasmalyte"};
    case ((_type find "plasma") >= 0): {"plasma"};
    default {"fluid"};
};
private _volume = getNumber (_cfg >> "volume");
if (_volume <= 0) then {_volume = 500;};
if (_label == "") then {_label = getText (configFile >> "CfgWeapons" >> _bagClass >> "displayName");};
if (_label == "") then {_label = "IV set";};

if !([_player, _class, _token] call ace_common_fnc_removeSpecificMagazine) exitWith {"That set is not in your gear." call _say; false};
[{[_this select 0] call ACME_fnc_inventoryLedgerReconcile;}, [_player]] call CBA_fnc_execNextFrame;
["ACME_ivStandStaging", ["stage",[_stand, _player, _class, _token, _setId, _label, _fluid, _volume]]] call CBA_fnc_serverEvent;
true
