#include "..\script_component.hpp"
/*
 * Author: Blue
 * Check if player can use BVM on patient.
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 * 2: In Progress Check? <BOOL>
 *
 * Return Value:
 * Can use BVM? <BOOL>
 *
 * Example:
 * [player, cursorTarget] call ACM_breathing_fnc_canUseBVM;
 *
 * Public: No
 */

params ["_medic", "_patient", ["_inProgress", false]];
// Mechanical ventilation owns this native channel; disconnect it before switching to a hand bag.
if ((_patient getVariable [QGVAR(BVM_provider),objNull]) isEqualTo _patient) exitWith {false};

if (!_inProgress && {[_patient getVariable [QGVAR(BVM_Medic), objNull], _patient] call FUNC(bvmSessionValid)}) exitWith {
    false;
};

!(_patient call ACEFUNC(common,isAwake)) || (_patient call ACEFUNC(common,isAwake) && (_patient getVariable [QEGVAR(core,Lying_State), false]))
