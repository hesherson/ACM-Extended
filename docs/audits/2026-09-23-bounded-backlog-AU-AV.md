# Bounded AU-AV: animation/provider contract reconciliation

Parent: `6f4324e0eebf6c55b498c68cedbdc94491b02b10` (validated AS-AT).

## Scope

This batch reconciles twelve historical animation/provider source-contract entries with the current controller architecture:

- H132: ordinary provider transitions are controller-owned priority-one `ACME_fnc_doAnim` entries; the old explicit animation queue assertions are retired.
- H133: HPMK wrapping is intentionally state-only and no longer rolls or physically animates the casualty.
- H134: CPR is native ACM-owned; ACME no longer carries a CPR animation override.
- H135: switchMove remains only for exact held-frame/state-lock repair and chest-roll resting-state ownership, not ordinary provider entry.
- H156: physical-roll provider theatre deliberately uses the known-good literal BI medic4 state after shared empty-hands/crouch preflight rather than requiring the compatibility wrapper as the live state.
- H179: stethoscope hold ownership is verified through the current treatment-pose episode, owner/observer freeze, and idempotent release lifecycle.
- H181: roll-provider hold timing is 2.2 seconds, not the retired 2.5-second value.
- H189: chest-roll provider entry is the literal BI medic4 state at priority one; priority two is not used for ordinary provider work.
- H190: response and airway checks use the current ACME_ResponseCheckWork and ACME_AirwayCheckWork wrappers while retaining authored treatment durations.
- H366: roll provider uses shared crouch/empty-hands preflight plus literal medic4, with no priority-two provider entry.
- H369: head positioning and chest roll now use named ACME patient states / owner-scoped animation leases rather than requiring raw historical grab/release literals at specific call sites.
- H370: priority-two animation is permitted only as a scoped state-graph repair/lock, while ordinary provider entry remains priority one.

No runtime SQF, configuration, treatment timing, animation timing, networking, or patient-state behavior changes in AU-AV. Only historical regression contracts, ledger accounting, audit documentation, and cumulative patch notes change.

Live RTM rendering remains outside source validation.
