# Bounded F: medication preparation UI ownership

Builds on bounded E. Test-only changes.

H044, H165, H175, H186, H188 and H203 retain their original identities. Their obsolete assumptions demanded a visible native selector, always-visible Body Map source groups or metadata-only labels. Current runtime uses the native list as hidden backing, one custom Medication/Contents/Vials group, live native labels with key-based metadata fallback, and a dedicated administration Body Map. Prep Infusion normalizes to preparation and suppresses flush sources without suppressing medication.

Thirty-one new cases execute the actual view-normalization prefix and row-visibility block or the complete infusionDrawStock function with explicit UI-boundary fixtures. They cover all three view inputs, normal/prepared mode, size/flush/medication groups, zero/partial/negative bounded draw values, moving or pending injections and allowed medication gating. Partial draws cannot trigger a backing-selector resync. Refresh does not change drawn volume or medication identity. Three negative source checks reject a wrong row target, visible native selector or wrong metadata join even with comment decoys. The existing medication-row execution tests enforce label fallback, deduplication and exact physical-vial stock preview.

The new cases pass on unchanged runtime. This is stale-test reconciliation, not six new gameplay fixes. Visibility requests do not prove rendered pixels, clipping, scrolling, real input focus or multiplayer transport. Negative finite inputs are covered; NaN/Inf engine validation is not simulated. The original index moves 138 to 132. All runtime/configuration/assets and other original entries remain unchanged. No skip or xfail is introduced; no stable-release approval.

## Complete-checkout validation

Focused: {'passed': 330}. Full historical addon before: {'passed': 3797, 'failed': 169, 'skipped': 4}. After: {'passed': 3856, 'failed': 160, 'skipped': 4}. Exactly nine historical identities now pass, all 50 new cases pass, and no prior identity is missing or newly failing. Both full-suite commands still return 1 with four existing skips and zero collection/setup errors. Full-project HEMTT check returns 0. All 4045 other existing tracked files retain their complete-checkout SHA256, including every runtime/configuration/asset file. The root preservation module is included; the entire root-tools suite was not rerun. No live Arma or stable-release approval.
