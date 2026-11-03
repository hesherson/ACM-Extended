/* Only the server may request inventory movement; duplicate deliveries reuse an exact receipt. */
params ["_actor","_id","_operation","_item",["_warm",-1]];
if (isRemoteExecuted && {remoteExecutedOwner != 2}) exitWith {};
if (isNull _actor || {!local _actor}) exitWith {};
if ((_actor getVariable ["ACME_equipmentWorldPending",""])!=_id) exitWith {};
if ((_actor getVariable ["ACME_eqReceiptRequest",""])!=_id) then {
    _actor setVariable ["ACME_eqReceiptRequest",_id,true];
    _actor setVariable ["ACME_eqReceipts",createHashMap,true];
};
private _receipts=_actor getVariable ["ACME_eqReceipts",createHashMap];
private _key=_id+":"+_operation;
private _ok=_receipts getOrDefault [_key,false];
if (!_ok) then {
    private _before=[_actor,_item] call ACME_fnc_itemCount;
    if (_operation=="take") then {
        if (_before>0) then {_ok=[_actor,_item] call ACME_fnc_itemTake;};
    } else {if (_warm>=0) then {
        _ok=[_actor,[_item,_warm],false] call ACME_fnc_coolerGiveBag;
    } else {
        if (_actor canAdd _item) then {_actor addItem _item;} else {
            private _containers=[backpackContainer _actor,vestContainer _actor,uniformContainer _actor] select {!isNull _x};
            if (_containers isNotEqualTo []) then {(_containers select 0) addItemCargoGlobal [_item,1];};
        };
        _ok=([_actor,_item] call ACME_fnc_itemCount)==_before+1;
    };};
    if (_ok) then {_receipts set [_key,true];_actor setVariable ["ACME_eqReceipts",_receipts,true];};
};
[_actor,_id,_operation,_ok] remoteExecCall ["ACME_fnc_equipmentAck",2];
