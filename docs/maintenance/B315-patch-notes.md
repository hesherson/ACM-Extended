# B315 candidate — confirmed equipment refund handoffs

Version 1.2.4.1 / B315 / network protocol 8. Cumulative on B314. Server, clients and HCs must use the same complete build; do not mix protocols 7 and 8.

- Removes B314's requirement to return a provider to its original machine for a never-issued refund. A funded refund starts on the current owner, or moves there after its previous executor proves its attempt unissued.
- Adds a numbered refund grant. The server advances it only after terminal negative proof; late acknowledgements and packets from an older grant cannot issue or settle the next one.
- A current owner can witness published terminal proof. Already delivered refunds settle without another item, including when the original acknowledgement was delayed.
- A private generation watermark rejects old packets even if public metadata arrives out of order during an away-and-back ownership change.
- Preserves original blood exposure through handoff, capacity retries and network delay. Existing spoilage and inventory-retention rules remain authoritative.
- Marks a native refund attempt before issuing inventory commands. An interrupted attempt or failed readback across a context change stays unconfirmed rather than being guessed unissued. A confirmed capacity/readback failure with stable context remains retryable.

Missing terminal proof from an unavailable executor still leaves a live-provider transfer pending and blocks a checkpoint. Actor deletion and loss of a client together with its private proof are not a newly implemented persistent recovery service. Native Arma/ownership/replica ordering, dedicated-server, HC/JIP, low FPS and Windows acceptance remain unexecuted here.

World schema 2 and schema 1 import, clinical calculations, equipment placement, models and Tempus artwork are unchanged. No new remote endpoint or mission save backend is added. Read B315-equipment-refund-handoffs.md for the protocol and acceptance matrix. The Linux integration candidate retains unbinarized source MLOD assets; the source installer performs the normal native Windows release.
