/* B286 local, opt-in aggregate only. No actor data, logging or network traffic.
 * Named timings are inclusive; nested handleUnitVitalsEvent is part of handleUnitVitals.
 */
if !(missionNamespace getVariable ["ACME_performance_enabled", false]) exitWith {false};
params [["_name", "", [""]], ["_milliseconds", 0, [0]], ["_frameMilliseconds", -1, [0]], ["_generation", -1, [0]]];
private _state = missionNamespace getVariable ["ACME_performance_state", createHashMap];
if (_generation >= 0 && {_generation != (_state getOrDefault ["generation", -2])}) exitWith {false};
private _now = diag_tickTime;
if (_now >= (_state get "deadline")) exitWith {
    ["stop"] call ACME_fnc_performanceDiagnostics;
    false
};
private _second = floor ((_now - (_state get "startedAt")) max 0);
private _bucket = _state get "bucket";
if (_second != (_bucket select 0)) then {
    ["advance", _second] call ACME_fnc_performanceDiagnostics;
    _bucket = _state get "bucket";
};
if (_frameMilliseconds >= 0 && {finite _frameMilliseconds}) then {
    _bucket set [1, (_bucket select 1) + 1];
    _bucket set [2, (_bucket select 2) + _frameMilliseconds];
    _bucket set [3, (_bucket select 3) max _frameMilliseconds];
};
if (_name != "" && {_name in ["ownerLifecycle", "idlePhysDiscovery", "preoxygenationTick", "coagulationTick", "flightTick", "circHandle", "handleUnitVitals", "handleUnitVitalsEvent"]}
    && {finite _milliseconds} && {_milliseconds >= 0}) then {
    private _timings = _bucket select 4;
    private _row = _timings getOrDefault [_name, [0, 0, 0]];
    _timings set [_name, [(_row select 0) + 1, (_row select 1) + _milliseconds, (_row select 2) max _milliseconds]];
};
true
