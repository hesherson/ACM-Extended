# Historical backlog batch 17: Semi-Fowler lower-completion collision ordering

Parent: `9bc73aa7cb7f9c8a7a394fc9114b4ee5b2bf8f2c`. Combined batches 15-17 start from published
`a488723656d8a370184df56209e55a17bc3901ef`, tree `544b2f4bebcb97573103e77be0fa14f2723383b1`.
They are prepared on `fix/backlog-batches15-17-20260923`, not on main.

## Confirmed runtime defect and minimal correction

An old visible Lower Head callback called headElevCollision(true) before checking
whether the casualty had been elevated again. The subsequent guard already
protected the newer placement's carrier and pose, but not its collision window.
A newer lift can deliberately have collision disabled while its body moves.

The existing re-elevation guard now runs **before** collision restoration. This
is the only runtime change across all three batches: two existing statements are
reordered in fn_headElevateStop.sqf, with an explanatory comment. No timing,
priority, animation, loadout algorithm, network field/message, polling worker,
clinical eligibility rule, version label or action ownership is added or retuned.

Two unchanged-runtime cases reproduce an old lower callback changing collision
after a new elevation has begun, including the suspended flag variant. All 18
new head-elevation cases pass with the correction; the same cases on unchanged
runtime produce **2 failed and 16 passed**. New-placement owner flags are explicit
fixtures, while the actual new lift and old lower-completion bodies execute.
This records collision commands, not physical impulses in Arma.

## Historical identities resolved

H350, H351 and H453 retain their names and signatures. Tests now use the current
ACME patient grab/release wrappers, rather than obsolete raw BI state spellings
or a removed animQueue call. They execute current pickup priority, startup grace,
pose-token checks, suspension/death/locality rejection, observed-hold repair,
quiet versus visible lowering, deferred carrier restoration and dead-casualty
delegation before living provider/pose work. Token/death/owner guards in the lift
function are not changed. The actual dedicated corpse-cleanup implementation is
not rewritten or replaced by the living lower sequence.

The Batch 17 focused selection, including current preservation checks, passes
**98 tests**. Only fn_headElevateStop's reviewed snapshot digest changes here.
The original unresolved source-contract index decreases from 138 to **135**.
H452 remains open; these tests do not claim the entire elevation lifecycle is safe.

## Combined validation: batches 15-17

| Historical addon suite | Unchanged baseline | Candidate |
| --- | ---: | ---: |
| Failed outcomes | 175 | 164 |
| Passing tests | 3,722 | 3,815 |
| Passing subtests | 5,518 | 5,518 |
| Collection/setup errors | 0 | 0 |
| Skips | 4 | 4 |

Both broad commands return **1**. The remaining failures are open, not waived.
The outcome-identity comparison finds exactly the 11 selected historical failures
now passing, no new failures, no formerly passing outcome regressions, and no
missing previous identities. The existing four skips are unchanged.

The retained Batch 14 focused selection plus all 82 new cases, all 11 selected
historical identities and the repaired root collection probe passes **1,823 tests
plus 400 subtests**, with no failures/errors/skips. The 82 new cases copied onto
unchanged runtime give **2 failed / 80 passed**. They are verification of current
contracts except for the two cases exposing the one runtime ordering defect.

Full-project **HEMTT 1.22.0 check returns 0**, with the same seven nonblocking
style suggestions. SQF-VM is v2026.04.03-ed9f5f5. Existing test identities,
signatures, decorators, other test bodies and module behavior are preserved; an
AST comparison permits only the 11 reviewed bodies. The root assertion and two
snapshot updates are checked separately. The final change set contains 19 paths:
13 changed existing paths and six additions. All **4,034 other existing tracked
paths remain byte-identical**, with no files deleted.

## Boundaries and remaining work

The correction is deliberately narrow. It does **not** establish generation safety
when a new elevation has itself already been lowered before the old callback is
delivered. Initial pre-roll retry callbacks, callback behavior across full heal or
owner-away-and-back sequences, newer stethoscope display leases, and interruption
of carrier choreography require separate work. In particular, H452 is retained in
the unresolved index rather than satisfied by a superficial token-count assertion.

No Arma client, dedicated server, release PBO or Workshop deployment was run.
This is **not stable-release sign-off**, and main is not changed by these batches.
Only Batch 17's runtime correction needs a rebuild. In-game testing should compare
ordinary visible/quiet lowering and gear return with a lower-then-re-elevate action
before the earlier lower completion fires. Verify collision behavior and provider/
patient choreography on a dedicated server before promoting this branch.

Local raw logs, JUnit/outcome streams, the unchanged-source control, scope proof,
resolved identity list and reviewed patch are retained in the accompanying evidence
package. The final branch's clean-checkout validation is reported separately with
its exact workflow run and commit, not inferred from a green focused subset.
