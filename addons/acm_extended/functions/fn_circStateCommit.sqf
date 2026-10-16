/*
 * Authoritative mutation gate for Extended circulation physiology.
 *
 * B203 network contract:
 * - owner-local physiology keeps the full HashMap exact on every 0.25 s circulation tick;
 * - the full ~90-field map is NOT broadcast on every tick;
 * - remote/JIP state is refreshed at a bounded cadence, with immediate publication for coarse clinically
 *   important transitions;
 * - helper counters include this formerly-untracked publication path.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_state", createHashMap, [createHashMap]],
    ["_public", true, [true]]
];
if (isNull _patient) exitWith {false};

// The owner always gets the exact current map without network traffic.
_patient setVariable ["ACME_circ_State", _state, false];
if (!_public) exitWith {true};

// Preserve correctness for any legacy/non-owner caller instead of suppressing its explicit public request.
if (!local _patient) exitWith {
    _patient setVariable ["ACME_circ_State", _state, true];
    true
};

private _now = diag_tickTime;
private _interval = missionNamespace getVariable ["ACME_circ_stateNetInterval", 2.0];
if !(_interval isEqualType 0 && {finite _interval}) then {_interval = 2.0;};
_interval = _interval max 0.25;

// Coarse signature: publish important state-band transitions immediately without turning continuous physiology
// into a packet-per-tick stream. Fine-grained values still refresh on the bounded interval below.
private _sig = [
    count _state > 0, // A clear must publish even when the previous map was physiologically neutral.
    _state getOrDefault ["shockActive", false],
    round (10 * (_state getOrDefault ["shockSeverity", 0])),
    round (10 * (_state getOrDefault ["totalAcidosis", 0])),
    round ((_state getOrDefault ["paCO2", 40]) / 2),
    round (10 * (_state getOrDefault ["ionizedCa", 1.15])),
    round (2 * (_state getOrDefault ["temp", 37])),
    round (10 * (_state getOrDefault ["ichRisk", 0]))
];

private _lastAt = _patient getVariable ["ACME_circ_stateNetAt", -1];
private _lastSig = _patient getVariable ["ACME_circ_stateNetSig", []];
private _ownerStamp = [owner _patient, local _patient];
private _publish = (_lastAt < 0)
    || {(_patient getVariable ["ACME_circ_stateNetOwner", []]) isNotEqualTo _ownerStamp}
    || {_sig isNotEqualTo _lastSig}
    || {(_now - _lastAt) >= _interval};

private _counting = missionNamespace getVariable ["ACME_net_count", false];
if (!_publish) exitWith {
    if (_counting) then {
        private _saved = missionNamespace getVariable ["ACME_net_saved", createHashMap];
        _saved set ["ACME_circ_State", (_saved getOrDefault ["ACME_circ_State", 0]) + 1];
        missionNamespace setVariable ["ACME_net_saved", _saved];
    };
    true
};

_patient setVariable ["ACME_circ_stateNetAt", _now, false];
_patient setVariable ["ACME_circ_stateNetSig", _sig, false];
_patient setVariable ["ACME_circ_stateNetOwner", _ownerStamp, false];
_patient setVariable ["ACME_circ_State", _state, true];

if (_counting) then {
    private _sent = missionNamespace getVariable ["ACME_net_sent", createHashMap];
    _sent set ["ACME_circ_State", (_sent getOrDefault ["ACME_circ_State", 0]) + 1];
    missionNamespace setVariable ["ACME_net_sent", _sent];
};

true
