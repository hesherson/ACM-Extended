#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle attempt to slap patient awake (LOCAL)
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_disability_fnc_slapAwakeLocal;
 *
 * Public: No
 */

params ["_medic", "_patient"];

private _hintArray = ["%1<br/>%2", LSTRING(SlapPatient_Attempt), LSTRING(AttemptWakeUp_Failure)];

if (ACE_player == _patient) then {
    addCamShake [5, 0.2, 30];
};

if (random 1 < 0.2) then {
    [_patient, 0.051, "head", "slap", _medic] call ACEFUNC(medical,addDamageToUnit);
};

if !(IS_UNCONSCIOUS(_patient)) exitWith {};

if !([_patient, true] call EFUNC(core,canWake)) exitWith {
    [QACEGVAR(common,displayTextStructured), [_hintArray, 2, _medic, 12], _medic] call CBA_fnc_targetEvent;
};

private _oxygenSaturationChance = linearConversion [80, 99, GET_OXYGEN(_patient), 0.05, 0.4, true] ;

if (random 1 < _oxygenSaturationChance) then {
    if ([_patient, true, "slap"] call EFUNC(core,requestWake)) then {
        [QEGVAR(core,playWakeUpSound), _patient] call CBA_fnc_localEvent;
        _hintArray set [2, LSTRING(AttemptWakeUp_Success)];
    };
};

[QACEGVAR(common,displayTextStructured), [_hintArray, 2, _medic, 12], _medic] call CBA_fnc_targetEvent;
