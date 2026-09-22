# Historical-test verification

## Scope and verdict

Verified baseline: 5dca0429d9ef211f3366cd54b4f3c95274ba7a48.
Verified current source: c3dd15f41a56a253461d876b478f91849d23551f.
Independent complete-checkout CI run: 35689544716, artifact 10677288512.
No production source or main change was made in this verification. This audit branch contains read-only workflows and this report.

The historical failures are not all harmless. Three concrete control-flow/lifecycle defects were found, plus a separately modeled multiplayer race. This is not an all-clear: 262 original source-contract outcomes remain explicitly not cleared. An obsolete first assertion does not validate every later assertion or associated gameplay feature.

## Reproduction

Scope: addons/acm_extended/tools, --continue-on-collection-errors, excluding the separately inspected test_b77_branding_authors.py import-time process exit.

| Source | Execution tools | Failed | Passed | Skipped | Errors |
|---|---|---:|---:|---:|---:|
| Baseline 5dca0429 | None | 448 | 1587 | 151 | 12 |
| Current c3dd15f4 | None | 448 | 1599 | 185 | 12 |
| Baseline 5dca0429 | HEMTT/SQF-VM | 471 | 1711 | 4 | 12 |
| Current c3dd15f4 | HEMTT/SQF-VM | 461 | 1767 | 4 | 12 |

Each run also reports 2747 passing subtests. The original 448 failures are 423 failing parent test reports plus25 failing subtest reports, not448 distinct gameplay bugs. The previous phrase '12 collection errors' was inaccurate: there are seven collection failures and five setup failures, the latter all from one SVT setup routine.

The plain baseline/current runs fail on identical outcome identities. The equipped current run has ten fewer failing identities and zero newly failing identities compared with the equipped baseline. The13 additional failures compared with current plain were previously skipped checks activated by installing runtime tools.

Pinned tools: HEMTT1.22.0 and SQF-VM v2026.04.03-ed9f5f5, release hashes checked. CI installed pytest9.1.1, pytest-subtests0.15.0, pytest-json-report1.5.0, NumPy, Pillow and SoundFile. Exact environment and raw logs are retained in the evidence artifact. The generic JSON plugin summary miscounts some subtest totals; the table uses terminal results and separately captured TestReport/SubtestReport events.

Workflow success means the evidence-capture job completed. It does not mean the historical tests passed.

## Confirmed findings

### F01: surgical-airway reservation before accepted startup

Original H460; related H458. addons/airway/functions/fnc_establishSurgicalAirway.sqf sets SurgicalAirway_InProgress=true before beginContinuousAction accepts the action. The controller rejects an already active action, dead provider or unconscious provider before installing this action's cancellation callback.

Three probes executing the actual adapted SQF entry/controller reproduced: rejected start, reservation left true, no new controller or cancellation handler, and a later valid retry rejected as already in progress. The transient reconciler deliberately does not infer surgical-airway cancellation from replicated session metadata, so recovery cannot be assumed for this rejected-start case.

This is a confirmed defect. Reservation acquisition must belong to accepted startup, with scoped rejection/rollback that cannot clear another valid provider's reservation. No fix was applied during verification.

### F02: live player identity handoff does not immediately cancel the original hold

Activated runtime E006, test_menu_death_lifecycle.py player-swap case. The real adapted head-tilt/controller code continues after ACE_player changes while the original medic is alive/local. Its immediate cancellation condition does not bind the old player-controlled session to that identity.

This confirms the immediate-handoff failure, not a permanent orphan in every situation. Separate periodic provider reconciliation and the server heartbeat watchdog may eventually release it. Ordinary death/unconsciousness tests are distinct and must not be called broken based on this case. An eventual fix should preserve legitimate AI/remote contexts rather than add an unconditional all-actions medic==ACE_player rule.

### F03: stethoscope immediate active-flip abort is unreachable

Discovered while tracing H456. fn_stethoscopeClose.sqf writes ACME_stethFlipActive=false before reading it into _flipWasActive. The immediate active-flip abort branch therefore never runs through this path.

A probe executed the actual close-function prefix through the entire abort branch with an initially active flip. Neither the provider nor patient cancellation hook ran. Later common chest/pose cleanup was outside the probe, so this is not proof of permanent pose failure on every close. The original H456 first failure itself is a stale three-argument pose-stop literal versus the intentional four-argument handoff.

### F04: Hang Bag nonserialized acquisition window

Original H454. fn_hangBagStart.sqf accepts against replicated holder state and directly publishes the holder from the provider. An ownerDispatch hangBagClaim path exists but is not used by start. fn_hangBagTick.sqf detects conflicting holders after acceptance.

