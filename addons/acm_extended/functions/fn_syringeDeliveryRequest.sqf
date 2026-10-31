/* Queue only immutable, current-owner syringe protocol messages. Numeric CBA
 * handles and UI continuations stay private; the server holds source authority. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_syringeDeliveryRequest;}; _ok};
params ["_mode","_medic","_request",["_data",[]],["_callback",{}],["_args",[]]];
if (isNull _medic || {!local _medic} || {!(_mode in ["begin","batch","stop","recover","heartbeat"])}) exitWith {false};
// Freeze nested payloads before the first send; every retry retains the same
// exact dose/row even if a later caller edits its original arrays.
_data = [_data] call ACME_fnc_syringeDeliveryCopy;
private _epoch = _medic getVariable ["ACME_providerLocalityEpoch",0];
private _kit = _medic getVariable ["ACME_equipmentKitEpoch",0];
private _session = _data param [0,"",[""]];
private _suffix = if (_mode == "batch") then {_data param [1,"",[""]]} else {_mode};
private _key = format ["%1:%2:%3",netId _medic,_request,_suffix];
private _states = missionNamespace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap];
// A second BEGIN cannot replace or replay a captured continuation.
if (_mode == "begin" && {_request in _states}) exitWith {false};
if (_mode == "begin") then {
    _states set [_request,[_medic,_session,_epoch,_kit,"begin",CBA_missionTime,_data param [1,""],-1]];
    missionNamespace setVariable ["ACME_syringeDeliveryClientSessions",_states];
    private _callbacks = missionNamespace getVariable ["ACME_syringeDeliveryBeginCallbacks",createHashMap];
    _callbacks set [_request,[_medic,_session,_epoch,_kit,_callback,[_args] call ACME_fnc_syringeDeliveryCopy]];
    missionNamespace setVariable ["ACME_syringeDeliveryBeginCallbacks",_callbacks];
};
if (_mode in ["stop","recover"]) then {
    private _state = _states getOrDefault [_request,[]];
    if !(_state isEqualTo []) then {_state set [4,"stopping"]; _states set [_request,_state];};
    missionNamespace setVariable ["ACME_syringeDeliveryClientSessions",_states];
};
if (_mode == "stop") then {
    // STOP is a barrier for every already-submitted aliquot from this local
    // period. Reordered transport cannot return the carrier ahead of a batch.
    private _manifest = [];
    private _pending = missionNamespace getVariable ["ACME_syringeDeliveryOutbox",createHashMap];
    {
        private _entry = _pending get _x;
        private _message = _entry select 0;
        if ((_message select 0) == "batch" && {(_message select 1) isEqualTo _medic}
            && {(_message select 2) == _request} && {(_entry select 1) == _epoch}
            && {(_entry select 2) == _kit}) then {_manifest pushBack +(_message select 4);};
    } forEach (keys _pending);
    _data = +_data; _data set [2,_manifest];
};
private _wire = [_mode,_medic,_request,clientOwner,_data];
if (_mode != "heartbeat") then {
    private _outbox = missionNamespace getVariable ["ACME_syringeDeliveryOutbox",createHashMap];
    private _existing = _outbox getOrDefault [_key,[]];
    // Repeated Stop/Finalize can retry the original message but cannot mutate it.
    if !(_existing isEqualTo []) then {_wire = _existing select 0;} else {
        _outbox set [_key,[_wire,_epoch,_kit,CBA_missionTime+2]];
        missionNamespace setVariable ["ACME_syringeDeliveryOutbox",_outbox];
    };
};
["ACME_syringeDelivery",_wire] call CBA_fnc_serverEvent;
true
