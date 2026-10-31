/* Portable cylinders cannot satisfy fixed facility/vehicle oxygen actions. No inventory mutation. */
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_source", "facility", [""]]];
if (isNull _medic || {isNull _patient}) exitWith {false};
switch (_source) do {
    case "portable": {([_medic, "ACM_OxygenTank_425"] call ACME_fnc_itemCount) > 0};
    case "vehicle": {[_medic] call ace_medical_treatment_fnc_isInMedicalVehicle
        || {[_patient] call ace_medical_treatment_fnc_isInMedicalVehicle}};
    case "facility": {[_medic] call ace_medical_treatment_fnc_isInMedicalFacility
        || {[_patient] call ace_medical_treatment_fnc_isInMedicalFacility}};
    default {false};
}
