# Non-ledger BC-BD: current UI timing and geometry reconciliation

Parent: `586271f324d74cace5f8d845065ee6e4499f1774` (BA-BB, original historical ledger at zero).

This bounded pass addresses eight remaining addon-suite failures that are **not** part of the original H-ledger.

- B20 / B22 Narc Box geometry: current medication/source columns are intentionally `_uiW / 5.25` with fixed inner edges at `_uiW / 3.3`. The retired 1/6.5 safe-zone width and final-syringe-name controls are not restored.
- B64 carousel movement: prepared-syringe navigation is immediate. The retired 135 ms physical slide and single-syringe nudge were removed to avoid client UI hitches.
- B66 carousel linger: promotion now commits immediately and remains expanded for 1.35 seconds after navigation; hover/retention refreshes a 0.90-second collapse deadline.
- B73 compound Save: a compound is committed and a fresh preparation session is initialized in place immediately. The nonblocking Saved! flash lasts 0.45 seconds; the old WasteEnd teardown/reopen path is not restored.
- B76 feedback timing: medication Draw feedback remains 1.00 second, compound Save acknowledgement is 0.45 seconds, and medicated-flush Save keeps its 1.10-second close/reopen handoff.
- NA8.5 darkness ownership: Roller Clamp vision/darkness refresh remains in `fn_registerClampDragRuntime.sqf`, not `fn_updateClampDialog.sqf`, specifically to avoid sampling transient normal vision during dialog creation and recreating the NV blackout.

No runtime SQF, configuration, assets, gameplay timing, networking or physiology changes in BC-BD.
