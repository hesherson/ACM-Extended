#include "..\script_component.hpp"
/* Author: ACM Extended Fork. Core-owned writer for ACM's lying-state flag. */
params [["_patient", objNull, [objNull]], ["_lying", false, [true]], ["_public", true, [true]]];
if (isNull _patient) exitWith {false};
_patient setVariable [QGVAR(Lying_State), _lying, _public];
if (!isNil "ACME_fnc_aiProtectionSync") then {
    if (local _patient) then {
        [_patient] call ACME_fnc_aiProtectionSync;
    } else {
        ["ACME_aiProtectionRefresh", [_patient], _patient] call CBA_fnc_targetEvent;
    };
};
true
