/* One low-frequency transport worker; private visual plunger changes are never
 * broadcast. A queued old-owner message cannot survive an away/back handoff. */
private _outbox = missionNamespace getVariable ["ACME_syringeDeliveryOutbox",createHashMap];
{
    private _entry = _outbox getOrDefault [_x,[]];
    if (_entry isEqualTo []) then {continue;};
    _entry params ["_wire","_epoch","_kit","_next"];
    _wire params ["_mode","_medic","_request","_sender","_data"];
    if (isNull _medic || {!local _medic} || {_sender != clientOwner}
        || {(_medic getVariable ["ACME_providerLocalityEpoch",0]) != _epoch}
        || {_mode != "recover" && {(_medic getVariable ["ACME_equipmentKitEpoch",0]) != _kit}}) then {
        _outbox deleteAt _x;
        continue;
    };
    if (CBA_missionTime >= _next) then {
        _entry set [3,CBA_missionTime+2]; _outbox set [_x,_entry];
        // Commit before an in-process server reply can remove this request.
        missionNamespace setVariable ["ACME_syringeDeliveryOutbox",_outbox];
        ["ACME_syringeDelivery",_wire] call CBA_fnc_serverEvent;
        _outbox = missionNamespace getVariable ["ACME_syringeDeliveryOutbox",createHashMap];
    };
} forEach (+(keys _outbox));
missionNamespace setVariable ["ACME_syringeDeliveryOutbox",_outbox];
private _states = missionNamespace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap];
{
    private _request = _x;
    private _state = _states get _request;
    _state params ["_medic","_session","_epoch","_kit","_phase","_last","_kind"];
    if (_phase != "active") then {continue;};
    if (isNull _medic || {!local _medic}
        || {(_medic getVariable ["ACME_providerLocalityEpoch",0]) != _epoch}
        || {(_medic getVariable ["ACME_equipmentKitEpoch",0]) != _kit}) then {
        _state set [4,"retired"]; _states set [_request,_state];
        continue;
    };
    private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
    private _livePush = _kind == "push" && {_job isEqualType createHashMap}
        && {_job getOrDefault ["syringeDelivery",false]}
        && {(_job getOrDefault ["medic",objNull]) isEqualTo _medic}
        && {(_job getOrDefault ["session",""]) == _session}
        && {(_job getOrDefault ["providerLocalityEpoch",-1]) == _epoch}
        && {_job getOrDefault ["flowing",false]};
    // BEGIN without a live continuation must expire, even on a healthy owner.
    // An ordinary injection always queues its batch and STOP synchronously.
    if (!_livePush) then {
        ["stop",_medic,_request,[_session,"orphaned-continuation"]] call ACME_fnc_syringeDeliveryRequest;
        _states = missionNamespace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap];
        continue;
    };
    if (_kind == "push" && {hasInterface} && {_medic isNotEqualTo ACE_player}) then {
        ["stop",_medic,_request,[_session,"controlled-provider-changed"]] call ACME_fnc_syringeDeliveryRequest;
        _states = missionNamespace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap];
        continue;
    };
    if (CBA_missionTime - _last >= 2) then {
        _state set [5,CBA_missionTime]; _states set [_request,_state];
        missionNamespace setVariable ["ACME_syringeDeliveryClientSessions",_states];
        ["heartbeat",_medic,_request,[_session]] call ACME_fnc_syringeDeliveryRequest;
        _states = missionNamespace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap];
    };
} forEach (+(keys _states));
missionNamespace setVariable ["ACME_syringeDeliveryClientSessions",_states];
