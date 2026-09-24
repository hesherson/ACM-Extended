// the manual core-temperature check. it reads the current core temp of the patient, ACME_hypo_temp, maintained by
// the hypothermia model through injury-driven cooling and cold products, with the ambient as a multiplier, and
// freezes it as the displayed reading until the medic checks again.
// it is the same manual-update behavior as a NIBP blood-pressure reading: the number does not auto-track, and you
// take a fresh reading when you want an update. the frozen value renders persistently in the medical-menu vitals
// section through fn_tempinjuryentry.
// _this is [_medic, _patient, _bodyPart], the ACE treatment callbacksuccess args.
params ["_medic", "_patient"];
if (isNull _medic || {isNull _patient}) exitWith {};
// B33: recheck the reusable SureTemp on completion, including if it was dropped
// after treatment started. An ungated callback must not reveal an exact reading.
if (([_medic, "ACM_Thermometer"] call ACME_fnc_itemCount) <= 0) exitWith {};

private _t = _patient getVariable ["ACME_hypo_temp", 37];
_patient setVariable ["ACME_tempReading", _t, true];
_patient setVariable ["ACME_tempReadingAt", serverTime, true];

[format ["Temperature: %1%2C", (_t toFixed 1), (toString [176])], 1.75, _medic] call ace_common_fnc_displayTextStructured;
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    [_patient, "quick_view", "Temperature: %1 C", "Core temp %1 C", [(_t toFixed 1)]] call ACME_fnc_medLog;
};
