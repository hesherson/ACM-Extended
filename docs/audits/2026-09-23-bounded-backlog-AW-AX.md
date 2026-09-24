# Bounded AW-AX: high-value airway/chest ownership pass

Parent: `0a138fc5a2212f4507b77d6c8028cccc168d251e` (validated AU-AV plus patch-note-only commit).

## AW runtime correction

H389 identified a real fail-open path in `fn_chestSealFlip.sqf`. If provider roll theatre could not acquire, the button handler directly dispatched `ACME_fnc_chestSealRoll`, allowing the casualty to roll before the provider had entered the authored medic4 work state.

The fail-open roll is removed. A failed provider acquisition now:
- clears the pending Flip token, target and UI lock;
- re-enables the Flip button;
- restores the persistent hands-on-chest provider hold when possible;
- releases the Direct Pressure handoff if this click paused it;
- does not change the patient-facing side or dispatch any patient animation.

The physical roll remains exclusively dispatched by `fn_chestSealFlipTick.sqf` after the current provider episode/token and exact medic4 animation state are observed.

A dedicated mutation contract rejects restoration of either direct fail-open roll form.

## AX contract reconciliation

- H339: B120 intentionally allows laryngoscopy on perfusing/awake casualties. Reflex, sedation, paralysis, gagging and bucking are handled by the procedure rather than hiding the menu action.
- H341: Elevate/Lower Head are Head-only, set `ACM_rollToBack = 0`, and the current core treatment bridge passes the selected body part through unchanged. ACME's own head-position start owns actual-prone-to-supine normalization.
- H386: CPR and BVM are routed through `addons/core/overrides/fnc_treatment.sqf` into `ACM_core_fnc_treatmentNative` before generic provider preflight. No ACME CPR/BVM continuous-action replacement is restored.
- H390: both traumatic-seal and thoracostomy burp paths are patient-owner gated and use the no-timer `chestSealBurpReady` predicate. Neither path reuses the seal-placement medic3 theatre. A dead legacy thoracostomy `chestSealBurpGesture` dispatch was removed.

Live multiplayer, RTM rendering and PhysX behavior remain outside source validation.
