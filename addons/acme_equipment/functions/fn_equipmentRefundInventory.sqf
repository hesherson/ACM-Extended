/* Private owner-side refund executor/witness. Queries never touch native inventory. */
params ["_actor","_id","_item","_warm","_sampled","_query","_lease","_stamp"];
if (canSuspend) exitWith {isNil {_this call ACME_fnc_equipmentRefundInventory;};};
if (isRemoteExecuted && {remoteExecutedOwner!=2}) exitWith {};
if (isNull _actor || {!(_lease isEqualType [])} || {count _lease!=2}) exitWith {};
_lease params ["_generation","_executor"];
if !(_generation isEqualType 0 && {_generation>=0} && {_generation==floor _generation}
    && {_executor isEqualType 0} && {_executor>1} && {_executor==floor _executor}) exitWith {};
if ((_actor getVariable ["ACME_equipmentWorldPending",""])!=_id
    || {(_actor getVariable ["ACME_eqRefundLease",[]]) isNotEqualTo ([_id]+_lease)}
    || {_query && {clientOwner!=_executor}} || {!_query && {!local _actor}}) exitWith {};
private _seen=_actor getVariable ["ACME_eqLocalRefundWatermark",["",-1,-1]];
if ((_seen select 0)==_id && {_generation<(_seen select 1)
    || {_generation==(_seen select 1) && {_executor!=(_seen select 2)}}}) exitWith {};
private _localReceipts=_actor getVariable ["ACME_eqLocalReceipts",createHashMap];
private _receipts=_actor getVariable ["ACME_eqReceipts",createHashMap];
private _prefix=_id+":refund:";
private _key=_prefix+str _generation;
if ((_seen select 0)!=_id || {_generation>(_seen select 1)}) then {
    _actor setVariable ["ACME_eqLocalRefundWatermark",[_id,_generation,_executor]];
    // A private high-water mark rejects obsolete packets even if public metadata regresses.
    {if ((_x find _prefix)==0 && {_x!=_key}) then {_localReceipts deleteAt _x;};} forEach keys _localReceipts;
    {if ((_x find _prefix)==0 && {_x!=_key}) then {_receipts deleteAt _x;};} forEach keys _receipts;
};
private _decision=_localReceipts getOrDefault [_key,[]];
// An interrupted or context-changing native attempt is not proof of non-delivery.
if !(_decision isEqualType []) exitWith {};
if (count _decision>2) exitWith {};
if (_decision isEqualTo []) then {_decision=_receipts getOrDefault [_key,[]];};
if (_decision isNotEqualTo [] && {!(_decision isEqualType []) || {count _decision!=2}
    || {!((_decision select 0) isEqualType false)} || {!((_decision select 1) isEqualType false)}}) exitWith {};
if (_decision isEqualTo [] && {!_query} && {clientOwner!=_executor}) exitWith {};
private _attemptStamp=if (!_query && {_decision isEqualTo []}) then {[_actor] call ACME_fnc_equipmentTransferStamp} else {[]};
if (!_query && {_decision isEqualTo []} && {_attemptStamp isEqualTo []}) exitWith {};
private _ok=false;private _retired=false;
if (_decision isNotEqualTo []) then {
    _ok=_decision select 0;_retired=_decision select 1;
} else {
    if (_query) then {_retired=true;} else {
        _localReceipts set [_key,[false,false,"attempting"]];
        _actor setVariable ["ACME_eqLocalReceipts",_localReceipts];
        private _before=[_actor,_item] call ACME_fnc_itemCount;
        if (_warm>=0) then {
            private _age=_warm;
            if (_sampled>=0) then {_age=_age+((serverTime-_sampled) max 0);};
            _ok=[_actor,[_item,_age],false] call ACME_fnc_coolerGiveBag;
        } else {
            if (_actor canAdd _item) then {_actor addItem _item;} else {
                private _containers=[backpackContainer _actor,vestContainer _actor,uniformContainer _actor] select {!isNull _x};
                if (_containers isNotEqualTo []) then {(_containers select 0) addItemCargoGlobal [_item,1];};
            };
            _ok=([_actor,_item] call ACME_fnc_itemCount)==_before+1;
        };
        if (!_ok && {_attemptStamp isEqualTo ([_actor] call ACME_fnc_equipmentTransferStamp)} && {local _actor}) then {
            _localReceipts deleteAt _key;
        };
        _actor setVariable ["ACME_eqLocalReceipts",_localReceipts];
    };
};
if (!_ok && {!_retired} && {count (_localReceipts getOrDefault [_key,[]])>2}) exitWith {};
if (_ok || {_retired}) then {
    _decision=[_ok,_retired];
    _localReceipts set [_key,_decision];_actor setVariable ["ACME_eqLocalReceipts",_localReceipts];
    _receipts set [_key,_decision];_actor setVariable ["ACME_eqReceipts",_receipts,true];
};
private _current=!_query && {_stamp isEqualTo ([_actor] call ACME_fnc_equipmentTransferStamp)};
[_actor,_id,"refund",_ok,_retired,_current,_lease] remoteExecCall ["ACME_fnc_equipmentAck",2];
