# Historical backlog, maintenance batch 1

## Scope

Base: `19d01b8b27fd53bb9d3c381c7445add589336159`. This batch changes tests and audit documentation only. All SQF, configuration, runtime settings, artwork, sound and other production blobs remain byte-identical. No historical assertion was used as a reason to restore a retired runtime exception, dose, timing, layout or state writer. The four prior lifecycle fixes remain intact.

## What was repaired

- Exact source aliases replace obsolete Extended override paths. The startup/debug reader bundles statically named initialization-module calls, ignoring quoted/commented examples. This is structural source discovery, not proof of runtime branch reachability. There is no global Path monkeypatch or fuzzy fallback. One hundred original failed outcomes pass without changing their assertions.
- The plunger arithmetic test reads balanced current assignments and the actual two cursor arguments, rather than a one-line regex tied to old X-coordinate spelling. Its original three assertions and 400 cursor-feedback cases pass. Unsupported arithmetic tokens are rejected instead of silently discarded.
- Five SVT checks now execute current rhythm/rate decisions in SQF-VM. They verify native fatal-rate boundaries, native arrest/rhythm authority, bradycardia, the existing mature-torsades morphology distinction, grace and the separation of pain from rhythm-generated heart-rate feedback. They do not reinstate an SVT exception above 220 bpm.
- Read-only medication inventories are generated in memory from the native and Extended configuration shipped together. No missing generated audit JSON is required; unresolved macros remain symbolic. Subsequent old assertions are still reported individually, not automatically cleared.
- B80's checks and previously excluded B77 branding checks now collect as ordinary tests rather than aborting collection. Their original checks remain visible, including obsolete release-label failures. B91 follows the actual called interaction initializer and tests current version consistency separately from the original malformed-comment, cleanup and structural guards.
- Reviewed clinical contracts follow current authoritative writers and admission boundaries. Executable probes cover IO mode distinctions, acute ROSC stress reset, native rhythm recovery, instructor chest reset/equipment preservation, seal/tract epoch and revision checks, BVM with CPR, reserved roles, in-place compound Save and surgical-kit/debit ordering. Rendering, transport, inventory APIs and similar engine boundaries are mocked explicitly.

The SQF-VM version does not implement `continue`. One rhythm probe lowers the single outer patient-loop continue to an equivalent named-iteration breakOut; the narrow source shape is asserted. This limitation is not hidden or treated as live engine execution.

## Results and accounting

A complete independent checkout of the unchanged base produced **460 failed, 1,796 passed, four skipped and 12 errors**, with 2,747 passing subtests. The baseline excluded the one B77 script that called sys.exit during import.

The local candidate full run, now including B77, produced **354 failed, 2,446 passed, four skipped and zero errors**, with 5,508 passing subtests. No previously passing outcome became a failure. The broad suite is deliberately still red; this is not a full clearance.

The original 460-outcome ledger maps completely: **128 passing outcomes, 320 still failing, and all 12 collection/setup blockers unblocked**. The 128 passes include the previously demonstrated 100 unchanged-assertion source-locator corrections, 27 reviewed contract updates, and one other outcome already addressed by preceding runtime work. A collected module can still contain failing tests; unblocking it is not equivalent to clearing it.

Of the specifically unresolved **262 source-contract outcomes**, **20** now have passing reviewed contracts, leaving **242 unresolved**. The companion JSON records the exact H-identifiers and each renamed/oracle-changed case. It does not classify untouched failures as harmless.

Previously hidden B31, B37, B38, B13, B80 and B91 checks now run; newly visible failures remain in the broad-suite result. B77 is outside the original ledger and contributes its original branding/version checks separately. Increased passes/subtests partly reflect newly collectable independent models and test-infrastructure cases, not thousands of newly demonstrated gameplay guarantees.

Independent candidate validation is recorded in the final GitHub Actions evidence associated with this batch. No production commit is published until the complete checkout has passed the focused suite, exact-tree and production-preservation checks, and HEMTT check. The full historical run must retain its recorded failures and zero setup/collection errors; its nonzero pytest return code is not relabeled a test pass.

## Deliberately left outstanding

The 242 unresolved source contracts, remaining old release/layout/settings checks, newly revealed assertion mismatches and engine-dependent behavior remain open. This batch does not retune physiology, reintroduce one-off cardiac exemptions, restore delayed Save/carousel redraws, or erase historical checks to force a green badge. Existing nonblocking HEMTT style suggestions and existing environment-dependent skips are not changed.

No Arma client or dedicated server was run. The evidence is source inspection, original-oracle numerical checks, and real SQF fragments/functions executed with explicit engine-boundary mocks. In-game networking, animations, sound and rendered UI still require live validation.

## Using the batch

The source updates are test maintenance, not a gameplay hotfix. Use the current repository rather than superseded local patch scripts. `pytest addons/acm_extended/tools` now collects without the old import-time exits, but is expected to report the remaining historical failures. Do not treat them as new gameplay regressions merely because previously blocked tests can now run.
