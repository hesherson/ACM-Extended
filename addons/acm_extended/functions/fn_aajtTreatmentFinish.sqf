/* Retire exactly the AAJT episode that ACE completed. Never select a weapon or stop a newer provider pose. */
params ["_args", ["_success", false, [false]]];
_args params ["_medic", "_patient", "_bodyPart", "_classname"];
if (isNull _medic || {!local _medic}) exitWith {false};
private _token = _args param [7, -1];
private _record = _medic getVariable ["ACME_aajtTreatment", []];
if (_token < 0 || {(_record param [0, -2]) != _token}
    || {(_record param [1, objNull]) isNotEqualTo _patient}
    || {(_record param [2, ""]) != _bodyPart}
    || {(_record param [3, ""]) != toLowerANSI _classname}) exitWith {false};
_medic setVariable ["ACME_aajtTreatment", [], false];
private _epoch = _record param [4, -1];
if (_epoch >= 0) then {[_medic, "aajt", _epoch] call ACME_fnc_treatmentPoseStop;};
if (!_success && {((toLowerANSI _classname) find "acme_applyaajt_") == 0} && {!isNull _patient}) then {
    [_patient, "aajtApplying", ["", false]] call ACME_fnc_ownerDispatch;
};
true
