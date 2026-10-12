/* Continuation receives [accepted, args]. Never dispatch patient work before the server certificate. */
params ["_owner","_request","_code",["_args",[]]];
if (isNull _owner || {!local _owner}) exitWith {false};
private _held = (_owner getVariable ["ACME_inventoryEscrow",createHashMap]) getOrDefault [_request,[]];
if (_held isEqualTo []) exitWith {[false,_args] call _code;false};
private _callbacks = missionNamespace getVariable ["ACME_inventoryCallbacks",createHashMap];
_callbacks set [_request,[_owner,_code,_args]];
missionNamespace setVariable ["ACME_inventoryCallbacks",_callbacks];
private _brokerArgs = ["claim",_owner,_held select 2,(_held select 1) select 0,_held select 1,_request];
private _requests = _owner getVariable ["ACME_inventoryRequests",createHashMap];
_requests set [_request,[_brokerArgs,CBA_missionTime+1,0]];
_owner setVariable ["ACME_inventoryRequests",_requests,true];
["ACME_inventoryBroker",_brokerArgs] call CBA_fnc_serverEvent;
true
