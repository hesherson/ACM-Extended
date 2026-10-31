/*
 * Author: Blue; owner/progression integration by ACM Extended B35
 * Perform (finger) thoracostomy on patient. (LOCAL)
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 * 2: Used Kit <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorTarget] call ACM_breathing_fnc_Thoracostomy_startLocal;
 *
 * Public: No
 */

params ["_medic", "_patient", ["_usedKit", false], ["_report", true]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    ["ACM_breathing_Thoracostomy_startLocal", _this, _patient] call CBA_fnc_targetEvent;
};
// Native treatment has no side identifier. A completed tract/tube must not be
// overwritten by a delayed legacy start packet; surgical side-aware repeats use
// the epoch-checked owner aftercare transaction instead.
if (_report && {(_patient getVariable ["ACM_breathing_Thoracostomy_State", 0]) >= 1}) exitWith {};
[_patient] call ACME_fnc_ptxEnsure;


private _hintArray = ["%1", "STR_ACM_Breathing_ThoracostomySweep_Complete"];
private _hintLogArray = [];
private _hintLogFormat = "%1: %2";

private _height = 2.5;

private _RR = (_patient getVariable ["ACM_breathing_RespirationRate", 18]);

switch (true) do {
    case (_patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0] > 0.8): {
        _height = 3;

        _hintArray set [0, "%1<br/><br/>%2<br/>%3"];
        _hintArray append ["STR_ACM_Breathing_ThoracostomySweep_SevereBlood", "STR_ACM_Breathing_ThoracostomySweep_SevereCollapse"];

        _hintLogArray append ["STR_ACM_Breathing_ThoracostomySweep_SevereCollapse_Short", "STR_ACM_Breathing_ThoracostomySweep_SevereBlood_Short"];
        _hintLogFormat = "%1: %2, %3";
    };
    case (_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]): {
        _hintArray set [0, "%1<br/><br/>%2"];
        _hintArray pushBack "STR_ACM_Breathing_ThoracostomySweep_SevereCollapse";

        _hintLogArray pushBack "STR_ACM_Breathing_ThoracostomySweep_SevereCollapse_Short";
    };
    case (_patient getVariable ["ACM_breathing_Hemothorax_State", 0] > 0): {
        _hintArray set [0, "%1<br/><br/>%2"];
        _hintArray pushBack "STR_ACM_Breathing_ThoracostomySweep_Bleeding";

        _hintLogArray pushBack "STR_ACM_Breathing_ThoracostomySweep_Bleeding_Short";
    };
    case (_patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0] > 0): {
        _height = 3;

        _hintArray pushBack "STR_ACM_Breathing_ThoracostomySweep_Blood";
        _hintLogArray pushBack "STR_ACM_Breathing_ThoracostomySweep_Blood_Short";

        _hintLogFormat = "%1: %2, %3";

        if (_RR < 1) then {
            _hintArray set [0, "%1<br/><br/>%2<br/>%3"];
            _hintArray pushBack "STR_ACM_Breathing_ThoracostomySweep_NotInflating";

            _hintLogArray pushBack "STR_ACM_Breathing_ThoracostomySweep_NotInflating";
        } else {
            _hintArray set [0, "%1<br/><br/>%2<br/>%3"];
            _hintArray pushBack "STR_ACM_Breathing_ThoracostomySweep_Normal";

            _hintLogArray pushBack "STR_ACM_Breathing_ThoracostomySweep_Normal_Short";
        };
    };
    case (_RR < 1 || !(alive _patient)): {
        _hintArray set [0, "%1<br/><br/>%2"];
        _hintArray pushBack "STR_ACM_Breathing_ThoracostomySweep_NotInflating";

        _hintLogArray pushBack "STR_ACM_Breathing_ThoracostomySweep_NotInflating";
    };
    default {
        _hintArray set [0, "%1<br/><br/>%2"];
        _hintArray pushBack "STR_ACM_Breathing_ThoracostomySweep_Normal";

        _hintLogArray pushBack "STR_ACM_Breathing_ThoracostomySweep_Normal";
    };
};

private _logArray = ["STR_ACM_Breathing_ThoracostomySweep_ActionLog"];
_logArray append _hintLogArray;

if (_report) then {
    private _drained = [_patient, _medic, "finger", [_patient] call ACME_fnc_clinicalEpoch, [], false] call ACME_fnc_thoraDrainBloodLocal;
    _hintArray set [0, (_hintArray select 0) + format ["<br/>Blood drained: %1 mL", (round ((_drained max 0) * 10000)) / 10]];
    ["ace_common_displayTextStructured", [_hintArray, _height, _medic, 13], _medic] call CBA_fnc_targetEvent;
    [_patient, "quick_view", _hintLogFormat, _logArray] call ace_medical_treatment_fnc_addToLog;
};

_patient setVariable ["ACM_breathing_Thoracostomy_State", 1, true];

private _anestheticEffect = [_patient, "Lidocaine", false, 1] call ace_medical_status_fnc_getMedicationCount;

if (_anestheticEffect < 0.7) then {
    [_patient, (1 - _anestheticEffect)] call ace_medical_fnc_adjustPainLevel;
    if (_anestheticEffect < 0.5) then {
        ["ace_medical_CriticalVitals", _patient] call CBA_fnc_localEvent;
    };
};

_patient setVariable ["ACM_breathing_Thoracostomy_UsedKit", _usedKit, true];
[_patient, "thora"] call ACME_fnc_ptxTreat;
[_patient] call ACM_breathing_fnc_updateLungState;