Executing the actual acceptance and conflict-check prefixes under an explicit two-provider interleaving admits both, then can cancel both after each observes the other's write. This is a source-supported modeled multiplayer race, not a live dedicated-server reproduction or proof of inventory loss. It remains open and must not be dismissed as a stale assertion.

Six observed-behavior probes passed because they assert that these bad conditions occur. Their passing result is defect-reproduction evidence, not release approval.

## Verified test-side causes

100 original failed outcomes pass after read-only source-locator corrections alone, with original assertions and production source unchanged. This includes13 subtest outcomes. Locators now follow canonical core/breathing/circulation/gui native functions and actual startup/debug initialization modules. This proves those source contracts, not in-game rendering or transport. Individual outcome identities are mapped; the full probe population also gains newly collected tests, so total probe summaries cannot simply be subtracted from448.

83 additional original outcomes have specifically diagnosed stale/overbroad/source-literal first assertions, not full behavioral passes. These include48 old version/build gates and12 CBA setting-scope expectations. Current config is1.2.2.1/B143. Tests demanding old r7/r28/r42/1.2.0-r0 stamps cannot all govern the current tree. CBA documents isGlobal=2 as not overwritable; tests equating client-local strictly with0 misread that contract.

Other diagnosed examples: incompatible historical carousel timings0.085/0.135/0.180 versus current immediate selection; Save tests demanding retired close/reopen delays; a dead-patient token prohibition catching the explicit successful postmortem/no-physiology receipt; contradictory IO-syncope expectations; a diagnostic test banning every RPT emitter despite intentional patient dumps; and the old one-shot roller-clamp darkness-tail requirement that would reintroduce the reported NV defect.

Eleven of the13 newly activated current failures pass with test-only corrections: eight with corrected fixtures and three with obsolete trauma-burp gesture-count expectations removed. The latter retain the original physics, logs, repeatability and dead-patient assertions, but are explicitly not called unchanged-assertion tests. Fixtures model current owner-routed markers, draft/edit controls and chest-access busy state; a balanced namespace adapter removes only the third top-level public setVariable flag, not nested values.

Adding the corrected plunger parser gives14 passing probe tests plus400 passing subtests (eleven activated cases plus three formerly uncollected plunger tests). This does not turn the unmodified suite green. The remaining two activated cases are F02 and a strict HEMTT --error-on-all style gate; standard project checking passes with nonblocking suggestions.

## Error accounting

- H001: old plunger cursor regex fails at import. A copied parser update permits three passing tests/400 subtests.
- H002: imports H001 and inherits its error; later animation assertions remain after collection is enabled.
- H003: removed Extended updateActions path; canonical native locator permits collection.
- H004,H007: missing generated audit/MEDICATION_MATRIX.json. Repository generator creates46 classes/26 concentrations from current sources; it is not engine preprocessing and does not clear all later assertions.
- H005: old updateActions path followed by another obsolete import-time1.2.0-r0 version gate.
- H006: import-time hardcoded B92 startup requirement.
- H071-H075: five setup failures in one SVT source parser, first failing on a multiline _hrReleases expression. Parser correction reaches another obsolete inline-source assumption. No justification to restore an old SVT exception just to match it.

A five-module follow-up after parser/generated-fixture corrections still had18 failures and one collection error, alongside153 passes and2342 passing subtests. Enabling collection is not an all-pass. The B77 import-time sys.exit was logged separately and consistently excluded from the quoted scope.

## Original outcome disposition

| Disposition | Outcomes |
|---|---:|
| Assertion passes after source-location correction only |100|
| Diagnosed first-assertion mismatch, not full behavioral clearance |83|
| Surgical-start defect / related recovery gap / Hang Bag race |3|
| Reproduced source contracts not cleared |262|
| Diagnosed collection/setup errors |12|
| Total original outcomes |460|

F02 belongs to activated runtime checks, not the original448. F03 is an adjacent finding while tracingH456. The262 remaining outcomes are not claimed harmless or stale; they need contract-specific verification before being waived or replaced. These findings are not claimed to be the only defects.

Separate project-root tools/ scope:137 passes and46 collection errors, recorded separately from the original addon-only total.

## Preservation and limits

Main was not updated. Local production verification matched3999 tracked files with zero modifications. Only the two repository-root logo PAA files were absent from the local fixture; independent CI used complete checkouts. Full terminal logs, report events, per-outcome ledger, copied-test diffs and observed-behavior probes were packaged for the user. No font files, game assets or executables are in that package.

No Arma client, listen server or dedicated server was run. SQF-VM adapts engine/UI/animation/network boundaries. No medication, animation, physiology or gameplay changes were made just to satisfy historical text tests. This report is verification evidence, not a release sign-off.
