/* Trusted server helper. Device already exists and is funded; no inventory mutation. */
params ["_device","_mount","_kind"];
if (canSuspend) exitWith {private _result=false;isNil {_result=[_device,_mount,_kind] call ACME_fnc_equipmentMountApply;};_result};
if (!isServer || {isNull _device} || {isNull _mount} || {!(_kind in ["pro","ls"])}
    || {getText(configOf _mount >> "ACME_eq_mountKind") != _kind}
    || {!isNull (_mount getVariable ["ACME_eq_device",objNull])}
    || {!isNull attachedTo _device}) exitWith {false};
private _box=boundingBoxReal _device;
private _min=_box select 0;private _max=_box select 1;
private _offset=[-((_min select 0)+(_max select 0))/2,-((_min select 1)+(_max select 1))/2,0.023-(_min select 2)];
_device setVariable ["ACME_eq_simBeforeMount",simulationEnabled _device];
_device attachTo [_mount,_offset];
_device setVectorDirAndUp [[0,1,0],[0,0,1]];
if (attachedTo _device isNotEqualTo _mount) exitWith {false};
_device enableSimulationGlobal false;
private _epoch=(_mount getVariable ["ACME_eq_mountEpoch",0])+1;
_mount setVariable ["ACME_eq_mountEpoch",_epoch,true];_device setVariable ["ACME_eq_mountEpoch",_epoch,true];
_device setVariable ["ACME_eq_mount",_mount,true];
_device setVariable ["ACME_eq_mounted",true,true];
_mount setVariable ["ACME_eq_device",_device,true];
true
