# Bounded AB: former-owner animation broadcast

Builds on bounded AA. The provider finalizer already cleared its private, non-public flags after losing locality, but also broadcast an animation-speed reset. That broadcast could reach the provider after another machine owned it.

The correction preserves every private retirement operation, including active/mode/stage cleanup, head-owned DP pause cleanup and pin-token retirement. It checks locality only before the existing global animation-speed event. Suppressing private retirement as well would leave stale locks on this machine, so that broader candidate was rejected during review. Normal local finalization is unchanged. Only headElevMedicSeq changes runtime, with no added timer, state key, network operation, animation or patient/gear rule.

Ten full-source execution cases use explicit locality/animation/network fixtures: 8 fail and 2 pass on original Y-Z runtime, all pass after correction. They cover both modes and four provider stages, no former-owner global event, intact private flag/pause/token cleanup, unchanged casualty placement, and still-local unconscious retirement. This does not migrate controllers, certify new-owner initialization, or handle ownership leaving and returning between PFH ticks. Those remain open. No live Arma or stable-release approval.

## Complete-checkout verification

{
  "base": "436075c2c93d6f808993f6ad24e55e0328a617dd",
  "AA": "482170008caa34aa64df27e99ec3a03f969da540",
  "AA_original": {
    "failed": 32,
    "passed": 8
  },
  "AB_original": {
    "failed": 8,
    "passed": 2
  },
  "focused": {
    "passed": 135
  },
  "addon_before": {
    "passed": 4415,
    "failed": 105,
    "skipped": 4
  },
  "addon_after": {
    "passed": 4470,
    "failed": 104,
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
    "H343"
  ],
  "remaining_original_entries": 76,
  "new_passing_cases": 54,
  "missing_previous": [],
  "newly_failing": [],
  "runtime_files_changed": [
    "addons/acm_extended/functions/fn_headElevMedicSeq.sqf"
  ],
  "changed_existing": [
    "addons/acm_extended/functions/fn_headElevMedicSeq.sqf",
    "addons/acm_extended/tools/test_b71_tag_head_intubation.py",
    "addons/acm_extended/tools/test_bounded_head_provider_sequence.py",
    "docs/audits/historical-backlog-remaining-20260922.txt"
  ],
  "unchanged_existing_files": 4094,
  "hemtt_exit": 0,
  "live_arma_tested": false,
  "stable_release_approved": false
}

The full addon and root suites remain failing overall. No new skip or xfail. Fixtures record requests, not live UI, RTM, PhysX, networking or gear behavior. Protected snapshots are unchanged.
