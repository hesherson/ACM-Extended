/* Medical-menu eligibility; sensor commits are serialized on the server. */
params ["_medic","_patient","_kind","_action",["_apply",false],["_device",objNull]];
if (isNull _medic || {isNull _patient} || {!alive _medic} || {!alive _patient}
    || {!(_medic isKindOf "CAManBase")} || {!(_patient isKindOf "CAManBase")}
    || {_medic distance _patient > 4} || {!isNull objectParent _patient}
    || {!isNull objectParent _medic} || {_medic getVariable ["ACE_isUnconscious",false]}
    || {_medic getVariable ["ACME_persistenceFrozen",false]} || {_patient getVariable ["ACME_persistenceFrozen",false]}
    || {!(_kind in ["pro","ls"])}) exitWith {false};
if (_apply && {!isRemoteExecuted} && {!local _medic}) exitWith {false};
if (isRemoteExecuted && {!_apply}) exitWith {false};
if (_apply && {isRemoteExecuted && {!isServer || {remoteExecutedOwner != owner _medic}}}) exitWith {false};
private _ls = _kind == "ls";
private _prefix = ["acme_tempus","acme_tempusls"] select _ls;
private _class = ["ACME_TempusPro","ACME_TempusLS"] select _ls;
private _setup = _action isEqualTo "setup";
private _sensor = _action isEqualType [] && {count _action == 2}
    && {(_action select 0) in ([[0,1,2,3,4],[0,5]] select _ls)}
    && {(_action select 1) isEqualType false};
