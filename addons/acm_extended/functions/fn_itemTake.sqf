/* Take one of an item from a unit for a treatment. The counterpart of ACME_fnc_itemCount: with Enhanced
   First Aid Kits loaded a loose one goes first, otherwise one straight out of a kit
   (efak_medical_fnc_takeItem). Otherwise the engine's removeItem, as before. True when one was taken. */
params [["_unit", objNull, [objNull]], ["_item", "", [""]]];
if (isNull _unit || {_item == ""}) exitWith {false};
private _taken = if (!isNil "efak_medical_fnc_takeItem" && {_unit isKindOf "CAManBase"}) then {
    [_unit, _item] call efak_medical_fnc_takeItem
} else {
    private _before = [_unit, _item] call ace_common_fnc_getCountOfItem;
    if (_before > 0) then {_unit removeItem _item;};
    ([_unit, _item] call ace_common_fnc_getCountOfItem) < _before
};
_taken || {!isNull ([_unit, _item] call ACME_fnc_ivStartKitUnpack)}
