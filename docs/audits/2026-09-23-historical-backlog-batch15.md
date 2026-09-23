# Historical backlog batch 15: persistent direct-pressure ownership

## Baseline and scope

Starts from published `a488723656d8a370184df56209e55a17bc3901ef`, tree
`544b2f4bebcb97573103e77be0fa14f2723383b1`. All 4,047 tracked baseline paths were
hash-verified before editing. This batch changes tests and the audit index only.
No runtime function, configuration, animation, network protocol or clinical rule changes.

## Historical identities resolved

H131, H372 and H373 retain their original test names and signatures. The old
priority-one-only stop rule and torso-exclusive continuous-action controller are
superseded. Current normal pressure entry is priority one. Only an observed
stuck direct-pressure hold uses the existing priority-two escape on exit.
Persistent direct pressure does not own native continuous-action globals in any
supported region. Incompatible work yields its clinical marker and later resumes
without counting paused time toward pressure/clot progression. Accepted BVM
explicitly releases this provider's pressure; rejected BVM and another provider's
pressure are preserved. These are tests of existing behavior, not new gameplay changes.

## Execution and results

The 31 new SQF-VM cases execute the actual start, marker, tick and stop bodies for
external torso/limb pressure and supported self-pressure sites. They exercise
native global ownership, one-time yield/resume messages, paused timing, normal
entry versus observed-loop exit, and delivery of a retired pressure worker after
replacement. Selected original identities also run the existing native BVM
handoff cases. Focused result: **34 passed**, no failures/errors/skips.

Object identity, input, animation state, network delivery and wound-loss
integration are explicit fixtures. No Arma animation, hemorrhage physiology or
live dedicated-server result is claimed. No test is skipped or marked expected-failure
because it remains unresolved.

The original source-contract index decreases from 146 to **143**. Combined
before/after suite results and remaining release boundaries are recorded in the
Batch 17 report. This batch alone does not require a gameplay rebuild.
