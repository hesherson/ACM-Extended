# Stable 1.2.4.1 B212 treatment flow

Base: B211, `3a190071bf37a84da12628d97c4a689c6c39d5bf`.
Public version remains `1.2.4.1`; runtime and all package components identify as `B212`.

## Pleural blood

Accepted finger widening and a repeated finger sweep remove the entire blood accumulation present at that instant. They do not clear hemothorax severity, terminate the hemorrhage worker, or return shed blood to circulating volume. Subsequent bleeding can accumulate again. This is a discrete drainage event, not continuous drainage without a tube.

A burp or removal of a surgical or traumatic chest seal drains a pressure-scaled fraction of the current pool, measured before pressure relief:

`drained = fluid * clamp(max(PTX pressure, fluid / 1.2 L), 0, 1)`

Native tension pneumothorax forces the pressure contribution to one. The popup reports the actual debit in mL to one decimal place, including zero. A generic successful peel acknowledgment cannot overwrite that result. A tube in the selected tract blocks finger care; the opposite tube's state and measured output are preserved.

ACM has one casualty-wide hemothorax fluid reservoir. Eligibility remains side-specific, but this change does not introduce fictional independent left/right blood volumes.

The casualty owner accepts each transaction. Clinical epochs, synchronized request age, bounded per-origin sequence receipts, and existing seal revisions prevent delayed/replayed events from draining newly accumulated blood. Initial widening retains its kit reservation until the owner acknowledges acceptance; rejection refunds once. A retry asks about the same receipt and cannot apply a second drainage.

## Lung sounds

The existing breath and crackle channels now apply anterior/posterior transmission gains from native airway/breathing effectiveness. At the strongest shallow-breath setting, anterior transmission is 25% and posterior transmission is 70%; normal-depth transmission remains unchanged. Near-zero airflow fades both channels to silence. A driving ventilator uses measured exhaled tidal volume, avoiding a false shallow-breath penalty solely from paralysis. Existing laterality, positional findings, and heart sounds are preserved.

## Assessments

- Check Breathing uses `AinvPknlMstpSnonWnonDr_medic4` for a two-second assessment at 1.5x speed.
- Check Airway samples `AinvPknlMstpSnonWnonDr_medic5` at exactly 1.375 native animation seconds (about 0.917 wall seconds at 1.5x), freezes that sample, then immediately requests interpolated `AinvPknlMstpSnonWnonDr_medic4` at 1.5x.
- The initial airway duration is `ceil((1.375 + native medic4 duration) / 1.5)`. The installed game's inherited `CfgMoves` speed supplies the native duration. The same progress action extends to the next whole second if the actual blend delays completion. It cannot succeed before the observed final animation completes; missing/interrupted animation fails through bounded cleanup.
- Weapon/carrier preparation finishes before the assessment timer starts. Cancellation, locality changes, vehicle entry, stale same-class callbacks, and replacement treatments retain scoped cleanup.
- Prone providers use the supported prone equivalent; seated care does not request on-foot animations.

## Provider posture

The personal CBA setting **ACM Extended: Systems / Interface / Crouch when opening the medical menu** controls automatic menu kneeling. It defaults on and is not overwritten at post-init. Disabling it retires an existing menu pose. Ordinary treatment animations retain their authored standing/crouched behavior.

Prone providers use existing BI prone treatment variants where available, or the shipped `ACM_ProneContinuous` hold when specialty choreography has no prone equivalent. This covers native/AI treatment, BVM and continuous actions, shared assessment/workspace/carrier/flip poses, direct pressure, Hang Bag, and head-position provider work. Entry, delayed callbacks, held-state comparisons, cancellation, and cleanup preserve prone posture. Known prone animation states are also recognized when Arma reports an undefined stance. CPR keeps its explicit forced posture. Patient repositioning animations are not globally remapped.

The B211 Direct Pressure input behavior remains: movement reasserts the hold, RMB cancels, and MMB retains its existing cancellation behavior.

## Validation and limitations

Exact automated results are recorded in `2026-09-30-b212-results.json`. All 2,041 distinct required checks pass (75 ownership, 1,260 network, 689 behavior, plus 17 repaired breathing checks). The signed release contains 14 verified PBOs and 14 signatures; all 58 changed/new SQF files match their reviewed source bytes. The strict native-state ownership audit reports zero violations. The release gates cover ownership, network execution, behavioral regressions, the new B212 cases, HEMTT static validation, package stamps/signatures, and bundle import. Additional historical outcomes are compared against the untouched B211 checkout. After complete reruns of six affected test modules, the comparison has no unresolved regressions: 6,583 passing cases, 301 failures, 44 errors, and 27 skips in the final JUnit inventory. The 345 remaining failures/errors all match the baseline; 33 existing cases improve and the previously uncollectable breathing module executes all 17 cases. The historical suite is not green. Raw full-run reports, final module reruns, comparison provenance, and focused reports are retained in `2026-09-30-b212-test-reports.zip`. The later changes repair outdated source assertions/snapshot expectations and missing test-engine boundaries; gameplay source is unchanged from the signed build.

SQF execution tests run production functions with explicit engine/config/animation/scheduling boundaries. They do not render Arma RTMs or reproduce a live multiplayer session. Linux packaging uses `hemtt release --no-bin --no-archive`; the Windows deployment helper performs the normal asset-binarizing release. Live confirmation remains necessary for the visual blend and exact freeze sample, posterior listening, and remote-client presentation.

## Delivery

`ACME-B212.bundle` contains B211 and B212 after B210, so it fast-forwards either checkout. Verify/fetch the selected local bundle, merge only after a successful fetch, and run `tools/Deploy-ACME-B212.ps1`. Use a process-scoped `powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File` invocation if local script policy requires it. Restart with the same complete build on participating machines.
