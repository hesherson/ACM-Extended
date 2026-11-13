/* Commit a patient assignment after placement or after claiming a free field monitor. */
params ["_device","_patient","_kind","_firstSensor"];
private _ls = _kind == "ls";
private _prefix = ["acme_tempus","acme_tempusls"] select _ls;
if (_ls) then {
    [_device] call ACME_fnc_tempusLsChargeClear;
    _device setVariable ["acme_tempusls_pace",[false,70,0,false],true];
    _device setVariable ["acme_tempusls_pads",_firstSensor == 5,true];
    _device setVariable ["acme_tempusls_ecg",_firstSensor == 0,true];
} else {
    private _sensors = [false,false,false,false,false];
    if (_firstSensor >= 0) then {_sensors set [_firstSensor,true];};
    _device setVariable ["acme_tempus_sensors",_sensors,true];
};
_device setVariable [_prefix+"_v",[],true];
_device setVariable ["ACME_eq_feedOwner",[],true];
_device setVariable ["ACME_eq_feedRetryAt",0];
_device setVariable ["ACME_eq_kind",_kind,true];
_device setVariable ["ACME_eq_patient",_patient,true];
_device setVariable [_prefix+"_pat",_patient,true];
_patient setVariable ["ACME_eq_"+_kind,_device,true];
private _devices = missionNamespace getVariable ["ACME_eqDevices",[]];
_devices pushBackUnique _device;
missionNamespace setVariable ["ACME_eqDevices",_devices];
[_device,_patient] remoteExecCall [["ACME_fnc_tempusFeed","ACME_fnc_tempusLsFeed"] select _ls,_patient];
