#include "\x\ACM\addons\circulation\script_component.hpp"
/* B14: onset-aware, route-normalized family burden; native overdose syndromes retained.
   A reversal cannot be immediately undone by replaying the same historical exposure. */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
private _handleOverdoseEffect = {
    params ["_patient", "_classname"];

    switch (_classname) do {
        case "Amiodarone_IV": {
            [_patient, "Overdose_Amiodarone", 60, 360, (random [-100, -110, -120]), 0, 0, ACM_ROUTE_IV, 300, 0, 0, 0, 1, "Overdose_Amiodarone", -1] call ACEFUNC(medical_status,addMedicationAdjustment);
        };
        case "Ketamine";
        case "Ketamine_IV": {
            [_patient, "Overdose_Ketamine", 60, 360, (random [-20, -35, -40]), 0, 0, ACM_ROUTE_IM, 240, 0, (random [-0.9, -0.95, -1]), (random [-0.01, -0.05, -0.1]), 1, "Overdose_Ketamine", -1] call ACEFUNC(medical_status,addMedicationAdjustment);
        };
        case "Lidocaine": {
            [_patient, "Overdose_Lidocaine", 60, 360, (random [-40, -45, -50]), 0, 0, ACM_ROUTE_IM, 240, 0, (random [-0.9, -0.95, -1]), 0, 1, "Overdose_Lidocaine", -1] call ACEFUNC(medical_status,addMedicationAdjustment);
        };
        case "Fentanyl";
        case "Fentanyl_IV";
        case "Fentanyl_BUC";
        case "Morphine";
        case "Morphine_IV": {
            [_patient, "Overdose_Opioid", 60, 360, (random [-10, -15, -20]), 0, 0, ACM_ROUTE_IM, 240, (random [-40, -45, -50]), (random [-0.9, -0.95, -1]), (random [-0.01, -0.05, -0.1]), 1, "Overdose_Opioid", -1] call ACEFUNC(medical_status,addMedicationAdjustment);
        };
        case "Penthrox": {
            [_patient, "Overdose_Penthrox", 30, 300, (random [-10, -15, -20]), 0, 0, ACM_ROUTE_IM, 120, (random [-40, -45, -50]), (random [-0.9, -0.95, -1]), (random [-0.01, -0.05, -0.1]), 1, "Overdose_Penthrox", -1] call ACEFUNC(medical_status,addMedicationAdjustment);
        };
    };
};

// B14: combine within-family toxic burden using each route's OWN normalized threshold.
// No raw mg addition across fentanyl/morphine or across nasal product units.
private _groups = [
    ["opioid","Fentanyl_IV","Overdose_Opioid",["Fentanyl","Fentanyl_IV","Fentanyl_BUC","Morphine","Morphine_IV"]],
    ["ketamine","Ketamine_IV","Overdose_Ketamine",["Ketamine","Ketamine_IV","Esketamine"]],
    ["Amiodarone_IV","Amiodarone_IV","Overdose_Amiodarone",["Amiodarone_IV"]],
    ["Penthrox","Penthrox","Overdose_Penthrox",["Penthrox"]]
];
private _generations = _patient getVariable ["ACME_medicationGenerations",createHashMap];
private _fired = _patient getVariable ["ACME_medicationToxicityFired",createHashMap];
{
    _x params ["_family","_trigger","_syndrome","_classes"];
    private _burden = 0;
    {
        private _cfg = configFile >> "ACM_Medication" >> "Medications" >> _x;
        private _limit = getNumber (_cfg >> "maxDose");
        private _reference = getNumber (_cfg >> "maxEffectDose");
        if (getNumber (_cfg >> "weightEffect") > 0) then {
            _reference = _reference * (GET_BODYWEIGHT(_patient) / IDEAL_BODYWEIGHT);
        };
        if (_limit > 0 && {_reference > 0}) then {
            _burden = _burden + ([_patient,_x,false] call ACME_fnc_medicationCountCompat) * _reference / _limit;
        };
    } forEach _classes;
    private _generation = _generations getOrDefault [_family,0];
    private _last = _fired getOrDefault [_family,-1];
    if (_burden > 1.05 && {_generation > _last}
        && {([_patient,_syndrome,true] call ACME_fnc_medicationCountCompat) <= 0.001}) then {
        _fired = [_patient, "mark", _family, _generation, createHashMap, true] call ACME_fnc_medicationToxicityFiredCommit; // commit before adding another medication record
        [_patient,_trigger] call _handleOverdoseEffect;
    };
} forEach _groups;
