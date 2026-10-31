# B303: collect registered medical litter

Candidate 1.2.4.1 / B303, multiplayer protocol 2. Baseline B302 `d5c8293a2f92f33f53bb4d1ad985711776a3b9c1`. PR #31 remains draft and unmerged.

## Player interaction

ACE self-interaction > Equipment > Collect medical litter is available to any conscious, unoccupied player on foot who is not prone or already performing another provider action. It has no medic-role, faction, litter-creator or patient-ownership restriction. One short pickup collects up to 25 registered pieces within 2 metres; another use can collect any remaining pieces. No reusable supplies or inventory trash-bag item are created.

The server selects from the exact live `ace_medical_treatment_litterObjects` registry. The client supplies no target objects, classes, scan results or positions. Selection also requires a live simple object within true 3D reach. Objects that merely look like bandages or trash, dropped equipment, usable supplies, corpses and unregistered world objects are not eligible. There is no world-object scan or idle collection worker.

## Animation and cancellation

After a valid server grant, the provider uses the existing one-shot weapon preflight, kneels and performs the exact provider Putdown entry and return used for both Semi-Fowler's elevation and lowering:

- `AmovPknlMstpSnonWnonDnon`
- `AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown`
- `AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon`

Completion requires observed entry and return states, followed by the neutral kneel. The native intermediate Putdown state is also handled. The finite sequence never substitutes an elapsed timeout for successful animation. It respects the existing intervention-animation setting; with presentation disabled it retains the finite collection time without forcing a pose.

Movement/input, Escape, prone stance, a newer treatment, unconsciousness, death, entering a vehicle, controlled-unit/locality change or the finite deadline cancels. No objects disappear on cancellation. Each active pickup owns only its own short-lived worker and key handler; despawn and stale callbacks retire those exact handles. A locality/pose/treatment fingerprint prevents a late pickup from releasing a newer action's stance. No unit loadout, animation-speed coefficient, patient pose or Semi-Fowler's function is changed.

## Server authority and registry ownership

The server issues a private request-bound capability to the provider's current owner. Commit rechecks that owner, exact request/capability, bounded real-time lease, minimum action time, current life/vehicle state, movement from origin and current registry membership/distance. Server time checks use elapsed `diag_tickTime`, independently of mission-time acceleration. Invalid authoritative completion releases the pending client request rather than leaving it locked until timeout.

Concurrent collectors can target the same litter. A private pending-delete set and per-provider completion records ensure each object is removed/counted once even before the engine turns a deleted handle null. Replay, cancellation, stale grants, expired requests, auto-cleanup, later spawns and changed locality cannot broaden the selected set or duplicate removal. Duplicate grants never replay the animation.

ACE retains ownership of its registry, timestamps, count limits and automatic-cleanup scheduler. ACME does not rewrite that native array or its cleanup flag. Deleted handles become null and ACE retires their slots through its normal lifetime/count path. Remaining entries and creation ages are preserved. The implementation was checked against the supplied ACE source's `fnc_createLitterServer.sqf`, `fnc_litterCleanupLoop.sqf` and litter classes; those source files are not overridden.

## Validation and limits

50 production-code SQF-VM cases cover registered-only deletion, malformed/unregistered/distant/non-simple objects, true 3D reach, ordinary players and overlapping collectors, duplicate requests/commits, cancellation, expiry, owner and capability mismatch, native auto-cleanup, new litter, batch limits, pending engine deletes, animation ordering and observed-state completion, holster readiness, all interruption paths, disabled presentation, despawn and stale callbacks, stance-owner handoff and idempotent self-action registration without idle polling.

201 existing provider/Semi-Fowler's/prone/pressure/chest-exit regressions pass. The root suite has 690 passing cases and the unchanged React suite has 45. Strict HEMTT checks 2,150 SQFs, 15 stringtables and 22 configs; native-owner audit reports zero direct native-state writes. Current GUI/React sources, medical art, patient-positioning functions, treatment/flow calculations and inventory custody remain byte-exact to B302. Signed package verification covers all 19 addons, B303 stamps, exact packed runtime sources, compiled function registrations and exact source-patch tree reconstruction.

Arma cannot run in this container. Actual animation graph playback, self-action placement, simple-object deletion propagation, JIP and low-FPS dedicated-server acceptance still require in-game verification. Container packages omit Arma Tools model/animation binarization; the Windows helper runs native HEMTT release. Fully close Arma before deploying the complete matching build/key on server, clients and HCs. Retain the persistence profile/adapter and avoid duplicate standalone DD1380. B302 UI changes remain intact; no UI restyling or new medical screen is introduced.
