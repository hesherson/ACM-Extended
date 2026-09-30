// B204 network publication gate.
// Usage: [_object, _variableName, _value] call ACME_fnc_setVarNet.
//
// Owner-local callers suppress a publication only after THIS helper has already published the same value.
// Scalars and identity types are compared directly. Arrays and HashMaps use a serialized fingerprint so mutable
// by-reference containers cannot make the cache silently mutate underneath us. Non-owner writes are never
// suppressed here: those call sites must be owner-dispatched or explicitly rate-limited by their subsystem.
//
// Counters measure helper publication requests, not bytes or delivery acknowledgements.
params [["_obj", objNull, [objNull]], ["_name", "", [""]], "_value"];
if (isNull _obj || {_name isEqualTo ""}) exitWith {};

private _counting = missionNamespace getVariable ["ACME_net_count", false];
if (_counting && {isNil "ACME_net_since"}) then { ACME_net_since = diag_tickTime; };

private _hasValue = !isNil "_value";
private _type = if (_hasValue) then {typeName _value} else {"NIL"};
private _cacheKey = toLowerANSI _name;
private _cache = _obj getVariable ["ACME_net_scalarCache", createHashMap];
if !(_cache isEqualType createHashMap) then {_cache = createHashMap;};
private _ownerStamp = [owner _obj, local _obj];
if !((_obj getVariable ["ACME_net_cacheOwner", []]) isEqualTo _ownerStamp) then {
    _cache = createHashMap;
    _obj setVariable ["ACME_net_scalarCache", _cache, false];
    _obj setVariable ["ACME_net_cacheOwner", _ownerStamp, false];
};

// Type-tag the cache value. This prevents a real string such as "<ACME:NIL>" from colliding with the
// sentinel for an undefined variable, and prevents cross-type values with the same textual form from suppressing
// a required publication.
private _fingerprint = switch (_type) do {
    case "ARRAY";
    case "HASHMAP": {[_type, str _value]};
    case "NIL": {["NIL"]};
    default {[_type, _value]};
};

private _same = false;
if (local _obj) then {
    private _published = _cache get _cacheKey;
    if (!isNil "_published") then {
        if (!_hasValue) then {
            _same = isNil {_obj getVariable _name} && {_published isEqualTo _fingerprint};
        } else {
            private _old = _obj getVariable _name;
            private _localSame = if (_type in ["ARRAY", "HASHMAP"]) then {
                !isNil "_old" && {[_type, str _old] isEqualTo _fingerprint}
            } else {
                !isNil "_old" && {_old isEqualTo _value}
            };
            _same = _localSame && {_published isEqualTo _fingerprint};
        };
    };
};

if (_same) exitWith {
    if (_counting) then {
        private _m = missionNamespace getVariable ["ACME_net_saved", createHashMap];
        _m set [_name, (_m getOrDefault [_name, 0]) + 1];
        missionNamespace setVariable ["ACME_net_saved", _m];
    };
};

if (_counting) then {
    private _m = missionNamespace getVariable ["ACME_net_sent", createHashMap];
    _m set [_name, (_m getOrDefault [_name, 0]) + 1];
    missionNamespace setVariable ["ACME_net_sent", _m];
};

if (local _obj) then {
    _cache set [_cacheKey, _fingerprint];
    _obj setVariable ["ACME_net_scalarCache", _cache, false];
    // Exact resets and approximate physiology can write the same field. Keep the approximate baseline at
    // the value actually sent, otherwise it can suppress the first update after a reset using an older packet.
    private _approx = _obj getVariable ["ACME_net_approxCache", createHashMap];
    if !(_approx isEqualType createHashMap) then {_approx = createHashMap;};
    if !((_obj getVariable ["ACME_net_approxOwner", []]) isEqualTo _ownerStamp) then {
        _approx = createHashMap;
        _obj setVariable ["ACME_net_approxOwner", _ownerStamp, false];
    };
    if (_type == "SCALAR") then {
        _approx set [_cacheKey, [_value, diag_tickTime]];
    } else {
        _approx deleteAt _cacheKey;
    };
    _obj setVariable ["ACME_net_approxCache", _approx, false];
};

if (!_hasValue) exitWith {_obj setVariable [_name, nil, true];};
_obj setVariable [_name, _value, true];
