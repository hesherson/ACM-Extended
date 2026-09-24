# ACM Extended — Upcoming Release Candidate Patch Notes

These notes cover the cumulative backlog/stability work from the validated batch series through AS-AT. This is still an RC/testing build until live multiplayer acceptance is completed.

## Stability and multiplayer ownership

- Hardened stethoscope teardown so a stale display cannot trigger provider exit animation over a newer interaction.
- Added generation/session ownership checks across several delayed medical UI callbacks to stop old dialogs from modifying newer sessions.
- Improved provider-animation cleanup when locality changes so the previous owner does not broadcast stale animation resets.
- Prevented older head-position callbacks from restoring collision, changing facing, or resuming after a replacement placement has taken ownership.
- Head-position provider sequences now cancel cleanly when the medic moves, leaves the medical menu, becomes unconscious, or loses ownership.
- Reworked head-position cancellation tokens so old delayed callbacks cannot match a later restart.
- Preserved dead-patient interaction paths while tightening provider ownership and cleanup rules.

## Head positioning and patient handling

- Elevate Head and Lower Head now consistently remain Head-only medical actions.
- Fixed delayed Lower Head and Elevate Head retry ownership so older retries cannot interrupt newer placement state.
- Improved collision restoration ordering during head-position completion.
- Preserved connected grab/hold/supine release behavior without teleporting the patient back to cached coordinates.
- Provider exit sequences continue to finish crouched without forcing the casualty out of the intended position.

## Narc Box and medication administration

- Normal timed pushes are now bound to the original display, provider, patient, syringe identity, and workspace generation.
- Closing or replacing a Narc Box dialog can no longer let stale push callbacks unlock, retarget, or modify the replacement interaction.
- Confirmed push-dose epinephrine volume is locked when Push is pressed, so changing the dose selector mid-push cannot change the already-authored dose.
- A timed push now also owns the syringe's dosing-relevant contents. If medication, syringe size, drug volume, diluent volume, component recipe, or recipe marker changes under the same stable syringe ID, the old push is cancelled instead of administering altered contents.
- Body Map flushes now use the casualty displayed by that exact dialog instead of falling back to mutable shared patient state.
- Body Map injection confirmation rejects patient disagreement between the displayed casualty and shared preparation state.
- Stale Body Map site clicks are blocked before they can alter site selection, dispatch a flush, or stage medication during a newer/locked interaction.
- Preserved explicit site -> syringe -> Push/Inject staging instead of returning to immediate-on-click medication delivery.
- Native syringe draw endpoint ownership remains with the native drag loop; the Extended UI no longer competes with plunger endpoint writes.

## Syringe tags and preparation UI

- Fixed delayed tag-editor autofocus so callbacks from an older editor cannot steal focus in a reopened dialog or different syringe.
- Fixed delayed tag-color focus callbacks with the same session/syringe ownership rules.
- Preserved three 25-character tag lines and stable syringe identity.
- Updated historical UI contracts for the current Medication / Contents / Vials presentation, tag dropdowns, native syringe sizing, transparent editors, font fallback, and Body Map visibility behavior.
- Corrected the Accessibility setting description: normal medical-menu action rows use uniform white text rather than alternating pale red.

## Direct pressure and procedure interaction

- Preserved Direct Pressure as a non-exclusive treatment state where compatible actions can pause/resume pressure without incorrectly granting clotting time.
- Retained BVM integration behavior where an accepted BVM interaction ends that provider's pressure episode.
- Reconciled pressure ownership and cleanup tests with the current controller model.

## Medical menu presentation

- Auscultation clinical descriptors still display "Auscultate Chest" without rewriting ACM's base localized action name.
- Auscultation no longer depends on a retired Chest Inspection subgroup; if it is presented as a grouped child, exactly one child indent is preserved.
- Removed stale test expectations for alternating pale-red ordinary action rows.
- Group headers retain their existing optional per-section colors while normal treatment rows remain white.

## Internal QA

- Historical backlog reduced from 146 original unresolved entries to 59 after AS-AT.
- Full-suite comparisons are used to ensure previously passing identities do not regress.
- Root-level legacy collection failures are tracked separately from the historical addon backlog.
- Live dedicated-server and multi-client acceptance testing is still required before stable-release sign-off.
