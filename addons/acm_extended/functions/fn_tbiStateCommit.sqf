/*
 * B204 authoritative mutation gate for Extended TBI state.
 * Owner-local physiology remains exact at 4 Hz. The full state HashMap is replicated at a bounded cadence, with
 * immediate refresh on coarse neurological transitions. This prevents a TBI casualty from broadcasting a large
 * mutable map every circulation frame.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_state", createHashMap, [createHashMap]],
    ["_public", true, [true]]
];
if (isNull _patient) exitWith {false};

_patient setVariable ["ACME_tbi_State", _state, false];
if (!_public) exitWith {true};

if (!local _patient) exitWith {
    _patient setVariable ["ACME_tbi_State", _state, true];
    true
};

private _now = diag_tickTime;
private _interval = missionNamespace getVariable ["ACME_tbi_stateNetInterval", 1.0];
if !(_interval isEqualType 0 && {finite _interval}) then {_interval = 1.0;};
_interval = _interval max 0.25;

private _pupils = _state getOrDefault ["pupils", []];
private _sig = [
    count _state > 0,
    round (20 * (_state getOrDefault ["severity", 0])),
    round (_state getOrDefault ["icp", 0]),
    round ((_state getOrDefault ["cpp", 0]) / 2),
    _state getOrDefault ["herniating", false],
    _state getOrDefault ["herniationStage", 0],
    _state getOrDefault ["cushing", false],
    _state getOrDefault ["gcsMotor", 6],
    str _pupils
];

private _lastAt = _patient getVariable ["ACME_tbi_stateNetAt", -1];
private _lastSig = _patient getVariable ["ACME_tbi_stateNetSig", []];
private _ownerStamp = [owner _patient, local _patient];
private _publish = (_lastAt < 0)
    || {(_patient getVariable ["ACME_tbi_stateNetOwner", []]) isNotEqualTo _ownerStamp}
    || {_sig isNotEqualTo _lastSig}
    || {(_now - _lastAt) >= _interval};

private _counting = missionNamespace getVariable ["ACME_net_count", false];
if (!_publish) exitWith {
    if (_counting) then {
        private _saved = missionNamespace getVariable ["ACME_net_saved", createHashMap];
        _saved set ["ACME_tbi_State", (_saved getOrDefault ["ACME_tbi_State", 0]) + 1];
        missionNamespace setVariable ["ACME_net_saved", _saved];
    };
    true
};

_patient setVariable ["ACME_tbi_stateNetAt", _now, false];
_patient setVariable ["ACME_tbi_stateNetSig", _sig, false];
_patient setVariable ["ACME_tbi_stateNetOwner", _ownerStamp, false];
_patient setVariable ["ACME_tbi_State", _state, true];

if (_counting) then {
    private _sent = missionNamespace getVariable ["ACME_net_sent", createHashMap];
    _sent set ["ACME_tbi_State", (_sent getOrDefault ["ACME_tbi_State", 0]) + 1];
    missionNamespace setVariable ["ACME_net_sent", _sent];
};
true
