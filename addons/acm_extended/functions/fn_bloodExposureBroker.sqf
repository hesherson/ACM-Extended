/* B287: synchronize ordinary inventory blood before moving it into/out of a cooler.
 * Seed delivery is durable across inventory replication lag. The client supplies
 * its post-add class count; the server acknowledges only after a physical row
 * can inherit the preserved exposure. Replays never seed another replacement.
 */
params [["_mode", "read", [""]], "_holder", ["_class", "", [""]], ["_request", [], [[]]],
    ["_warm", 0, [0]], ["_sampled", serverTime, [0]], ["_expected", 1, [0]]];
if (!isServer || {isNull _holder} || {count _request != 2}
    || {!(_mode in ["read", "seed"])} || {([_class] call ACME_fnc_coolerBagVolume) <= 0}) exitWith {};
_request params ["_machine", "_sequence"];
if !(_machine isEqualType 0 && {_sequence isEqualType 0}
    && {finite _sequence} && {_sequence >= 1} && {_sequence == floor _sequence}) exitWith {};
private _now = serverTime;
if (!finite _warm || {_warm < 0} || {!finite _sampled} || {_sampled > _now}
    || {!finite _expected} || {_expected < 1} || {_expected != floor _expected}) exitWith {};
private _authorized = _machine == owner _holder;
if (!_authorized && {_mode == "seed"}) then {
    private _entry = [_request, _class, _warm, _sampled, _expected];
    _authorized = _entry in (_holder getVariable ["ACME_bloodExposurePending", []]);
    if (!_authorized) then {
        private _claims = _holder getVariable ["ACME_bloodSeedPending", createHashMap];
        if (_claims isEqualType createHashMap) then {
            {
                private _claim = _claims get _x;
                if (_claim isEqualType [] && {count _claim >= 6}
                    && {(_claim # 0) == _class} && {(_claim # 1) isEqualTo _request}
                    && {(_claim # 2) == _warm} && {(_claim # 3) == _sampled}
                    && {(_claim # 5) == _expected}) exitWith {_authorized = true;};
            } forEach keys _claims;
        };
    };
};
if (!_authorized) exitWith {};
private _sync = {
    // Many loadout/UI callbacks can request the same inventory view in one
    // frame. One world reconciliation suffices; queued seeds wait for the next
    // retry if their native placement becomes visible later in that frame.
    private _fresh = false;
    if ((missionNamespace getVariable ["ACME_ccBrokerFrame", -1]) != diag_frameNo) then {
        _fresh = true;
        missionNamespace setVariable ["ACME_ccBrokerFrame", diag_frameNo];
        // The generic pass releases every deployed source before acquiring
        // receiver cargo, including when invoked by a non-broker loadout nudge.
        [0] call ACME_fnc_bloodColdChainTick;
    };
    _fresh
};
private _key = netId _holder;
private _machineKey = format ["%1:%2", _key, _machine];
private _result = -1;
private _defer = false;
if (_mode == "seed") then {
    private _tokens = _holder getVariable ["ACME_bloodExposureSeedTokens", createHashMap];
    private _history = _tokens getOrDefault [_machineKey, [0, []]];
    private _seen = _history # 1;
    private _receipt = _seen findIf {(_x # 0) == _sequence};
    if (_sequence <= (_history # 0)) then {_result = _warm;}
    else {
        if (_receipt >= 0) then {_result = (_seen # _receipt) # 2;}
        else {
            private _pending = _holder getVariable ["ACME_bloodExposurePending", []];
            private _entry = [_request, _class, _warm, _sampled, _expected];
            private _existing = _pending findIf {(_x # 0) isEqualTo _request};
            if (_existing < 0 && {count _pending < 128}) then {
                _pending pushBack _entry;
                _holder setVariable ["ACME_bloodExposurePending", _pending];
            };
            // A repeated request is immutable; altered bodies cannot replace
            // the already queued source exposure.
            if (_existing < 0 || {(_pending # _existing) isEqualTo _entry}) then {
                call _sync;
                _tokens = _holder getVariable ["ACME_bloodExposureSeedTokens", createHashMap];
                _history = _tokens getOrDefault [_machineKey, [0, []]];
                _seen = _history # 1;
                _receipt = _seen findIf {(_x # 0) == _sequence};
                if (_receipt >= 0) then {_result = (_seen # _receipt) # 2;};
            };
        };
    };
} else {
    private _fresh = call _sync;
    private _store = missionNamespace getVariable ["ACME_ccByHolder", createHashMap];
    private _record = _store getOrDefault [_key, [[], []]];
    private _trackedCount = {(_x # 0) == _class} count (_record # 0);
    private _liveCount = {_x == _class} count ((uniformItems _holder) + (vestItems _holder) + (backpackItems _holder));
    if (!_fresh && {_trackedCount != _liveCount}) then {
        // A later inventory event in this frame invalidated the cached view.
        // Reconcile next frame instead of returning a fresh-zero fallback or
        // performing another world scan in the same frame.
        _defer = true;
        private _deferred = _holder getVariable ["ACME_bloodExposureDeferred", []];
        if !(_request in _deferred) then {
            _deferred pushBack +_request;
            _holder setVariable ["ACME_bloodExposureDeferred", _deferred];
            [{
                params ["_holder", "_request", "_retry"];
                if (isNull _holder) exitWith {};
                private _deferred = _holder getVariable ["ACME_bloodExposureDeferred", []];
                _deferred = _deferred select {!(_x isEqualTo _request)};
                _holder setVariable ["ACME_bloodExposureDeferred", _deferred];
                _retry call ACME_fnc_bloodExposureBroker;
            }, [_holder, +_request, +_this]] call CBA_fnc_execNextFrame;
        };
    } else {
        {
            if ((_x # 0) == _class) then {_result = _result max (_x # 2);};
        } forEach (_record # 0);
    };
};
if (_defer) exitWith {};
["ACME_bloodExposureReply", [_holder, _request, _class, _result, _now], _holder] call CBA_fnc_targetEvent;
