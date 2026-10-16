/* Read-only fast preflight, repeated on the patient owner before carrier creation.
   Bag presence is about the selected route, not flow or a hidden physiological diagnosis. */
params ["_patient", "_part", "_iv", "_site"];
if (isNull _patient) exitWith {"patient-unavailable"};
if !([_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid) exitWith {"access-missing"};
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [toLowerANSI _part, []];
private _occupied = _bags findIf {
    (_x param [3, -1]) == _site && {(_x param [4, true]) == _iv}
        && {!((_x param [0, ""]) in ["ACME_Empty", "ACME_EmptySaline"])}
};
if (_occupied >= 0) exitWith {"line-occupied"};
if ([_patient, _part, _iv, _site] call ACME_fnc_isYLineAccess) exitWith {"blood-y-line"};
""
