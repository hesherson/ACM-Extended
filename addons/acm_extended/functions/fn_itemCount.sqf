/* Count loose supplies, EFAK contents and available sealed IV Start Kits. */
params [["_unit", objNull, [objNull]], ["_item", "", [""]], ["_includeStartKits", true]];
if (isNull _unit || {_item == ""}) exitWith {0};
private _count = if (!isNil "efak_medical_fnc_countItem" && {_unit isKindOf "CAManBase"}) then {
    [_unit, _item] call efak_medical_fnc_countItem
} else {
    [_unit, _item] call ace_common_fnc_getCountOfItem
};
if (_includeStartKits) then {
    ([_unit, _item] call ACME_fnc_ivStartKitStock) params ["_contents", "_kits"];
    _count = _count + (({_x == _item} count _contents) * count _kits);
};
_count
