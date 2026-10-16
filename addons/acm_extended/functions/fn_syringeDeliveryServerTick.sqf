/* Server work survives all provider-local controllers. A lease can end input,
 * never manufacture a clinical decision. Keep exact pending requests forever. */
if (!isServer) exitWith {};
private _all = missionNamespace getVariable ["ACME_syringeDeliveries",createHashMap];
private _kept = [];
{
    private _request = _x;
    private _j = _all getOrDefault [_request,createHashMap];
    if (count _j == 0 || {(_j get "state") == "settled"}) then {continue;};
    _kept pushBack _request;
    private _medic = _j get "medic";
    if (!isNull _medic && {(_j get "state") in ["active","awaitBegin"]}
        && {owner _medic != (_j get "owner")
            || {(_medic getVariable ["ACME_equipmentKitEpoch",0]) != (_j get "kit")}
            || {CBA_missionTime > (_j get "lease")}}) then {
        ["recover",_medic,_request,owner _medic,[]] call ACME_fnc_syringeDeliveryBroker;
    };
    private _batches = _j get "batches";
    {
        private _batchId = _x;
        private _b = _batches get _batchId;
        if ((_b select 3) != "pending") then {continue;};
        private _args = _b select 0;
        private _patient = _args select 0;
        private _gone = isNull _patient;
        private _id = _args select 3;
        private _receipt = if (_gone) then {[]} else {
            (_patient getVariable ["ACME_medicationReceiptsB14",createHashMap]) getOrDefault [_id,[]]
        };
        if (count _receipt >= 2) then {
            ["receipt",_medic,_request,owner _patient,[_j get "session",_batchId,_id,_patient,_receipt select 0,_receipt select 1]] call ACME_fnc_syringeDeliveryBroker;
            continue;
        };
        if (CBA_missionTime < (_b select 5)) then {continue;};
        private _nonce = _b param [8,""];
        if (_gone && {_nonce == ""}) then {
            // An empty persisted nonce proves this server never dispatched the
            // request. The deleted target cannot execute it in the future.
            ["receipt",_medic,_request,_b select 6,[_j get "session",_batchId,_id,_patient,false,"patient removed before dispatch"]] call ACME_fnc_syringeDeliveryBroker;
            continue;
        };
        if (_nonce == "") then {
            private _machines = missionNamespace getVariable ["ACME_syringeDeliveryMachines",createHashMap];
            _nonce = _machines getOrDefault [str (_b select 6),""];
            if (_nonce == "") then {continue;};
            _b set [8,_nonce];
            private _meta = +(_args select 9); _meta set [6,_nonce];
            _args = +_args; _args set [9,_meta]; _b set [0,_args];
        };
        _b set [5,CBA_missionTime+5]; _batches set [_batchId,_b];
        if (_gone || {owner _patient != (_b select 6)}) then {
            // The original machine either proves its exact decision or installs
            // a permanent rejection tombstone. An unmatched incarnation cannot
            // deny the old machine's dose; disconnected unknowns remain held.
            ["ACME_syringeDeliveryPatientQuery",[_medic,_request,_j get "session",_batchId,_id,_patient,_b select 6,_nonce],_b select 6] call CBA_fnc_ownerEvent;
            continue;
        };
        [_patient,"medicationLine",_args] call ACME_fnc_ownerDispatch;
    } forEach (keys _batches);
    if (!isNull _medic && {(_j get "state") in ["ready","stopping"]}
        && {CBA_missionTime >= (_j get "nextReply")}) then {
        ["recover",_medic,_request,owner _medic,[]] call ACME_fnc_syringeDeliveryBroker;
    };
} forEach (missionNamespace getVariable ["ACME_syringeDeliveryActive",[]]);
missionNamespace setVariable ["ACME_syringeDeliveryActive",_kept];
