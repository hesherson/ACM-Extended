# ACM Extended B257 — dedicated-server acceptance gate

**Candidate:** Stable 1.2.4.1 / B257, network audit `NA8-B257-1.2.4.1-candidate`.
**Status:** Candidate only. CI success is necessary but **does not** substitute for a live dedicated-server multiplayer test.

## Setup

- Use the same ACME B257 client/server/headless-client PBOs. Record server and both clients' debug-overlay batch and startup RPT stamps.
- First run with CBA, ACE, and ACME on a dedicated server (2 clients, 1 unconscious AI casualty and 1 player casualty). Repeat essential tests with a headless client and then Antistasi Ultimate.
- Keep dedicated-server, headless-client and both player RPT files. Note build, owner location, treatment and any script errors at the instant of failure.
- Verify default ACME medical menus and overlay before beginning. Avoid using saved patients or legacy sessions from an older build as a clean baseline.

## Mandatory live matrix

| Case | Procedure | Acceptance criterion |
| --- | --- | --- |
| 01 — Direct Pressure | Start on arm/head/body; move, pause 2 s and resume; cancel; retest with another provider | Only one site holder, correct clinical marker and clot effects, no stuck pose or blocked restart |
| 02 — DP network race | Two players request the same site at nearly the same instant; one disconnects during a pending ACK; the other retries | One winning claim; stale ACK cannot take or release the new holder's claim |
| 03 — DP locality | Move an AI provider between server/HC while pressure is held; transfer away and back rapidly | Original claim retires, old handlers and stance are released, a new provider can claim immediately |
| 04 — CPR | Start/pause/resume/stop CPR, including during preparation and with a second nearby provider | Single valid compression lease, no AnimDone re-entry after stop, normal animation speed restored |
| 05 — CPR locality | Move a medic AI to/from HC while CPR is active; interrupt during entry and after compression starts | Old client neither restarts CPR nor writes to the new owner's animation |
| 06 — CPR ↔ BVM | Alternate CPR and BVM at least 10 times, including paused BVM and a second provider assisting | No simultaneous same-role leases; valid independent CPR + BVM providers coexist; swap cannot resurrect obsolete treatment |
| 07 — BVM handoff race | Leave BVM for CPR, then start another action or move provider ownership before the delayed swap | Old delayed callback cannot start CPR; valid same-owner swap still works |
| 08 — Patient movement | Load a casualty into a vehicle, carry, unload, semi-Fowler lower and return | Treatments terminate or persist by documented rules, no permanent pose/animation/collision locks |
| 09 — Vehicle care | With medic and patient in the same vehicle, exercise narc box, auscultation, chest inspection/seal, IV and ventilator | Each supported action opens, finishes and releases correctly, without false range or animation blocks |
| 10 — Chest access | Repeated carrier off/on, front/back roll, seal mini-game, thoracostomy, recovery-position interruption | No stuck provider pose or procedure lease; correct state after closing or timing out |
| 11 — Network idle | Log a healthy, untreated AI group for several minutes; then begin real circulation/infusion/coagulation cases | No unnecessary healthy-idle state broadcast; newly active cases still enroll promptly |
| 12 — UI responsiveness | Repeat transfusion, AED, breathing, pressure and ventilator actions on remote casualties | No dead controls, stale modal sessions, or sustained button delay |
| 13 — Patient death | Repeat DP/CPR/BVM and chest work on a dead casualty when the action is supported | Appropriate corpses remain accessible; no lingering handler/lease or spurious live physiology |

## Exit criteria

1. Full B257 GitHub CI completes with **success** and no skipped/newly failing current tests.
2. No script error, leaked PFH/input handler, stuck global ContinuousAction gate, duplicate claim, phantom treatment, or unexpected animation-speed change in the matrix above.
3. A repeat run after disconnect/respawn/HC migration remains clean; no older treatment reappears.
4. Performance/network comparison must be based on RPT or measured instrumentation, not inference from source alone.
5. After every fix or CI failure, rebuild and rerun at least the affected matrix case plus smoke tests 01, 04, 06, 08 and 09.

**Go/no-go:** An untested case or any failing criterion blocks public-release approval. CI green only permits controlled dedicated-server acceptance. Keep stable public version at 1.2.4.1 until acceptance is complete.
