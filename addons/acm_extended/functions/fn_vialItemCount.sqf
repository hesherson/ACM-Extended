/* Count one vial/item in either a person inventory or a vehicle cargo inventory. */
params [["_holder", objNull, [objNull]], ["_item", "", [""]]];
if (isNull _holder || {_item == ""}) exitWith {0};
if (_holder isKindOf "CAManBase") exitWith {
    private _carrier = [_holder] call ACME_fnc_carrierInventoryGet;
    private _count = [_holder, _item] call ACME_fnc_itemCount;
    if (!isNull _carrier) then {_count = _count + ({_x == _item} count itemCargo _carrier);};
    _count
};
private _cargo = getItemCargo _holder;
private _idx = (_cargo select 0) find _item;
if (_idx < 0) exitWith {0};
(_cargo select 1) param [_idx, 0]
