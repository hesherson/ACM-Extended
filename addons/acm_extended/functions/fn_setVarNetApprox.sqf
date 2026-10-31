/*
 * Publish a continuously changing scalar without sending every physiology tick.
 *
 * The object owner always keeps the exact value locally. Remote machines receive a
 * value when it moves by at least _epsilon or when _maxAge seconds have elapsed.
 * Ownership changes invalidate the cache and force a fresh publication, so locality
 * transfer never inherits a stale suppression decision from the previous owner.
 *
 * Usage: [_patient, "ACME_state", _value, 0.005, 3] call ACME_fnc_setVarNetApprox;
 */
params [
    ["_obj", objNull, [objNull]],
    ["_name", "", [""]],
    ["_value", 0, [0]],
    ["_epsilon", 0, [0]],
    ["_maxAge", 5, [0]]
];
if (isNull _obj || {_name isEqualTo ""}) exitWith {};
// A non-finite scalar must never enter Arma's replicated state. Apart from wasting packets, NaN/Inf can poison
// downstream comparisons so every later tick appears changed. Preserve the last good value instead.
if !(finite _value) exitWith {
    if (missionNamespace getVariable ["ACME_net_count", false]) then {
        private _bad = missionNamespace getVariable ["ACME_net_nonFiniteSuppressed", createHashMap];
        _bad set [_name, (_bad getOrDefault [_name, 0]) + 1];
        missionNamespace setVariable ["ACME_net_nonFiniteSuppressed", _bad];
    };
};
if !(finite _epsilon) then {_epsilon = 0;};
if !(finite _maxAge) then {_maxAge = 5;};
_epsilon = abs _epsilon;
_maxAge = _maxAge max 0;

// This helper is intended for owner-local physiology. Preserve correctness if a
// caller violates that contract instead of silently keeping a local-only value.
if (!local _obj) exitWith {
    _obj setVariable [_name, _value, true];
};

private _stamp = [owner _obj, local _obj];
private _cache = _obj getVariable ["ACME_net_approxCache", createHashMap];
if !(_cache isEqualType createHashMap) then {_cache = createHashMap;};
if !((_obj getVariable ["ACME_net_approxOwner", []]) isEqualTo _stamp) then {
    _cache = createHashMap;
    _obj setVariable ["ACME_net_approxCache", _cache, false];
    _obj setVariable ["ACME_net_approxOwner", _stamp, false];
};

private _key = toLowerANSI _name;
private _row = _cache getOrDefault [_key, []];
private _now = diag_tickTime;
private _publish = (count _row) < 2;
if (!_publish) then {
    private _lastValue = _row param [0, _value, [0]];
    private _lastAt = _row param [1, -1, [0]];
    private _moved = if (_epsilon > 0) then {
        abs (_value - _lastValue) >= _epsilon
    } else {
        _value != _lastValue
    };
    private _aged = _maxAge > 0 && {_lastAt < 0 || {_now - _lastAt >= _maxAge}};
    _publish = _moved || _aged;
};

// Exact physiology stays owner-local even when a packet is suppressed.
_obj setVariable [_name, _value, false];

private _counting = missionNamespace getVariable ["ACME_net_count", false];
if (!_publish) exitWith {
    if (_counting) then {
        private _saved = missionNamespace getVariable ["ACME_net_saved", createHashMap];
        _saved set [_name, (_saved getOrDefault [_name, 0]) + 1];
        missionNamespace setVariable ["ACME_net_saved", _saved];
    };
};

_obj setVariable [_name, _value, true];
_cache set [_key, [_value, _now]];
_obj setVariable ["ACME_net_approxCache", _cache, false];
// Share the last-publication fingerprint with the exact helper. A caller may update its local value before
// requesting an exact reset; the exact helper must not mistake its own older packet for the current one.
private _exact = _obj getVariable ["ACME_net_scalarCache", createHashMap];
if !(_exact isEqualType createHashMap) then {_exact = createHashMap;};
if !((_obj getVariable ["ACME_net_cacheOwner", []]) isEqualTo _stamp) then {
    _exact = createHashMap;
    _obj setVariable ["ACME_net_cacheOwner", _stamp, false];
};
_exact set [_key, ["SCALAR", _value]];
_obj setVariable ["ACME_net_scalarCache", _exact, false];
if (_counting) then {
    private _sent = missionNamespace getVariable ["ACME_net_sent", createHashMap];
    _sent set [_name, (_sent getOrDefault [_name, 0]) + 1];
    missionNamespace setVariable ["ACME_net_sent", _sent];
};
