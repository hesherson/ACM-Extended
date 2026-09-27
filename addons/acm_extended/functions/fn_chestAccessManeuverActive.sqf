// Chest custody lasts through paused/entering CPR and BVM, not just delivered compressions or breaths.
params ["_patient"];
if (isNull _patient) exitWith {false};
([_patient] call ACM_core_fnc_cprActive)
    || {[_patient] call ACM_core_fnc_bvmActive}
    || {[_patient getVariable ["ACM_circulation_CPR_Medic", objNull], _patient] call ACM_circulation_fnc_cprSessionValid}
    || {[_patient getVariable ["ACM_breathing_BVM_Medic", objNull], _patient] call ACM_breathing_fnc_bvmSessionValid}
