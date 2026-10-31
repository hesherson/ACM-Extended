# B286 unconscious-casualty performance capture

This capture is off by default. It observes the machine where it is started, stores at most 600 seconds of aggregate data, and removes its sole EachFrame observer on stop or the first frame at the deadline. It does not send data, write patient state, or log per frame. Leave diagnostic overlays and medical menus closed during the workload. Use the same complete build, CBA/ACE/RHS/CUP versions, medical settings, view settings and VR mission on each comparison.

The B285 baseline does not contain these helpers or named timing boundaries. For a frame comparison, copy the **unchanged** B286 `fn_performanceDiagnostics.sqf` and `fn_performanceRecord.sqf` into a `perf` folder in the baseline test mission. Load them locally on each participating machine from that mission's `init.sqf`:

```sqf
ACME_fnc_performanceRecord = compile preprocessFileLineNumbers "perf\fn_performanceRecord.sqf";
ACME_fnc_performanceDiagnostics = compile preprocessFileLineNumbers "perf\fn_performanceDiagnostics.sqf";
```

This adds the same bounded frame observer to the baseline without replacing medical functions, settings or schedules. Label these captures **B285 plus frame observer**: named timing rows will be absent, which means uninstrumented, not zero cost. B286 already includes the same helpers; label those captures **B286 plus named timings**. Compare frame metrics between these windows, and use B286 named timings to locate its current costs. Do not infer a baseline handler speedup from absent timing rows. Named timing overhead exists only on B286 in this setup, so also run both builds with the capture stopped; record that limitation with results.

Run locally on the machine that owns the tested AI:

```sqf
["start", 120] call ACME_fnc_performanceDiagnostics;
```

Use `report` to inspect, or `stop` to end early. Repeated start preserves the current capture. Start after stopping to begin an independent window. The duration is clamped to 1–600 seconds.

```sqf
private _report = ["stop"] call ACME_fnc_performanceDiagnostics;
copyToClipboard str _report;
```

For a server or headless client, export after capture using that machine's local debug execution or a temporary test-mission collector:

```sqf
private _report = ["report"] call ACME_fnc_performanceDiagnostics;
private _samples = _report get "samples";
_report deleteAt "samples";
diag_log format ["ACME_B286_PERF_META %1", _report];
{diag_log format ["ACME_B286_PERF_SAMPLE %1", _x];} forEach _samples;
```

Each sample is `[elapsedSecond, frameCount, meanFrameMS, maxFrameMS, timings, registrySizes]`. A timing row is `[name, calls, totalMS, maxMS]`. Rows cover the owner lifecycle, shared discovery, preoxygenation, coagulation, flight and circulation callbacks, accepted native vitals updates, and the synchronous native vitals event. `handleUnitVitals` includes `handleUnitVitalsEvent`; do not add those two totals. Calls spanning a second boundary are attributed to their completion second. Samples cover observed seconds only: a stalled scheduler creates no synthetic catch-up samples. Registry counts are sampled at bucket closure, and are not unique casualty counts. No patient identifiers, loadouts or clinical values are retained.

Keep total AI population **M fixed** throughout these windows, using identical modded loadouts and group layout:

1. Warm up the mission, then capture 120 seconds with 0 unconscious AI.
2. Shoot 1 AI unconscious through ordinary damage and capture a fresh 120-second window after the entry transition. Repeat with 5 and 10 unconscious AI. Record which owner runs each casualty, the total population M, build and capture label. Keep the same injury procedure and time after injury for both builds.
3. Capture the entry transition separately if a one-time downing hitch also occurs. Compare steady windows separately from damage/entry work.
4. Use the real medical full-heal/recovery path, then capture another window. Check that candidate and active registries settle, steady registration work stops, and AI protection, wake/get-up, treatment, loadouts and subsequent downing still behave correctly.
5. Repeat all windows on the baseline and candidate builds using the baseline helper-loading procedure above. Include a run with diagnostics stopped to estimate observer overhead. For multiplayer acceptance, repeat the affected ownership placements; host-only results establish host-only behavior.

Compare maximum frame times and named call/time distributions across identical windows. A 1 Hz FPS sample can miss a short hitch; this capture aggregates **every observed frame** in each bucket. It still cannot attribute uninstrumented engine work, prove wire traffic changes, or establish an FPS improvement from source or SQF-VM tests. Handler timings are inclusive elapsed time and instrumentation has a cost. Retain the original RPT intervals and record recovery or gameplay failures even when timings improve.
