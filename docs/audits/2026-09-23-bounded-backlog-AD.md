# Bounded AD: staged site selection and explicit timed confirmation

Builds on AC. H319 and H380 retain their original pytest identities.

Site selection stages a target without starting a push or locking syringe selection. The explicit action button starts the push for the then-selected syringe. Normal confirmation defaults to three seconds, retains typed vascular timing, interpolates individual plunger frames and hands off only after the captured duration. The historical tests no longer demand immediate administration in BeginInjection or ctrlCommit 3.0.

Eleven new cases verify actual BeginInjection for IV/IO/IM, rejected staging without target mutation, and source mutations that reject immediate flow, a wrong target, a changed default, IM timing override or a lost duration argument even when old text survives in comments. These eleven cases pass against unchanged runtime. AC's full-confirmation cases cover normal duration and handoff behavior. No runtime changes in AD; the two reviewed historical assertions are reconciled, not removed. The ledger moves 76 to 74, keeping every other entry verbatim. No skips or xfails added. No live Arma or stable-release approval.

## Complete-checkout validation

```json
{
  "base": "bf745808d8e92c56af211a1b32d315174a155004",
  "AC_original_runtime": {
    "failed": 21,
    "passed": 16
  },
  "AD_original_runtime": {
    "passed": 11
  },
  "focused": {
    "passed": 199
  },
  "addon_before": {
    "passed": 4470,
    "failed": 104,
    "skipped": 4
  },
  "addon_after": {
    "passed": 4520,
    "failed": 102,
    "skipped": 4
  },
  "root_before": {
    "error": 46,
    "passed": 137
  },
  "root_after": {
    "error": 46,
    "passed": 137
  },
  "resolved_original_ids": [
    "H319",
    "H380"
  ],
  "remaining_original_entries": 74,
  "new_passing_cases": 48,
  "newly_failing": [],
  "missing_previous": [],
  "runtime_files_changed": [
    "addons/acm_extended/functions/fn_skConfirmInjection.sqf",
    "addons/acm_extended/functions/fn_skClose.sqf"
  ],
  "changed_existing": [
    "addons/acm_extended/functions/fn_skClose.sqf",
    "addons/acm_extended/functions/fn_skConfirmInjection.sqf",
    "addons/acm_extended/tools/test_b68_syringe_tag_push_layout.py",
    "addons/acm_extended/tools/test_b76_carousel_push_memory.py",
    "docs/audits/historical-backlog-remaining-20260922.txt"
  ],
  "unchanged_existing_files": 4097,
  "hemtt_exit": 0,
  "live_arma_tested": false,
  "stable_release_approved": false,
  "AC": "0a85c1cedcb1034983e44505198fe516fa0b3ae6"
}
```

Both broad suites remain failing overall. Root identities and outcomes are unchanged, with no new skip or xfail. Engine boundaries are explicit fixtures, not live Arma or release-package validation.
