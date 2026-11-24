/* B397: a Prepared IV Set comes back from an IV stand's hook into this provider's gear (fn_ivStandServer.sqf
 * "unstage", or "stage" refused). Its records come with it through the inventory ledger, as when it is taken out of
 * a crate (the Take handler's own steps: fn_inventoryLedgerInit.sqf). If it was taken down to be connected to a
 * casualty, the transfusion menu opens on them with the set among the provider's prepared sets, and once it runs
 * the bag goes back up on the stand it came from (ACME_ivStand_connect, fn_ivStandInit.sqf).
 * [magazine, token, casualty or objNull, stand or objNull, set id, message] */
params [["_class", ""], ["_token", -1], ["_patient", objNull], ["_stand", objNull], ["_setId", ""], ["_message", ""]];
private _player = call ACME_fnc_controlledProvider;
if (isNull _player || {!local _player} || {_class == ""} || {_token < 0}) exitWith {};
if (_message != "") then {[_message, 2] call ace_common_fnc_displayTextStructured;};
private _carried = true;
if (_player canAdd [_class, 1]) then {
    _player addMagazine [_class, _token];
} else {
    // no room: it is put down at the provider's feet, to be picked up (the ledger follows it, as for any drop)
    private _drop = createVehicle ["GroundWeaponHolder", getPosATL _player, [], 0, "CAN_COLLIDE"];
    _drop addMagazineAmmoCargo [_class, 1, _token];
    _carried = false;
    ["No room in your gear: the set is on the ground at your feet.", 2.5] call ace_common_fnc_displayTextStructured;
};
if (!_carried) exitWith {};
[_player, "prepared"] call ACME_fnc_inventoryLedgerMarkIncoming;
[{[_this select 0] call ACME_fnc_inventoryLedgerReconcile;}, [_player]] call CBA_fnc_execNextFrame;
if (isNull _patient) exitWith {};

// connect: wait for the set's records to be adopted, then open the transfusion menu on the casualty
private _running = {
    params ["_patient"];
    private _out = createHashMap;
    {
        _out set [toLowerANSI _x, count (_y select {(_x param [1, 0]) > 0.01})];
    } forEach (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);
    _out
};
_player setVariable ["ACME_ivStand_connect", [_stand, _patient, _setId, CBA_missionTime + 180, [_patient] call _running]];
[{
    params ["_player", "_setId"];
    ((_player getVariable ["ACME_preparedIVSets", []]) findIf {(_x select 0) == _setId}) >= 0
}, {
    params ["_player", "_setId", "_patient"];
    private _part = ["leftarm", "rightarm", "leftleg", "rightleg", "body", "head"] select {[_patient, _x, 0, -1] call ACM_circulation_fnc_hasIV};
    private _ioParts = ["leftarm", "rightarm", "leftleg", "rightleg", "body", "head"] select {[_patient, _x, 0] call ACM_circulation_fnc_hasIO};
    _part = (_part + _ioParts) param [0, "leftarm"];
    [_player, _patient, _part] call ACM_circulation_fnc_openTransfusionMenu;
    ["Select the set under Prepared IV Sets and hang it on an access site.", 3] call ace_common_fnc_displayTextStructured;
}, [_player, _setId, _patient], 8, {
    params ["_player"];
    _player setVariable ["ACME_ivStand_connect", nil];
    ["The set is in your gear under Prepared IV Sets.", 2.5] call ace_common_fnc_displayTextStructured;
}] call CBA_fnc_waitUntilAndExecute;
