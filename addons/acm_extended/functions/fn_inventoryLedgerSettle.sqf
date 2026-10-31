/* Terminal receipts alone release escrow; no timeout manufactures a fresh kit refund. */
params ["_owner","_request","_consume",["_payload",[]]];
if (isNull _owner || {!local _owner}) exitWith {false};
private _held = (_owner getVariable ["ACME_inventoryEscrow",createHashMap]) getOrDefault [_request,[]];
if (_held isEqualTo []) exitWith {false};
if (_payload isEqualTo []) then {_payload = +(_held select 1);};
private _brokerArgs = [["return","consume"] select _consume,_owner,_held select 2,(_held select 1) select 0,_payload,_request];
private _requests = _owner getVariable ["ACME_inventoryRequests",createHashMap];
_requests set [_request,[_brokerArgs,CBA_missionTime+1,0]];
_owner setVariable ["ACME_inventoryRequests",_requests,true];
["ACME_inventoryBroker",_brokerArgs] call CBA_fnc_serverEvent;
true
