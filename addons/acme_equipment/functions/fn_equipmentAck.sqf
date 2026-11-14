params ["_actor","_id","_phase","_ok",["_retired",false],["_contextCurrent",true],["_refundLease",[]]];
if (canSuspend) exitWith {isNil {[_actor,_id,_phase,_ok,_retired,_contextCurrent,_refundLease] call ACME_fnc_equipmentAck;};};
if !(_ok isEqualType false && {_retired isEqualType false} && {_contextCurrent isEqualType false}) exitWith {};
if (!isServer || {isNull _actor}) exitWith {};
private _pending=missionNamespace getVariable ["ACME_eqPending",createHashMap];
private _r=_pending getOrDefault [_id,createHashMap];
if (count _r==0 || {(_r get "actor") isNotEqualTo _actor} || {_phase!=(_r get "phase")}) exitWith {};
if (_phase=="refund") exitWith {
    private _lease=_r getOrDefault ["refundLease",[]];
    if (!(_r getOrDefault ["debited",false]) || {count _lease!=2} || {_refundLease isNotEqualTo _lease}
        || {_r getOrDefault ["refundClosed",false]} || {_ok && {_retired}}) exitWith {};
    if (isRemoteExecuted && {remoteExecutedOwner!=owner _actor} && {remoteExecutedOwner!=(_lease select 1)}) exitWith {};
    private _key=_id+":refund:"+str (_lease select 0);
    private _proof=(_actor getVariable ["ACME_eqReceipts",createHashMap]) getOrDefault [_key,[]];
    if (_proof isNotEqualTo [_ok,_retired]) exitWith {};
    if (_ok) then {
        _pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];
        _actor setVariable ["ACME_eqRefundLease",[],true];
    } else {
        if (_retired) then {
            _r set ["refundClosed",true];
            [_actor,_id] call ACME_fnc_equipmentRefundRequest;
        };
    };
};
private _stamp=_r getOrDefault ["stamp",[]];
private _origin=if (count _stamp==2) then {(_stamp select 1) select 0} else {-1};
if (isRemoteExecuted && {remoteExecutedOwner!=owner _actor} && {remoteExecutedOwner!=_origin}) exitWith {};
private _receipts=_actor getVariable ["ACME_eqReceipts",createHashMap];
if !((_id+":"+_phase) in _receipts) exitWith {};
private _proved=_receipts get (_id+":"+_phase);
if (_ok isNotEqualTo _proved) exitWith {};
if (!_ok) exitWith {
    if (_retired && {_contextCurrent}) exitWith {};
    if (_phase=="take" || {_phase=="give" && {_retired}}) then {
        private _device=_r getOrDefault ["device",objNull];
        if (_phase=="give" && {!isNull _device}) then {_device setVariable ["ACME_eq_busy",false,true];};
        _pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];
    };
};
private _patient=_r get "patient";private _kind=_r get "kind";
// The owner's context result also fences a late public epoch update at the server.
private _current=_contextCurrent && {(_r getOrDefault ["stamp",[]]) isEqualTo ([_actor] call ACME_fnc_equipmentTransferStamp)};
if (_phase=="give") exitWith {
    private _device=_r get "device";
    // An external system can acquire the object while the owner-side credit is in flight.
    // Keep the device reserved and retry the same receipt after release; never credit twice or delete its carrier's object.
    if (!isNull _device && {!([_device] call ACME_fnc_equipmentPickupReady)}) exitWith {};
    if (!isNull _device) then {
        if (_device getVariable ["ACME_eq_mounted",false]) then {[_device] call ACME_fnc_equipmentMountRelease;};
        [_device] call ACME_fnc_equipmentUsbRelease;
        if (_kind in ["pro","ls"]) then {
            private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
            _device setVariable [_prefix+"_pat",objNull,true];
            if (_current) then {
                {_actor setVariable [_x select 0,_x select 1,true];} forEach (_r getOrDefault ["state",[]]);
                _actor setVariable [_prefix+"_pat",_patient,true];
            };
            if (_kind=="ls") then {
                [_device] call ACME_fnc_tempusLsChargeClear;
                if (_current) then {
                    [_actor] call ACME_fnc_tempusLsChargeClear;
                    _actor setVariable ["acme_tempusls_operator",_actor,true];
                    _actor setVariable ["acme_tempusls_pace",[false,70,0,false],true];
                    _actor setVariable ["acme_tempusls_st","",true];
                };
            };
            if (_current && {!isNull _patient}) then {[_actor,_patient] remoteExecCall [["ACME_fnc_tempusFeed","ACME_fnc_tempusLsFeed"] select (_kind=="ls"),_patient];};
        };
        if (!isNull _patient && {(_patient getVariable ["ACME_eq_"+_kind,objNull]) isEqualTo _device}) then {_patient setVariable ["ACME_eq_"+_kind,objNull,true];};
        deleteVehicle _device;
    };
    _pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];
};
if (_phase=="take") then {_r set ["debited",true];};
if (_kind=="blood") exitWith {
    private _box=_r get "device";
    private _state=if (isNull _box) then {[]} else {[_box,([] call ACME_fnc_clinicalClock)] call ACME_fnc_coolerBoxReconcile};
    private _used=0;if (_state isNotEqualTo []) then {{_used=_used+([_x select 0] call ACME_fnc_coolerBagVolume);} forEach (_state select 2);};
    private _capacity=if (_state isEqualTo []) then {0} else {getNumber(configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl")};
    if (_state isEqualTo [] || {_used+([_r get "item"] call ACME_fnc_coolerBagVolume)>_capacity} || {_actor distance _box>4.5} || {_box getVariable ["ACME_coolerPacking",false]}) exitWith {
        _r set ["phase","refund"];_r set ["sent",serverTime];
        [_actor,_id] call ACME_fnc_equipmentRefundRequest;
    };
    private _bag = _r get "item";
    private _warm = (_r get "warm") + ((([] call ACME_fnc_clinicalClock)-(_r get "sample")) max 0);
    if ((["spoil"] call ACME_fnc_bloodTiming) && {_warm >= ([_bag] call ACME_fnc_bloodWarmLimit)}) exitWith {
        _r set ["phase","refund"];_r set ["sent",serverTime];
        [_actor,_id] call ACME_fnc_equipmentRefundRequest;
    };
    private _before = {_x == _bag} count itemCargo _box;
    _box addItemCargoGlobal [_bag,1];
    if (({_x==_bag} count itemCargo _box)!=_before+1) exitWith {
        _r set ["phase","refund"];_r set ["sent",serverTime];[_actor,_id] call ACME_fnc_equipmentRefundRequest;
    };
    private _entries=+(_state select 2);
    _entries pushBack [_bag,_warm];
    _state set [2,_entries];_box setVariable ["ACME_boxCoolerState",_state,true];
    _pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];
};
private _manual=_r get "manual";
private _provider = _r getOrDefault ["provider",_actor];
private _invalid = !alive _provider || {_provider getVariable ["ACE_isUnconscious",false]} || {!isNull objectParent _provider}
    || {_provider getVariable ["ACME_persistenceFrozen",false]}
    || {if (_manual) then {_actor distance (ASLToAGL (_r get "spot"))>3.5} else {
        isNull _patient || {_provider distance _patient>4.5} || {!isNull objectParent _patient}
            || {_patient getVariable ["ACME_persistenceFrozen",false]}
            || {!isNull (_patient getVariable ["ACME_eq_"+_kind,objNull])}
    }};
private _o=objNull;
if (!_invalid) then {
    private _pose=if (_manual) then {[_r get "spot",vectorDir _actor vectorMultiply -1]} else {[_patient,_kind] call ACME_fnc_equipmentPose};
    if (_pose isNotEqualTo []) then {_o=createVehicle [_r get "class",ASLToAGL (_pose select 0),[],0,"CAN_COLLIDE"];};
    if (!isNull _o) then {[_o,_pose,_provider] call ACME_fnc_equipmentSeat;};
};
if (isNull _o) exitWith {
    _r set ["phase","refund"];_r set ["sent",serverTime];
    [_actor,_id] call ACME_fnc_equipmentRefundRequest;
};
{_o setVariable [_x select 0,_x select 1,true];} forEach (_r getOrDefault ["state",[]]);
if (_kind in ["pro","ls"] && {_current}) then {
    private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
    _actor setVariable [_prefix+"_pat",objNull,true];
    {_actor setVariable [_x select 0,nil,true];} forEach (_r getOrDefault ["state",[]]);
    if (_kind=="ls") then {
        [_actor] call ACME_fnc_tempusLsChargeClear;
        _actor setVariable ["acme_tempusls_pace",[false,70,0,false],true];
    };
};
if (_kind=="ls") then {[_o] call ACME_fnc_tempusLsChargeClear;_o setVariable ["acme_tempusls_st","",true];};
_o setVariable ["ACME_eq_kind",_kind,true];_o setVariable ["ACME_eq_patient",_patient,true];_o setVariable ["ACME_eq_manual",_manual,true];
if (!isNull _patient) then {_patient setVariable ["ACME_eq_"+_kind,_o,true];};
if (_kind in ["pro","ls"] && {!isNull _patient}) then {
    if (_manual) then {
        private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
        _o setVariable [_prefix+"_pat",_patient,true];
        [_o,_patient] remoteExecCall [["ACME_fnc_tempusFeed","ACME_fnc_tempusLsFeed"] select (_kind=="ls"),_patient];
    } else {
        [_o,_patient,_kind,_r getOrDefault ["firstSensor",-1]] call ACME_fnc_equipmentBindMonitor;
    };
};
private _devices=missionNamespace getVariable ["ACME_eqDevices",[]];_devices pushBackUnique _o;missionNamespace setVariable ["ACME_eqDevices",_devices];
_pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];
