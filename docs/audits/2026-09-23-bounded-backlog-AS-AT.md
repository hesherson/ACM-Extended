# Bounded AS-AT: medical-menu presentation contract reconciliation

Parent: `6b84cc4024d394a4c31523fd7c4d386bb14680ef` (validated AM-AR).

## Scope

This batch reconciles five historical source-contract entries with the current medical-menu design:

- H120: Elevate Head and Lower Head are intentionally Head-only actions. The earlier Head+Body placement was retired to prevent duplicate posture actions on the chest.
- H121 / H140: ordinary action rows are intentionally uniform white. The earlier alternating pale-red row treatment was removed because it visually implied warning/error state on normal actions.
- H139 / H148: auscultation no longer depends on a dedicated Chest Inspection examination group. Clinical-descriptor paint still renames the stethoscope action to Auscultate Chest, and if a caller already presents it as a grouped child the renderer preserves exactly one child indent rather than forcing a group or accumulating indentation.

The Accessibility setting description is corrected to say that regular action rows use uniform white text. This is a wording correction only; the renderer already used uniform white.

No treatment eligibility, medical callbacks, animations, networking, medication logic, patient state, or menu colors are changed by this batch.

## Validation intent

Focused tests must verify:
- posture actions remain in Examine and are Head-only;
- the renderer defaults both ordinary-row color slots to white;
- the CBA setting text matches that behavior;
- Auscultate Chest remains a paint-time clinical descriptor;
- no retired Chest Inspection group is reintroduced;
- existing grouped-child indentation is preserved exactly once.

The full addon suite, root suite, HEMTT check, and previous-identity comparison are run in CI before publishing the validated checkpoint. No live Arma acceptance is claimed.
