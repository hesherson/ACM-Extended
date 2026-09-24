# ACM Extended — Upcoming Release Candidate Patch Notes

These notes cover the cumulative backlog/stability work from the validated batch series through BA-BB. This is still an RC/testing build until live multiplayer acceptance is completed.

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

## Animation and Provider Control

- Reconciled provider animation ownership with the current single-controller model.
- Ordinary medical provider entry continues to use priority-one interpolated movement instead of priority-two snap entry.
- Physical patient chest rolls use owner-scoped animation leases so competing providers cannot continually overwrite the same casualty.
- A narrowly scoped priority-two fallback remains only when Arma's lying-state graph swallows the requested patient roll transition.
- Stethoscope, pulse, chest-inspection, chest-access, and roll holds continue to freeze on their authored timeline and synchronize that held frame to observers.
- Roll-provider hold timing remains 2.2 seconds.
- Response and airway assessments retain their current authored wrapper animations and treatment durations.
- HPMK wrapping no longer physically rolls or repositions the casualty, avoiding unnecessary animation ownership and collision handoffs.
- CPR and BVM remain native ACM-owned continuous actions rather than ACME animation replacements.
- Priority-two/switchMove usage is limited to exact held-frame synchronization, explicit resting-state locks, and scoped state-graph recovery rather than ordinary treatment entry.

## Airway and Chest Interaction Ownership

- Laryngoscopy remains available for a perfusing/awake casualty when the required equipment and airway conditions are met; reflex, gagging, sedation, paralysis and bucking remain procedure-owned rather than being hidden behind an unconscious-only menu gate.
- Elevate Head and Lower Head remain Head-only actions and do not invoke ACM's generic roll-to-back behavior; ACME owns actual-prone-to-supine normalization.
- CPR and BVM remain routed directly through ACM's native continuous-treatment bridge before generic ACME provider preflight.
- Fixed chest-seal Flip so a failed provider-animation acquisition can no longer roll the casualty directly from the button handler.
- Physical chest Flip now remains gated behind the current provider token/episode and observed medic4 work state.
- A failed Flip acquisition cleanly unlocks the UI, restores the hands-on-chest hold when possible, and resumes a Direct Pressure handoff without moving the patient.
- Chest-seal and thoracostomy burp paths remain patient-owner authoritative with no gameplay timer between valid burps.
- Removed a dead thoracostomy burp gesture dispatch so burping cannot reuse the medic3 animation reserved for actual chest-seal placement.

## Cuff Syringe, Menu and Vision Presentation

- Laryngoscopy cuff inflation continues to use ACM's real 10 mL syringe backbit/plunger with ACME's replacement flush barrel artwork.
- Native syringe drawing uses the replacement barrel only for a selected 10 mL saline flush; ordinary medication syringes retain ACM's generic barrel.
- Cuff inflation remains a one-second hold and now visibly drives the plunger from its authored 8 mL starting mark toward empty while the distal tip remains anchored to the pilot balloon.
- Opening another patient's medical menu no longer holsters the provider's weapon. The menu requests the matching weapon-in-hand crouch; treatment actions that require empty hands own their own preflight.
- Narc Box medication/contents/vial rows retain one cohesive dark section and scale selection indentation from the actual dialog width.
- Prep Infusion tally layout reads the actual syringe-size list bounds and follows the widened current Narc Box source-column geometry.
- Roller Clamp darkness/NV refresh remains owned by its independent runtime rather than the dialog update function, preventing transition-frame normal-vision sampling from latching an opaque shade over NVGs.

## Body Map and Prepared Syringe Carousel

- Consolidated historical carousel expectations around the current single adaptive five-slot Body Map carousel.
- Retired three-slot mini-carousel and fading-gray underlay remain removed.
- Carousel selection/promotion commits immediately instead of interpolating dozens of controls over 220 ms, reducing client-side UI hitch risk.
- Hover now changes opacity only and cannot resize or shift the syringe under the pointer.
- Compact and promoted carousel tracks use separate toolbar-relative widths, while syringe art keeps the current larger promoted presentation.
- Carousel hit regions are clipped between Edit Syringe Tag and the current Body Map action/duration row so invisible controls cannot cover clinical buttons.
- A/D navigation hints remain noninteractive and move outward when the carousel is promoted.
- Patient-name placement is calculated from the real screen-to-head gap rather than a fixed Y offset.
- Saving a prepared syringe remains on Draw Syringe instead of automatically opening Body Map.
- Body Map uses a patient-name-only header; the selected syringe itself provides medication/tag information.
- Draw Syringe and stored-syringe tag selectors use the syringe's physical tag-face anchor.
- Medicated-flush tag metadata is committed at Save rather than each Draw.
- Dedicated tag editing owns input: A/D navigation and center-toggle are blocked while text/tag editing is active.

## Internal QA

- All 146 original historical backlog entries have now been reconciled or fixed; the original H-ledger is at 0 unresolved after BA-BB.
- Full-suite comparisons are used to ensure previously passing identities do not regress.
- Root-level legacy collection failures are tracked separately from the historical addon backlog.
- Live dedicated-server and multi-client acceptance testing is still required before stable-release sign-off.
