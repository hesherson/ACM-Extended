# B314 equipment transfer epochs and receipt recovery

Version 1.2.4.1 / B314 / protocol 7. B313 pickup custody and USB cleanup remain in force. B312's world equipment schema 2 and schema 1 import are unchanged.

## Admission and funding

The server captures a transfer stamp: `[kitEpoch,[machineId,localityEpoch]]`. It records the stamp with the pending request and publishes `ACME_eqAdmission=[requestId,stamp]` on the provider. Owner inventory commands wait until that exact complete admission is visible. A packet arriving ahead of its metadata neither changes inventory nor emits a terminal failure.

The kit generation is `ACME_equipmentKitEpoch`. A deliberate full-loadout replacement must continue to call the existing owner-local `ACM_core_fnc_equipmentKitChanged`; ordinary item movement is not a kit replacement. No new loadout writer or inventory-difference guess is introduced. Ownership epochs remain private to each machine. The local owner uses `clientOwner` and its private epoch; a remote server reader uses `ACME_vent_batterySwapOwnerPeriod`, already maintained by the shared owner registration/locality lifecycle. Stale or missing server-side owner-period metadata prevents a new admission.

This distinction matters because the engine's [owner command](https://community.bistudio.com/wiki/owner) is server-only. Client-side context does not compare itself to that command's zero result. The adapter consumes the existing published owner period without changing its publisher.

Before a physical operation, an outdated setup/load debit or pickup credit is refused. A refused pickup unlocks its original device; it does not recreate a monitor, restore a USB cable or remount a tray already released at admission. Once a physical item has moved, its receipt remains authoritative even if the provider subsequently changes kit or ownership period. Funded world placement or pickup can finish once. Actor monitor state is only cleared/copied and its feed restarted if both the owner's completion result and the server's current stamp still match the admission. Context is recomputed after native inventory calls, including synchronous callbacks.

Paid refunds are tied to their source debit and can complete after a kit change on the same machine. An unpaid refund waits for funding proof and cannot manufacture an item. A full-inventory credit/refund retains its pending request until native placement succeeds. Blood-return packets carry a sample time; the recipient adds elapsed transport time before the existing bag placement/spoilage path. Spoiled blood remains subject to the existing inventory-retention behavior.

## Immutable receipts and live ownership handoff

`ACME_eqLocalReceiptRequest` and `ACME_eqLocalReceipts` are private on each machine's actor replica. They retain only that actor's current request. Terminal results are also published in `ACME_eqReceipts`. Private proof takes precedence over a lagging public sample. A failed debit is terminal: a later same-request retry cannot consume stock that arrived after the failure. A failed, unexecuted capacity/readback attempt for a credit/refund remains retryable.

After a live provider changes machines, the ordinary two-second server retry also queries the admitted original machine. The query uses the existing server-authorized inventory endpoint, performs no nonlocal inventory mutation, and only republishes a terminal result or seals a never-executed setup/pickup. The server accepts an acknowledgement from the current actor owner or that request's admitted original machine, with matching actor, request, phase and explicit public terminal proof. Other senders and contradictory proof are refused. A new machine waits for that proof rather than treating an absent replica as a negative result.

An unissued paid refund is not reassigned to a different machine. Its provider must regain locality on the original machine before it can issue that refund. If it was already issued, the original machine can prove delivery after the handoff. This conservative limit avoids reissuing a refund whose previous delivery may still be in flight. An unavailable original machine, missing proof or full inventory can leave a live-provider transfer pending; no timeout chooses delivery or cancellation. Such a pending request continues to block both owner and server persistence readiness. This feature does not add a persistent transfer journal across actor deletion, a reconnect with lost private proof, or mission restart. Existing deleted-provider handling is unchanged.

The transport uses [remoteExecCall](https://community.bistudio.com/wiki/remoteExecCall) and machine-local/public [object variables](https://community.bistudio.com/wiki/setVariable). No new remote endpoint is added; the transfer-stamp reader is a private registered function. Request metadata and private receipts are runtime state, not new world-save fields. Continue quiescing and draining transfers before coordinated clinical/cargo/world capture.

## Native acceptance

Run a dedicated server with two clients and an HC where used. Cover server-owned AI, player-owned units and owner return after a handoff. Verify:

- Replace a provider's kit after admission but before inventory delivery: no replacement item is taken or granted; the pending request cancels and an uncredited pickup unlocks its source.
- Replace a kit or transfer locality after a proved debit/credit: one funded device/item settles; new-kit monitor power, patient connection, preferences and pacing remain unchanged by old completion.
- Delay admission publication, receipt publication and acknowledgements independently; replay a negative take result after adding new stock; retry a failed native credit readback.
- Transfer a provider to another machine before and after physical movement. Confirm original-machine receipt queries, sender rejection, one settlement and no nonlocal native inventory mutation.
- For an unissued refund, confirm that the new machine waits; return the provider to the original machine and confirm one refund. For a delivered refund with a delayed ACK, confirm proof-based settlement after handoff without another grant.
- Delay a blood refund at transport, fill the recipient's containers, then free space. Confirm preserved warm exposure, existing spoilage rules and no duplicate/drop.
- Test source tray release, external carry during pickup, USB cleanup, low server FPS, JIP and checkpoint refusal while a live transfer remains pending. Once drained, perform a complete coordinated save/restart using the existing mission adapter.

SQF-VM uses explicit native boundaries and cannot certify these engine behaviors. The signed Linux candidate uses --no-bin and retains source MLOD models. Use the source installer for the normal native Windows build.
