# B284: syringe stop and acknowledgement settlement

Version **1.2.4.1**, build **B284**, network protocol **1**.
Baseline: B283, `41975761697fcc50e856166df10a4ae5f442bcf4`.

## Corrected behavior

- A manual/completion stop whose final batch cannot be constructed before dispatch returns its known unsent tail to the same syringe. It releases the stopped controller and does not report a successful completed push.
- Stops and plunger ticks retain their captured session and handler identity across synchronous callbacks. A synchronous acknowledgement cannot recreate an empty controller after finalization or retirement. A replaced controller keeps its own inventory, controls, overlay and worker. A failed refund retires the original evidence and exits before global finalization.
- Refunds validate every component, source/index, finite nonnegative volume, current mixture total and syringe capacity before one private store write. A missing/changed component or failed writer cannot report a successful partial refund.
- Rejected patient aliquots and unsent plunger travel are validated individually and restored together. The exact request, pending count and both deltas remain available when restoration fails.
- Medication acknowledgement removes the canonical syringe escrow only after settlement succeeds. A private exact-request guard prevents synchronous duplicate acknowledgement from reentering a refund.
- A deliberate fresh-kit reset invalidates the old syringe settlement while preserving its immutable patient request until a terminal acknowledgement arrives. That acknowledgement closes the old accounting without refunding into the replacement kit or retrying forever.
- Active settlement checks its provider, syringe identity, patient receipt, session, equipment kit, locality epoch and provider owner. Known local rejection before patient dispatch is retained as unsent evidence; it does not wait for a nonexistent patient acknowledgement.

These checks preserve dose/carrier conservation. Native inventory placement and patient medication delivery retain their existing broker/owner paths. Private plunger updates do not become public per-frame traffic.

## Validation

The added SQF-VM regressions execute production Stop, SendBatch, RestoreDelta, acknowledgement, archive recovery, store and token settlement code. Engine inventory, displays and CBA transport are explicit fixture boundaries. Cases include failed batch construction, malformed/currently edited mixtures, failed writes with later retry, duplicate acknowledgements, foreign provider/kit periods and synchronous successor sessions. Existing numerical and retired-syringe cases remain required.

The historical medication-accuracy fixture now returns `true` from its successful mocked store writer, matching the production writer's Boolean result. No clinical expectations are relaxed.

The supplied ACM, ACE3 and Animate archives were inspected as read-only integration references. Recovery does not replay treatment-success callbacks or animation entry/exit. Source validation and automated tests do not certify native multiplayer transport or PhysX.

## Remaining acceptance boundaries

This change does not implement syringe provider-ownership migration. Machine-local plunger state and accepted claims whose original continuation disappears still require a server-authoritative begin/delivery protocol before they can be safely replayed or refunded. Missing/changed row authority remains held; an arbitrary recreated row with the same ID does not establish custody.

Dedicated-server event delivery, actual moving-aircraft behavior, native inventory races and heavily modded low-FPS acceptance still require Arma testing. Keep PR #31 draft pending that acceptance. Medmash remains on `dev`.
