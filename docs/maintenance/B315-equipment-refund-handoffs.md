# B315 confirmed refund handoffs

Version 1.2.4.1 / B315 / protocol 8. B314's kit/ownership admission and terminal take/give receipts remain in force. This guide supersedes B314's rule pinning an unissued refund to its original machine. World schema 2 and schema 1 import do not change.

## Funded grants

The server records that the setup/cooler-load debit was proved before it can authorize a refund. The private server helper refuses an unmatched actor/request, a different phase, an absent provider pending marker or an unproved debit. A new refund grant is `[generation,executorMachine]`; the first is generation 0 on the provider's current owner. The public provider field is `ACME_eqRefundLease=[requestId,generation,executorMachine]`.

Inventory packets carry that exact grant. The recipient waits for matching public admission and grant metadata. Only the named executor can begin a native refund, and only while it owns the provider locally. The current owner can also witness an already published terminal result without performing another inventory mutation. A grant's proof is stored under `requestId:refund:generation` as `[delivered,retiredUnissued]`; server acknowledgements must name the same actor, request, phase and live grant, match terminal proof, and come from the executor or the current owner.

The server republishes its live grant on ordinary two-second retries. The recipient has a private per-request generation watermark. A lower-generation packet remains refused even if delayed public metadata temporarily regresses. Obsolete local refund rows can be pruned after observing a newer generation; the watermark prevents their re-execution. Private journals retain only the actor's current request.

## Ownership changes

When the provider changes machines, the server sends the normal refund retry to the current owner and a proof-only query to the grant's executor. The query never changes nonlocal inventory.

- A proved delivery completes the refund once. The server does not issue a replacement grant, and a witness can settle published proof after a delayed original acknowledgement.
- If the executor has never issued that attempt, it seals a terminal negative result before replying. That seal prevents a queued old packet from executing later. The server then increments the generation and assigns the refund to the provider's current owner. An away-and-back handoff still gets a fresh generation, even if the executor machine number is the same.
- No response, no terminal proof or an unknown native attempt leaves the grant pending. The server never advances a generation merely because enough time passed. An owner ID of zero after closure delays assignment until a valid owner exists; repeated closure replies do not advance the counter again.

The refund remains funded by its original debit. Kit changes do not cancel a paid refund. The completion path only returns the item; it does not copy old monitor preferences/patient connections into a replacement kit or restart old therapy/feed state. Existing pickup tray release and USB cleanup are unchanged.

## Native uncertainty and blood age

Before a native refund command, the executor records an attempting marker privately. It replaces that marker with terminal delivery proof only after successful placement readback. A failed placement with unchanged, locally valid context clears the marker and can retry the same grant. An interrupted call, or failed readback spanning a kit/locality change, retains an unconfirmed marker. Such a query cannot seal the attempt as unissued, so no new executor is authorized to duplicate an outcome that remains unknown.

An unconfirmed attempt or missing proof from an unavailable executor can therefore keep a live-provider transfer pending and block owner/server checkpoint readiness. This is not a durable recovery backend after actor deletion, mission restart or loss of the originating client and its proof. Existing deleted-provider handling is unchanged. Never copy runtime grant fields/journals into a normal world-object recreation or force-clear them to make a checkpoint pass.

Blood refund age is always derived from the original sampled exposure and sample time. Every retry or handoff recomputes current exposure, and the recipient adds packet transport time. Neither generation changes nor duplicate replies renew blood. The existing bag placement helper still decides spoilage and capacity; spoiled blood is not dropped as a new fallback. Normal full-inventory failure retains the owed refund until placement is possible.

## Native acceptance matrix

Run a dedicated server, two clients and an HC where used. Test server-owned AI, player-owned units and away/back ownership changes:

1. Fund a setup/load, force its placement to fail and transfer the provider before the refund is issued. Confirm one closure of the old grant, one new generation and one refund on the current owner.
2. Deliver a refund, delay its acknowledgement, then transfer the provider. Confirm settlement from original or witnessed proof without another grant/item.
3. Delay/reorder grant metadata, terminal proof, queries, native packets and acknowledgements independently. Replay a closed grant after its successor, including regressed public metadata on owner return.
4. Fill the recipient's containers, retry, free space, and confirm one placement on the same grant. Change kit/locality during failed native readback and confirm that the uncertain attempt stays pending.
5. Delay a blood refund across several ownership changes; confirm cumulative warm exposure, existing expiry conversion and inventory retention. Do not reset sample time when a grant changes.
6. Make the prior executor unavailable without proof. Confirm pending/checkpoint refusal rather than automatic cancellation or reissue. Separately test already published positive/negative witness proof.
7. Retest ordinary setup/pickup, external carry takeover, tray/USB behavior, low FPS, JIP and coordinated save/restart after all transfers drain.

SQF-VM executes the production decisions with explicit native object, replica/locality, inventory and RPC boundaries. It cannot certify engine behavior. Use the source installer for a normal Windows build; the signed Linux candidate uses --no-bin and retains source MLOD models.
