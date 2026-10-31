# B207 dedicated multiplayer validation

Status: **live execution pending**. Automated SQF tests exercise claim ordering, callback lifetime, counters and diagnostic cleanup with simulated engine boundaries. They do not establish CBA delivery timing, rendered animations, vehicle compatibility, PhysX safety or a measured FPS improvement.

## Test environment

Use one dedicated server, two player clients (A and B), and one headless client (HC). Install the same complete B207 package on all four machines, with the same ACE/CBA versions and mission settings. Keep the public version at 1.2.4.1. Record the internal build, network protocol, mod list, mission revision, AI/casualty counts and each machine's role separately. Do not identify patients by player name or UID in the diagnostic record.

The mission should provide a repeatable injured adult casualty, a usable IV with a partially filled bag, plate carrier and no-carrier variants, a vehicle with accessible seats, and the mission's normal HC ownership-transfer facility. Include a server-owned AI casualty, an HC-owned AI casualty and a player casualty. Use the existing treatment/reset interfaces to exercise full-heal and respawn; direct variable clearing bypasses the lifecycle under test.

Use an isolated test session for version mismatch and deliberate network impairment. Apply latency/loss through the test network's transport controls; do not replace or wrap CBA functions, engine commands, treatment handlers or the diagnostic sampler to manufacture results. Record the impairment and its start/end times. A host-only session is a separate smoke test and does not replace dedicated validation.

## Bounded local capture

`ACME_fnc_networkDiagnostics` is off by default. It installs one machine-local 1-second PFH only after `start`, retains at most 120 samples by default (hard maximum 600), and removes the PFH at the limit or on `stop`. Sampling can be slower during a stalled frame; it never fabricates missing samples or catches up in bursts. It performs no world scan or network send. Stopping restores the prior `ACME_net_count` enabled/undefined state and preserves the existing counter maps.

Run on each player through **Local Exec**, separately:

```sqf
["start", 120] call ACME_fnc_networkDiagnostics;
```

Inspect the local report; this does not start or sample a session:

```sqf
["report"] call ACME_fnc_networkDiagnostics;
```

End early if needed:

```sqf
["stop"] call ACME_fnc_networkDiagnostics;
```

An explicit sample is accepted only during an active session and only when the 1-second interval is due:

```sqf
["sample"] call ACME_fnc_networkDiagnostics;
```

For a server/HC-owned AI provider, pass that known mission object locally when starting. `testMedic` below is a mission variable chosen by the test author; it is not searched or discovered by the sampler. A nonlocal provider is ignored. Default client sampling watches the local `ACE_player`; respawn/control switching requires stopping and starting a new capture for the new provider.

```sqf
["start", 120, testMedic] call ACME_fnc_networkDiagnostics;
```

To start one capture on every machine without a remote execution broadcast, put this temporary block in the **test mission's** `init.sqf`. Each machine executes its own block. The sampler and this bounded collector should be removed from the mission after validation. Run the ordinary gameplay scenarios while the capture is active.

```sqf
[] spawn {
    waitUntil {sleep 0.25; !isNil "ACME_fnc_networkDiagnostics" && {time > 1}};
    ["start", 120] call ACME_fnc_networkDiagnostics;
    waitUntil {sleep 1; !((["report"] call ACME_fnc_networkDiagnostics) get "active")};
    private _report = ["report"] call ACME_fnc_networkDiagnostics;
    private _samples = _report get "samples";
    _report deleteAt "samples";
    diag_log format ["ACME_B207_NET_DIAG_META %1", _report];
    {diag_log format ["ACME_B207_NET_DIAG_SAMPLE %1", _x];} forEach _samples;
};
```

The collector writes one RPT line per sample, avoiding one oversized line for the entire capture. For a later manually started window, export the current report on that same machine:

```sqf
private _report = ["report"] call ACME_fnc_networkDiagnostics;
private _samples = _report get "samples";
_report deleteAt "samples";
diag_log format ["ACME_B207_NET_DIAG_META %1", _report];
{diag_log format ["ACME_B207_NET_DIAG_SAMPLE %1", _x];} forEach _samples;
```

Player clients can also copy the complete bounded report:

```sqf
copyToClipboard str (["report"] call ACME_fnc_networkDiagnostics);
```

