/* UI entry: durable request IDs make repeated network delivery harmless. */
if (canSuspend) exitWith {private _ok=false; isNil {_ok=_this call ACME_fnc_coolerBoxRequest;}; _ok};
params ["_mode",["_owner",ACE_player],["_sid",""],["_box",objNull],["_continuation",[]]];
if (isNull _owner || {!local _owner} || {!alive _owner} || {!(_mode in ["deploy","pack","draw"])}) exitWith {false};
private _sequence=(missionNamespace getVariable ["ACME_coolerActionSequence",0])+1;
missionNamespace setVariable ["ACME_coolerActionSequence",_sequence];
private _request=format ["cooler-box:%1:%2:%3",clientOwner,diag_tickTime,_sequence];
private _enqueue={
    params ["_mode","_owner","_sid","_box","_request",["_continuation",[]]];
    if (_continuation isNotEqualTo []) then {
        private _callbacks=missionNamespace getVariable ["ACME_coolerBoxCallbacks",createHashMap];
        _callbacks set [_request,[_owner,_continuation,_owner getVariable ["ACME_providerLocalityEpoch",0],_owner getVariable ["ACME_equipmentKitEpoch",0]]];
        missionNamespace setVariable ["ACME_coolerBoxCallbacks",_callbacks];
    };
    private _requests=_owner getVariable ["ACME_coolerBoxRequests",createHashMap];
    private _kit=_owner getVariable ["ACME_equipmentKitEpoch",0];
    private _locality=_owner getVariable ["ACME_providerLocalityEpoch",0];
    _requests set [_request,[_mode,_owner,_sid,_box,_request,serverTime+1,_kit,_locality]];
    _owner setVariable ["ACME_coolerBoxRequests",_requests,true];
    private _tracked=missionNamespace getVariable ["ACME_inventoryTracked",[]]; _tracked pushBackUnique _owner;
    missionNamespace setVariable ["ACME_inventoryTracked",_tracked];
    ["ACME_coolerBoxBroker",[_mode,_owner,_sid,_box,_request,_kit,_locality]] call CBA_fnc_serverEvent;
};
if (_mode in ["pack","draw"]) exitWith {
    if (isNull _box || {_owner distance _box > 4.5} || {_box getVariable ["ACME_coolerPacking",false]}) exitWith {false};
    [_mode,_owner,_sid,_box,_request,_continuation] call _enqueue;
    true
};
private _receipt=[_owner,"cooler",_sid,_request] call ACME_fnc_inventoryLedgerReserve;
if (_receipt isEqualTo []) exitWith {false};
private _intents=_owner getVariable ["ACME_coolerIntents",createHashMap];
_intents set [_request,["deploy",serverTime]];
_owner setVariable ["ACME_coolerIntents",_intents,true];
[_owner,_request,{
    params ["_accepted","_args"];
    _args params ["_owner","_sid","_request","_enqueue","_continuation"];
    if (!_accepted) exitWith {[_owner,_request,false] call ACME_fnc_inventoryLedgerSettle;};
    ["deploy",_owner,_sid,objNull,_request,_continuation] call _enqueue;
},[_owner,_sid,_request,_enqueue,_continuation]] call ACME_fnc_inventoryLedgerClaim;
true
