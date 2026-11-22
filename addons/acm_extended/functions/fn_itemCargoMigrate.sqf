params ["_holder"];
if (isNull _holder || {!local _holder}) exitWith {};

if (_holder isKindOf "CAManBase") exitWith {
    private _nvg = hmd _holder;
    private _canonical = [_nvg, "CfgWeapons"] call ACME_fnc_itemClassCanonical;
    if (_canonical != _nvg) then {
        _holder unlinkItem _nvg;
        _holder linkItem _canonical;
    };
    {
        [_x] call ACME_fnc_itemCargoMigrate;
    } forEach [uniformContainer _holder, vestContainer _holder, backpackContainer _holder];
};

(getItemCargo _holder) params ["_items", "_counts"];
{
    private _canonical = [_x, "CfgWeapons"] call ACME_fnc_itemClassCanonical;
    if (_canonical != _x) then {
        private _count = _counts select _forEachIndex;
        _holder addItemCargoGlobal [_x, -_count];
        _holder addItemCargoGlobal [_canonical, _count];
    };
} forEach _items;
{
    _x params ["_class", "_ammo"];
    private _canonical = [_class, "CfgMagazines"] call ACME_fnc_itemClassCanonical;
    if (_canonical != _class) then {
        _holder addMagazineAmmoCargo [_class, -1, _ammo];
        _holder addMagazineAmmoCargo [_canonical, 1, _ammo];
    };
} forEach magazinesAmmoCargo _holder;
{[_x select 1] call ACME_fnc_itemCargoMigrate;} forEach everyContainer _holder;
