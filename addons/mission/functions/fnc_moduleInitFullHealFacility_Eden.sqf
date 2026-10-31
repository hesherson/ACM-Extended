#include "..\script_component.hpp"
/*
 * Author: Blue
 * Module to create full heal facility in eden.
 *
 * Arguments:
 * 0: The module logic <OBJECT>
 * 1: Synchronized objects <ARRAY>
 * 2: Activated <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [LOGIC, [], true] call ACM_mission_fnc_moduleInitFullHealFacility_Eden;
 *
 * Public: No
 */

params ["_logic", "_syncedObjects", "_activated"];

if (!_activated) exitWith {};

private _distance = (_logic getVariable ["InteractionDistance", 5]) max 0;
private _position = _logic getVariable ["InteractionPosition", [0,0,0]];

if (typeName _position == "STRING") then {
    _position = (_position select [1, ((count _position) - 2)]) splitString ",";
};

if ((typeName _position != "ARRAY") || {count _position != 3}) then {
    _position = [0,0,0];
} else {
    _position = +_position;
    {
        // Eden may already supply a numeric array. parseNumber accepts strings/bools, not numbers.
        private _component = _x;
        if (_component isEqualType "") then {_component = parseNumber _component;};
        if !(_component isEqualType 0 && {finite _component}) then {_component = 0;};
        _position set [_forEachIndex, _component];
    } forEach _position;
};

{
    [_x, _distance, _position] call FUNC(initFullHealFacility);
} forEach _syncedObjects;
