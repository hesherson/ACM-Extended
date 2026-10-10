/* Attached-device action. No clinical timer or second device purchase. */
params ["_medic", "_patient"];
if (isNull _medic || {!local _medic} || {!alive _medic} || {isNull _patient}) exitWith {false};
private _pending = _medic getVariable ["ACME_ventMaskPending", []];
if (_pending isNotEqualTo [] && {serverTime < (_pending param [4, -1])}) exitWith {false};
private _serial = (_medic getVariable ["ACME_ventMaskSerial", 0]) + 1;
_medic setVariable ["ACME_ventMaskSerial", _serial, false];
private _presentation = [_medic getVariable ["ACME_treatmentPoseEpoch", 0],
    _medic getVariable ["ACME_providerLocalityEpoch", 0], serverTime + 3,
    _medic getVariable ["ACME_providerTreatmentEpoch", 0], _medic getVariable ["ACME_headElev_medicAnimToken", 0]];
private _request = [_serial, _patient, _patient getVariable ["ACME_vent_custodyId", ""],
    [_patient] call ACME_fnc_clinicalEpoch, serverTime + 3, _presentation];
_medic setVariable ["ACME_ventMaskPending", _request, false];
[_patient, _medic, _request select 2, _request select 3, _request select 4, _request] call ACME_fnc_ventSetMaskCPAP;
true
