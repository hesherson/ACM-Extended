# Bounded AF: exact site click and current-syringe confirmation

Builds on AE. H276 and H292 retain their original pytest identities. Their immediate-administration assumptions predate the explicit staging/confirmation workflow. The tests now follow the actual site-click -> BeginInjection -> ConfirmInjection handoff instead of restoring immediate delivery.

Fourteen new cases pass on unchanged medication runtime. They execute the complete click, staging and normal-confirmation functions with the authoritative skInjectSite call recorded. Cases cover exact IV/IO site checks, IM without vascular access, changing the selected stable syringe after staging, retained three-second default and no premature handoff, rejection of removed access without changing the pending target, and the separate selected-flush dispatch. Four mutation controls reject immediate medication delivery, the wrong IV index, a lost flush branch and a removed busy guard even when correct old tokens remain in comments.

The two historical bodies now check executable call targets, current stable selection, busy/route guard context and the existing timed-confirmation contract. They are not dropped, skipped or xfailed. All other historical test bodies remain intact. The original index moves 74 to 72; every other H line remains verbatim.

No runtime changes in AF. These checks do not render or click an Arma hotspot, administer medication, debit inventory, flush an actual line, simulate live event propagation, or cover every changed-patient/epinephrine UI path. Source checks are not a substitute for live acceptance testing. No live Arma or stable-release approval.

## Complete-checkout validation

```json
{
  "base": "a0f065f64952143015341bf818eb8061994f2e37",
  "AE_original_runtime": {
    "failed": 16,
    "passed": 6
  },
  "AF_original_runtime": {
    "passed": 14
  },
  "focused": {
    "passed": 86
  },
  "addon_before": {
    "passed": 4520,
    "failed": 102,
    "skipped": 4
  },
  "addon_after": {
    "passed": 4558,
    "failed": 100,
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
    "H276",
    "H292"
  ],
  "remaining_original_entries": 72,
  "new_passing_cases": 36,
  "newly_failing": [],
  "missing_previous": [],
  "changed_existing": [
    "addons/acm_extended/functions/fn_skClose.sqf",
    "addons/acm_extended/functions/fn_skInject.sqf",
    "addons/acm_extended/tools/test_b63_tag_carousel_interaction.py",
    "addons/acm_extended/tools/test_b64_syringe_tag_carousel_refinement.py",
    "addons/acm_extended/tools/test_bounded_normal_push_lifetime.py",
    "docs/audits/historical-backlog-remaining-20260922.txt"
  ],
  "runtime_files_changed": [
    "addons/acm_extended/functions/fn_skInject.sqf",
    "addons/acm_extended/functions/fn_skClose.sqf"
  ],
  "unchanged_existing_files": 4100,
  "hemtt_exit": 0,
  "live_arma_tested": false,
  "stable_release_approved": false,
  "AE": "1735f62063e6f030e4fa21f167bd3453c76ce965",
  "broad_comparison_source_run": 35927614107,
  "broad_comparison_artifact_sha256": "9f4ad7841f81f798cdec13a8035b70b0e1047ab0d1eabde163b1d4a5d6a9b16c",
  "final_formatting_only_difference": "One extra EOF newline removed from test_b64_syringe_tag_carousel_refinement.py; AST and all runtime bytes unchanged.",
  "fresh_after_formatting": [
    "original-runtime controls",
    "focused 86 tests",
    "HEMTT check",
    "diff check",
    "complete file preservation"
  ]
}
```

Both broad suites remain failing overall. All previous raw JUnit identities remain comparable, with no new skip or xfail. Protected snapshots are unchanged.
