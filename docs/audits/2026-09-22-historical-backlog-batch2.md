# Historical backlog, maintenance batch 2

## Scope and preservation

Base: `5e134975242f182ebbed1225c96709eb7b2cce96`. This is an additive test/documentation batch on top of the newer batch 1 that reached main during the first investigation. The older experimental candidate `2e3882437a17a1db9ee7e0a09f5aa8344ab5e525` was not pushed over main. Its overlapping source-alias, CBA scope, version, SVT, CPR/BVM, thoracostomy and fixture edits were discarded in favor of the already verified main versions.

All production SQF, configuration, settings, assets and previously fixed lifecycle paths remain byte-identical. This batch changes six test modules, adds three test helpers/infrastructure files and updates three audit documents/indexes. No file is deleted and no existing source-discovery helper is replaced.

## Additional contracts verified

The following eleven original unresolved IDs have reviewed passing replacements:

- **H008:** native CPR/post-shock rhythm precedence retains the shared AED beat clock, not a retired second switch timer.
- **H012:** executing the real registered ROSC callback and acute-stress writer clears the rocuronium acute HR/resistance debt and applies grace while preserving historical awareness and active motor blockade.
- **H015:** treatment ECG artifact leases still start and stop, and chest UI acquisition occurs in the actual dialog initializer with the same lease released on close. A pending/refused open must not create this side effect.
- **H017:** syringe/vial functions are registered through the native circulation PREP table instead of deleted Extended overrides.
- **H018:** the Kelly panel consumes the native artifact-composited ECG buffers without applying artifact twice.
- **H021:** the shipped PEA subtype gate distinguishes wide/narrow morphology without allowing it to override another native rhythm. Narrow PEA is intentionally not required to look different from sinus. Existing source contracts still require zero PEA mechanical pressure/output.
- **H040:** executing the current rhythm observer preserves native arrest/shock precedence and only admits the existing treatment-dependent perfusing-VT recovery path. No retired ACME fatal-rate or SVT exception is reinstated.
- **H095:** the instructor chest reset and actual breathing writers retire PTX state and its worker while preserving external wound evidence, the tube and NCD equipment.
- **H099:** native breathing callbacks remain registered through PREP and owner-event hooks, with no old runtime wrapper reinstated.
- **H116/H117:** executing the real chest-effect code rejects stale/duplicate peel revisions and wrong clinical epochs, closes only the selected surgical tract, does not seal over an installed tube and does not convert external chest wounds into a blanket seal.

Two additional stale first-oracle expectations were replaced with existing intended behavior: IO placement and medication pain do not independently schedule fluid-pressure syncope; repeated fluid delivery shares its existing pending token. Compound Save commits/resets in place, and a failed commit must preserve the draft rather than recreate/close the dialog. Neither behavior was changed in production.

Six shipped-SQF probes use explicit mocks for Arma objects, CBA transport, rendering and inventory interfaces. The rhythm observer probe lowers its single outer-loop `continue` to an equivalent named iteration break because this SQF-VM build lacks that operator. Source shape is asserted; no production code is lowered or changed. The five expression-extraction infrastructure checks reject missing, ambiguous, incomplete and commented/quoted assignments.

## Results and accounting

The existing main baseline had **299 failed, 2,505 passed, four skipped and zero errors**, with 5,518 passing subtests. The local candidate full run has **286 failed, 2,523 passed, four skipped and zero errors**, with the same 5,518 passing subtests. Thirteen prior failing parent tests now pass; five new infrastructure cases account for the remaining increase in passes. No previously passing outcome became a failure.

The combined focused suite keeps the entire preceding verified selection and adds the new groups: **527 tests and 419 subtests passed, with no failures, errors or skips**. The local broad suite remains deliberately failing; pytest's exit code 1 is not relabeled a passing suite. An initial combined local run stalled with extra environment pytest plugins loaded; a clean plugin environment completed, and the independent GitHub validation repeats that environment.

The original source-contract subset is reduced from **249 to 238** in this batch. Together with batch 1, **24 of the originally unresolved 262 source-contract outcomes** have been verified. The companion JSON maps each original ID to its actual current test. The remaining-index file retains every other entry unchanged. A source-contract pass does not certify all gameplay in that subsystem.

Independent full-checkout validation must verify the same candidate tree, all production blobs, the combined focused suite, the broad before/after counts and HEMTT before this test-only candidate is promoted to main. Final run identity and recorded results accompany the publication evidence. Previous audit and batch 1 reports are not overwritten.

## Still open

The broad historical suite still contains **286 failing outcomes**. The **238 source-contract outcomes** are only one subset; these two counts must not be equated with each other or with distinct gameplay bugs. They remain unresolved, not waived, skipped or converted to expected successes. No Arma client or dedicated server was executed, so real transport ordering, animations, sound and rendered UI still require in-game validation.

There is no gameplay hotfix or old installer to apply from this batch. Pulling the tests does not require rebuilding the unchanged game code. Keep the old local stash as a backup and do not reapply superseded consciousness/seizure patch scripts.
