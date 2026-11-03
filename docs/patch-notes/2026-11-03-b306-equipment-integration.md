# B306 — medical equipment integration candidate

Baseline: B305, `1b153d0023a776cbb74f762a3abfe91e0d207e71`, on the existing network/UI continuation branch. Public version remains 1.2.4.1. Main/dev and their release boundaries are not changed by this candidate.

## Changes

- Added the supplied ACCUVAC, six blood-cooler models, six Ventway variants and five HPMK models. The 26 corrected ACCUVAC/Ventway PAAs are combined with the original complete model/HPMK package. All 71 imported PAAs were successfully decoded.
- Added `acme_equipment` to bind existing ACME clinical items, prepared cooler carriers and deployed cooler containers to their new models. Existing capacities, weights, custody and cold-chain algorithms remain authoritative. Dedicated cooler models keep their fabric textures and native size; the old red texture/0.65 scale fallback is retained only for legacy models.
- Hidden duplicate art-only inventory items. Supplied ground holders issue the existing functional ACME item classes. Prop variants remain available for Eden placement.
- Dropped HPMKs use the supplied open-shell model through the existing collision-free anchor presentation. The supplied standalone ACE treatment module is excluded: its `setUnitLoadout`/equipment replacement path must not bypass ACME's existing reservation, warming, CPR gating and gear protections.
- Added editable configs and the supplied embedded Tempus Pro, Tempus LS and ATAK/BATDOK HTML/SQF. These are local PBO interfaces; they do not require the hosted demos. Disable separately loaded copies of the supplied model, Tempus and ATAK addons: their identical prefixes/classes must not override the integrated versions. ATAK remains optional through its cTab/BCE dependency gate.
- Added a local native-waveform adapter. The Tempus sweep canvases consume ACM/ACME LifePak ECG, pleth and capno samples. Generator target/cursor context is restored immediately; waveform samples are not broadcast over the network. Twelve-lead traces are simulated projections of the single ACME source, not independent electrode measurements.
- Added cancellable 2.5-second physical power-key holds to Pro and LS. Opening the close-up view no longer automatically powers the device. The existing Pro backlight/splash/self-test/admission sequence remains in the embedded interface.
- LS shock requests validate sender, actor/device/patient distance, power, connection, charge, clinical epoch and request age. Identified requests consume one LS charge and use the existing ACME shock backend. Temporary native pad/charge context is restored afterward.
- LS pacing now contributes at the native HR endpoint instead of writing HR from a competing PFH. Demand mode inhibits capture when intrinsic rate is adequate. Disconnect, power-off, cardiac arrest, loss of pulse and a changed clinical epoch remove capture. Locality handoff fails closed rather than leaving a stale public capture flag.
- BATDOK accepts server record operations from the claimed provider's network owner. The existing roster, sensor readers, manual measurements, trends, triage, logs and transfer paths are retained.
- Corrected a native IV-complication removal loop that used unary `params` instead of `_x params`; this was exposed by current HEMTT correctness checks. Standardized config include separators for the current build tool.
- Updated the B306 identity contract and journalled deploy helper to expect all 27 PBOs.

## Deliberate limits and remaining acceptance

This is an integration candidate, not a native multiplayer acceptance certificate. The build environment cannot run Arma or Windows Addon Builder.

- The downloadable candidate is signed and rapified, with the editable medical MLOD models retained (`hemtt release --no-bin`). The Windows source deploy command performs the normal native release build, including available model binarization.
- Physical key alignment, camera framing, materials, collision geometry, proxy paths and equipment placement need Arma inspection.
- The worn HPMK mesh is supplied but automatic casualty wearing remains disabled. Enabling it must preserve uniform/vest selections and respect existing collision/pose protections. The current clinical wrap/warming workflow remains active.
- Open/closed cooler states and the Ventway connection variants are provided as model assets. The active clinical cooler retains one native container and its existing ledger. Dynamic physical opening, cable placement, live 3D Ventway display projection and physical Pro/LS docking are separate presentation work.
- Record/sensor/device connections are mission runtime state; no new cross-session backend is introduced.
- Test patient-owner changes, death/heal, power cycling, multiple nearby devices, pad removal, lost connectivity and optional ATAK dependencies on a dedicated server. Do not represent mock-boundary SQF/browser checks as native networking proof.

## Source provenance

Assets and interfaces came from the user-supplied `ACME_Medical_Models.zip`, the 26 texture additions in `ACME_Medical_Models(1).zip`, `acme_tempus.pbo`, `acme_tempusls.pbo` and `@ACME ATAK Enhancement.zip`. The original medical archive credits mavis and states not for profit. The supplied ATAK wrapper credits knox; packed config metadata credits ACME. Existing source/third-party notices in imported files are preserved. Original Blender/build sources remain in the supplied archives.
