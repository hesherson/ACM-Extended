# Stable 1.2.4.1 B213 observation, animation and debug update

Base: B212, `4788b9029c3e2ee221d085e831040dc19cbc957a`.
Public version stays `1.2.4.1`; runtime and package components identify as `B213`.

## Direct pressure

The provider now completes the existing real empty-hands preparation before entering the pressure hold. Hiding a selected weapon in the weaponless hold was insufficient: movement made the engine reveal it again. No previous weapon is stored for automatic restoration.

Pressure captures its own shared held-animation generation and retires only that generation. It no longer increments the shared generation on every paused frame, which previously invalidated the provider's new auscultation/chest preparation while the casualty sequence continued.

Movement retires the hold through `AinvPknlMstpSnonWnonDnon_medicEnd` at 1.5x while preserving the clinical pressure episode within its existing leash. Stopping and facing the casualty allows the empty-hands hold to resume. Explicit cancellation releases the pressure claim and uses the same exit. A successor treatment takes ownership immediately; delayed pressure callbacks cannot restart the old hold. Prone providers retain a supported prone exit instead of being pulled into the kneeling RTM.

The uploaded Animate Rewrite sources reset animation speed when leaving walking. The finite exit therefore maintains its owned 1.5x coefficient after actual entry. Observer synchronization is scoped to the pressure episode and does not issue animation commands.

## Chest-seal exit and airway assessment

Closing an acquired chest-seal workspace inserts the same literal `medicEnd` at 1.5x between the held chest work and the existing carrier-restoration reach/return. The patient owner waits for a bounded, session-specific provider acknowledgment before starting the reverse carrier lift. Existing generation and remaining-viewer checks protect a reopened workspace. Prone and seated providers retain their existing safe paths.

Check Airway now samples the initial `medic5` at **1.75 native animation seconds**, about **1.167 real seconds at 1.5x**. This adds 0.25 real seconds to B212's initial motion. It still immediately interpolates into a complete `medic4`, and its action duration rounds up to a whole second. Check Breathing remains two seconds.

## Measure Respirations

The new **Measure Respirations** action is available under examination for the head and torso. It uses the existing Feel Pulse provider choreography, including its prone-safe path. Same-vehicle observation keeps both units seated.

A dedicated observation watch and breath counter share the same monotonic clock. Provider preparation does not consume observation time. The watch counts exactly **15 real seconds**, independent of accelerated mission daytime. Each observed breath uses the existing BVM blue gradient and inflation/collapse shape. The final counted cue may finish after the watch reaches 15, but no additional observation time or breaths are included.

The result is a rounded rate with a trailing tilde, for example **16~ /min**, calculated from the counted breaths over the 15-second window. Cancellation does not produce a completed measurement. The action reads replicated clinical state without writing physiology; delivered ventilator breaths remain distinct from spontaneous respiratory effort.

## Debug display

- All yes/no field names gain a question mark.
- Requested labels are expanded or renamed; `Ca` is **Calcium** and TBI `Struct` is **Brain damage** (structural injury severity).
- Left/right thoracostomy fields show **[TUBE]** in the medical menu's cyan when a tube is present.
- **MEDICATIONS** displays every registered concrete medication, grouped by drug across route variants. The current inventory has 29 drugs and 46 route classes; zero values remain visible. Values are effective reference-dose equivalents, not medication inventory or milligrams.
- A separate **SEDATION / AWARENESS** section retains nondrug sedation and awareness values.
- Runtime/network information follows machine/patient ownership; metabolic information sits between airway/chest and neuro/TBI.
- Patient name, blood type and weight sit immediately below the title.
- Each field is indented. Colons align to the longest label in each column, with one space before the colon. Sections have bottom separators.
- The overlay uses the full available height and at most 24.5% of screen width. Medication registry discovery is cached.

## Verification

All **2,196 distinct required checks pass** (75 ownership, 1,432 networking/feature execution, 689 behavioral). The B213 feature modules execute 168 passing cases. HEMTT check and release pass; all 14 PBO signatures and component stamps are verified, and all 29 changed/new SQF files match their reviewed source bytes inside the signed packages. The strict native-state ownership audit reports zero violations.

The full comparison against untouched B212 has no unresolved regressions. Final JUnit outcomes are 6,755 passed, 301 failed, 44 errors and 27 skipped; remaining failures/errors match the historical baseline. Raw full, focused and targeted reports, package verification and debug previews are retained in `2026-09-30-b213-test-reports.zip`. Exact counts and provenance are recorded in `2026-09-30-b213-results.json`.

SQF execution tests use explicit engine, UI, configuration, timing and networking boundaries. Generated debug previews use production-generated rows but surrogate font metrics. Neither those previews nor automated tests render live Arma RTMs or reproduce a live multiplayer session.

Linux release verification uses HEMTT's non-binarizing release path; the Windows deployment helper runs the normal asset-binarizing `hemtt release`. All participating machines should use the same complete B213 build.
