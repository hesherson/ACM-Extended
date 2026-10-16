/* B286 bounded machine-local capture. Off by default; only start installs an EachFrame observer.
 * Samples: [elapsed second, frame count, mean frame ms, max frame ms,
 *           [[name,calls,total ms,max ms],...], [[registry,count],...]].
 * This is elapsed handler time plus observed frame deltas, not native engine attribution or FPS proof.
 */
params [["_operation", "report", [""]], ["_limit", 120, [0]]];
private _state = missionNamespace getVariable ["ACME_performance_state", createHashMap];
private _active = missionNamespace getVariable ["ACME_performance_enabled", false];
private _now = diag_tickTime;
private _snapshot = {
    private _bucket = _state get "bucket";
    private _timings = _bucket select 4;
    private _names = keys _timings;
    _names sort true;
    private _rows = _names apply {[_x] + (_timings get _x)};
    private _registries = ["ACME_clinical_ownedUnits", "ACME_clinical_activePatients", "ACME_aiProtection_candidates",
        "ACME_circ_activePatients", "ACME_preox_activePatients", "ACME_coag_activePatients", "ACME_flight_activePatients"] apply {
        private _list = missionNamespace getVariable [_x, []];
        [_x, if (_list isEqualType []) then {count _list} else {-1}]
    };
    [_bucket select 0, _bucket select 1, if ((_bucket select 1) > 0) then {(_bucket select 2) / (_bucket select 1)} else {0},
        _bucket select 3, _rows, _registries]
};
private _flush = {
    private _bucket = _state get "bucket";
    if ((_bucket select 1) > 0 || {count (_bucket select 4) > 0}) then {
        private _samples = _state get "samples";
        if (count _samples < 600) then {_samples pushBack (call _snapshot);};
    };
};
switch (toLowerANSI _operation) do {
    case "start": {
        if (_active) exitWith {["report"] call ACME_fnc_performanceDiagnostics};
        if !(finite _limit) then {_limit = 120;};
        _limit = (floor _limit max 1) min 600;
        private _generation = 1 + (_state getOrDefault ["generation", 0]);
        private _role = if (isServer) then {if (hasInterface) then {"listen_server"} else {"dedicated_server"}}
            else {if (hasInterface) then {"player_client"} else {"headless_client"}};
        _state = createHashMapFromArray [["generation", _generation], ["startedAt", _now], ["deadline", _now + _limit],
            ["limit", _limit], ["stoppedAt", -1], ["samples", []], ["bucket", [0, 0, 0, 0, createHashMap]],
            ["machine", [_role, clientOwner, missionNamespace getVariable ["ACME_buildBatch", "unknown"]]]];
        missionNamespace setVariable ["ACME_performance_state", _state];
        missionNamespace setVariable ["ACME_performance_enabled", true];
        // The generation is embedded in this observer so a queued old callback cannot sample a restarted capture.
        private _code = compile format ["['',0,diag_deltaTime * 1000,%1] call ACME_fnc_performanceRecord;", _generation];
        _state set ["handle", addMissionEventHandler ["EachFrame", _code]];
        ["report"] call ACME_fnc_performanceDiagnostics
    };
    case "advance": {
        if (!_active) exitWith {false};
        call _flush;
        _state set ["bucket", [_limit, 0, 0, 0, createHashMap]];
        true
    };
    case "stop": {
        if (_active) then {
            missionNamespace setVariable ["ACME_performance_enabled", false];
            removeMissionEventHandler ["EachFrame", _state get "handle"];
            call _flush;
            _state set ["handle", -1];
            _state set ["stoppedAt", _now];
        };
        ["report"] call ACME_fnc_performanceDiagnostics
    };
    case "report": {
        // Return independent arrays: inspecting/editing a report must not mutate an active capture.
        private _samples = (_state getOrDefault ["samples", []]) apply {
            [_x select 0, _x select 1, _x select 2, _x select 3, (_x select 4) apply {+_x}, (_x select 5) apply {+_x}]
        };
        if (_active && {count _samples < 600}) then {
            private _bucket = _state get "bucket";
            if ((_bucket select 1) > 0 || {count (_bucket select 4) > 0}) then {_samples pushBack (call _snapshot);};
        };
        createHashMapFromArray [["active", _active], ["limitSeconds", _state getOrDefault ["limit", 120]],
            ["startedAt", _state getOrDefault ["startedAt", -1]], ["stoppedAt", _state getOrDefault ["stoppedAt", -1]],
            ["machine", +(_state getOrDefault ["machine", []])], ["samples", _samples],
            ["meaning", "local inclusive elapsed handler times and observed frame deltas; not engine attribution or measured FPS improvement"]]
    };
    default {createHashMapFromArray [["error", "Use start, stop or report"]]};
}
