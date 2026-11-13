/* Reconcile canonical patient slots and physical links on the server, without moving field devices. */
params ["_device"];
if (!isServer || {isNull _device}) exitWith {};
private _kind=_device getVariable ["ACME_eq_kind",""];
if !(_kind in ["pro","ls"]) exitWith {};
private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
private _patient=_device getVariable [_prefix+"_pat",objNull];
private _old=_device getVariable ["ACME_eq_patient",objNull];
if (_old isNotEqualTo _patient) then {
    if (!isNull _old && {(_old getVariable ["ACME_eq_"+_kind,objNull]) isEqualTo _device}) then {_old setVariable ["ACME_eq_"+_kind,objNull,true];};
    _device setVariable ["ACME_eq_patient",_patient,true];
    if (isNull _patient) then {_device setVariable ["ACME_eq_feedOwner",[],true];};
};
if (!isNull _patient && {isNull (_patient getVariable ["ACME_eq_"+_kind,objNull])}) then {_patient setVariable ["ACME_eq_"+_kind,_device,true];};
if (!isNull _patient && {(_device getVariable ["ACME_eq_feedOwner",[]]) isNotEqualTo [_patient,owner _patient]}
    && {serverTime >= (_device getVariable ["ACME_eq_feedRetryAt",0])}) then {
    _device setVariable ["ACME_eq_feedRetryAt",serverTime+2];
    [_device,_patient] remoteExecCall [["ACME_fnc_tempusFeed","ACME_fnc_tempusLsFeed"] select (_kind=="ls"),_patient];
};
private _mount=_device getVariable ["ACME_eq_mount",objNull];
if (_device getVariable ["ACME_eq_mounted",false] && {isNull _mount || {attachedTo _device isNotEqualTo _mount}}) then {[_device] call ACME_fnc_equipmentMountRelease;};
if (_kind != "ls") exitWith {};
private _usb=_device getVariable ["ACME_eq_usb",objNull];
if (!isNull _usb) then {
    private _proPatient=_usb getVariable ["acme_tempus_pat",objNull];
    private _valid=!(_device getVariable ["ACME_eq_busy",false]) && {!(_usb getVariable ["ACME_eq_busy",false])}
        && {_device distance _usb <= 2.5} && {(_usb getVariable ["ACME_eq_usbLs",objNull]) isEqualTo _device}
        && {isNull _patient || {isNull _proPatient} || {_patient isEqualTo _proPatient}};
    if (!_valid) then {
        if ((_usb getVariable ["ACME_eq_usbLs",objNull]) isEqualTo _device) then {_usb setVariable ["ACME_eq_usbLs",objNull,true];};
        _device setVariable ["ACME_eq_usb",objNull,true];
        _device setVariable ["ACME_eq_usbEpoch",(_device getVariable ["ACME_eq_usbEpoch",0])+1,true];
    } else {
        if (((_device getVariable ["acme_tempusls_pw",[false]]) select 0)
            && {(_usb getVariable ["acme_tempus_pw",[false]]) select 0}
            && {(_device getVariable ["acme_tempusls_link",objNull]) isNotEqualTo _usb}) then {_device setVariable ["acme_tempusls_link",_usb,true];};
    };
};
private _link=_device getVariable ["acme_tempusls_link",objNull];
if (!isNull _link) then {
    private _proPatient=_link getVariable ["acme_tempus_pat",objNull];
    if (_device distance _link > 10 || {!isNull _patient && {!isNull _proPatient} && {_patient isNotEqualTo _proPatient}}) then {_device setVariable ["acme_tempusls_link",objNull,true];};
};
