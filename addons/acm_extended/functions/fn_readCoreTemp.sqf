// the core-temperature readout for the ACM_Thermometer tool. it fires after the roughly 8 s active-use action
// completes.
// it reads the core temp of the patient, ACME_hypo_temp, the source of truth of the hypothermia system and the same
// value fn_circhandle and fn_togglehypothermia use, and reports it to the medic with a clinical band.
// the thermometer is a reusable tool rather than a consumed one, so this only reads and never changes the
// temperature.
// _this is the ACE callback [_medic, _patient, _bodyPart].
params ["_medic", "_patient"];
if (isNull _medic || {isNull _patient}) exitWith {};
// B33: the alternate exact-temperature action uses the same reusable device.
// The action condition alone cannot cover a tool dropped during treatment.
if (([_medic, _patient, "ACM_Thermometer"] call ACME_fnc_treatmentSupplyCount) <= 0) exitWith {};

private _t = _patient getVariable ["ACME_hypo_temp", 37];
private _band = switch (true) do {
    case (_t < 28):   {"SEVERE hypothermia"};
    case (_t < 32):   {"moderate hypothermia"};
    case (_t < 35):   {"mild hypothermia"};
    case (_t > 38.3): {"hyperthermia"};
    default           {"normothermic"};
};

[format ["Core temperature: %1 C  (%2)", _t toFixed 1, _band], 4, _medic] call ace_common_fnc_displayTextStructured;

if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    [_patient, "activity", "Core temperature measured: %1 C (%2)", "Core temp %1 C, %2", [_t toFixed 1, _band]] call ACME_fnc_medLog;
};
