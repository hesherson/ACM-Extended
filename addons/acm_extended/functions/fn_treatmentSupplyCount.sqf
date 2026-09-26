/* Display count for the same physical treatment item sources as ACE useItem.
   This is eligibility only; treatmentSupplyTake checks again at the actual debit. */
params ["_medic", "_patient", "_item"];
private _total = 0;
private _vehicles = [];
{
    _total = _total + ([_x, _item] call ACME_fnc_itemCount);
    private _vehicle = objectParent _x;
    if (!isNull _vehicle && {!(_vehicle in _vehicles)}) then {
        _vehicles pushBack _vehicle;
        _total = _total + ({_x == _item} count (itemCargo _vehicle));
    };
} forEach ([_medic, _patient] call ACME_fnc_treatmentSupplyOrder);
_total
