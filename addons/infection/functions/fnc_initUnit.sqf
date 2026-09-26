#include "..\script_component.hpp"
/*
 * Initialize infection state. Runtime advancement belongs to the single global locality-safe worker.
 */
params ["_patient"];
if (!local _patient) exitWith {};
[_patient] call FUNC(resetVariables);
