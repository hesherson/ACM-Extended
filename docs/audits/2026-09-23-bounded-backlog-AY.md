# Bounded AY: equipment, cuff and menu contract reconciliation

Parent: `d86ff5c3d35bedb6a44839e38f620ed965fd4cde` (validated AW-AX).

AY reconciles H137, H194, H195, H209 and H214 with the current implementation.

- H137: the laryngoscopy cuff syringe uses ACM's real PBO path for backbit and plunger, while the barrel intentionally uses ACME's replacement saline-flush artwork. The old assertion incorrectly required ACM's generic barrel as well.
- H194: the replacement 10 mL flush barrel is present in both the cuff view and the native draw dialog. The draw dialog now chooses the replacement only for a selected prefilled flush and restores ACM's generic medication barrel otherwise, so the historical direct literal ctrlSetText assertion was stale.
- H195: cuff pilot-balloon anchor, syringe-tip anchor and one-second hold remain authored in `fn_laryngoCuff.sqf` as local missionNamespace fallbacks. The plunger now starts at the 8 mL mark, so its travel includes the current start fraction rather than the retired full-10 mL formula.
- H209: simply opening another patient's medical menu no longer holsters the provider's weapon. The provider enters the matching weapon-in-hand crouch through `ACME_fnc_doAnim`; treatments that require empty hands own their own preflight.
- H214: the Narc Box cohesive row section retains its dark backing, shared medication columns and selected-row indent. The indent is now scaled from the actual dialog width (`_uiW / 240`) instead of global safeZone width.

No runtime files or assets change in AY.
