# Bounded AJ: timed push and native cardiac authority contract

Builds on AI. H327 retains its historical identity. Its obsolete assertions demanded a three-second ctrlCommit inside BeginInjection and the retired Extended minimum-HR floor. The check now follows explicit staging, timed confirmation and the native cardiac state-machine authority. It executes normal IV/IO/IM timing and the existing observer noninterference cases rather than restoring a retired floor or direct arrest dispatch.

Nine new cases pass on unchanged AG-AH runtime: five execute the actual observer using the existing full-source fixture; four mutation checks reject early administration, direct arrest dispatch, an observer heart-rate write or restoring the retired floor. The previous cardiac machinery and every clinical threshold are untouched. No runtime change in AJ. The ledger moves 70 to 69; every other H entry and historical body remains intact. No skip/xfail added.

These fixtures do not certify clinical calibration, actual ECG pixels or live multiplayer; both broad suites remain failing overall. No stable-release approval.

## Complete-checkout validation

```json
{
  "base": "f611ac7cf346da659534b47f34d79cdb3eab4bd2",
  "AI_original_runtime": {
    "passed": 21,
    "failed": 13
  },
  "AJ_original_runtime": {
    "passed": 9
  },
  "focused": {
    "passed": 233
  },
  "addon_before": {
    "passed": 4618,
    "failed": 98,
    "skipped": 4
  },
  "addon_after": {
    "passed": 4662,
    "failed": 97,
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
    "H327"
  ],
  "remaining_original_entries": 69,
  "new_passing_cases": 43,
  "missing_previous": [],
  "newly_failing": [],
  "runtime_files_changed": [
    "addons/acm_extended/functions/fn_skConfirmInjection.sqf",
    "addons/acm_extended/functions/fn_skInjectSite.sqf"
  ],
  "changed_existing": [
    "addons/acm_extended/functions/fn_skConfirmInjection.sqf",
    "addons/acm_extended/functions/fn_skInjectSite.sqf",
    "addons/acm_extended/tools/test_b68_syringe_tag_push_layout.py",
    "addons/acm_extended/tools/test_b69_narcbox_carousel_visibility.py",
    "docs/audits/historical-backlog-remaining-20260922.txt"
  ],
  "unchanged_existing_files": 4109,
  "hemtt_exit": 0,
  "live_arma_tested": false,
  "stable_release_approved": false,
  "AI": "817439db51e8ed74171f953299ff5b05ac54815a"
}
```

The same full checkout and pinned toolchain were used for both sides. Every previous raw JUnit identity is retained. Protected snapshots are unchanged. HEMTT is not a release-package or live-engine acceptance test.
