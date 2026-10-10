#include "..\script_component.hpp"
/* Damage-owned publication of the two mutable wound ledgers used by Extended.
 * This endpoint does not choose/reopen wounds, change physical dressings, or
 * refresh bleeding. The owner-local caller retains those clinical decisions.
 * Unknown fields and non-HashMap ledgers are rejected without publication.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_changes", [], [[]]],
    ["_public", true, [true]]
];
if (isNull _patient || {!local _patient}) exitWith {0};
private _applied = 0;
{
    if (_x isEqualType [] && {count _x == 2} && {!isNil {_x select 0}} && {!isNil {_x select 1}}) then {
        private _field = _x param [0, ""];
        private _value = _x param [1, false];
        if (_field isEqualType "" && {_value isEqualType createHashMap}) then {
            private _key = switch (_field) do {
                case "clottedWounds": {QGVAR(ClottedWounds)};
                case "bandageProgress": {QGVAR(BandageProgress)};
                default {""};
            };
            if (_key != "") then {
                _patient setVariable [_key, _value, _public];
                _applied = _applied + 1;
            };
        };
    };
} forEach _changes;
_applied
