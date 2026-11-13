/* Pure logical selection. A disabled sensor has no cosmetic line; no physiology is changed. */
params ["_device"];
if (isNull _device || {_device getVariable ["ACME_eq_busy",false]} || {_device getVariable ["ACME_eq_restoreStaged",false]}) exitWith {[]};
private _kind=_device getVariable ["ACME_eq_kind",""];
if (_kind=="") then {
    if (_device isKindOf "ACME_TempusPro") then {_kind="pro";};
    if (_device isKindOf "ACME_TempusLS") then {_kind="ls";};
};
if !(_kind in ["pro","ls"]) exitWith {[]};
private _out=[];private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
private _patient=_device getVariable [_prefix+"_pat",objNull];
if (!isNull _patient && {_device distance _patient <= 6} && {isNull objectParent _patient}) then {
    if (_kind=="pro") then {
        private _sensors=_device getVariable ["acme_tempus_sensors",[true,false,false,false,false]];
        if !(_sensors isEqualType []) then {_sensors=[];};
        {if ((_sensors param [_forEachIndex,false]) isEqualTo true) then {_out pushBack [_x,_patient,true];};} forEach ["ecg","spo2","nibp","capno","temp"];
    } else {
        if ((_device getVariable ["acme_tempusls_pads",true]) isEqualTo true) then {_out pushBack ["pads",_patient,true];};
        if ((_device getVariable ["acme_tempusls_ecg",false]) isEqualTo true) then {_out pushBack ["ecg",_patient,true];};
    };
};
if (_kind=="ls") then {
    private _usb=_device getVariable ["ACME_eq_usb",objNull];
    if (!isNull _usb && {_device distance _usb <= 2.5}
        && {(_usb getVariable ["ACME_eq_usbLs",objNull]) isEqualTo _device}) then {_out pushBack ["usb",_usb,false];};
};
_out
