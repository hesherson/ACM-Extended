params ["_actor","_patient","_kind",["_operation","setup"],["_manual",false],["_spot",[]],["_device",objNull],["_bag",""]];
if (!isServer || {isNull _actor} || {!alive _actor}) exitWith {};
if (isRemoteExecuted && {remoteExecutedOwner!=owner _actor}) exitWith {};
if (_actor getVariable ["ACE_isUnconscious",false] || {_actor getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
if (!isNull _patient && {_patient getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
if (!isNull _device && {(_device getVariable ["ACME_eq_patient",objNull]) getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
private _types=createHashMapFromArray [["pro",["ACME_TempusPro_Item","ACME_TempusPro"]],["ls",["ACME_TempusLS_Item","ACME_TempusLS"]],["accu",["ACM_ACCUVAC","ACME_AccuvacRescue"]]];
if !(_kind in _types) exitWith {};
private _pending=missionNamespace getVariable ["ACME_eqPending",createHashMap];
if ((values _pending findIf {(_x get "actor") isEqualTo _actor})>=0) exitWith {};
private _item=(_types get _kind) select 0;
if (_operation=="setup") then {
    if (!isNull objectParent _actor) then {_item="";};
    if (_manual) then {
        if (count _spot!=3 || {_actor distance (ASLToAGL _spot)>3.5}) exitWith {_item="";};
    } else {
        if (isNull _patient || {_actor distance _patient>4} || {!isNull objectParent _patient}) exitWith {_item="";};
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
    if (_device getVariable ["ACME_eq_restoreStaged",false]) exitWith {_item="";};
    if (!(_device getVariable ["ACME_eq_mounted",false]) && {!isNull attachedTo _device}) exitWith {_item="";};
};
if (_item=="") exitWith {};
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
private _record=createHashMapFromArray [["actor",_actor],["patient",_patient],["kind",_kind],["operation",_operation],["manual",_manual],["spot",_spot],["device",_device],["item",_item],["class",(_types get _kind) select 1],["sent",serverTime],["state",_state],["phase",["take","give"] select (_operation=="pickup")]];
_actor setVariable ["ACME_equipmentWorldPending",_id,true];
_pending set [_id,_record];missionNamespace setVariable ["ACME_eqPending",_pending];
if (_operation=="pickup") then {_device setVariable ["ACME_eq_busy",true,true];if (_kind=="ls") then {[_device] call ACME_fnc_tempusLsChargeClear;};};
if (_operation=="pickup" && {_device getVariable ["ACME_eq_mounted",false]}) then {[_device] call ACME_fnc_equipmentMountRelease;};
[_actor,_id,_record get "phase",_item] remoteExecCall ["ACME_fnc_equipmentInventory",_actor];
