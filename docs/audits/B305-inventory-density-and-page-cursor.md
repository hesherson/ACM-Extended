# B305 — Inventory density and Body Map handoff

Build 1.2.4.1 / B305, multiplayer protocol 2. Baseline: B304 `6150e0f958512f25ec3063fdd5e04b34eb9540b5`.

## Right-side Inventory

B304 compacted Fluids, Prepared IV sets and Prepared Infusions but left the normal Inventory pane at two entries. The screenshot shows that normal Inventory pane. It now displays six entries, triple the prior capacity, in the existing available space above Spike Bag. Each row is about 0.0373 safe-zone heights, versus the prior 0.09. Single-line fluid names are vertically centered alongside proportional icons. Scrolling, exact source-row identity, selection and full hover details are retained. The pool is bounded to 23 cards, created once per display; unchanged refreshes do not resize or recreate them. Existing left-side Fluids and prepared queues remain compact.

## Body Map navigation

The native Syringe Draw constructor formerly painted its preparation page before ACME's next-frame injection selected Body Map. The launch finalizer could also start a hidden compound-preparation session after selecting Body Map. Navigation did not preserve cursor position across the different native dialog resources.

The constructor now has an optional ACME ready callback for page-navigation launches. Ordinary non-navigation opens retain their existing deferred setup. It runs after native geometry is initialized and before the first rendered frame. The exact current launch selects the requested Body Map view during that callback. Deferred finalization recognizes the injected display instead of injecting it again, and Body Map skips hidden compound/flush preparation. Native plunger movement cannot pin the cursor while Body Map owns the view. Switching between Narc Box and Body Map within their shared dialog remains in place and releases only the local plunger grab.

Cross-dialog navigation captures cursor coordinates before closing its source, carries them with its existing transition epoch through bounded teardown retries, and restores them once in the matching destination constructor. A superseded epoch, retired display, malformed coordinates or repeated callback cannot move the pointer. The later legacy size/flush cursor restore is excluded for page-navigation launches. No cursor-restoring PFH or delayed mouse warp is introduced.

Transfusion and Body Map still use their existing native dialog resources. This change avoids an intermediate preparation-page paint and preserves the cursor across their handoff; it does not replace those resources with a new screen. Existing provider, patient, selected syringe, inventory custody, launch-failure cleanup, treatment workers and pressure behavior are retained.

## Verification and limits

Production SQF-VM checks cover six-slot scroll identities, stable card allocation/geometry, cursor bounds/epoch/display ownership and one-shot restoration, constructor-time injection, skipped hidden preparation, and preserved patient/body-part routing. Existing page navigation, launch cancellation, close-generation, card geometry, palette/scope, pressure and UI regressions are rerun. Root checks, pinned Node bundle reproduction, strict HEMTT and the native-owner audit are required.

Local validation: 27 new cases, 151 existing feature regressions, 385 additional UI regressions and 690 root checks pass, as do 52 Node tests and exact offline-bundle reproduction. Strict HEMTT compiles 2,151 SQFs and checks 15 stringtables and 22 configs; the native-owner audit reports zero violations.

Native Arma rendering and cursor/input acceptance still require an in-game check. Deploy the complete matching addon and key set to server, clients and headless clients together, with Arma closed. The container package omits Arma Tools model/animation binarization; `tools/Deploy-ACME-B305.ps1` performs the native Windows release. The public version remains 1.2.4.1; the draft PR remains unmerged.
