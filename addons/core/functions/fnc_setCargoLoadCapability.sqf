#include "..\script_component.hpp"
/* Core-owned ACE cargo integration; preserve the object's explicit load flag. */
params [
    ["_object", objNull, [objNull]],
    ["_canLoad", true, [true]],
    ["_public", true, [true]]
];
if (isNull _object) exitWith {false};
_object setVariable ["ace_cargo_canLoad", _canLoad, _public];
true
