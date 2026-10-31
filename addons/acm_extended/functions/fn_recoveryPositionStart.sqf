/* B215: recovery uses exactly Flip's provider theatre, including its prone and holster path. */
params ["_medic", "_patient", "_part", "_classname"];
if ((toLowerANSI _classname) != "recoveryposition") exitWith {};
private _serial = (_medic getVariable ["ACME_recoverySerial", 0]) + 1;
_medic setVariable ["ACME_recoverySerial", _serial];
private _token = format ["recovery:%1:%2:%3", clientOwner, netId _medic, _serial];
_this set [7, _token];
private _started = [_medic, "recoveryPosition", _patient] call ACME_fnc_rollProviderStart;
private _epoch = if (_started) then {(_medic getVariable ["ACME_treatmentPoseState", []]) param [0, -1]} else {-1};
_medic setVariable ["ACME_recoveryAction", [_token, _patient, _epoch, _medic getVariable ["ACME_rollProviderToken", ""], false, [_patient] call ACME_fnc_clinicalEpoch, _medic getVariable ["ACME_providerLocalityEpoch", 0]]];
