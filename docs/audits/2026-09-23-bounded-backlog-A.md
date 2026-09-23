# Bounded continuation A: stethoscope provider exit generation

Baseline: `a488723656d8a370184df56209e55a17bc3901ef` (published batch 14). Separately named to avoid claiming integration of an unavailable, reportedly unpushed batches 15-17 package.

## Confirmed defect

Stethoscope Unload guarded continuous-action teardown but not its final `headElevMedicSeq` lower request. A superseded display could issue that provider exit over a newer continuous action. The captured continuous-action generation now gates the final request as well. Do not substitute the stethoscope pose epoch: an active Flip legitimately advances the roll pose within the same scope session.

Only that final guard changes runtime. Normal Putdown/inventory/crouch choreography, speed release, Flip cancellation, supine requests, carrier/dead-patient equipment routing, cursor, audio, medication and physiology code remain unchanged.

One existing stethoscope test assertion now expects the current four-argument `treatmentPoseStop` handoff (`true`) instead of requiring the obsolete generic exit. Its identity and other assertions remain. This is contract reconciliation, not a second gameplay defect.

## Validation

The complete actual Unload SQF executes in 25 new cases through the existing SQF-VM harness. Unchanged runtime: {"passed": 15, "failed": 10, "error": 0, "skipped": 0}. Candidate: all 25 pass. Cases include missing/stale/current generations, independent pose epochs, ordinary/active-Flip exit, absent/present carrier handoffs, live/dead patients, and provider locality, vehicle, consciousness, life and existing-sequence exclusions.

Focused before: {"passed": 110, "failed": 1, "error": 0, "skipped": 0}. Focused after: {"passed": 136, "failed": 0, "error": 0, "skipped": 0}. Existing chest-workspace and menu-lifecycle execution modules remain included. HEMTT check returns 0, retaining seven nonblocking suggestions. The preservation test module also passes after one explicitly reviewed digest update for the changed runtime file. No test body is removed and no skip/xfail added. Raw commands, outputs, JUnit identities and before/after manifests are retained in the Actions evidence artifact.

## Boundaries

These tests record calls across explicit engine fixtures. They do not render an Arma animation or certify real displays, network traffic, hearing gain, patient animation-lease release, carrier-lease identity or stale active-Flip cancellation elsewhere in Unload. The actual gear-restoration algorithm is unchanged; the new tests check its dispatch, not engine inventory behavior. No full historical addon suite was rerun. Do not replace its last published 175-failure aggregate with an inferred count. The 146-entry original source-contract index is unchanged. No stable-release approval.
