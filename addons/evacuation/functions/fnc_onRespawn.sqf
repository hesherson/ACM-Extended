#include "..\script_component.hpp"
/*
 * Author: Blue
 * Do stuff on respawn.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 * 1: Dead body <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [alive, body] call ACM_evacuation_fnc_onRespawn;
 *
 * Public: No
 */

params ["_unit", "_dead"];

if !(isMultiplayer) exitWith {};

if !(local _unit) exitWith {};

if !(isPlayer _unit) exitWith {};

_unit setVariable [QGVAR(playerSpawned), true];

// B265: respawn is an intentional kit replacement, unlike a medical
// animation. Capture the intended snapshot and reject a delayed write once
// the player, locality, saved preset, or live inventory has changed.
private _saved = _unit getVariable ["ENH_savedLoadout", []];
if !(_saved isEqualType [] && {count _saved == 10}) exitWith {};
private _before = getUnitLoadout _unit;
if (_before isEqualTo _saved) exitWith {};
private _epoch = (_unit getVariable ["ACM_evacuation_loadoutEpoch", 0]) + 1;
_unit setVariable ["ACM_evacuation_loadoutEpoch", _epoch];
[{
    params ["_unit", "_saved", "_before", "_epoch"];
    if (isNull _unit || {!local _unit} || {!alive _unit} || {!isPlayer _unit}) exitWith {};
    if ((_unit getVariable ["ACM_evacuation_loadoutEpoch", -1]) != _epoch
        || {(_unit getVariable ["ENH_savedLoadout", []]) isNotEqualTo _saved}
        || {(getUnitLoadout _unit) isNotEqualTo _before}) exitWith {};
    // Use CBA's real extended-loadout hooks. Participating appearance/equipment
    // addons may preserve their own metadata; this is not a universal dump of
    // arbitrary object variables and cannot invent absent appearance records.
    private _extended = [_unit] call CBA_fnc_getLoadout;
    _extended set [0, +_saved];
    [_unit, _extended, false] call CBA_fnc_setLoadout;
}, [_unit, +_saved, _before, _epoch]] call CBA_fnc_execNextFrame;
