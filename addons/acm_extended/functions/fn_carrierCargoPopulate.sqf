/* Populate an EMPTY destination from carrierCargoSnapshot, without refilling or merging magazines. */
params ["_container", "_snapshot"];
if (isNull _container || {count _snapshot != 4}) exitWith {false};
clearItemCargoGlobal _container;
clearMagazineCargoGlobal _container;
clearWeaponCargoGlobal _container;
clearBackpackCargoGlobal _container;
_snapshot params ["_items", "_magazines", "_weapons", "_children"];
{_container addItemCargoGlobal [_x, 1];} forEach _items;
{_x params ["_class", "_ammo"]; _container addMagazineAmmoCargo [_class, 1, _ammo];} forEach _magazines;
{_container addWeaponWithAttachmentsCargoGlobal [_x, 1];} forEach _weapons;
{
    _x params ["_class", "_backpack", "_contents"];
    private _before = (everyContainer _container) apply {_x select 1};
    if (_backpack) then {_container addBackpackCargoGlobal [_class, 1];}
    else {_container addItemCargoGlobal [_class, 1];};
    private _after = everyContainer _container;
    private _index = _after findIf {(_x select 0) == _class && {!((_x select 1) in _before)}};
    if (_index >= 0) then {[(_after select _index) select 1, _contents] call ACME_fnc_carrierCargoPopulate;};
} forEach _children;
true
