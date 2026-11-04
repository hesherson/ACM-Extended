params ["_actor","_id","_phase","_ok"];
if (canSuspend) exitWith {isNil {[_actor,_id,_phase,_ok] call ACME_fnc_equipmentAck;};};
if (!isServer || {isNull _actor}) exitWith {};
if (isRemoteExecuted && {remoteExecutedOwner!=owner _actor}) exitWith {};
private _pending=missionNamespace getVariable ["ACME_eqPending",createHashMap];
private _r=_pending getOrDefault [_id,createHashMap];
if (count _r==0 || {(_r get "actor") isNotEqualTo _actor} || {_phase!=(_r get "phase")}) exitWith {};
if (_ok && {!((_actor getVariable ["ACME_eqReceipts",createHashMap]) getOrDefault [_id+":"+_phase,false])}) exitWith {};
if (!_ok) exitWith {
    if (_phase=="take") then {_pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];};
};
private _patient=_r get "patient";private _kind=_r get "kind";
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
            {_actor setVariable [_x select 0,_x select 1,true];} forEach (_r getOrDefault ["state",[]]);
            _device setVariable [_prefix+"_pat",objNull,true];
            _actor setVariable [_prefix+"_pat",_patient,true];
            if (_kind=="ls") then {
                [_device] call ACME_fnc_tempusLsChargeClear;[_actor] call ACME_fnc_tempusLsChargeClear;
                _actor setVariable ["acme_tempusls_operator",_actor,true];
                _actor setVariable ["acme_tempusls_pace",[false,70,0,false],true];
                _actor setVariable ["acme_tempusls_st","",true];
            };
            if (!isNull _patient) then {[_actor,_patient] remoteExecCall [["ACME_fnc_tempusFeed","ACME_fnc_tempusLsFeed"] select (_kind=="ls"),_patient];};
        };
        if (!isNull _patient && {(_patient getVariable ["ACME_eq_"+_kind,objNull]) isEqualTo _device}) then {_patient setVariable ["ACME_eq_"+_kind,objNull,true];};
        deleteVehicle _device;
    };
    _pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];
};
if (_phase=="refund") exitWith {_pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];};
if (_kind=="blood") exitWith {
    private _box=_r get "device";
    private _state=if (isNull _box) then {[]} else {[_box,serverTime] call ACME_fnc_coolerBoxReconcile};
    private _used=0;if (_state isNotEqualTo []) then {{_used=_used+([_x select 0] call ACME_fnc_coolerBagVolume);} forEach (_state select 2);};
    private _capacity=if (_state isEqualTo []) then {0} else {getNumber(configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl")};
    if (_state isEqualTo [] || {_used+([_r get "item"] call ACME_fnc_coolerBagVolume)>_capacity} || {_actor distance _box>4.5} || {_box getVariable ["ACME_coolerPacking",false]}) exitWith {
        _r set ["phase","refund"];_r set ["sent",serverTime];
        [_actor,_id,"refund",_r get "item",(_r get "warm")+((serverTime-(_r get "sample")) max 0)] remoteExecCall ["ACME_fnc_equipmentInventory",_actor];
    };
    private _bag=_r get "item";private _before={_x==_bag} count itemCargo _box;
    _box addItemCargoGlobal [_bag,1];
    if (({_x==_bag} count itemCargo _box)!=_before+1) exitWith {_r set ["phase","refund"];};
    private _entries=+(_state select 2);
    _entries pushBack [_bag,(_r get "warm")+((serverTime-(_r get "sample")) max 0)];
    _state set [2,_entries];_box setVariable ["ACME_boxCoolerState",_state,true];
    _pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];
};
private _manual=_r get "manual";
private _invalid=!alive _actor || {_actor getVariable ["ACE_isUnconscious",false]} || {!isNull objectParent _actor}
    || {if (_manual) then {_actor distance (ASLToAGL (_r get "spot"))>3.5} else {
        isNull _patient || {_actor distance _patient>4.5} || {!isNull objectParent _patient}
            || {!isNull (_patient getVariable ["ACME_eq_"+_kind,objNull])}
    }};
private _o=objNull;
if (!_invalid) then {
    private _pose=if (_manual) then {[_r get "spot",vectorDir _actor vectorMultiply -1]} else {[_patient,_kind] call ACME_fnc_equipmentPose};
    if (_pose isNotEqualTo []) then {_o=createVehicle [_r get "class",ASLToAGL (_pose select 0),[],0,"CAN_COLLIDE"];};
    if (!isNull _o) then {[_o,_pose] call ACME_fnc_equipmentSeat;};
};
if (isNull _o) exitWith {
    _r set ["phase","refund"];_r set ["sent",serverTime];
    [_actor,_id,"refund",_r get "item"] remoteExecCall ["ACME_fnc_equipmentInventory",_actor];
};
{_o setVariable [_x select 0,_x select 1,true];} forEach (_r getOrDefault ["state",[]]);
if (_kind in ["pro","ls"]) then {
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
    private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
    _o setVariable [_prefix+"_pat",_patient,true];
    if (_kind=="pro") then {
        if (!_manual || {isNil {_o getVariable "acme_tempus_sensors"}}) then {_o setVariable ["acme_tempus_sensors",[true,false,false,false,false],true];};
        [_o,_patient] remoteExecCall ["ACME_fnc_tempusFeed",_patient];
    } else {
        if (!_manual || {isNil {_o getVariable "acme_tempusls_pads"}}) then {_o setVariable ["acme_tempusls_pads",true,true];};
        if (!_manual || {isNil {_o getVariable "acme_tempusls_ecg"}}) then {_o setVariable ["acme_tempusls_ecg",false,true];};
        [_o,_patient] remoteExecCall ["ACME_fnc_tempusLsFeed",_patient];
    };
};
private _devices=missionNamespace getVariable ["ACME_eqDevices",[]];_devices pushBackUnique _o;missionNamespace setVariable ["ACME_eqDevices",_devices];
_pending deleteAt _id;_actor setVariable ["ACME_equipmentWorldPending","",true];
