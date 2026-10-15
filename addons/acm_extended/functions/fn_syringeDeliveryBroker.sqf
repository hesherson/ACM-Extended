/* Durable syringe delivery. Only this server journal may dispatch a registered
 * batch or choose the returned payload. Timeouts stop flow; they never decide
 * whether medication reached the patient. */
if (!isServer) exitWith {false};
params ["_mode","_medic","_request","_sender",["_data",[]]];
if (isNull _medic) exitWith {false};
private _all = missionNamespace getVariable ["ACME_syringeDeliveries",createHashMap];
if (_mode == "recover" && {_request == ""}) exitWith {
    if (_sender != owner _medic) exitWith {false};
    {
        private _j = _all get _x;
        if ((_j get "medic") isEqualTo _medic && {(_j get "state") != "settled"}) then {
            ["recover",_medic,_x,_sender,[]] call ACME_fnc_syringeDeliveryBroker;
        };
    } forEach (keys _all);
    ["ACME_syringeDeliveryReply",["recover",_medic,"","",true,[],0,[]],_medic] call CBA_fnc_targetEvent;
    true
};
private _j = _all getOrDefault [_request,createHashMap];
if (count _j == 0 || {(_j get "medic") isNotEqualTo _medic}) exitWith {false};
private _session = _j get "session";
private _reply = {
    params ["_kind","_ok",["_info",[]]];
    ["ACME_syringeDeliveryReply",[_kind,_medic,_request,_j get "session",_ok,+(_j get "row"),_j get "revision",_info],_medic] call CBA_fnc_targetEvent;
};
private _publish = {
    _all set [_request,_j]; missionNamespace setVariable ["ACME_syringeDeliveries",_all];
    private _public = _medic getVariable ["ACME_syringeDeliverySessions",createHashMap];
    _public set [_request,[_j get "kit",_j get "session",_j get "state",_j get "token",_j get "revision"]];
    _medic setVariable ["ACME_syringeDeliverySessions",_public,true];
};
private _finish = {
    if ((_j get "state") == "settled") exitWith {};
    if ((_j get "state") == "ready" && {CBA_missionTime < (_j get "nextReply")}) exitWith {};
    private _pending = ((values (_j get "batches")) findIf {(_x select 3) == "pending"}) >= 0;
    if (!_pending && {(_j get "state") in ["stopping","ready"]}) then {
        _j set ["state","ready"];
        _j set ["nextReply",CBA_missionTime+2];
        call _publish;
        ["settle",true,[_j get "kit",_j get "token","ready"]] call _reply;
    };
};
// Patient decisions are independently durable even if the provider disappeared.
if (_mode == "receipt") exitWith {
    if (count _data != 6) exitWith {false};
    _data params ["_episode","_batchId","_id","_patient","_accepted","_reason"];
    private _batches = _j get "batches";
    private _batch = _batches getOrDefault [_batchId,[]];
    if (count _batch < 7 || {_episode != _session} || {(_batch select 0 select 3) != _id}
        || {(_batch select 0 select 0) isNotEqualTo _patient}
        || {!(_accepted isEqualType true)}) exitWith {false};
    // A delayed owner decision can be proven by the replicated exact receipt.
    // A sender from the captured dispatch owner is also valid after migration.
    private _proof = (_patient getVariable ["ACME_medicationReceiptsB14",createHashMap]) getOrDefault [_id,[]];
    if (_sender != (_batch select 6) && {count _proof < 2 || {(_proof select 0) isNotEqualTo _accepted}}) exitWith {false};
    private _restored = [];
    if ((_batch select 3) == "pending" && {!_accepted}) then {
        _restored = [_j get "row",_batch select 1,true] call ACME_fnc_syringeDeliveryDelta;
    };
    if ((_batch select 3) == "pending" && {!_accepted} && {_restored isEqualTo []}) exitWith {false};
    if ((_batch select 3) == "pending") then {
        if (!_accepted) then {_j set ["row",_restored];};
        _batch set [3,["rejected","accepted"] select _accepted];
        _batch set [4,_reason]; _batches set [_batchId,_batch]; _j set ["batches",_batches];
        _j set ["revision",(_j get "revision")+1];
        call _publish;
    };
    // Replay the immutable stored decision, never a duplicate's changed result.
    private _decision = (_batch select 3) == "accepted";
    ["ack",_decision,[_batchId,_batch select 2,_batch select 4]] call _reply;
    call _finish;
    true
};
if (_sender != owner _medic) exitWith {false};
if (_mode == "recover") exitWith {
    if ((_j get "state") != "settled") then {
        if ((_j get "state") != "ready") then {_j set ["state","stopping"];};
        call _publish;call _finish;
    };
    true
};
if (_mode == "stop") exitWith {
    if ((_data param [0,""]) != _session) exitWith {false};
    // Closing input carries every emitted, not-yet-acknowledged batch. STOP
    // may overtake its original packet; admission still precedes any return.
    if ((_j get "state") == "active") then {
        {
            ["batch",_medic,_request,_sender,_x] call ACME_fnc_syringeDeliveryBroker;
        } forEach (_data param [2,[],[[]]]);
    };
    if ((_j get "state") != "settled") then {
        if ((_j get "state") != "ready") then {_j set ["state","stopping"];};
        call _publish;call _finish;
    };
    true
};
private _owns = _sender == (_j get "owner")
    && {(_j get "kit") == (_medic getVariable ["ACME_equipmentKitEpoch",0])}
    && {CBA_missionTime <= (_j get "lease")};
