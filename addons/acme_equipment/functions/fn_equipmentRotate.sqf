/* The server authenticates the operator before forwarding to the device's current owner. */
params ["_actor","_device",["_ownerPass",false,[false]]];
if (_ownerPass && {!isRemoteExecuted || {remoteExecutedOwner != 2}}) exitWith {};
if (!_ownerPass && {!isServer || {isNull _actor} || {isRemoteExecuted && {remoteExecutedOwner != owner _actor}}}) exitWith {};
if !([_actor,_device] call ACME_fnc_equipmentRotateReady) exitWith {};
if (!local _device) exitWith {
    if (!_ownerPass) then {[_actor,_device,true] remoteExecCall ["ACME_fnc_equipmentRotate",_device];};
};
private _position = getPosWorld _device;
_device setVectorDirAndUp [[_device,_position,_actor,vectorDir _device] call ACME_fnc_equipmentFacing,[0,0,1]];
_device setPosWorld _position;
