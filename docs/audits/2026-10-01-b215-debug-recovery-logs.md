# Stable 1.2.4.1 B215 debug, recovery and activity-log fixes

Base: B214, `ef500f20a5db69fe850331c2eb67d5c7641bec7e`.
Public version remains **1.2.4.1**; runtime and every package component identify as **B215**.

## Debug display

The overlay measures its final fitted text and contracts the background to that width plus padding. Its maximum width remains a ceiling, not a fixed empty strip. PTX uses three decimal places. Medication labels split words while preserving abbreviations. The CHEST-SEAL TRANSPORT section is removed.

The medication section remains **MEDICATIONS**, with the caption **Effective reference-dose equivalents**. Its source values are dose/effect equivalents, not measured serum concentrations; renaming them as serum levels would misrepresent the data.

Fluid bags now use nested bullets: stored initial bag volume and fluid shorthand form the title; location, remaining fluid, blood type when relevant, clamp/drop-set details and remaining added medications appear underneath. The native bag's stored initial volume includes added solution; there is no separate immutable factory-capacity field. The display uses the recorded volume rather than guessing a nominal commercial bag size. Receiving FBTK bags remain visible even when empty. Medication records match bag UID first, with strict metadata matching only for legacy records lacking a UID. Reading the menu no longer assigns bag identity or changes clinical state.

Production rows were captured with empty and populated infusion lists and rendered at 1920×1080 and 2560×1440. The previews use substitute monospace font metrics; they verify row structure, fit calculations and padding, not Arma's exact font rendering.

## Logs and fracture descriptions

- Respirations: `Provider measured respirations @ 28 RR/min~ (7 breaths in 15 seconds)`.
- Direct pressure: `Provider applied direct pressure to LUE`, with the corresponding body-part abbreviation for other sites.
- Pressure on a fracture retains its pain/cooldown/wake effects but no longer adds the redundant severe-pain activity entry.

The old hardcore descriptor for a mild native fracture explicitly said no crepitus. Native ACM grades 1, 2 and 3 all represent fractures. Confirmed unsplinted fractures now report crepitus, including a positive ACE fracture without an ACM grade. Splinted/stabilized limbs retain their stabilized wording. Negative bruising and unknown findings do not become positive fractures, and non-hardcore inspection retains the native behavior.

## Recovery positioning

Recovery uses the existing Flip provider controller, including its shared animation rate, prone variant and weapon-holster behavior. Explicit start/progress/success/failure callbacks prevent it from inheriting the Check Airway assessment sequence. Semi-Fowler lowering remains patient-only for this action, avoiding a second provider sequence competing with Flip. Cancel Recovery retains its native roll-to-back behavior.

The patient owner takes a bounded animation lease and issues the documented Arma 2.18 array form of `switchMove`, starting with blend factor zero. No native move class is reopened or replaced. The action's provisional visual pose becomes clinical recovery only after successful completion and the owner observes the requested pose with an almost-complete engine blend. Episode tokens, clinical reset epochs, shared-clock deadlines and locality checks prevent stale cancellation/completion from changing a successor action. Cancellation unwinds only the provisional pose it still owns.

Reference: [Bohemia switchMove documentation](https://community.bohemia.net/wiki/switchMove). The project's existing minimum required Arma version is 2.18.

## Verification

All **2,344 required checks pass** (75 ownership, 1,580 networking/feature execution, 689 behavioral), including 128 new B215 cases. HEMTT check and release pass. All 14 PBO signatures and B215 component stamps verify; the strict native-state ownership audit reports zero violations. The compiled native move inheritance check passes, and 41 packaged SQF files match the reviewed source byte-for-byte.

The complete suite comparison against a fresh, unchanged B214 checkout reports no new regression or missing existing testcase. Current outcomes: 6,903 passed, 301 failed, 44 errors, 27 skipped. The failures/errors are historical baseline outcomes; they are retained in the reports. Exact counts, source hashes, debug previews, raw test results, baseline comparison and compiled-package checks are retained in `2026-10-01-b215-results.json` and `2026-10-01-b215-test-reports.zip`.

These checks do not render RTMs inside Arma or reproduce live multiplayer. In-game animation smoothness still needs a client/server check. Linux release verification uses `--no-bin`; the Windows deployment helper runs normal `hemtt release` with asset binarization. Restart Arma and use the same complete B215 build on clients and server.