if (_mode == "begin") exitWith {
    private _episode = _data param [0,""];
    if (!_owns || {_episode == ""} || {count _data != 7}
        || {!((_data select 1) in ["push","inject"])}
        || {!alive _medic} || {isNull (_data select 2)}) exitWith {["begin",false,["invalid or expired source"]] call _reply;false};
    if ((_j get "state") == "awaitBegin") then {
        _j set ["session",_episode]; _j set ["binding",[_data] call ACME_fnc_syringeDeliveryCopy];
        _j set ["state","active"]; _j set ["lease",CBA_missionTime+20];
        _j set ["revision",(_j get "revision")+1];call _publish;
    };
    private _ok = (_j get "state") == "active" && {(_j get "binding") isEqualTo _data};
    ["begin",_ok,[]] call _reply;
    _ok
};
if (_mode == "heartbeat") exitWith {
    if (_owns && {(_j get "state") == "active"} && {(_data param [0,""]) == _session}) then {
        _j set ["lease",CBA_missionTime+20];call _publish;
    };
    true
};
if (_mode != "batch" || {count _data != 4}) exitWith {false};
_data params ["_episode","_batchId","_args","_delta"];
private _batches = _j get "batches";
private _old = _batches getOrDefault [_batchId,[]];
if !(_old isEqualTo []) exitWith {
    if ((_old select 7) isNotEqualTo _data) exitWith {false};
    if ((_old select 3) != "pending") then {
        ["ack",(_old select 3) == "accepted",[_batchId,_old select 2,_old select 4]] call _reply;
    };
    true
};
if (!_owns || {(_j get "state") != "active"} || {_episode != _session} || {_batchId == ""}) exitWith {false};
if !(_args isEqualType [] && {count _args == 10}) exitWith {false};
private _binding = _j get "binding";
if ((_args select 0) isNotEqualTo (_binding select 2) || {(_args select 1) isNotEqualTo _medic}
    || {(_args select 2) isNotEqualTo (_binding select 6)} || {(_args select 3) != _batchId}
    || {(_args select 4) != "administer"} || {(_args select 5) != (_binding select 3)}
    || {(_args select 7) isNotEqualTo (_binding select 4)} || {(_args select 8) isNotEqualTo (_binding select 5)}) exitWith {false};
private _reject = {
    params ["_reason"];
    private _rejected = [[_args] call ACME_fnc_syringeDeliveryCopy,[_delta] call ACME_fnc_syringeDeliveryCopy,
        [(_args select 9)] call ACME_fnc_syringeDeliveryCopy,"rejected",_reason,0,owner (_args select 0),[_data] call ACME_fnc_syringeDeliveryCopy];
    _batches set [_batchId,_rejected]; _j set ["batches",_batches];
    _j set ["state","stopping"]; _j set ["revision",(_j get "revision")+1];call _publish;
    ["ack",false,[_batchId,_rejected select 2,_reason]] call _reply;
    call _finish;
    false
};
private _row = [_j get "row",_delta,false] call ACME_fnc_syringeDeliveryDelta;
if (_row isEqualTo []) exitWith {["invalid source delta"] call _reject};
if !([_j get "row",_delta,_args select 6] call ACME_fnc_syringeDeliveryDoseValid) exitWith {["dose does not match funded source"] call _reject};
private _inner = [(_args select 9)] call ACME_fnc_syringeDeliveryCopy;
private _wire = [_args] call ACME_fnc_syringeDeliveryCopy;
private _patient = _wire select 0;
private _machines = missionNamespace getVariable ["ACME_syringeDeliveryMachines",createHashMap];
private _nonce = _machines getOrDefault [str (owner _patient),""];
_wire set [9,["syringeDeliveryB285",_request,_session,_batchId,_inner,owner _patient,_nonce]];
private _batch = [_wire,[_delta] call ACME_fnc_syringeDeliveryCopy,_inner,"pending","",CBA_missionTime+2,owner _patient,[_data] call ACME_fnc_syringeDeliveryCopy,_nonce];
_batches set [_batchId,_batch]; _j set ["batches",_batches];
_j set ["row",_row]; _j set ["revision",(_j get "revision")+1];
_j set ["lease",CBA_missionTime+20];
// Persist reservation and exact request before any synchronous patient callback.
call _publish;
if (_nonce != "") then {[_patient,"medicationLine",_wire] call ACME_fnc_ownerDispatch;};
true
