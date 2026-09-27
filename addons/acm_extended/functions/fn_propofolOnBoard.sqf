/* Read the effect of admitted propofol from the native medication history.
   fn_infusionDeliver uses the same Propofol_IV class as a manual IV push.
   Native medicationLocal applies dose, weight and kinetics. Do not scale it again here. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {isNil "ace_medical_status_fnc_getMedicationCount"}) exitWith {0};
private _effect = [_patient, "Propofol_IV", false] call ACME_fnc_medicationCountCompat;
if (!(_effect isEqualType 0) || {!finite _effect}) exitWith {0};
_effect max 0
