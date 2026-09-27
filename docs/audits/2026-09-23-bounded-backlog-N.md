# Bounded N: connected patient animations and non-teleporting recovery contracts

Builds on bounded M from K-L parent `2fcd3e987eba4b7fd8a2ff5ba25d236983777431`.
Test-only changes in this batch. Six original test identities are retained:
H329, H350, H351, H415, H416 and H453.

The active grab/hold/release wrappers inherit the original BI grab/release states.
The zero-speed hold and connected supine release are intentional; tests now follow
that inheritance rather than demanding the raw base animation names in callers.
Priority-two entry/release and the existing startup grace are preserved. The old
helper-creation and cached-ASL-teleport expectations are replaced by the current
legacy-helper retirement and no-patient-teleport requirements. Dead-patient Lower
Head delegates to death recovery before living animation/restore work; the test
no longer requires a retired animQueue call as its source-ordering anchor.

Thirty new cases execute actual lift/hold callbacks or mutation-check token/config
contracts. Coverage includes current versus already-visible holds, invalid nonpositive
or wrong-type lift duration fallback, pose/life/locality/suspension invalidation,
legacy-helper deletion and recorded mass recovery, no-replay cleanup and priority,
teleport/helper/guard mutations with comment decoys. The existing 20 completion
execution cases from M verify both normal and stale completion boundaries.
The six original assertions fail before reconciliation and pass after it.

No other historical test body is changed, no skip/xfail is added and the other H
entries remain verbatim. The original index moves 115 to 109. The test names remain
historical identifiers; their retired positive-teleport assumptions are not restored.

The fixtures record engine-boundary calls, not RTM rendering, PhysX mass effects,
actual helper attachment or inventory writes. New N cases pass on unchanged K-L
runtime. Pre-roll callback generations, same-state lifecycle round trips and actual
multiplayer behavior remain open. No live Arma or stable-release approval.

## Complete-checkout validation

Focused: {'passed': 308}. M controls on original runtime: {'failed': 6, 'passed': 14}; N checks on original runtime: {'passed': 30}. Full addon before: {'passed': 4041, 'failed': 143, 'skipped': 4}; after: {'passed': 4097, 'failed': 137, 'skipped': 4}. Exactly six retained historical identities now pass and 50 new cases pass. No new failure or missing prior identity. Both full addon commands remain failing overall with four unchanged skips and zero collection/setup errors. Root before: {'error': 46, 'passed': 137}; after: {'error': 46, 'passed': 137}, with identical normalized identities and outcomes. Only the two reviewed digest-valued snapshot labels are normalized; raw JUnit remains in evidence. HEMTT check returns 0. Only the two documented collision-order runtime edits are present; 4062 other existing tracked files retain their SHA256. No live Arma or stable-release approval.