Retain all four RPTs and label captures by machine and scenario. On Windows, extract diagnostic lines from a saved RPT with:

```powershell
Select-String -Path '.\server.rpt' -Pattern 'ACME_B207_NET_DIAG_' |
    ForEach-Object { $_.Line } |
    Set-Content '.\server-B207-diagnostics.txt'
```

## Reading the samples

| Field | Meaning |
| --- | --- |
| `machine` | `[role, clientOwner, publicVersion, internalBuild, auditRevision]`; `clientOwner` identifies a machine, not a user. |
| `at`, `elapsed` | Local `diag_tickTime` timestamp and actual time since the preceding sample/start. Local uptime clocks are not cross-machine timestamps. |
| `fps`, `frameDelta` | Sampled `diag_fps` and `diag_deltaTime`; `-1` marks an invalid reading. These are not a full frame-time trace or proof of improvement. |
| `helperRequestDeltas` | Three `[delta, resetDetected]` pairs, ordered by report `counterOrder`: publication requests, suppressed requests, non-finite rejections. |
| `counterEnabled` | Whether the existing helper counters were enabled at that sample. An external change can create an incomplete observation window. |
| `registrySizes` | Counts of the listed existing machine-local registries; `-1` means the expected array was malformed. These are neither unique casualty counts nor world population. |
| `directPressure` | `[pending/active/idle/not_local, pendingAgeSeconds, activeFlag]`. Pending age uses the provider's local request clock; `-1` means no valid pending age. |
| `hangBag` | `[pending/renewing/active/idle/not_local, pendingAgeSeconds, requestSequence, acknowledgedSequence]`. Age uses `serverTime`, matching the Hang Bag request clock. |
| `compatibility` | `[localStatus, serverVerificationStatus, serverBuild, attempts, localIssueCount, issueCount, serverPeerCount]`. Full manifests/issues remain in the existing compatibility diagnostic variables. |

**The helper counters are not wire statistics.** They omit raw `setVariable` publications, unrelated CBA events, engine replication, `remoteExec`, retransmissions, bytes and delivery acknowledgements. A reset marker means the interval cannot support a continuous rate comparison; the delta includes only increases/new values observable after that reset. Do not sum the helper counts and call the result packets saved.

The sampler does not reset counters or capture patient names, UIDs, object references, claim tokens, inventory, coordinates or clinical values. Stop it before restarting a workload window, export that report, then start the next window. Starting while already active intentionally leaves the current capture unchanged.

## Scenario matrix

Run the baseline and stressed cases with both clients watching the same casualty. Repeat owner-sensitive cases for server, HC and player ownership. Record action outcome, visible behavior, capture label, compatibility status and any RPT errors. Do not mark a row passed from helper counts alone.

