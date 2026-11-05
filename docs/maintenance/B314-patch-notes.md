# B314 candidate — equipment transfer admission and receipts

Version 1.2.4.1 / B314 / network protocol 7. Cumulative on B313. Use the same complete build on server, clients and HCs; do not mix protocol 6 and 7.

- Setup, pickup and deployed-cooler loading now capture the admitted kit and ownership period. An unexecuted old request cannot debit or credit replacement inventory.
- Already funded transfers settle from an immutable receipt. Late completion does not clear or overwrite replacement Pro/LS state, start an old feed, or stop new-kit LS pacing.
- Failed debits are terminal, so an early negative acknowledgement cannot race a later retry that consumes newly acquired stock. Capacity/readback failures for an inventory credit or paid refund remain retryable.
- The server can query the original machine after a live-provider handoff. Its private terminal receipt proves delivery or an unexecuted setup/pickup; missing replication on a new machine does not decide an outcome.
- Blood refunds include elapsed transport time in their preserved warm exposure. Retrying a refund neither adds another bag nor renews its age.
- Owner inventory decisions run unscheduled, and context is checked again after native inventory callbacks. Client-side stamps use clientOwner; remote server reads use the existing published owner period.

An unresolved live-provider handoff remains pending and blocks a checkpoint. A never-executed paid refund stays with its original machine and waits for that provider to regain locality there; it is not automatically reissued by a different machine. Already delivered refunds can settle from the original receipt after handoff. This does not add durable recovery after deletion of the actor or loss of the original client together with its proof; existing deleted-provider handling is unchanged.

World schema 2, legacy schema 1 import, placement, models, Tempus artwork, sensor/therapy formulas and existing blood spoilage limits are unchanged. No mission save backend or autosave is installed. Read B314-equipment-transfer-epochs.md for the protocol, handoff limits and native acceptance matrix. Windows/Arma, dedicated-server, low-FPS, JIP and actual ownership/replication ordering remain unexecuted here. The Linux candidate retains unbinarized source MLOD assets; the source installer performs the normal native Windows release.
