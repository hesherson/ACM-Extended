/* Keep the existing device at its current ASL pose. No grants and no recreation. */
params ["_device"];
if (canSuspend) exitWith {private _result=false;isNil {_result=[_device] call ACME_fnc_equipmentMountRelease;};_result};
if (!isServer || {isNull _device}) exitWith {false};
private _mount=_device getVariable ["ACME_eq_mount",objNull];
private _wasMounted=_device getVariable ["ACME_eq_mounted",false];
if (!_wasMounted && {isNull _mount}) exitWith {true};
private _pos=getPosASL _device;private _dir=vectorDir _device;private _up=vectorUp _device;
private _parent=attachedTo _device;
// An external carry/attachment may have taken over. Retire our mount claim
// without detaching another system's object or changing its simulation.
if (isNull _parent || {_parent isEqualTo _mount}) then {
    detach _device;
    _device setVectorDirAndUp [_dir,_up];_device setPosASL _pos;
    _device enableSimulationGlobal (_device getVariable ["ACME_eq_simBeforeMount",true]);
};
if (!isNull _mount && {(_mount getVariable ["ACME_eq_device",objNull]) isEqualTo _device}) then {_mount setVariable ["ACME_eq_device",objNull,true];};
_device setVariable ["ACME_eq_mount",objNull,true];_device setVariable ["ACME_eq_mounted",false,true];
_device setVariable ["ACME_eq_mountEpoch",0,true];
true
