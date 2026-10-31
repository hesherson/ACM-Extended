/* One owner-authored topology field; no bag or inventory mutations. */
params ["_patient", "_lines", ["_public", true]];
if (isNull _patient || {!local _patient} || {!(_lines isEqualType createHashMap)}) exitWith {false};
[_patient, "ACME_PiggybackLines", _lines, _public] call ACME_fnc_setVarNet;
true
