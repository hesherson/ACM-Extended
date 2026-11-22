#include "..\script_component.hpp"
/*
 * Author: Blue
 * Init unit.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_airway_fnc_initUnit;
 *
 * Public: No
 */

params ["_patient"];

// (B387: rolled by the unit's own machine only and sent to all; every machine rolling its own raced)
if (local _patient) then {_patient setVariable [QGVAR(AirwayObstructionVomit_Count), (round(2 + random 2)), true];};
