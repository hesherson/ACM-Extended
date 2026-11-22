/* Reuse ACME's bounded capture on the server. The mission writes the report once. */
params [["_seconds", 120, [0]]];
if (!isServer || {isNil "ACME_fnc_performanceDiagnostics"}
    || {missionNamespace getVariable ["ACMEQA_captureActive", false]}
    || {missionNamespace getVariable ["ACME_performance_enabled", false]}) exitWith {false};
ACMEQA_captureActive = true;
["start", _seconds] call ACME_fnc_performanceDiagnostics;
diag_log format ["[ACME QA] PERF_START run=%1 seconds=%2 workload=%3", ACMEQA_run, _seconds, ACMEQA_workload];
[_seconds] spawn {
    params ["_seconds"];
    sleep (_seconds + 1);
    private _report = ["stop"] call ACME_fnc_performanceDiagnostics;
    private _samples = _report getOrDefault ["samples", []];
    _report deleteAt "samples";
    diag_log format ["[ACME QA] PERF_META run=%1 workload=%2 buckets=%3 report=%4", ACMEQA_run, ACMEQA_workload, count _samples, _report];
    {diag_log format ["[ACME QA] PERF_SAMPLE run=%1 %2", ACMEQA_run, _x];} forEach _samples;
    ACMEQA_captureActive = false;
};
true
