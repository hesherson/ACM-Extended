#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle Ammonia Inhalant effects (LOCAL)
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_circulation_fnc_handleMed_AmmoniaInhalantLocal;
 *
 * Public: No
 */

params ["_patient"];

private _timeSinceLastUse = CBA_missionTime - (_patient getVariable [QGVAR(AmmoniaInhalant_LastUse), -1]);

_patient setVariable [QGVAR(AmmoniaInhalant_LastUse), CBA_missionTime, true];

if (_timeSinceLastUse < 10) exitWith {};

if !([_patient, true] call EFUNC(core,canWake)) exitWith {};

private _oxygenSaturationChance = linearConversion [80, 99, GET_OXYGEN(_patient), 0.5, 1, true] ;

if (random 1 < _oxygenSaturationChance) then {
    if (IS_UNCONSCIOUS(_patient)) then {
        if ([_patient, true, "ammonia"] call EFUNC(core,requestWake)) then {
            [QEGVAR(core,playWakeUpSound), _patient] call CBA_fnc_localEvent;
        };
    };
};
