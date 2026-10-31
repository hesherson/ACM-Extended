/* Delivery receipts settle only their captured session. Recovery installs the
 * server's complete canonical row; it never adds an old owner's visual delta. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_syringeDeliveryReply;};};
params ["_mode","_medic","_request","_session","_ok",["_row",[]],["_revision",0],["_info",[]]];
if (isNull _medic || {!local _medic}) exitWith {};
private _epoch = _medic getVariable ["ACME_providerLocalityEpoch",0];
private _kit = _medic getVariable ["ACME_equipmentKitEpoch",0];
private _outbox = missionNamespace getVariable ["ACME_syringeDeliveryOutbox",createHashMap];
private _states = missionNamespace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap];
private _state = _states getOrDefault [_request,[]];
private _same = count _state >= 8 && {(_state select 0) isEqualTo _medic}
    && {(_state select 1) == _session} && {(_state select 2) == _epoch}
    && {(_state select 3) == _kit};
private _remove = {
    params ["_kind",["_batch",""]];
    {
        private _wire = (_outbox get _x) select 0;
        if ((_wire select 1) isEqualTo _medic && {(_wire select 2) == _request}
            && {(_wire select 0) == _kind}
            && {_batch == "" || {((_wire select 4) param [1,""]) == _batch}}) then {_outbox deleteAt _x;};
    } forEach (+(keys _outbox));
    missionNamespace setVariable ["ACME_syringeDeliveryOutbox",_outbox];
};
private _closeLocal = {
    private _messages = missionNamespace getVariable ["ACME_syringeDeliveryOutbox",createHashMap];
    {
        private _message = (_messages get _x) select 0;
        if ((_message select 1) isEqualTo _medic && {(_message select 2) == _request}) then {_messages deleteAt _x;};
    } forEach (+(keys _messages));
    missionNamespace setVariable ["ACME_syringeDeliveryOutbox",_messages];
    private _callbacks = missionNamespace getVariable ["ACME_syringeDeliveryBeginCallbacks",createHashMap];
    _callbacks deleteAt _request; missionNamespace setVariable ["ACME_syringeDeliveryBeginCallbacks",_callbacks];
    private _sessions = missionNamespace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap];
    private _current = _sessions getOrDefault [_request,[]];
    if !(_current isEqualTo []) then {_current set [4,"terminal"]; _current set [7,_revision]; _sessions set [_request,_current];};
    missionNamespace setVariable ["ACME_syringeDeliveryClientSessions",_sessions];
};
if (_mode == "recover") exitWith {["recover"] call _remove;};
if (_mode == "begin") exitWith {
    ["begin"] call _remove;
    private _callbacks = missionNamespace getVariable ["ACME_syringeDeliveryBeginCallbacks",createHashMap];
    private _callback = _callbacks getOrDefault [_request,[]];
    if (_callback isEqualTo []) exitWith {}; // duplicate BEGIN cannot replay a debit.
    _callbacks deleteAt _request; missionNamespace setVariable ["ACME_syringeDeliveryBeginCallbacks",_callbacks];
    if (!_same || {(_callback select 0) isNotEqualTo _medic}
        || {(_callback select 1) != _session} || {(_callback select 2) != _epoch}
        || {(_callback select 3) != _kit} || {(_state select 4) != "begin"}) exitWith {
        ["recover",_medic,_request,[]] call ACME_fnc_syringeDeliveryRequest;
    };
    _state set [4,if (_ok) then {"active"} else {"stopping"}];
    _state set [7,_revision]; _states set [_request,_state];
    missionNamespace setVariable ["ACME_syringeDeliveryClientSessions",_states];
    if (_ok) then {
        [_ok,_callback select 5] call (_callback select 4);
    } else {["recover",_medic,_request,[]] call ACME_fnc_syringeDeliveryRequest;};
};
if (_mode == "ack") exitWith {
    _info params [["_batch",""],["_meta",[]],["_reason",""]];
    private _key = format ["%1:%2:%3",netId _medic,_request,_batch];
    private _entry = _outbox getOrDefault [_key,[]];
    // The batch's originating period alone may update its live plunger. A
    // missing old-owner outbox is resolved only by canonical final settlement.
    if (_entry isEqualTo []) exitWith {};
    ["batch",_batch] call _remove;
    if (!_same || {(_entry select 1) != _epoch} || {(_entry select 2) != _kit}) exitWith {};
    private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
    if (_job isEqualType createHashMap && {_job getOrDefault ["syringeDelivery",false]}
        && {(_job getOrDefault ["session",""]) == _session}
        && {(_job getOrDefault ["medic",objNull]) isEqualTo _medic}
        && {(_job getOrDefault ["providerLocalityEpoch",-1]) == _epoch}) then {
        // Remove the immutable outbox entry BEFORE possible synchronous refund.
        [_medic,_meta,_ok,_reason,""] call ACME_fnc_hardcorePushAck;
    };
};
if (_mode != "settle" || {!_ok} || {count _info < 3}) exitWith {};
_info params ["_sourceKit","_token","_serverState"];
private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
private _sid = if (count _record >= 2) then {_record select 1} else {_row param [11,"",[""]]};
if (_sid == "") exitWith {}; // wait for exact server token replication.
// A delayed ready reply cannot write into a later claim, native recipient or
// replaced kit that reused the same source identity. Server retries let a reply
// that preceded token replication be considered again once its proof arrives.
if (count _record < 7) exitWith {};
if ((_record select 3) isNotEqualTo _medic || {(_record select 4) != _request}) exitWith {call _closeLocal;};
private _liveEscrow = (_medic getVariable ["ACME_inventoryEscrow",createHashMap]) getOrDefault [_request,[]];
if ((_record select 5) != "reserved" && {_liveEscrow isEqualTo []}) exitWith {call _closeLocal;};
private _applied = missionNamespace getVariable ["ACME_syringeDeliveryApplied",createHashMap];
private _past = _applied getOrDefault [_request,[-1,-1]];
if ((_past select 0) > _revision) exitWith {};
private _settling = missionNamespace getVariable ["ACME_syringeDeliverySettling",createHashMap];
if (_request in _settling) exitWith {};
_settling set [_request,_revision];
missionNamespace setVariable ["ACME_syringeDeliverySettling",_settling];
private _releaseGuard = {
    private _guards = missionNamespace getVariable ["ACME_syringeDeliverySettling",createHashMap];
    _guards deleteAt _request;
    missionNamespace setVariable ["ACME_syringeDeliverySettling",_guards];
};
private _stored = true;
if ((_past select 0) < _revision || {(_past select 1) != _sourceKit}) then {
    private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
    if (_job isEqualType createHashMap && {_job getOrDefault ["syringeDelivery",false]}
        && {(_job getOrDefault ["session",""]) == _session}
        && {(_job getOrDefault ["medic",objNull]) isEqualTo _medic}) then {
        [_session,missionNamespace getVariable ["ACME_HCMedPushPFH",-1],"server-settled"] call ACME_fnc_hardcorePushRetire;
    };
    if (_sourceKit == _kit) then {
        private _rows = +(_medic getVariable ["ACME_narcStore",[]]);
        private _at = _rows findIf {(_x param [11,"",[""]]) == _sid};
        private _hasSolution = count _row >= 12 && {(_row param [2,0]) + (_row param [4,0]) > 0.0005};
        if (_hasSolution) then {
            if (_at < 0) then {_rows pushBack +_row;} else {_rows set [_at,+_row];};
        } else {if (_at >= 0) then {_rows deleteAt _at;};};
        _stored = [_medic,_rows,false] call ACME_fnc_narcStoreCommit;
    };
    if (_stored) then {_applied set [_request,[_revision,_sourceKit]];
        missionNamespace setVariable ["ACME_syringeDeliveryApplied",_applied];};
};
if (!_stored) exitWith {call _releaseGuard;};
call _closeLocal;
private _escrow = _medic getVariable ["ACME_inventoryEscrow",createHashMap];
private _held = _escrow getOrDefault [_request,[]];
// A Local event can precede provider escrow replication. Rebuild only this
// journal-certified carrier, never a generic source or additive refund.
if (_held isEqualTo [] && {count _record >= 7} && {(_record select 3) isEqualTo _medic}
    && {(_record select 4) == _request} && {(_record select 5) == "reserved"}) then {
    _held = [_token,[_sid,+_row],"syringe",_request,_sourceKit,true,["syringeDeliveryB285",clientOwner]];
    _escrow set [_request,_held]; _medic setVariable ["ACME_inventoryEscrow",_escrow,true];
};
if (_held isEqualTo []) exitWith {call _releaseGuard;};
private _consume = _sourceKit != _kit || {count _row < 12} || {(_row param [2,0]) + (_row param [4,0]) <= 0.0005};
[_medic,_request,_consume,if (_consume) then {[]} else {[_sid,+_row]}] call ACME_fnc_inventoryLedgerSettle;
call _releaseGuard;
