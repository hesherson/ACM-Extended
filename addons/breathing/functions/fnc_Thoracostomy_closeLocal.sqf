/* ACM procedure callback: patient-owner readiness gate and completion log.
   Body posture does not cause delayed tube failure. Closing drainage preserves
   residual collapse after the internal leak has settled. */
params ["_medic", "_patient", ["_report", false]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    ["ACM_breathing_Thoracostomy_closeLocal", _this, _patient] call CBA_fnc_targetEvent;
};
// Closing an incision is not removal of an installed chest tube.
if ((_patient getVariable ["ACME_thora_tube_left", false])
    || {_patient getVariable ["ACME_thora_tube_right", false]}) exitWith {
    ["ace_common_displayTextStructured", ["Remove the chest tube before closing the incision.", 2, _medic], _medic] call CBA_fnc_targetEvent;
};
[_patient] call ACME_fnc_ptxEnsure;
if !([_patient] call ACME_fnc_ptxCanClose) exitWith {
    ["ace_common_displayTextStructured", ["Maintain chest drainage until PTX is stable, and seal all chest wounds before closing the incision.", 3, _medic], _medic] call CBA_fnc_targetEvent;
};

_patient setVariable ["ACM_breathing_Thoracostomy_State", 0, true];
_patient setVariable ["ACM_breathing_Thoracostomy_UsedKit", false, true];
// Native Close has no side selection, so close both recorded surgical tracts.
// External traumatic wound records and their seals remain untouched.
{
    _patient setVariable [format ["ACME_thora_open_%1", _x], "", true];
    _patient setVariable [format ["ACME_thora_tube_%1", _x], false, true];
    _patient setVariable [format ["ACME_thora_sealed_%1", _x], false, true];
    _patient setVariable [format ["ACME_thora_closed_%1", _x], false, true];
    _patient setVariable [format ["ACME_thora_incision_%1", _x], [], true];
    _patient setVariable [format ["ACME_thora_site_%1", _x], [], true];
} forEach ["left", "right"];
// Owner callbacks must let every viewer notice this version, including the owner.
_patient setVariable ["ACME_thora_ver", (_patient getVariable ["ACME_thora_ver", 0]) + 1, true];
[_patient, "close"] call ACME_fnc_ptxTreat;
[_patient] call ACM_breathing_fnc_updateLungState;
if (_report) then {
    [_patient, "activity", localize "STR_ACM_Breathing_ThoracostomyClose_ActionLog", [[_medic, false, true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;
};
