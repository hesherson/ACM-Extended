/* Server adapter. [] is a failed capture; [1,[]] is a valid empty world.
 * Bind every device and referenced object to a mission-owned durable ID first.
 * The mission must quiesce external actions and save clinical/cargo state alongside this payload. */
if (canSuspend) exitWith {private _result = [];isNil {_result = call ACME_fnc_equipmentWorldSnapshot;};_result};
if (!isServer || {isRemoteExecuted} || {!(call ACME_fnc_persistenceJournalsReady)}) exitWith {[]};
if (count (missionNamespace getVariable ["ACME_eqPending",createHashMap]) > 0) exitWith {[]};
private _rows = []; private _ok = true;
private _reference = {
    params ["_o"];
    private _ref = ["encode",_o] call ACME_fnc_clinicalObjectRef;
    if (!isNull _o && {(_ref select 2) == ""}) then {_ok = false;};
    _ref
};
private _devices = (missionNamespace getVariable ["ACME_eqDevices",[]]) select {!isNull _x};
{
    private _o = _x;
    private _kind = _o getVariable ["ACME_eq_kind",""];
    if (!(_kind in ["pro","ls","accu","vent"]) || {_o getVariable ["ACME_eq_busy",false]} || {_o getVariable ["ACME_eq_restoreStaged",false]}) exitWith {_ok = false;};
    private _id = ([_o] call _reference) select 2;
    private _patient = _o getVariable ["ACME_eq_patient",objNull];
    private _prefix = ["acme_tempus","acme_tempusls"] select (_kind == "ls");
    if (_kind in ["pro","ls"]) then {_patient = _o getVariable [_prefix+"_pat",objNull];};
    private _link = if (_kind == "ls") then {_o getVariable ["acme_tempusls_link",objNull]} else {objNull};
    private _state = [false,[false,false,false,false,false],false,false];
    if (_kind in ["pro","ls"]) then {
        _state = [(_o getVariable [_prefix+"_pw",[false]]) select 0,
            +(_o getVariable ["acme_tempus_sensors",[true,false,false,false,false]]),
            _o getVariable ["acme_tempusls_pads",true],_o getVariable ["acme_tempusls_ecg",false]];
    };
    private _custody = [];
    if (_kind == "vent") then {
        private _r = (missionNamespace getVariable ["ACME_vent_custody",createHashMap]) getOrDefault [_patient getVariable ["ACME_vent_custodyId",""],createHashMap];
        if (count _r == 0 || {(_r getOrDefault ["phase",""]) != "attached"}
            || {!(_patient getVariable ["ACME_vent_onPatient",false])}) exitWith {_ok = false;};
        _custody = [[_r getOrDefault ["supplier",objNull]] call _reference,_r getOrDefault ["supplierUID",""],
            [(_r getOrDefault ["supplyOrigin",[]]) param [1,objNull]] call _reference,
            [_r getOrDefault ["recoveryOperator",objNull]] call _reference,_r getOrDefault ["recoveryOperatorUID",""]];
    };
    private _mount=_o getVariable ["ACME_eq_mount",objNull];
    if (isNull _mount && {!isNull attachedTo _o}) then {_ok=false;};
    if (_o getVariable ["ACME_eq_mounted",false] && {isNull _mount || {attachedTo _o isNotEqualTo _mount}}) then {_ok=false;};
    if (!isNull _mount && {!(_o getVariable ["ACME_eq_mounted",false]) || {(_mount getVariable ["ACME_eq_device",objNull]) isNotEqualTo _o}}) then {_ok=false;};
    private _usb=if (_kind=="ls") then {_o getVariable ["ACME_eq_usb",objNull]} else {objNull};
    if (!isNull _usb && {(_usb getVariable ["ACME_eq_usbLs",objNull]) isNotEqualTo _o || {_o distance _usb > 2.5}}) then {_ok=false;};
    _rows pushBack [_id,_kind,getPosASL _o,vectorDir _o,vectorUp _o,_o getVariable ["ACME_eq_manual",false],
        [_patient] call _reference,_state,[_link] call _reference,_custody,[_mount] call _reference,[_usb] call _reference];
} forEach _devices;
private _save = [2,_rows];
if (!_ok || {!([_save] call ACME_fnc_equipmentWorldSchema)}) exitWith {[]};
_save
