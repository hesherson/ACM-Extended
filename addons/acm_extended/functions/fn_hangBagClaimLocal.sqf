// Unscheduled patient-owner arbitration. An unexpired lease wins even before the
// provider's Active flag replicates. No inventory, dose, patient-life or animation policy here.
params ["_patient", "_operation", "_args"];
if (isNull _patient || {!local _patient}) exitWith {false};
_args params [["_medic", objNull, [objNull]], ["_episode", -1, [0]],
    ["_flow", 1.75, [0]], ["_epoch", -1, [0]], ["_providerOwner", -1, [0]],
    ["_sequence", -1, [0]], ["_sentAt", -1, [0]]];
private _holder = _patient getVariable ["ACME_hang_Medic", objNull];
private _heldEpisode = _patient getVariable ["ACME_hang_Episode", -2];
private _exact = _holder isEqualTo _medic && {_heldEpisode == _episode};
if (_operation == "release") exitWith {
    // Legacy cleanup callers carry only medic/episode; the token still isolates their cancellation.
    private _releaseEpoch = if (_epoch >= 0) then {_epoch} else {[_patient] call ACME_fnc_clinicalEpoch};
    [_patient,"hang",_medic,_episode,_releaseEpoch,"cancel"] call ACME_fnc_actionClaimLedger;
    if (_exact) then {
        _patient setVariable ["ACME_hang_flowMult", 1, true];
        _patient setVariable ["ACME_hang_Medic", objNull, true];
        _patient setVariable ["ACME_hang_Episode", -1, true];
        _patient setVariable ["ACME_hang_LeaseUntil", -1, true];
    };
    _exact
};
if !(_operation in ["claim", "renew"]) exitWith {false};
private _now = serverTime;
private _reason = [_patient,_medic,_epoch,_providerOwner,_sentAt] call ACME_fnc_actionClaimValidate;
private _valid = _reason == "" && {finite _episode} && {_episode >= 0}
    && {finite _flow} && {finite _sequence} && {_sequence >= 0} && {_sequence == floor _sequence}
    && {isNull objectParent _medic}
    && {_medic distance _patient <= (missionNamespace getVariable ["ACME_hang_leash", 3])}
    && {missionNamespace getVariable ["ACME_sys_hang", true]};
private _leaseUntil = _patient getVariable ["ACME_hang_LeaseUntil", -1];
private _holderValid = !isNull _holder && {alive _holder} && {
    if (_leaseUntil >= 0) then {
        _leaseUntil > _now && {(_patient getVariable ["ACME_hang_LeaseEpoch", -1]) == _epoch}
    } else {
        // Preserve a pre-upgrade active holder rather than steal its workspace.
        _holder getVariable ["ACME_hang_Active", false]
    }
};
private _cached = [_patient,"hang",_medic,_episode,_epoch,"lookup",_sequence] call ACME_fnc_actionClaimLedger;
private _state = _cached select 0;
private _newSequence = _sequence > (_cached select 1);
private _accepted = _valid && {!(_state in ["cancelled","blocked"])} && {
    if (!_newSequence) then {
        _state == "accepted" && {_exact} && {_leaseUntil > _now}
    } else {
        if (_operation == "renew") then {_exact && {_leaseUntil > _now}} else {
            _sequence == 0 && {!_holderValid || {_exact}}
        }
    }
};
private _replySequence = _sequence;
private _replyUntil = _leaseUntil;
if (!_newSequence && {_accepted}) then {
    // Replay the latest compact result without extending the owner lease or repeating side effects.
    _replySequence = _cached select 1;
    _replyUntil = (_cached select 2) param [1,_leaseUntil];
};
if (_newSequence && {!(_state in ["cancelled","blocked"])}) then {
    _replyUntil = if (_accepted) then {_now + 6} else {_leaseUntil};
    private _stored = [_patient,"hang",_medic,_episode,_epoch,["reject","accept"] select _accepted,
        _sequence,[_accepted,_replyUntil]] call ACME_fnc_actionClaimLedger;
    _accepted = _accepted && {(_stored select 0) == "accepted"};
};
if (_accepted && {_newSequence}) then {
    if (!_exact) then {
        _patient setVariable ["ACME_hang_Medic", _medic, true];
        _patient setVariable ["ACME_hang_Episode", _episode, true];
        _patient setVariable ["ACME_hang_LeaseEpoch", _epoch, true];
    };
    _patient setVariable ["ACME_hang_LeaseUntil", _replyUntil, true];
    private _nextFlow = (_flow max 1) min 5;
    if ((_patient getVariable ["ACME_hang_flowMult", 1]) != _nextFlow) then {
        _patient setVariable ["ACME_hang_flowMult", _nextFlow, true];
    };
};
if (!isNull _medic) then {
    ["ACME_hangClaimAck", [_patient, _medic, _episode, _accepted, _epoch, _providerOwner, _replyUntil, _replySequence], _medic] call CBA_fnc_targetEvent;
};
_accepted
