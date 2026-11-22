/* Open one kit in the exact container it came from. Return that container
   on success. A reusable BOA band is issued with the rest of the supplies. */
params ["_unit", "_item", ["_consume", true]];
if (_unit getVariable ["ACME_persistenceFrozen", false]) exitWith {objNull};
private _source = objNull;
isNil {
    private _stock = [_unit, _item] call ACME_fnc_ivStartKitStock;
    if (_stock isEqualTo []) exitWith {};
    private _kits = [];
    {_kits pushBackUnique (_x select 0);} forEach _stock;

    private _containers = [uniformContainer _unit, vestContainer _unit, backpackContainer _unit];
    {
        private _container = _x;
        if (!isNull _container) then {
            private _cargo = itemCargo _container;
            private _index = _cargo findIf {_x in _kits};
            if (_index >= 0) then {
                private _kit = _cargo select _index;
                // what this kit holds (catheters of its own gauge), less the item taken from it now
                private _contents = +(getArray (configFile >> "CfgWeapons" >> _kit >> "ACME_ivStartKitContents"));
                if (_consume) then {_contents deleteAt (_contents find _item);};
                private _before = {_x == _kit} count _cargo;
                _container addItemCargoGlobal [_kit, -1];
                if (({_x == _kit} count (itemCargo _container)) == _before - 1) then {
                    private _added = [];
                    {
                        private _class = _x;
                        if !(_container canAdd _class) exitWith {};
                        private _count = {_x == _class} count (itemCargo _container);
                        _container addItemCargoGlobal [_class, 1];
                        if (({_x == _class} count (itemCargo _container)) != _count + 1) exitWith {};
                        _added pushBack _class;
                    } forEach _contents;
                    if (count _added == count _contents) then {
                        _source = _container;
                    } else {
                        {_container addItemCargoGlobal [_x, -1];} forEach _added;
                        _container addItemCargoGlobal [_kit, 1];
                    };
                };
            };
        };
        if (!isNull _source) exitWith {};
    } forEach _containers;
};
_source
