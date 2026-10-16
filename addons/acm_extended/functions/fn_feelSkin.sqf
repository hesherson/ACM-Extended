// the "Feel Skin" examine action callback. it reports the brief, color-coded skin descriptor, meaning the pallor,
// temperature and moisture, for the patient. it is a tactile and visual perfusion check.
// _this, the ACE callback, is [_medic, _patient, _bodyPart].
params ["_medic", "_patient"];
if (isNull _patient) exitWith {};

(_patient call ACME_fnc_skinSigns) params ["_short", "_desc", "_rgba", "_hex"];

[format ["<t color='%1'>%2</t>", _hex, _desc], 4, _medic] call ace_common_fnc_displayTextStructured;

// record the perfusion check in the ACE activity log, so the aar and scorecards capture that the skin was
// assessed.
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    private _args = [[_medic, false, true] call ace_common_fnc_getName, _desc];
    [_patient, "activity", "%1 felt skin: %2", _args] call ace_medical_treatment_fnc_addToLog;
    [_patient, "quick_view", "%1 felt skin: %2", _args] call ace_medical_treatment_fnc_addToLog;
};
