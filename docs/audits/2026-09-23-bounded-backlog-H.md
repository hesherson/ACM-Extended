# Bounded H: active syringe tooltip and memory boundaries

Builds on bounded G from published E-F parent `99da8584547c083c8a882c7786558885d6b8a5f7`. Test-only changes.

H252 and H265 retain their identities but now follow the active record's three tag fields.
They no longer require a retired per-slot tooltip variable. H303 retains the last-two-pulls
contract and now checks it at the actual active-syringe target behind the existing memory gate.
Older unidentified syringes remain "???"; a colored tag preserves the three written lines.
Written marks without a tag color still affect the existing memory rule; they are not falsely
asserted to render as a colored tag. Neighbor hitboxes retain empty tooltips.

37 new cases execute the actual memory function, tooltip selection, formatting and label
fallback helpers, plus four mutation controls that reject wrong fields, disclosure, targets
or history depth even when old text survives in comments. These pass on unchanged runtime.
Store payload preservation is checked. The memory cases cover the exact newest-three boundary,
older marked records and invalid empty-store indices. The existing identity and carousel-input
execution tests remain included, without claiming this isolated tooltip block tests mouse input.

This does not render hover events, measure fonts, resolve real Arma localization or count Unicode
graphemes. No runtime or asset changes. All original unreviewed entries remain verbatim.
The index moves 127 to 124. No new skip or xfail. No stable-release approval.

## Complete-checkout validation

Focused: {'passed': 453}. New cases on unchanged runtime: {'passed': 69}. Full addon before: {'passed': 3856, 'failed': 160, 'skipped': 4}. After: {'passed': 3933, 'failed': 152, 'skipped': 4}. Exactly eight retained historical identities now pass, 69 new cases pass, and no previous identity is missing or newly failing. Both full commands return 1, retaining four existing skips and zero collection/setup errors. Full-project HEMTT check returns 0. All 4051 other existing tracked files retain their SHA256, including every runtime/configuration/asset file and all protected snapshots. Root preservation is included; the entire root-tools suite was not rerun. No live Arma or stable-release approval.
