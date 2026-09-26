/* How many of an item a unit can use for treatment. Every read of a medic's or patient's supplies goes
   through here, so an inventory mod has one place to answer it: with Enhanced First Aid Kits loaded,
   what is packed in the unit's kits counts as well (efak_medical_fnc_countItem). Otherwise ACE's count. */
params [["_unit", objNull, [objNull]], ["_item", "", [""]]];
if (isNull _unit || {_item == ""}) exitWith {0};
if (!isNil "efak_medical_fnc_countItem" && {_unit isKindOf "CAManBase"}) exitWith {[_unit, _item] call efak_medical_fnc_countItem};
[_unit, _item] call ace_common_fnc_getCountOfItem
