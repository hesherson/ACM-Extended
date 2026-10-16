# B272 — Vented finger dressings and PTX resolution

Candidate **1.2.4.1 / B272**, protocol **1**, based on B271 `01ed17d8d435ca75903aef508c026d3c4652750f`. These are game simulation coefficients and timings.

## Treatment and recovery

All chest seals available in this game are vented. Covering a completed finger thoracostomy changes its outlet capacity rather than suturing the tract. Placement can precede internal-leak settlement and preserves existing air, pressure, leak, injury serial and observation credit. The owner commits the selected tract as `sealed=true`, `closed=false`, `open="sealed"`. Incomplete access, an installed tube, a previously covered tract or a genuinely closed tract cannot consume another seal.

An open finger or tube supplies capacity 5; a covered finger supplies capacity `2 × (1 − sealOcclusion)`. Capacities remain bounded per casualty and never multiply with seal icons or sides. A tube takes priority over its suture/secured flag. Historical records with a sealed tract and `closed=true` are understood as covered fingers; actual native incision closure removes the tract records. Surgical coverage does not cover unrelated traumatic entry or exit wounds. Ordinary wound sealing no longer automatically closes a finger incision.

A functioning covered finger qualifies for definitive recovery under the existing controlled interval, default **60 seconds**: every communicating traumatic wound including hidden exits covered, no tension, air at most 1, pressure at most 0.1, nonincreasing air and incoming flow no greater than outflow. Loss of control still resets that observation interval. Completion sets the injury's internal leak to zero. No blood-pressure, consciousness, oxygen-saturation or zero-bleeding gate is added. Ordinary traumatic seals and NCD retain natural leak healing without the definitive recovery bonus.

Burping clears existing seal obstruction and relieves pressure. Surgical peel and repeat finger sweep retain their existing relief. These aftercare actions preserve earned observation and never regenerate a settled leak. Initial finger establishment/widening and new injury retain their observation resets. Actual sutured incision closure still requires owner-verified settled PTX and observation; a vented dressing does not require this closure gate.

The new **Pneumothorax residual air clearance** setting defaults to **600 seconds per normalized air unit**. Once internal leak is zero, traumatic wounds are covered, tension is absent and pressure is at most 0.1, residual air and its temporary floor decrease together to zero. Open finger/tube outflow at capacity 5 multiplies this clearance by five; covered or closed recovered episodes clear at the base rate. A covered finger with residual air 0.5 therefore clears that floor in approximately five minutes at default settings after settlement. Clearance never silently treats established tension. Seven-field historical pure-model calibration preserves its earlier arithmetic.

Dry seals have no compulsory failure timer. Eligible ongoing external chest bleeding may obstruct the existing shared seal outlet. A continuing internal leak can then exceed available venting and cause gradual accumulation; seal placement itself does not add air. A healed leak stays zero under positive-pressure ventilation or seal obstruction. New trauma and uncovered communicating wounds can still cause new PTX; ambient pressure changes can expand gas that remains.

Vented surgical dressing does not introduce continuous hemothorax drainage or stop bleeding. Finger sweep/widening and surgical peel/burp retain their existing identified one-time retained-blood debits. Tube drainage remains separate.

## State and networking

The nine-number version-1 PTX state, persisted clinical fields, observation revision and network protocol are unchanged. Seal placement retains the B271 owner transaction, exact supply receipt, cached accepted/rejected decisions, 120-second first-arrival window and 16-second same-request reconciliation. No optimistic provider tract mutation is added. Locality, stale epoch, duplicate ACK and competing-provider protections remain applicable; clinical readiness is no longer a reason to reject a functioning vented dressing.

## Native acceptance

Use the same complete B272 package on server, clients and HC, with the separate original ACM disabled.

1. Create PTX, establish a finger tract and cover it immediately while the leak remains active. Verify one seal consumed, vent retained and no instantaneous increase or artificial disappearance of air. Cover all traumatic communications and maintain controlled PTX for the recovery interval; verify durable leak settlement and gradual resolution to zero.
2. Repeat on each side, with hidden exit wounds, a contralateral tube and saved B271 covered-finger flags. Verify covered surgical access never covers unrelated wounds or removes the opposite tube. Ordinary wound seal application must retain the surgical tract.
3. Exercise ongoing external chest bleeding, obstructed vents and positive-pressure delivery. Verify an active leak exceeding outflow produces gradual accumulation; surgical burp restores venting and keeps recovery credit. Repeat after settlement to confirm obstruction/PPV cannot recreate that internal leak.
4. Burp, peel, sweep and reopen the UI before and after settlement. Verify identified blood debits occur once, pressure relief does not add air, and aftercare preserves recovery progress. Initial establishment and new injury still reset observation.
5. Race providers on one tract, delay/drop initial requests and ACKs, transfer locality, replace the tract with a tube before owner acceptance, reset/full-heal and load old/current snapshots. Verify one winner, exact receipt settlement/refund and no stale mutation of a successor episode.
6. Verify actual suture closure remains gated while unresolved, then permits closure after observation. Compare resolution settings, tension, NCD, ordinary seals, tube removal, ambient gas expansion and lung findings while independent hemothorax/edema remain present.

Automated production-SQF execution uses explicit engine fixtures and cannot establish native Arma, Windows deployment or dedicated-server/two-client/HC acceptance. This update remains on the cumulative draft branch, without a main merge or public release.