| Case | Procedure | Expected behavior and evidence |
| --- | --- | --- |
| Matched installation | Join all four B207 machines; inspect compatibility locally and on server. | Local manifests and server verification settle to `ok`; no recurring negotiation loop. The server tracks connected peers without publishing the diagnostic maps. |
| Deliberate mismatch | In the isolated session, replace one participant with the prior build or an intentionally incomplete test package; reconnect, then restore B207. | Compatibility identifies the mismatch or unavailable handshake. No endless retry storm. An unavailable response is not evidence of compatibility. Confirm the corrected installation returns to `ok`. |
| DP simultaneous claim | A and B start Direct Pressure on the same patient/body part together; repeat rapidly. | Exactly one accepted provider per contested part; the other remains free to act. No doubled pose, duplicated activation, stale mouse hint or pressure left by a rejected provider. |
| DP cancel/restart | Start then cancel while the reply is pending; immediately restart. Repeat with controlled delay and release arriving ahead of the claim. | Cancelled claims cannot activate later. An old reply/release cannot cancel the replacement episode. Pending state clears, and the new claim can complete. |
| Hang Bag pending/renewal | Start, cancel during acquisition, restart, and continue beyond several renewals. Briefly impair and restore delivery; repeat with requests held beyond the admission window. | No prop/flow activation before owner acceptance. Old replies cannot extend/shorten a newer lease; expired acquisition/renewal fails cleanly. Sequence/ack progression is bounded, and a stopped holder leaves no flow multiplier or stuck pose. |
| Delayed admission | Delay claim traffic for less than and then more than the configured admission window; cancel before restoring transport. | Production admission rejects stale requests (current shared maximum is 5 seconds). Resuming transport must not resurrect the cancelled action. Capture actual recovery time; do not infer delivery from the sampler alone. |
| Reset race | Begin DP or Hang Bag, then use the mission's real full-heal/reset while request/reply is delayed. Start a fresh action after reset. | Old clinical epochs cannot reacquire the casualty or restore stale flow/pressure. Fresh requests use the reset state and remain usable. |
| Locality transfer | Move an AI casualty server → HC → server through the mission's normal owner transfer. Repeat with a pending claim, active hold and delayed cancellation. Disconnect/reconnect HC once. | Old-owner callbacks stop writing; new ownership resumes/cleans the correct episode. No duplicated physiology worker or permanently frozen provider. Registry counts should settle after recovery; exact neutral counts depend on the mission. |
| Shared continuous controller | Start/cancel BVM, thoracostomy and stethoscope work; switch controlled unit or lose provider locality while each is pending/active. Then start another action. | Matching controller cleanup releases only its actor/epoch. A stale controller cannot remove the new action's input handlers or hints. No blocked medical menu after cancellation. |
| Vehicle treatment | Put the provider/patient in the supported seat combinations and repeat Narc Box, auscultation, chest inspection, chest-seal UI and applicable medical work. Exercise dismount/cancel mid-entry. Try posture-dependent holds as well. | Supported procedures open/finish correctly. Actions requiring a ground posture decline or release cleanly rather than freezing animations or reserving the patient. No stale claim/pose after dismount or cancellation. |
| Semi-Fowler transitions | Raise/lower, rapidly cancel/restart, then transfer to carry, CPR or BVM. Repeat with and without a plate carrier, observed by both clients. | Correct handoff and eventual restored mass on all peers; no body launch, new impact injuries, stuck carry pose or full-mass collision during the moving frame. Live PhysX/animation observation is mandatory. |
| Ventilator death cleanup | Let a casualty die during startup, running and shutdown. Start ventilation on a fresh casualty afterward. | No lingering loop on a corpse; dead audio entries leave the hot registry; fresh casualties still register and play the normal sequence. |
| JIP/reconnect | B rejoins while A maintains a supported hold; repeat after A has cancelled that hold. | Current presentation/state appears on join; cancelled episodes do not replay from JIP storage. No replayed one-shot treatment sound. |
| Idle and recovery soak | Run 30–45 minutes with a reproducible casualty load; treat/reset/recover casualties, then leave them idle. Export bounded windows at start and approximately 10, 20 and 30 minutes. | No steadily growing inactive registry/claim ledger, stuck controller, repeated compatibility requests or recurring RPT error. Active gameplay can legitimately retain registry members. Every diagnostic window auto-stops at its cap. |

## Release evidence

For each case record `pending / pass / fail`, machine role, build/protocol, owner placement, impairment, action sequence and capture filenames. Attach a short video for animation/vehicle/PhysX issues and the complete affected RPT interval. Automated comparator output must separately identify new regressions and unchanged baseline failures; the historical full suite must not be described as all green.

If comparing performance, repeat the same mission workload, settings, population and capture duration on both builds. Report observed distributions/windows and instrumentation limits. These diagnostics alone do not establish bandwidth reduction or FPS gain. A runtime error, ownership leak or stuck intervention blocks declaring that scenario passed even when the counters look lower.

## Command and field references checked in this tree

- `fn_networkDiagnostics.sqf`: local sampler lifecycle, caps and output schema.
- `fn_setVarNet.sqf`, `fn_setVarNetApprox.sqf`, `fn_netReport.sqf`: counter meaning and exclusions.
- `fn_actionClaimValidate.sqf`, `fn_directPressureStart.sqf`, `fn_hangBagStart.sqf`, `fn_hangBagTick.sqf`: admission window and the distinct DP/Hang clocks.
- `fn_debugDumpToClipboard.sqf`: existing `diag_fps`, `diag_tickTime`, `diag_log` and clipboard diagnostic patterns.
- `fn_ventPanelTick.sqf`: existing `diag_deltaTime` use.
- B207 network compatibility runtime: the local `ACME_networkCompat*` status/manifest fields. The sampler reads status and aggregate issue/peer counts only.
