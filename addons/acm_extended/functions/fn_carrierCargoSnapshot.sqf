/* Owner-frame cargo snapshot. Preserve individual partial magazines, attached weapons and nested containers.
   Only current engine cargo is authoritative; the pre-removal loadout is never a live supplies ledger. */
params ["_container"];
if (isNull _container) exitWith {[[], [], [], []]};
private _items = +itemCargo _container;
private _children = [];
{
    _x params ["_class", "_child"];
    private _index = _items find _class;
    if (_index >= 0) then {_items deleteAt _index;};
    _children pushBack [_class, _class in backpackCargo _container, [_child] call ACME_fnc_carrierCargoSnapshot];
} forEach everyContainer _container;
[_items, magazinesAmmoCargo _container, weaponsItemsCargo _container, _children]
