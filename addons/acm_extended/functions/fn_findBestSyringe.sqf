params [["_unit", ACE_player]];

private _items = [_unit, 0] call ACME_fnc_itemList;
private _result = -1;

{
    private _class = format ["ACM_Syringe_%1", _x];
    if (_class in _items) exitWith {_result = _x};
} forEach [10, 5, 3, 1];

_result;
