/* Match ACE shared-equipment availability. Disposable kit remains the preferred
   path; the optional surgical kit is reusable and never removed from inventory. */
params ["_medic", "_patient"];
if (isNull _medic || {isNull _patient}) exitWith {""};
if ([_medic, _patient, ["ACME_ThoracostomyKit"]] call ace_medical_treatment_fnc_hasItem) exitWith {"ACME_ThoracostomyKit"};
if (missionNamespace getVariable ["ACME_thora_allowSurgicalKit", false]
    && {[_medic, _patient, ["ACE_surgicalKit"]] call ace_medical_treatment_fnc_hasItem}) exitWith {"ACE_surgicalKit"};
""
