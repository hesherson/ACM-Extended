# Bounded AH: native draw endpoints and non-competing UI repair

Builds on AG. H334 and H363 retain their original pytest identities. They demanded exact-endpoint writes from the old UI tick. Current native drag owns the zero/vial-ceiling snap; the UI tick supplies stock bounds and delegates staged overage to syringeDrawSetAmount instead of acting as a competing plunger writer. Existing compound-floor assertions are retained.

Thirty-five new checks pass on unchanged native runtime: twenty execute the actual moving block across four syringe sizes and five hand positions; four verify that both volume and pixel proximity are needed before rounding to an endpoint; six exercise the actual UI repair branch at/below/above its tolerance; five reject mutated limits, endpoint values, guards or direct-write regressions despite comment decoys. Same-frame vial-limit lookup, bounded hit-control geometry and the visual plunger offset remain checked.

Engine controls, mouse input, resolution and linearConversion use explicit numeric fixtures. VialSession and stock-repair calls are recorded, not real inventory transactions. The tests verify exact numeric amount endpoints and bounded geometry, not pixel-perfect rendering, glyphs, arbitrary malformed values, live regrab/input scheduling or a full compound-drug transaction. No native draw, UI tick, dose, configuration or asset changes in AH. The ledger moves 72 to 70; every other H entry remains verbatim. No new skip or xfail. No stable-release approval.

## Complete-checkout validation

```json
{
  "base": "dd294e53c7fb850c31dde42454adbbd92c4e1bb3",
  "AG_original_runtime": {
    "failed": 15,
    "passed": 8
  },
  "AH_original_runtime": {
    "passed": 35
  },
  "focused": {
    "passed": 154
  },
  "addon_before": {
    "passed": 4558,
    "failed": 100,
    "skipped": 4
  },
  "addon_after": {
    "passed": 4618,
    "failed": 98,
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
    "H334",
    "H363"
  ],
  "remaining_original_entries": 70,
  "new_passing_cases": 58,
  "newly_failing": [],
  "missing_previous": [],
  "runtime_files_changed": [
    "addons/acm_extended/functions/fn_skConfirmInjection.sqf",
    "addons/acm_extended/functions/fn_skInject.sqf"
  ],
  "changed_existing": [
    "addons/acm_extended/functions/fn_skConfirmInjection.sqf",
    "addons/acm_extended/functions/fn_skInject.sqf",
    "addons/acm_extended/tools/test_b70_semifowler_bvm_thora_syringe.py",
    "addons/acm_extended/tools/test_b73_syringe_tag_vial_carousel_anim.py",
    "addons/acm_extended/tools/test_bounded_normal_push_lifetime.py",
    "docs/audits/historical-backlog-remaining-20260922.txt"
  ],
  "unchanged_existing_files": 4104,
  "hemtt_exit": 0,
  "live_arma_tested": false,
  "stable_release_approved": false
}
```

Both broad suites remain failing overall. Full before/after JUnit retains all previous identities with no new failures. Root identities/outcomes and protected snapshots are unchanged. HEMTT is a source/build check, not a live Arma or release-package acceptance test.
