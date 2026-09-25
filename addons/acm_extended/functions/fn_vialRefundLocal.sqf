/* Source-owner settlement for an exact previously debited solution receipt.
   A shared drawer may still hold a live lease when a rejected bag ACK arrives.
   Queue the delta until that lease ends, then add it to the current ledger once.
   Queue and receipts follow the inventory object through locality changes. */
params ["_holder", ["_id","",[""]], ["_components",[],[[]]]];
if (isNull _holder) exitWith {};
if (!local _holder) exitWith {[_holder,"vialRefund",[_id,_components]] call ACME_fnc_ownerDispatch;};

isNil {
    private _queue = +(_holder getVariable ["ACME_vialRefundQueue",[]]);
    private _settled = _holder getVariable ["ACME_vialRefundReceipts",createHashMap];
    if (_id != "" && {!(_settled getOrDefault [_id,false])} && {(_queue findIf {(_x select 0) == _id}) < 0}) then {
        private _valid = _components isEqualType [] && {!(_components isEqualTo [])};
        {
            if !(_x isEqualType [] && {count _x == 2} && {(_x select 0) isEqualType ""}
                && {(_x select 1) isEqualType 0} && {finite (_x select 1)} && {(_x select 1) > 0}
                && {([_x select 0] call ACME_fnc_vialCapacity) > 0}) then {_valid = false;};
        } forEach _components;
        if (_valid) then {
            _queue pushBack [_id,+_components];
            _holder setVariable ["ACME_vialRefundQueue",_queue,true];
        };
    };
    if !(_queue isEqualTo []) then {
        private _lease = _holder getVariable ["ACME_vialLease",[objNull,"",0]];
        private _leaseMedic = _lease param [0,objNull];
        private _busy = !isNull _leaseMedic && {alive _leaseMedic}
            && {(_lease param [1,""]) != ""} && {(_lease param [2,0]) > serverTime};
        if (!_busy) then {
            private _map = _holder getVariable ["ACME_infusion_openVials",createHashMap];
            {
                _x params ["_receiptId","_parts"];
                if !(_settled getOrDefault [_receiptId,false]) then {
                    {_x params ["_med","_ml"]; _map set [_med,(_map getOrDefault [_med,0]) + _ml];} forEach _parts;
                    _settled set [_receiptId,true];
                };
            } forEach _queue;
            [_holder,_map] call ACME_fnc_openVialStoreCommit;
            _holder setVariable ["ACME_vialRefundReceipts",_settled,true];
            _holder setVariable ["ACME_vialRefundQueue",[],true];
        } else {
            // One wake-up per owning machine. A migrated old wake-up forwards
            // through ownerDispatch; repeated queued/settled IDs remain inert.
            if ((_holder getVariable ["ACME_vialRefundWakeOwner",-1]) != clientOwner) then {
                _holder setVariable ["ACME_vialRefundWakeOwner",clientOwner];
                [{
                    params ["_holder","_wakeOwner"];
                    if (isNull _holder) exitWith {};
                    if ((_holder getVariable ["ACME_vialRefundWakeOwner",-1]) == _wakeOwner) then {
                        _holder setVariable ["ACME_vialRefundWakeOwner",-1];
                    };
                    [_holder,"vialRefund",[]] call ACME_fnc_ownerDispatch;
                },[_holder,clientOwner],0.25] call CBA_fnc_waitAndExecute;
            };
        };
    };
    false
};
