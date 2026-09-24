# Residual backlog BE: full-suite historical contract reconciliation

Parent checkpoint: `222cf9c94e7994991aadc16bbf0014e9062a461b` (residual BD).

The first complete addon-suite run after restoring Python test dependencies reached execution and reported 23 failures with 2,560 passing tests. BE reconciles those 23 failures against the current shipped contracts without changing runtime SQF, config, networking, assets, treatment logic or release packaging.

## Reconciled contracts

- IO pain: placement remains pain-only; actual IO fluid flow retains the later delayed, owner-local syncope contract.
- Narc Box geometry: historical 1/6.5 safe-zone width assertions now protect the current widened canvas-relative 1/5.25 columns.
- Stethoscope: provider-pose retirement remains presentation-only and cannot terminate the scope.
- PPV/BVM: pleural context uses the shared server-time `ACME_bvm_lastBreathServer` delivery marker.
- Medical menu: normal treatment rows arm pending reopen; Direct Pressure apply/stop remain immediate in-place exceptions.
- Hang Bag: provider props/held animation begin only after patient-owner lease acceptance in `fn_hangBagActivate.sqf`.
- Prepared-syringe carousel: current navigation is immediate, with no retired slide/nudge interpolation; the promoted state uses the current 1.35 s browse lifetime.
- Corpse medication transactions: requests remain callable and are acknowledged for inventory/accounting, but terminate before medication physiology is created.
- Compound Save: the Narc Box resets in place immediately; only the short 0.45 s Saved! presentation is delayed. Medicated flush Save retains its separate 1.10 s handoff.
- Head positioning: retired DraggerBase provider lift expectations are replaced by the shared exact-once Putdown sequence and current one-shot weapon preflight.
- Hardcore settings audit: `ACME_hc_medications` was present in runtime/settings but missing from the NA6 audit catalog. The catalog now includes all 15 individual Hardcore checkboxes while the 14 tuning-effective flags correctly exclude Clinical Descriptors.
- RPT audit: later reliability/error diagnostics are protected by an exact file/count whitelist rather than the obsolete zero-emitter rule.
- EJ descriptors: the compatibility wrapper delegates to `fn_updateTransfusionAccessHotspots.sqf`, which owns descriptor-aware labels.
- Roller Clamp NV: darkness/focus refresh remains intentionally outside `fn_updateClampDialog.sqf` and inside the independent clamp runtime, preserving the hosted-server NV-blackout fix.
- Semi-Fowler death: current death cleanup uses the authored normal lay-flat release animation while still forbidding teleport/damage mutation.
- AAJT application clocks: replicated application markers use `serverTime`, not local `time`.

BE is test/audit-only. The next full-suite run is required before the residual count can be reduced from the observed 23 failures.
