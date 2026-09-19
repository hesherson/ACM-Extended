# ACM Extended 1.2.2: server bag visibility and BVM recovery

## Problems

Hang Bag created its hand prop and rope endpoints only on the provider's client. Broadcasting a local object handle did not create those objects for other players.

BVM startup and cancellation compared CBA key handler IDs numerically, although CBA returns strings. An error could interrupt the continuous controller or its cleanup, leaving the provider restricted and the patient reserved. Dead providers also blocked the start path, and there was no server watchdog for abandoned sessions.

## Changes

- Send the resolved bag model, texture, hand placement, line endpoints and custom rope class to observing clients. Each client creates matching local presentation objects. Joining clients receive the active hold too.
- Keep the bag and line visible through the existing lowering animation. Remove them when the episode ends, the provider dies, becomes unconscious, enters a vehicle, disconnects or changes owner, or either object is deleted. Delayed messages cannot remove a newer hold.
- Keep the provider's original bag, custom line, hand calibration and treatment animations. Replication adds no shared physics objects or continuous network position updates.
- Handle CBA input IDs as strings. Release BVM patient and provider ownership before removing input handlers or interface elements.
- Track each BVM session with its provider and generation. Cancellation and respawn clean up the captured session without cancelling a newer treatment. Pausing ventilation still reserves the patient.
- Add server recovery for death, disconnect, ownership transfer, incompatible vehicle positions, excessive distance and abandoned controllers. Active and paused sessions publish a heartbeat every two seconds; an abandoned session expires after ten seconds without a heartbeat.
- Reject cleanup from an older session and recover a stale reservation when starting BVM again. Preserve native continuous treatment animations, breath timing, oxygen use and the existing CPR handoff.

Version remains 1.2.2, with HEMTT metadata 1.2.2.0. Both main and dev include this fix.

## Validation

Each branch passed 33 checks, with one optional development package check skipped. These include 26 SQF execution cases, strict HEMTT 1.21.0 diagnostics, full addon config compilation and inspection of release packages to confirm the experimental drag handle remains excluded.

The execution cases cover string handler IDs, cancellation, respawn, disconnect, stale cleanup, paused sessions, server recovery, ownership changes, observer creation, duplicate and delayed events, joining-client ordering and removal of local props. Native UI, object and network commands are simulated while production control flow runs in SQF-VM.

Both branches also built 14 PBOs using `hemtt release --no-bin --no-sign --no-archive`. Six targeted checks per branch confirmed the new visual receiver, BVM cleanup and server registration are included in the packaged runtime. The existing Hang Bag animation and custom rope checks passed.

Full Windows asset binarization, signing and actual Arma multiplayer behavior remain unverified here. Update the server and every client, then restart the mission. With two clients, verify visibility while raising, holding and lowering each bag type, including a client joining during a hold. Verify BVM cancellation, pause/resume, respawn and disconnect, then have another provider ventilate the same patient. Repeat while a separate provider performs CPR.

## References

CBA documents the [string ID returned by addKeyHandler](https://github.com/CBATeam/CBA_A3/blob/master/addons/events/fnc_addKeyHandler.sqf). Bag presentation uses CBA's [global events for joining players](https://github.com/CBATeam/CBA_A3/blob/master/addons/events/fnc_globalEventJIP.sqf) and [event removal](https://github.com/CBATeam/CBA_A3/blob/master/addons/events/fnc_removeGlobalEventJIP.sqf).
