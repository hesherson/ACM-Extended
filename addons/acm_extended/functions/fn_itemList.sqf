/* The item classes a unit has for treatment, for code that picks from a list rather than asking for one
   item (ACME_fnc_itemCount). Same modes as ace_common_fnc_uniqueItems: 0 items, 1 items and magazines,
   2 magazines only. With Enhanced First Aid Kits loaded the unit's kits are listed too
   (efak_medical_fnc_listItems). The result may be shared: never change it. */
params [["_unit", objNull, [objNull]], ["_mode", 0, [0]]];
if (isNull _unit) exitWith {[]};
if (!isNil "efak_medical_fnc_listItems" && {_unit isKindOf "CAManBase"}) exitWith {[_unit, _mode] call efak_medical_fnc_listItems};
[_unit, _mode] call ace_common_fnc_uniqueItems
