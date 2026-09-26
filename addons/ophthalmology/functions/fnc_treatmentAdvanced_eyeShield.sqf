#include "..\script_component.hpp"
/*
 * ACME 1.3.0 eye-shield treatment.
 * Placement is dispatched to the casualty owner. Recovery/stabilization belongs to the single
 * global structural worker, never to a per-treatment PFH.
 */
params ["_medic", "_patient"];

private _eyeInjuries = _patient getVariable [QGVAR(eyeInjuries), [1, 1]];
private _eyeIndex = [1,0] select ((_eyeInjuries select 0) <= (_eyeInjuries select 1));
private _shieldItem = ["kat_eyecovers_right","kat_eyecovers_left"] select _eyeIndex;

[QGVAR(applyEyeShield), [_patient,_shieldItem,_eyeIndex], _patient] call CBA_fnc_targetEvent;

[_patient, LLSTRING(eyeshield_item)] call ACEFUNC(medical_treatment,addToTriageCard);
[_patient, "activity", ACELSTRING(medical_treatment,Activity_usedItem), [[_medic] call ACEFUNC(common,getName), LLSTRING(eyeshield_item)]] call ACEFUNC(medical_treatment,addToLog);
