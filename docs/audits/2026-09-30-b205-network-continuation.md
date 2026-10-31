# Stable 1.2.4.1 B205 network continuation

Base: `133d8bdd2ddefb92990c505ff19af7643d36e694` (B204, main).
Debug identity: `1.2.4.1 | B205 | NA5-B205-1.2.4.1-stable`.

## Corrections

- Exact and approximate scalar publishers now share their last transmitted value. An exact reset can no longer leave the approximate publisher suppressing a required update, or vice versa. Locality events invalidate snapshot and native-state publication caches, including a transfer away and back to the same machine.
- Empty circulation/TBI resets publish immediately even when the previous map was neutral. Infusion clamp, drop-set, entry and dose-revision changes publish immediately; ordinary changing volumes/rates retain their bounded snapshots.
- Infusion drive additions and completions share a one-second publication budget. Owner-local mass/rate integration is unchanged. Manual bolus additions and completion remain immediate. One guarded trailing callback publishes the latest queue if the final short infusion sample retires the worker before its next snapshot.
- Native IV admission, drainage, reset and removal use the same publication cache. Local staging and a final nil clear invalidate its fingerprint.
- Thoracostomy prep is merged by the patient owner instead of replacing another provider's work from a stale replica. Duplicate packets do not bump the revision. Applied prep survives closing, tool changes and side changes; pending local points survive delayed replication. Reset epochs reject stale work. The first owner-confirmed rib target wins; a viewer sends one pending proposal and cannot finish palpation against an unconfirmed target.
- Closing laryngoscopy flushes the final existing-tube depth adjustment, including movements below the render threshold. Clinical epoch and existing tube insertion time prevent the new close packet from affecting a reset, extubated or replaced tube. This does not redesign every existing airway transaction.
- Dead casualties leave the ventilator's 10 Hz sound registry after cleanup, including death during startup/shutdown before a source exists.
- Head-elevation cleanup uses the existing deferred global mass-restoration helper. It preserves the saved original mass until restoration executes, and respects a competing moving animation lease.
- The B204 audit's incorrectly escaped patterns were replaced with existing source-token scanning. Fixtures prove real broadcasts/world scans are detected and comments/ordinary strings are ignored. CI now runs the execution regressions on pull requests as well as the main audit.

No drug dose, kinetics, flow formula, consciousness threshold or public version change is included.

## Validation

- 198 focused checks passed, including actual-source SQF execution and current version invariants.
- The 74-check network/ownership gate passed; the native-state audit reported zero direct Extended writes across all four native domains.
- HEMTT 1.22.0 `check` and `release --no-bin --no-archive` passed: 14 PBOs, 14 signatures and one key. No source errors/warnings; seven pre-existing style-help diagnostics remain. The unavailable wiki refresh used HEMTT's bundled command metadata.
- Full baseline/candidate regression runs used SQF-VM v2026.04.03-ed9f5f5 and pytest 9.0.2. The suite remains failing overall. Actual JUnit testcase records compare as follows:

| Outcome | B204 | B205 |
| --- | ---: | ---: |
| Passed | 4,879 | 4,973 |
| Failed | 868 | 838 |
| Error | 47 | 47 |
| Skipped | 29 | 29 |

There are 64 new passing cases, 30 existing cases now passing, zero introduced failures/errors, zero missing cases and zero newly skipped cases. Existing observer/head-pose harnesses were reconciled with B204's interface guard and B202's coalesced collision requests; the 30 improvements do not represent 30 newly fixed gameplay bugs.

Four parameter IDs were stabilized after the broad run so the identity gate retains the original cases. The affected module's 31 tests passed on rerun, and those measured results replace only that module in the final comparison. No runtime source changed after the broad run. Counts use actual testcase records because nested JUnit header totals and pytest's subtest-inclusive console summary differ. See `2026-09-30-b205-network-results.json`.

The new execution tests run the checked-out SQF with explicit boundaries for native objects, UI, animation, clocks, scheduling and transport. They establish function-level publication counts and state transitions, not delivered packets, measured bandwidth, server FPS or rendered behavior. Selected new cases were also run against the original B204 source and reproduced their intended failures.

## Build and deployment

Use the B205 branch at `F:\ACM-Extended`, then run:

```powershell
.\tools\Deploy-ACME-B205.ps1
```

The script checks the B205 identity and a clean tracked checkout, runs `hemtt check` and `hemtt release`, verifies all 14 PBOs/signatures and the signing key, then copies `.hemttout\release` into the installed mod folder. Its default destination is the existing repository/mod folder. `-ModPath` and `-ServerKeysPath` accept existing explicit destinations.

Install the same release on server and clients, restart the mission, and verify the full B205 debug identity on both. Windows asset binarization on the release machine and live dedicated-server behavior still require validation.

## Dedicated-server checks

1. Repeat the affected multiplayer workload for 10–15 minutes, comparing the network counters and RPT with B204 under the same patient/player load. Counters record publication requests, not bytes.
2. Run multiple infusions, change clamps and add doses, then finish/remove them. Watch remote displays and transfer patient ownership, including away/back, without duplicating medication delivery.
3. Paint chest prep with two providers before either receives the other's update. Close mid-stroke, switch tools/sides, and full-heal/reset. Confirm both trails survive and stale work stays cleared.
4. Make a small ETT migration adjustment and immediately close; inspect from another client. Repeat with extubation/reset while the request is delayed.
5. Observe head elevation/lowering and cancellation from another client; confirm normal collision/mass after the pose settles. Test death during ventilator startup and shutdown, then configure a living casualty again.

The broader historical test backlog is not cleared by this patch. A passing focused suite or source build is not an all-modpack or lag-free certification.
