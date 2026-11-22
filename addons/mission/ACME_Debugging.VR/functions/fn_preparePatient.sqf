/* Run on the patient owner. Repeat preparation is suppressed for the same unit. */
params ["_patient", "_profile"];
if (isNull _patient || {!local _patient} || {!alive _patient}
    || {_patient getVariable ["ACMEQA_prepared", false]}) exitWith {false};
if (isNil "ace_medical_fnc_addDamageToUnit" || {isNil "ace_medical_fnc_setUnconscious"}) exitWith {false};
_patient setVariable ["ACMEQA_prepared", true, true];
_patient setVariable ["ACMEQA_patientRole", _profile, true];
removeBackpack _patient;
if (_profile in ["transfer", "player"]) then {
    removeVest _patient;
    _patient addVest "V_PlateCarrier1_rgr";
    _patient addItemToVest "ACE_tourniquet";
    _patient addItemToVest "ACE_fieldDressing";
};
if (_profile == "treatment") then {
    [_patient, .45, "leftleg", "bullet"] call ace_medical_fnc_addDamageToUnit;
    [_patient, .25, "leftarm", "bullet"] call ace_medical_fnc_addDamageToUnit;
};
if (_profile in ["transfer", "pickup", "player", "load"]) then {
    [_patient, true, 900] call ace_medical_fnc_setUnconscious;
};
diag_log format ["[ACME QA] PATIENT_PREP profile=%1 target=%2 owner=%3", _profile, vehicleVarName _patient, clientOwner];
true
