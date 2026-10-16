#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle closing up Thoracostomy incision
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorTarget] call ACM_breathing_fnc_Thoracostomy_close;
 *
 * Public: No
 */

params ["_medic", "_patient"];

if ((_patient getVariable [QGVAR(Thoracostomy_State), -1]) == 0) exitWith {
    [LLSTRING(ThoracostomyClose_Already), 2, _medic] call ACEFUNC(common,displayTextStructured);
};

if !([_patient] call ACME_fnc_ptxCanClose) exitWith {
    ["Maintain chest drainage until PTX is stable, and seal all chest wounds before closing the incision.", 3, _medic] call ACEFUNC(common,displayTextStructured);
};

[QGVAR(Thoracostomy_closeLocal), [_medic, _patient, true], _patient] call CBA_fnc_targetEvent;
