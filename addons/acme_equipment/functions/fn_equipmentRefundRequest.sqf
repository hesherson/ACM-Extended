/* Funded server refund. Only a sealed, unissued attempt may move to a new executor. */
params ["_actor","_id"];
if (canSuspend) exitWith {isNil {[_actor,_id] call ACME_fnc_equipmentRefundRequest;};};
if (!isServer || {isNull _actor}) exitWith {};
private _r=(missionNamespace getVariable ["ACME_eqPending",createHashMap]) getOrDefault [_id,createHashMap];
if (count _r==0 || {(_r get "actor") isNotEqualTo _actor} || {(_r get "phase")!="refund"}
    || {!(_r getOrDefault ["debited",false])} || {(_actor getVariable ["ACME_equipmentWorldPending",""])!=_id}) exitWith {};
private _lease=_r getOrDefault ["refundLease",[]];
if (_lease isEqualTo [] || {_r getOrDefault ["refundClosed",false]}) then {
    private _executor=owner _actor;
    if (_executor>1) then {
        private _generation=if (_lease isEqualTo []) then {0} else {(_lease select 0)+1};
        _lease=[_generation,_executor];
        _r set ["refundLease",_lease];_r set ["refundClosed",false];
    };
};
if (_lease isEqualTo [] || {_r getOrDefault ["refundClosed",false]}) exitWith {};
// Republish the live grant on retry; RPC and public metadata can arrive in either order.
_actor setVariable ["ACME_eqRefundLease",[_id]+_lease,true];
_actor setVariable ["ACME_eqAdmission",[_id,_r get "stamp"],true];
private _warm=if ((_r get "kind")=="blood") then {(_r get "warm")+((serverTime-(_r get "sample")) max 0)} else {-1};
[_actor,_id,"refund",_r get "item",_warm,serverTime,false,_lease] remoteExecCall ["ACME_fnc_equipmentInventory",_actor];
private _executor=_lease select 1;
if (_executor!=owner _actor) then {
    [_actor,_id,"refund",_r get "item",-1,-1,true,_lease] remoteExecCall ["ACME_fnc_equipmentInventory",_executor];
};
