# B285: durable syringe delivery and provider migration

Version **1.2.4.1**, build **B285**, network protocol **2**.
Baseline: B284, `1cff3a6f957615bbeaad34c07f512f2b2d3f99b4`.

## Delivery authority

An accepted syringe delivery claim creates a server journal before the original provider's continuation runs. The journal captures the exact inventory token, stable syringe identity, funded initial solution, equipment kit and request. A missing UI callback therefore cannot strand a claim without recovery authority.

The provider waits for an acknowledged BEGIN before starting the plunger or debiting an ordinary injection. BEGIN fixes the patient, clinical generation, body part, catheter generation and session. Each medication batch records its immutable request, exact solution delta and corresponding medication mass on the server before patient dispatch. Repeated messages retain the same identity and cannot replace a registered dose. Patient decisions reach the journal independently of the provider's current owner.

The plunger still updates privately. Its unsubmitted visual tail is absent from the server's debited source, so canonical recovery returns that tail without replaying medication or adding an old owner's local refund. The source is the initial funded solution minus registered aliquots, with exact rejected aliquots restored once.

## Stops and recovery

STOP includes an immutable manifest of all submitted batches still awaiting acknowledgement on that provider's local period. The server admits those exact batches before closing input. A reordered STOP cannot return a carrier ahead of its submitted dose.

Provider ownership changes, controlled-provider switches, an expired input lease and missing continuations stop new flow. Recovery never creates a plunger worker or resumes treatment. Pending patient decisions keep their source reserved. Heartbeats require the actual matching live push controller; an abandoned BEGIN cannot keep its own lease alive.

Only the complete canonical server row can settle the physical carrier. The current provider installs that row by exact identity and revision, then returns or consumes the original token. A delayed receipt cannot edit a later claim, another native recipient or a replacement kit. A fresh-kit reset retires old source accounting while retaining immutable patient decisions; it cannot refund into the new loadout.

Controller teardown precedes synchronous protocol replies. Exact request guards and acknowledgement deduplication protect hosted games and single player from recursive settlement, repeated refunds and old callbacks clearing a successor controller. Callback epochs also fence rapid away-and-back provider transfers.

## Patient ownership boundary

Patient delivery is fenced to the captured machine incarnation. A known patient receipt proves the terminal result; a matching machine can also establish that its exact request was never applied before recovery proceeds. Missing replicated state alone does not prove non-delivery.

Each machine announces a private incarnation nonce. The server waits for that identity before dispatching a dose. An ownership query records a permanent decision before replying; an unseen request receives a rejection tombstone, so a late packet after an away-and-back transfer cannot administer medication whose source was returned. Accepted private decisions are recorded before physiological callbacks and remain available if a replicated receipt is lost. Reused numeric owner IDs cannot stand in for the original machine.

If the captured machine disconnects and neither a terminal receipt nor a valid non-delivery proof exists, the uncertain aliquot remains held. A timeout cannot safely decide between duplicating an already applied medication dose and refunding its source. This unresolved case requires evidence or administrative reconciliation.

## Validation and release boundary

The regression suites execute production journal admission, source arithmetic, ordinary injection, timed push, patient receipts, canonical recovery and native token settlement against explicit engine boundaries. Tests cover lost continuations, private unsent travel, reordered and duplicate delivery, STOP manifests, equipment replacement and independent old-owner/new-owner/server projections. Historical tests retain their dose, duration, source conservation and identity assertions; their transport fixtures follow protocol 2.

The new focused coverage contains 129 source/dose cases, 42 delivery/migration cases and seven protocol bootstrap/compatibility cases. The migration cases include eight executed semantic mutations of the identity, custody and decision guards. The protocol is loaded from compiled component metadata both during startup and when a manifest precedes startup publication.

Automated checks do not certify native Arma event transport, Gear placement, dedicated-server ownership timing or heavily modded low-FPS gameplay. PR #31 remains a candidate pending that acceptance. Server, players and headless clients must use the same complete protocol-2 build. Medmash remains on `dev`.
