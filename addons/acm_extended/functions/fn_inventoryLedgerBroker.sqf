/* Server serializes issue/claim/settlement. Tokens never recycle, including consumed or retired kits. */
if (!isServer) exitWith {};
params ["_mode","_owner","_kind","_sid","_payload","_request",["_purpose",[]]];
if (isNull _owner || {!(_kind in ["prepared","syringe"])} || {_sid == ""}) exitWith {};
private _index = missionNamespace getVariable ["ACME_inventoryLedgerIndex",createHashMap];
private _key = _kind + ":" + _sid;
private _token = _index getOrDefault [_key,0];
private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
private _reply = {params ["_ok"]; ["ACME_inventoryReply",[_mode,_owner,_kind,_sid,_token,_request,_ok,0,_record param [6,0]],_owner] call CBA_fnc_targetEvent;};
if (_mode == "register") exitWith {
    private _pending = (_owner getVariable ["ACME_inventoryPending",createHashMap]) getOrDefault [_key,[]];
    if (count _pending < 4 || {(_pending select 3) != (_owner getVariable ["ACME_equipmentKitEpoch",0])}) exitWith {}; // event may precede object publication; durable allocation retries.
    // An older queued registration cannot replace a newer funded preparation.
    _payload = +(_pending select 2);
    // Token exhaustion is permanent for this mission. Reject once at register scope;
    // an inner exitWith would fall through and send a second failure ACK.
    if (_token == 0 && {(missionNamespace getVariable ["ACME_inventoryTokenSequence",0]) >= 65534}) exitWith {
        if (!(missionNamespace getVariable ["ACME_inventoryExhaustionReported",false])) then {
            missionNamespace setVariable ["ACME_inventoryExhaustionReported",true];
            diag_log "[ACME INVENTORY] Token space exhausted; funded preparation retained, no identity reused.";
        };
        [false] call _reply;
    };
    if (_token == 0) then {
        _token = (missionNamespace getVariable ["ACME_inventoryTokenSequence",0]) + 1;
        missionNamespace setVariable ["ACME_inventoryTokenSequence",_token];
        _index set [_key,_token]; missionNamespace setVariable ["ACME_inventoryLedgerIndex",_index,true];
        _record = [_kind,_sid,+_payload,_owner,"","held",0,createHashMap,[_kind,_payload] call ACME_fnc_inventoryLedgerClass];
        missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
    };
    if (count _record >= 7 && {(_record select 3) isEqualTo _owner} && {(_record select 5) == "held"} && {!(_pending isEqualTo [])}) then {
        if ((_record select 2) isNotEqualTo _payload) then {_record set [6,(_record select 6)+1];}; _record set [2,+_payload]; missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
    };
    [count _record >= 7 && {(_record select 3) isEqualTo _owner} && {(_record select 5) == "held"}] call _reply;
};
if (count _record < 7) exitWith {[false] call _reply;};
private _settled = _record param [7,createHashMap];
private _past = _settled getOrDefault [_request,[]];
private _escrow = (_owner getVariable ["ACME_inventoryEscrow",createHashMap]) getOrDefault [_request,[]];
private _physical = (([_owner,_kind] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) >= 0;
private _deliveries = missionNamespace getVariable ["ACME_syringeDeliveries",createHashMap];
private _delivery = _deliveries getOrDefault [_record select 4,createHashMap];
// A public Narc Box repaint is never an authority to alter a clinical claim.
if (_mode == "update" && {count _delivery > 0} && {(_delivery get "state") != "settled"}) exitWith {};
if (_mode in ["return","consume"] && {count _delivery > 0}) then {
    if ((_delivery get "state") in ["awaitBegin","active"]) then {
        ["recover",_owner,_request,owner _owner,[]] call ACME_fnc_syringeDeliveryBroker;
    };
};
if (_mode in ["return","consume"] && {count _delivery > 0}
    && {!((_delivery get "state") in ["ready","settled"])}) exitWith {[false] call _reply;};
if (_mode in ["return","consume"] && {count _delivery > 0}) then {
    private _row = +(_delivery get "row");
    private _empty = (_row param [2,0]) + (_row param [4,0]) <= 0.0005;
    _payload = if (_empty) then {[]} else {[_sid,_row]};
    _mode = ["return","consume"] select (_empty || {(_delivery get "kit") != (_owner getVariable ["ACME_equipmentKitEpoch",0])});
};
if (!(_past isEqualTo []) && {_mode in ["claim","return","consume"]}) exitWith {
    // Completed requests never re-acquire a token from a later native recipient.
    [_mode != "claim" && {(_past select 0) isEqualTo _owner} && {(_past select 1) == _mode} && {(_record select 3) isEqualTo _owner} && {(_record select 4) == _request}] call _reply;
};
if (_mode == "update") exitWith {
    // Only real custody or the exact outstanding escrow can update dose metadata.
    private _anyEscrow = values (_owner getVariable ["ACME_inventoryEscrow",createHashMap]);
    private _reserved = (_anyEscrow findIf {(_x param [0,0]) == _token && {(_x param [3,""]) == (_record select 4)}}) >= 0;
    if ((_physical && {(_record select 5) == "held"}) || {_reserved && {(_record select 5) == "reserved"} && {(_record select 3) isEqualTo _owner}}) then {
        _record set [2,+_payload]; _record set [3,_owner]; _record set [6,(_record select 6)+1];
        missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
    };
};
if (_mode == "claim") exitWith {
    if (_escrow isEqualTo []) exitWith {}; // durable provider requests retry after publication/locality arrives.
    // The clinical intent travels in the immutable request as well as escrow.
    // An earlier six-field Reserve publication must not receive a success ACK
    // before the matching delivery marker (and its journal) can be admitted.
    if ((_purpose param [0,""]) == "syringeDeliveryB285"
        && {count _escrow < 7 || {(_escrow select 6) isNotEqualTo _purpose}}) exitWith {};
    private _valid = count _escrow >= 6 && {(_escrow select 0) == _token} && {(_escrow select 1) isEqualTo _payload}
        && {(_escrow select 4) == (_owner getVariable ["ACME_equipmentKitEpoch",0])};
    _valid = _valid && {(_record select 5) == "held" || {(_record select 5) == "reserved" && {(_record select 4) == _request} && {(_record select 3) isEqualTo _owner}}};
    _valid = _valid && {(_record select 2) isEqualTo _payload};
    if (_valid) then {
        if ((_record select 5) == "held") then {_record set [6,(_record select 6)+1];};
        _record set [3,_owner]; _record set [4,_request]; _record set [5,"reserved"];
        missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
        if (_kind == "syringe" && {count _escrow >= 7}
            && {((_escrow select 6) param [0,""]) == "syringeDeliveryB285"}) then {
            [_owner,_request,_token,_record,_escrow] call ACME_fnc_syringeDeliveryClaim;
        };
    };
    [_valid] call _reply;
};
if (_mode in ["return","consume"]) exitWith {
    private _same = (_record select 3) isEqualTo _owner && {(_record select 4) == _request};
    if (_same && {(_record select 5) in ["spent","held"]}) exitWith {
        _settled set [_request,[_owner,_mode,_record select 5]]; _record set [7,_settled];
        missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
        [true] call _reply;
    };
    private _unclaimedReturn = _mode == "return" && {(_record select 5) == "held"} && {count _escrow >= 6} && {(_escrow select 0) == _token};
    if ((!_same || {(_record select 5) != "reserved"}) && {!_unclaimedReturn} || {count _escrow < 6}) exitWith {[false] call _reply;};
    _record set [3,_owner]; _record set [4,_request];
    private _retired = (_escrow select 4) != (_owner getVariable ["ACME_equipmentKitEpoch",0]);
    if (_unclaimedReturn) then {_payload = +(_record select 2);}; // a rejected stale claimant never overwrites canonical contents.
    _settled set [_request,[_owner,_mode,["held","spent"] select (_mode == "consume" || {_retired})]]; _record set [7,_settled];
    _record set [6,(_record select 6)+1];
    _record set [2,+_payload]; _record set [5,["held","spent"] select (_mode == "consume" || {_retired})];
    _record set [8,[_kind,_payload] call ACME_fnc_inventoryLedgerClass];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
    if (count _delivery > 0) then {
        _delivery set ["state","settled"];
        private _public = _owner getVariable ["ACME_syringeDeliverySessions",createHashMap];
        _public set [_request,[_delivery get "kit",_delivery get "session","settled",_token,_record select 6]];
        _owner setVariable ["ACME_syringeDeliverySessions",_public,true];
    };
    [true] call _reply;
};
