# B283: community PR integration

Stable version **1.2.4.1**, build **B283**, network protocol **1**.
Baseline: B282, `830062ba5e8f981695e750dff1b1227dbaf03b2e`.

## Scope

The integration covers PRs #6 and #31–41. PR #2 (Medmash) remains on `dev`; no Medmash addon is imported into this stable candidate. Contributor changes are adapted to the current architecture rather than replacing newer clinical, inventory or ownership transactions with old branch snapshots.

| PR | Result |
| --- | --- |
| #6 | Adapt remaining controlled-provider, IV launch, airway-volume, optional animation and ACRE handoff intentions to B282. Preserve newer equivalents described below. |
| #31 | Retain all B282 clinical clocks, gas/altitude composition, aircraft containment, clinical epochs, supply receipts and owner recovery. |
| #32 | Retain B282's NRB EFAK oxygen-source fallback and donor-bound reserve debit. |
| #33 | Integrate Spanish localization by key, preserving current non-Spanish text and correcting clear clinical wording errors. |
| #34 | Integrate airway equipment masses. |
| #35 | Integrate breathing equipment masses and reconcile filled/empty cylinder mass. |
| #36 | Apply autoinjector mass 1.8 through ItemInfo.mass; preserve medical classification flag 1. |
| #37 | Integrate Penthrox mass 2.2. |
| #38 | Integrate circulation item masses, reconciling effective overrides and prepared equipment. |
| #39 | Reconcile inactive legacy declarations with effective active definitions; do not resurrect retired items. |
| #40 | Integrate blood bag masses for all volumes and fresh-blood bases. |
| #41 | Integrate active Extended equipment/cooler masses and reconcile prepared carrier totals. |

## Inventory and localization resolutions

- Empty oxygen cylinder mass is 85; filled cylinder mass is 98.4, allowing approximately 425 L of oxygen gas in the same physical cylinder. Capacity remains 283 charges.
- ATNA/midazolam retain ACE_isMedicalItem=1; their intended item mass is 1.8.
- Effective Fentanyl definitions agree at 0.5. Empty and filled syringe masses agree by size, with four prepared physical carrier variants; all existing opaque identity and dose custody remain unchanged.
- IV preparation uses exact declared masses for current bags, Y combinations and directly spiked propofol bottles. All 19 historical carrier classes remain; 25 current combinations are added. Unknown third-party weights retain the existing fallback.
- Cooler masses are 20/42/75. The two-unit cooler retains 1000 mL capacity; its description now agrees.
- All 1,084 current localization keys have Spanish text. Non-Spanish source content is unchanged. Clear clinical mistranslations are corrected and placeholders are preserved.

## Preserved newer behavior

- The current treatment-bridge diagnostic identifies competing overrides and reports installation advice. The old PR's forced runtime recompilation would replace other addons' handlers and is intentionally superseded.
- Chest wounds retain the deliberately implemented six-per-side ceiling and physical wound identity. Reducing the total to six would silently discard tracked wounds and change pathology.
- Current chest-seal animation generations, clinical leases and physical flip preemption supersede old ApplyGestureSerial logic. Virtual flips receive equivalent cancellation.
- Current stethoscope audio already uses centered playSoundUI with native sound-ID custody, overlap and gain control; retain it instead of restoring old audio code.
- Current blood obstruction workers retain active-producer, owner and clinical-epoch recovery. Pooled contents alone do not enroll a new producer. Existing blood remaining-volume and aspiration receipt authority are preserved.
- ACE canInteractWith argument three lists exceptions. Its isNotInZeus exception remains where needed; removing it as in the old PR would reintroduce remote-care rejection.

## Optional animation behavior

Intervention Animations defaults to enabled. Disabling it preserves clinical clocks, progress, active treatment ownership, inventory costs and exact cleanup. Existing visual episodes retire their presentation safely; required engine releases (Get Up, full healing and leaving an already-held bag pose) remain available. Native and virtual readiness are checked against the captured episode rather than an animation that was never started.

## Validation and acceptance

Validation is recorded against the final integrated commit and its CI run, not inferred from the superseded B282 result. Version, clinical and inventory regressions, strict HEMTT validation and complete regression checks are required.

Native dedicated-server event delivery, actual moving-aircraft PhysX/ragdoll behavior and external scripts that replace animation/collision/state require in-game acceptance. This integration does not claim universal modpack certification. Server, all clients and headless clients must use the same complete build.

The separate B282 boundary for genuine syringe-provider ownership migration remains: accepted claims whose local continuation disappears require a server-authoritative delivery journal. Uncertain custody is held rather than guessed or refunded; other funded syringes remain usable.
