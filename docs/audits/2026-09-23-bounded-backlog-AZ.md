# Bounded AZ: tally geometry and clamp vision ownership

AZ reconciles H429 and H439.

- H429: the Narc Box source columns were deliberately widened from the historical 1/6.5 safe-zone layout to `_uiW / 5.25`, preserving fixed inner edges with `_columnInner = _uiW / 3.3`. Prep Infusion tally geometry reads the actual size-list rectangle, so the test now protects the current adaptive layout rather than the retired ratio copy.
- H439: IV, chest seal, thoracostomy, laryngoscopy, syringe-kit and Narc Box ticks still end in their minigame vision pass. Roller Clamp is intentionally different: `fn_updateClampDialog.sqf` does not sample vision during dialog transition; `fn_registerClampDragRuntime.sqf` owns the settling/10 Hz darkness and NV refresh. This prevents the transition-frame NV blackout regression.

No runtime files change in AZ.
