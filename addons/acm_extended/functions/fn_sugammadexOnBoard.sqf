// Effective sugammadex exposure, IV plus IM if recorded, with native onset and washout.
// call it as [_patient] call ACME_fnc_sugammadexOnBoard, which returns a number.
params ["_patient"];
if (isNull _patient || {isNil "ace_medical_status_fnc_getMedicationCount"}) exitWith {0};
private _rIV = [_patient, "Sugammadex_IV", false] call ACME_fnc_medicationCountCompat;
private _rIM = [_patient, "Sugammadex", false] call ACME_fnc_medicationCountCompat;
_rIV + _rIM
