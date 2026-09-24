#include "..\script_component.hpp"
/*
 * Author: Blue
 * Modify oxygen tank contents.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 *
 * Return Value:
 * Success? <BOOL>
 *
 * Example:
 * [player] call ACM_breathing_fnc_useOxygenTankReserve;
 *
 * Public: No
 */

params ["_unit"];

private _return = false;
private _found = false;

private _itemContainers = [uniformContainer _unit, vestContainer _unit, backpackContainer _unit];
private _containerString = ["uniform", "vest", "backpack"];

{
    private _container = _x;

    private _mags = magazinesAmmoCargo _container;

    private _targetMags = [];

    {
        _x params ["_magClassname", "_magCount"];

        if (_magClassname == "ACM_OxygenTank_425") then {
            _targetMags pushBack _magCount;
        };
    } forEach _mags;

    if (count _targetMags > 0) exitWith {
        _found = true;
        _targetMags sort true;

        private _targetAmmoCount = (_targetMags select 0);

        _container addMagazineAmmoCargo ["ACM_OxygenTank_425", -1, _targetAmmoCount];

        private _newCount = _targetAmmoCount - 1;

        if (_newCount < 1) then {
            [_unit, "ACM_OxygenTank_425_Empty", (_containerString select _forEachIndex)] call ACEFUNC(common,addToInventory);
        } else {
            _container addMagazineAmmoCargo ["ACM_OxygenTank_425", 1, _newCount];
            _return = true;
        };
    };
} forEach _itemContainers;

// No loose tank: one packed in an Enhanced First Aid Kits kit is drawn from right inside the kit, where it
// stays opened. drawCharge answers the units left in it, -1 when no kit holds a tank.
if (!_found && {!isNil "efak_medical_fnc_drawCharge"}) then {
    private _left = [_unit, "ACM_OxygenTank_425"] call efak_medical_fnc_drawCharge;

    if (_left == 0) then {
        [_unit, "ACM_OxygenTank_425_Empty"] call ACEFUNC(common,addToInventory);
    };

    _return = _left >= 1;
};

_return;
