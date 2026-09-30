# Stable 1.2.4.1 B208 treatment and debug corrections

Base: `57120f93493df7122f86861325daae34ef70013d` (B207). Public version remains `1.2.4.1`.
Runtime identity: `B208 | NA8-B208-1.2.4.1-stable`.

## Reproduced causes

The supplied B207 screenshot shows a single-player session (`MP no`, local server, client and owner IDs `0`). The B207 claim validator rejected every provider ID less than or equal to zero, before inspecting site occupancy. Its rejection ACK then displayed the same occupied-site message for every rejection reason. New source-execution cases reproduced failed claims on all six body regions, both before and after a clinical reset.

A second zero-ID guard existed in the chest-seal edit coordinator. It silently discarded single-player requests before acknowledging them, leaving the client to retry. The new chest regression reproduces the missing acknowledgement against B207 source.

Dead-patient menu eligibility and treatment execution used different policies. Explicit corpse exceptions could make an action visible, while the native executor and delayed preparation called the stock action condition again. Check Airway and Check Breathing additionally required a live patient. Some mechanical device callbacks separately refused corpses.

The debug renderer added leading spaces according to the integer/decimal portion of each value. Long unit strings therefore started farther left, words had different starting positions, and padded strings could exceed the measured field width and wrap. A full-width revision row also incorrectly enlarged both paired fields.

## Corrections

- Direct Pressure and Hang Bag accept a zero machine identity only for a local single-player provider. Multiplayer zero-ID rejection, request-age checks, clinical epochs, exact episode tokens, cancellation history, and immutable grant deadlines remain active. Pending DP reservations use the same local-provider identity rule.
- Pressure replies carry their actual refusal reason. Only a genuine competing reservation reports an occupied site. Other failures explain the appropriate retry/availability issue and record a bounded latest-failure tuple on the provider plus one RPT diagnostic per matching failed request.
- Single-player chest edits accept zero only for local provider/viewer objects. Replies still target the viewer object. Duplicate handling and patient-owner effect routing remain unchanged.
- Treatment execution and delayed preparation re-evaluate the same live ACME eligibility policy as the menu. Redundant corpse exception tables are removed: ACE's actual action configuration supplies clinical, skill, item, location, body-selection and underwater checks. ACME retains its procedure/HPMK restrictions and corpse provider/interaction checks. Airway and breathing assessment conditions permit dead targets; per-side thoracostomy and mounted ventilator conditions stay explicit in their actual action definitions.
- Corpse HPMK prep/wrap, carrier access, pressure cuffs, ventilator attachment/manual controls, and suction remain mechanical interventions. These paths retain provider, custody, epoch, supply and receipt checks. Dead-patient actions do not re-enroll frozen physiology, establish gas exchange or revive the patient. A SIMPLE-mode setting change makes one local attached-corpse pass to advance device metadata; it adds no recurring scan. Duplicate setting callbacks preserve the episode, while mode changes invalidate old manual-breath packets.
- Debug words, numbers, decimals and units use trailing padding and share a left edge. Normal paired rows retain their overall 66-character width and second-label position; the screenshot's one-digit value anchor moves six character positions left. Full-width revision rows no longer determine paired-field width, while still participating in panel fit. No in-game pixel position is claimed from the source test.

## Validation

- All 14 package component configurations carry B208/protocol/component stamps, and all 14 PBO signatures verify against the one generated package key.
- HEMTT 1.22.0 `check` and `release --no-bin --no-archive` pass. Windows asset binarization and live Arma execution are not available here.
- The strict native-owner audit passes with zero literal direct/generic-helper writes in its four audited native domains.
- The admission execution harness uses a byte-identical copy of `medical_treatment/functions/fnc_canTreat.sqf` from the supplied ACE source (`SHA-256 3f2d84e877a20334d689e793eda950df035a1647d78ddcb86a5939eac7ec9ab4`), alongside the current ACME policy. Engine UI, inventory, locality and scheduling boundaries are explicit adapters.
- **740 focused checks pass:** 75 ownership and 665 execution checks. This includes 151 new B208 cases plus four additional debug cases.
- Full outcome comparison passes against fresh B207 and original B204/main reports: zero newly failing, skipped or missing cases. **The full suite remains failing**, with 5,475 passed, 790 failed, 46 errors and 29 skipped. B207 had 5,315 passed, 795 failed, 46 errors and 29 skipped. There are 155 new passing cases and five improved existing cases; improvements include fixture repairs and are not a count of new gameplay fixes.
- Production source was frozen before the full run and remained unchanged. Four old test modules needed updated boundaries/source assertions: the HPMK string-backed object fixture lacked the newly exercised `alive` boundary; two carrier assertions required the previous corpse-rejecting guard; one CPR assertion required the previous direct stock-call layout. Entire modules were rerun, and their 43 measured records replace only the same original testcase identities in the comparison. The original broad report is preserved. No cases were removed or skipped. Five pre-existing failures in those modules remain represented.
- The old B157 Check Breathing module still has its pre-existing missing-helper collection error. Its updated corpse transition expectation is not counted as executed proof. The new B208 admission/device tests pass independently.
- See [machine-readable validation summary](2026-09-30-b208-results.json).

## Live acceptance

Install the complete matching B208 package on each participating machine and restart Arma. In single player, repeat the screenshot scenario on all six regions of living and engine-dead patients; check release/restart and a clinical reset. Repeat on dedicated server with another player and server/HC-owned AI, including contention, cancellation, JIP and ownership changes. Check dead-patient airway/breathing assessments, HPMK, mechanical device controls, retained device removal, and physical chest procedures with appropriate equipment and access.

Confirm debug words and unit-bearing readings share a left edge, CO/Auto do not wrap, and the last section remains visible at the unit's actual UI scale. Inspect RPT for the specific `DirectPressure rejected` reason if any request still fails.

Physiological effects, awakening and seizure induction remain inert on an engine-dead patient. Recovery Position and Semi-Fowler/head-elevation operations retain their living-patient animation/collision requirements.

These automated checks do not execute Arma's UI, animation, network delivery or dedicated-server runtime. B208 is a targeted correction of reproduced failures, not a guarantee against every modpack or load-dependent failure. Provider locality transfer during a running DP pose remains a live-test/review item; it was not established as the cause of this report or claimed fixed here.
