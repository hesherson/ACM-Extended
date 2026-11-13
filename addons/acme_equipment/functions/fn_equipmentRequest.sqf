params ["_actor","_patient","_kind",["_operation","setup"],["_manual",false],["_spot",[]],["_device",objNull],["_bag",""],["_firstSensor",-1],["_provider",objNull]];
if (canSuspend) exitWith {isNil {[_actor,_patient,_kind,_operation,_manual,_spot,_device,_bag,_firstSensor,_provider] call ACME_fnc_equipmentRequest;};};
if !(_actor isEqualType objNull && {_patient isEqualType objNull} && {_provider isEqualType objNull}
    && {_device isEqualType objNull} && {_kind isEqualType ""} && {_operation isEqualType ""}
    && {_manual isEqualType false} && {_spot isEqualType []} && {_firstSensor isEqualType 0}) exitWith {};
if (!isServer || {isNull _actor} || {!alive _actor}) exitWith {};
if (isNull _provider) then {_provider = _actor;};
if (!alive _provider || {isRemoteExecuted && {remoteExecutedOwner != owner _provider}}) exitWith {};
if (_provider isNotEqualTo _actor && {!(_kind == "accu" && {_operation == "setup"} && {!_manual}
    && {!isNull _patient} && {_actor in ([_provider,_patient] call ACME_fnc_treatmentSupplyOrder)})}) exitWith {};
if (_provider getVariable ["ACE_isUnconscious",false] || {_provider getVariable ["ACME_persistenceFrozen",false]}
    || {_actor getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
if (!isNull _patient && {_patient getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
private _devicePatient=if (isNull _device) then {objNull} else {_device getVariable ["ACME_eq_patient",objNull]};
if (!isNull _devicePatient && {_devicePatient getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
private _types=createHashMapFromArray [["pro",["ACME_TempusPro_Item","ACME_TempusPro"]],["ls",["ACME_TempusLS_Item","ACME_TempusLS"]],["accu",["ACM_ACCUVAC","ACME_AccuvacRescue"]]];
if !(_kind in _types) exitWith {};
private _sensorIndices = switch (_kind) do {
    case "pro": {[-1,0,1,2,3,4]};
    case "ls": {[-1,0,5]};
    default {[-1]};
};
if !(_firstSensor in _sensorIndices) exitWith {};
if (_firstSensor >= 0 && {_manual || {_operation != "setup"}}) exitWith {};
private _pending=missionNamespace getVariable ["ACME_eqPending",createHashMap];
if ((values _pending findIf {(_x get "actor") isEqualTo _actor
    || {(_x getOrDefault ["provider",objNull]) isEqualTo _provider}})>=0) exitWith {};
private _item=(_types get _kind) select 0;
if (_operation=="setup") then {
    if (!isNull objectParent _provider) then {_item="";};
    if (_manual) then {
        if (count _spot!=3 || {_actor distance (ASLToAGL _spot)>3.5}) exitWith {_item="";};
    } else {
        if (isNull _patient || {_provider distance _patient>4} || {!isNull objectParent _patient}) exitWith {_item="";};
        private _key="ACME_eq_"+_kind;
        private _existing=_patient getVariable [_key,objNull];
        if (isNull _existing && {_kind in ["pro","ls"]}) then {
            private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
            private _found=(nearestObjects [_patient,[(_types get _kind) select 1],8]) select {(_x getVariable [_prefix+"_pat",objNull]) isEqualTo _patient};
            _existing=_found param [0,objNull];
        };
        if (!isNull _existing || {(values _pending findIf {(_x get "patient") isEqualTo _patient && {(_x get "kind")==_kind}})>=0}) exitWith {_item="";};
    };
} else {
    if (_operation!="pickup" || {isNull _device} || {_actor distance _device>4}
        || {!(_device isKindOf ((_types get _kind) select 1))}
        || {_device getVariable ["ACME_eq_busy",false]}) exitWith {_item="";};
    if !([_device] call ACME_fnc_equipmentPickupReady) exitWith {_item="";};
};
if (_item=="") exitWith {};
private _stamp=[_actor] call ACME_fnc_equipmentTransferStamp;
if (_stamp isEqualTo []) exitWith {};
private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
private _state=[];
if (_kind in ["pro","ls"]) then {
    private _source=if (_operation=="pickup") then {_device} else {_actor};
    if (_manual || {_operation=="pickup"}) then {_patient=_source getVariable [_prefix+"_pat",objNull];};
    {if (!isNil {_source getVariable (_prefix+_x)}) then {_state pushBack [_prefix+_x,_source getVariable (_prefix+_x)];};} forEach ["_pw","_st","_v","_nibp","_sensors","_link","_metro","_pads","_ecg"];
};
private _serial=(missionNamespace getVariable ["ACME_eqSerial",0])+1;
if (!isNull _patient && {_patient getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
missionNamespace setVariable ["ACME_eqSerial",_serial];
private _id=format ["equipment:%1:%2:%3",clientOwner,_serial,random 1e9];
private _record=createHashMapFromArray [["actor",_actor],["provider",_provider],["patient",_patient],["kind",_kind],["operation",_operation],["manual",_manual],["spot",_spot],["device",_device],["item",_item],["class",(_types get _kind) select 1],["sent",serverTime],["firstSensor",_firstSensor],["state",_state],["stamp",_stamp],["phase",["take","give"] select (_operation=="pickup")]];
_actor setVariable ["ACME_eqAdmission",[_id,_stamp],true];
_actor setVariable ["ACME_equipmentWorldPending",_id,true];
_pending set [_id,_record];missionNamespace setVariable ["ACME_eqPending",_pending];
if (_operation=="pickup") then {_device setVariable ["ACME_eq_busy",true,true];if (_kind=="ls") then {[_device] call ACME_fnc_tempusLsChargeClear;};};
if (_operation=="pickup" && {_device getVariable ["ACME_eq_mounted",false]}) then {[_device] call ACME_fnc_equipmentMountRelease;};
if (_operation=="pickup") then {[_device] call ACME_fnc_equipmentUsbRelease;};
[_actor,_id,_record get "phase",_item] remoteExecCall ["ACME_fnc_equipmentInventory",_actor];
