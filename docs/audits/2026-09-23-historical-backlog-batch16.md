# Historical backlog batch 16: roll ownership and immediate cancellation

Parent: `bc79769a1c83d1e027deb4d2e7cf8f9ed54f7441`. This batch changes tests, one reviewed test-snapshot digest and
the audit index. All runtime functions and the animation configuration are unchanged.

## Historical identities resolved

H156, H181, H189, H366 and H389 retain their identities. Current provider roll
work uses the shared empty-hand medic4 controller with the existing **2.2-second**
authored hold. The **2.5-second** value in rollProviderStart is a fail-safe margin,
not the current work duration. Normal entry uses priority one; an explicit
mid-roll Cancel intentionally uses immediate engine control release. Retired
medic2/rifle-state mappings, forced reassertion loops and a blanket ban on that
explicit cancellation must not be restored to satisfy obsolete source strings.
Still-applicable weapon-disabling and crouch-connection assertions are retained.

When presentation acquisition succeeds, a physical flip waits for the provider's
observed medic4 work state and dispatches once. Acquisition failure has an
intentional one-shot physical fallback for an eligible casualty. A noneligible
casualty receives only a virtual view change. The fallback completion checks the
session and pending token before changing a reopened workspace.

## Execution and results

The 33 new cases execute actual roll-provider start/cancel, shared pose
start/stop, patient-roll cancel, chest Flip and FlipTick. Tests cover crouch/standing/
prone preparation, source-mismatched cancellation, duplicate cancellation, old
worker/timer delivery after replacement, explicit supine remote routing, awake/
unconscious/dead/seated patient cleanup, prep/observed-state gating, one-time
dispatch and scoped fallback completion. Flip presentation acquisition is a
boundary fixture there; its actual provider implementation executes separately.

Focused result including the five selected historical identities and the root
preservation tests: **115 passed**. The retained weapon-property assertions were
also retested separately after review: **1 passed**. No new skip or expected-failure
is introduced. Engine objects, animation observations, UI controls, network calls
and scheduling remain explicit fixtures; this is not a live multiplayer test.

The independent root-level phase-150 collection failure is corrected by requiring
`[_patient,"front"] call ACME_fnc_patientRollCancel` rather than the obsolete
one-argument call. The production call is unchanged. Its single preservation
digest is explicitly updated; other protected values remain untouched in this batch.
This collection repair is not counted as one of the five addon failures resolved.

The original unresolved source-contract index decreases from 143 to **138**.
Combined suite results and release limitations are in the Batch 17 report. No
runtime rebuild is required for this batch alone.
