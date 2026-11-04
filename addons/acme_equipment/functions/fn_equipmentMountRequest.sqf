params ["_actor","_mount","_device",["_on",true],["_expectedEpoch",-1]];
if (canSuspend) exitWith {isNil {[_actor,_mount,_device,_on,_expectedEpoch] call ACME_fnc_equipmentMountRequest;};};
if !(_actor isEqualType objNull && {_mount isEqualType objNull} && {_device isEqualType objNull}) exitWith {};
if (!isServer || {isNull _actor} || {isNull _mount} || {isNull _device} || {!(_on isEqualType false)}) exitWith {};
if (isRemoteExecuted && {remoteExecutedOwner != owner _actor}) exitWith {};
if !(_actor isKindOf "CAManBase") exitWith {};
if !(_expectedEpoch isEqualType 0) exitWith {};
if (_expectedEpoch<0 && {!isRemoteExecuted}) then {_expectedEpoch=if (_on) then {_mount getVariable ["ACME_eq_mountEpoch",0]} else {_device getVariable ["ACME_eq_mountEpoch",0]};};
if (!finite _expectedEpoch || {_expectedEpoch<0} || {_expectedEpoch!=floor _expectedEpoch}
    || {_expectedEpoch!=(_mount getVariable ["ACME_eq_mountEpoch",0])}
    || {!_on && {_expectedEpoch!=(_device getVariable ["ACME_eq_mountEpoch",0])}}) exitWith {};
if (!alive _actor || {_actor getVariable ["ACE_isUnconscious",false]} || {!isNull objectParent _actor}
    || {_actor distance _mount > 3} || {_actor distance _device > 3}
    || {_actor getVariable ["ACME_persistenceFrozen",false]} || {_device getVariable ["ACME_eq_busy",false]}
    || {(_actor getVariable ["ACME_equipmentWorldPending",""]) != ""}) exitWith {};
private _kind=getText(configOf _mount >> "ACME_eq_mountKind");
if (!(_kind in ["pro","ls"]) || {(_device getVariable ["ACME_eq_kind",""]) != _kind}) exitWith {};
if !(_device isKindOf (["ACME_TempusPro","ACME_TempusLS"] select (_kind=="ls"))) exitWith {};
private _prefix=["acme_tempus","acme_tempusls"] select (_kind=="ls");
private _patient=_device getVariable [_prefix+"_pat",objNull];
if (!isNull _patient && {_patient getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
if (_on) then {
    if (_device distance _mount <= 2.5) then {[_device,_mount,_kind] call ACME_fnc_equipmentMountApply;};
} else {
    if ((_mount getVariable ["ACME_eq_device",objNull]) isEqualTo _device
        && {(_device getVariable ["ACME_eq_mount",objNull]) isEqualTo _mount}) then {[_device] call ACME_fnc_equipmentMountRelease;};
};
