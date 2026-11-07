/* Server-authorized movement. Terminal local receipts survive delayed public replication and handoff. */
params ["_actor","_id","_operation","_item",["_warm",-1],["_sampled",-1],["_query",false],["_refundLease",[]]];
if (canSuspend) exitWith {isNil {[_actor,_id,_operation,_item,_warm,_sampled,_query,_refundLease] call ACME_fnc_equipmentInventory;};};
if (isRemoteExecuted && {remoteExecutedOwner != 2}) exitWith {};
if (isNull _actor || {!(_operation in ["take","give","refund"])}) exitWith {};
if ((_actor getVariable ["ACME_equipmentWorldPending",""])!=_id) exitWith {};
// An RPC may precede public admission. Wait for the exact complete request.
private _admission=_actor getVariable ["ACME_eqAdmission",[]];
if !(_admission isEqualType [] && {count _admission==2} && {(_admission select 0) isEqualTo _id}) exitWith {};
private _stamp=_admission select 1;
if !(_stamp isEqualType [] && {count _stamp==2} && {(_stamp select 0) isEqualType 0}
    && {(_stamp select 1) isEqualType []} && {count (_stamp select 1)==2}) exitWith {};
private _origin=(_stamp select 1) select 0;
if ((_query && {_operation!="refund"} && {clientOwner!=_origin})
    || {!_query && {!local _actor}}) exitWith {};
if ((_actor getVariable ["ACME_eqReceiptRequest",""])!=_id) then {
    _actor setVariable ["ACME_eqReceiptRequest",_id,true];
    _actor setVariable ["ACME_eqReceipts",createHashMap,true];
};
// Private to each machine's replica, independent of public-variable delivery order.
// Keep only that actor's current request; old packets fail the pending-ID fence above.
if ((_actor getVariable ["ACME_eqLocalReceiptRequest",""])!=_id) then {
    _actor setVariable ["ACME_eqLocalReceiptRequest",_id];
    _actor setVariable ["ACME_eqLocalReceipts",createHashMap];
};
private _localReceipts=_actor getVariable ["ACME_eqLocalReceipts",createHashMap];
private _receipts=_actor getVariable ["ACME_eqReceipts",createHashMap];
if (_operation=="refund") exitWith {
    [_actor,_id,_item,_warm,_sampled,_query,_refundLease,_stamp] call ACME_fnc_equipmentRefundInventory;
};
private _key=_id+":"+_operation;
private _decision=_localReceipts getOrDefault [_key,[]];
if (_decision isEqualTo [] && {_key in _receipts}) then {
    _decision=[_receipts get _key,_receipts getOrDefault [_key+":retired",false]];
};
// The new machine cannot infer the previous outcome from absent replication.
// The server also queries the original machine for its terminal local receipt.
if (_decision isEqualTo [] && {!_query} && {clientOwner!=_origin}) exitWith {};
private _current=!_query && {_stamp isEqualTo ([_actor] call ACME_fnc_equipmentTransferStamp)};
private _ok=false;private _retired=false;
if (_decision isNotEqualTo []) then {
    _ok=_decision select 0;_retired=_decision select 1;
} else {
    // A query seals an unexecuted old command without touching nonlocal inventory.
    if (_query || {!_current}) then {
        _retired=true;
    } else {
        private _before=[_actor,_item] call ACME_fnc_itemCount;
        if (_operation=="take") then {
            if (_before>0) then {_ok=[_actor,_item] call ACME_fnc_itemTake;};
        } else {if (_warm>=0) then {
            private _age=_warm;
            if (_sampled>=0) then {_age=_age+((serverTime-_sampled) max 0);};
            _ok=[_actor,[_item,_age],false] call ACME_fnc_coolerGiveBag;
        } else {
            if (_actor canAdd _item) then {_actor addItem _item;} else {
                private _containers=[backpackContainer _actor,vestContainer _actor,uniformContainer _actor] select {!isNull _x};
                if (_containers isNotEqualTo []) then {(_containers select 0) addItemCargoGlobal [_item,1];};
            };
            _ok=([_actor,_item] call ACME_fnc_itemCount)==_before+1;
        };};
    };
};
// A failed take is terminal, so its negative ACK cannot race a later successful debit.
// Full-inventory give/refund failures remain retryable until placement or proved retirement.
if (_ok || {_retired} || {_operation=="take"}) then {
    _localReceipts set [_key,[_ok,_retired]];_actor setVariable ["ACME_eqLocalReceipts",_localReceipts];
    _receipts set [_key,_ok];_receipts set [_key+":retired",_retired];
    _actor setVariable ["ACME_eqReceipts",_receipts,true];
};
// Native inventory callbacks can synchronously replace a kit or hand off locality.
_current=!_query && {_stamp isEqualTo ([_actor] call ACME_fnc_equipmentTransferStamp)};
[_actor,_id,_operation,_ok,_retired,_current] remoteExecCall ["ACME_fnc_equipmentAck",2];
