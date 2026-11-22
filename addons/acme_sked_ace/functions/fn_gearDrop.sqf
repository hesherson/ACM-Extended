/*
 * Lay a loadout on the ground beside a unit, in one pile: weapons with what is fitted to them, the uniform, vest
 * and pack and everything that was in them, helmet, glasses, binoculars and the linked items.
 * Arguments: 0: unit, 1: loadout (as getUnitLoadout gives it).
 */
params ["_unit", "_loadout"];
private _at = getPosATL _unit;
private _pile = createVehicle ["GroundWeaponHolder", _at vectorAdd [0.6, 0, 0], [], 0, "CAN_COLLIDE"];
private _add = {
    params ["_entry"];
    // one line of a container: [class, count], [magazine, count, rounds] or [[weapon and its parts], count]
    _entry params ["_what", ["_count", 1], ["_rounds", -1]];
    if (_what isEqualType []) exitWith {_pile addWeaponWithAttachmentsCargoGlobal [_what, _count];};
    if (_what == "") exitWith {};
    if (_rounds >= 0) exitWith {_pile addMagazineAmmoCargo [_what, _count, _rounds];};
    if (isClass (configFile >> "CfgVehicles" >> _what)) exitWith {_pile addBackpackCargoGlobal [_what, _count];};
    _pile addItemCargoGlobal [_what, _count];
};
{
    private _weapon = _loadout select _x;
    if (_weapon isNotEqualTo []) then {_pile addWeaponWithAttachmentsCargoGlobal [_weapon, 1];};
} forEach [0, 1, 2, 8];
{
    private _container = _loadout select _x;
    if (_container isNotEqualTo []) then {
        [[_container select 0, 1]] call _add;
        {[_x] call _add;} forEach (_container param [1, []]);
    };
} forEach [3, 4, 5];
{if (_x != "") then {_pile addItemCargoGlobal [_x, 1];};} forEach [_loadout select 6, _loadout select 7];
{if (_x != "") then {_pile addItemCargoGlobal [_x, 1];};} forEach (_loadout select 9);
_pile