private _connect = _sensor && {_action select 1};
private _slot = _patient getVariable ["ACME_eq_"+_kind,objNull];
private _usable = {
    params ["_candidate"];
    !isNull _candidate && {_candidate isKindOf _class} && {_candidate distance _medic <= 3.5}
        && {_candidate distance _patient <= 6} && {!(_candidate getVariable ["ACME_eq_busy",false])}
        && {!(_candidate getVariable ["ACME_eq_restoreStaged",false])} && {!isObjectHidden _candidate}
        && {isNull (attachedTo _candidate) || {_candidate getVariable ["ACME_eq_mounted",false]}}
};
if (isNull _device) then {_device = _slot;};
if ((_setup || {_connect}) && {isNull _slot} && {isNull _device}) then {
    private _candidates = nearestObjects [_patient,[_class],6];
    private _unbound = _candidates findIf {
        [_x] call _usable && {isNull (_x getVariable [_prefix+"_pat",objNull])}
    };
    if (_unbound >= 0) then {_device = _candidates select _unbound;};
};
if (isNull _device) exitWith {
    private _available = (_setup || {_connect}) && {isNull _slot}
        && {([_medic,_class+"_Item"] call ACME_fnc_itemCount)>0};
    if (_available && {_apply} && {!isRemoteExecuted}) then {
        private _firstSensor = if (_connect) then {_action select 0} else {-1};
        [_medic,_patient,_kind,"setup",false,[],objNull,"",_firstSensor] remoteExecCall ["ACME_fnc_equipmentRequest",2];
    };
    _available
};
if !([_device] call _usable) exitWith {false};
if (!isNull _slot && {_slot isNotEqualTo _device}) exitWith {false};
private _bound = _device getVariable [_prefix+"_pat",objNull];
if (isNull _bound) exitWith {
    if !(_setup || {_connect}) exitWith {false};
    if (_apply) then {
        if (!isServer) then {
            [_medic,_patient,_kind,_action,true,_device] remoteExecCall ["ACME_fnc_equipmentMonitorAction",2];
        } else {
            private _pending = missionNamespace getVariable ["ACME_eqPending",createHashMap];
            if (values _pending findIf {(_x get "patient") isEqualTo _patient && {(_x get "kind") == _kind}} >= 0) exitWith {};
            private _firstSensor = if (_connect) then {_action select 0} else {-1};
            [_device,_patient,_kind,_firstSensor] call ACME_fnc_equipmentBindMonitor;
        };
    };
    true
};
if (_bound isNotEqualTo _patient || {_setup}) exitWith {false};
if (_action isEqualTo "disconnect") exitWith {
    if (_apply) then {
        if (!isServer) then {
            [_medic,_patient,_kind,_action,true,_device] remoteExecCall ["ACME_fnc_equipmentMonitorAction",2];
        } else {
            [_device] call ACME_fnc_equipmentUsbRelease;
            if (_ls) then {
                [_device,_patient,false] remoteExecCall ["ACME_fnc_tempusLsPace",_patient];
                [_device] call ACME_fnc_tempusLsChargeClear;
                _device setVariable ["acme_tempusls_pace",[false,70,0,false],true];
                _device setVariable ["acme_tempusls_link",objNull,true];
                _device setVariable ["acme_tempusls_pads",false,true];
                _device setVariable ["acme_tempusls_ecg",false,true];
            } else {
                _device setVariable ["acme_tempus_sensors",[false,false,false,false,false],true];
            };
            _device setVariable [_prefix+"_pat",objNull,true];
            _device setVariable [_prefix+"_v",[],true];
            _device setVariable ["ACME_eq_feedOwner",[],true];
            _device setVariable ["ACME_eq_patient",objNull,true];
            _patient setVariable ["ACME_eq_"+_kind,objNull,true];
        };
    };
    true
};
if (_action in ["pair","usb","unplug"]) exitWith {
    if (!_ls) exitWith {false};
    private _pro = _patient getVariable ["ACME_eq_pro",objNull];
    private _usb = _device getVariable ["ACME_eq_usb",objNull];
    private _paired = _device getVariable ["acme_tempusls_link",objNull];
    private _proReady = !isNull _pro && {_pro distance _medic <= 3} && {_device distance _pro <= 2.3}
        && {!(_pro getVariable ["ACME_eq_busy",false])} && {!isObjectHidden _pro}
        && {(_pro getVariable ["acme_tempus_pat",objNull]) isEqualTo _patient};
    private _allowed = switch (_action) do {
        case "pair": {_proReady && {_paired isNotEqualTo _pro} &&
            {(_device getVariable ["acme_tempusls_pw",[false]]) select 0} &&
            {(_pro getVariable ["acme_tempus_pw",[false]]) select 0}};
        case "usb": {_proReady && {isNull _usb} && {isNull (_pro getVariable ["ACME_eq_usbLs",objNull])} && {_device distance _medic <= 3}};
        default {!isNull _usb && {_device distance _medic <= 3}};
    };
    if (_allowed && {_apply}) then {
        if (_action == "pair") then {
            if (isServer) then {_device setVariable ["acme_tempusls_link",_pro,true];} else {
                [_medic,_patient,_kind,_action,true,_device] remoteExecCall ["ACME_fnc_equipmentMonitorAction",2];
            };
        } else {
            [_medic,_device,_pro,_action == "usb",_device getVariable ["ACME_eq_usbEpoch",0]]
                remoteExecCall ["ACME_fnc_equipmentLinkRequest",2];
        };
    };
    _allowed
};
if (_action isEqualTo "view") exitWith {
    if (_apply && {!isRemoteExecuted}) then {
        private _use = [ACME_fnc_tempusUse,ACME_fnc_tempusLsUse] select _ls;
        [_use,[_device],0.1] call CBA_fnc_waitAndExecute;
    };
    true
};
if (_action isEqualTo "nibp") exitWith {
    private _allowed = !_ls && {(_device getVariable ["acme_tempus_sensors",[true,false,false,false,false]]) select 2}
        && {(_device getVariable ["acme_tempus_pw",[false]]) select 0};
    if (_allowed && {_apply}) then {
        if (isServer) then {_device setVariable ["ACME_eq_nibpRequest",CBA_missionTime,true];} else {
            [_medic,_patient,_kind,_action,true,_device] remoteExecCall ["ACME_fnc_equipmentMonitorAction",2];
        };
    };
    _allowed
};
if (!_sensor) exitWith {false};
_action params ["_index","_attach"];
private _sensors = +(_device getVariable ["acme_tempus_sensors",[true,false,false,false,false]]);
private _key = if (_index == 5) then {"acme_tempusls_pads"} else {"acme_tempusls_ecg"};
private _attached = if (_ls) then {_device getVariable [_key,_index==5]} else {_sensors select _index};
if (_attached == _attach) exitWith {false};
if (_apply) then {
    if (!isServer) then {
        [_medic,_patient,_kind,_action,true,_device] remoteExecCall ["ACME_fnc_equipmentMonitorAction",2];
    } else {
        if (_ls) then {
            _device setVariable [_key,_attach,true];
            if (_index == 5 && {!_attach}) then {
                [_device,_patient,false] remoteExecCall ["ACME_fnc_tempusLsPace",_patient];
                [_device] call ACME_fnc_tempusLsChargeClear;
                _device setVariable ["acme_tempusls_pace",[false,70,0,false],true];
            };
        } else {
            _sensors set [_index,_attach];
            _device setVariable ["acme_tempus_sensors",_sensors,true];
        };
    };
};
true
