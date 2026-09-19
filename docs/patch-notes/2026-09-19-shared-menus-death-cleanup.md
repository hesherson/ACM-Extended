# ACM Extended 1.2.2: shared menus and death cleanup

## Confirmed failures

Chest menu requests could overwrite the current context while delayed opens were still pending. Old panels and duplicate update handlers then used that shared context. The drag integrator treated a second update at the same timestamp as an immediate jump to the cursor. The roster itself had no two-provider limit, but menu entry still went through a physical stance and holster preflight.

Head Tilt–Chin Lift, Carry Assist, Feel Pulse and the stethoscope still compared CBA string key handler IDs with numbers. Those comparisons could abort startup or cancellation. CPR requested medicEnd without queuing a controllable native idle, while its custom movement states connected back only to CPR.

The ventilator panel explicitly treated `!alive` as recovery in progress. Its update and navigation functions also rejected dead patients, even though the custody system intentionally keeps the device attached to the body until recovery is requested.

## Changes

- Open shared chest and connected ventilator panels without a physical treatment preflight. Keep access, distance, inventory and skill checks.
- Give each client one pending panel request. Bind update loops and unloads to their display, reject stale callbacks and reset chest drag state on close.
- Keep drag resistance when two updates have the same timestamp.
- Track chest viewer tokens on the server. Release abandoned viewers without evicting other providers. A delayed last-viewer restoration cannot overwrite a newly opened workspace.
- Keep the ventilator bound to its connected patient after death. Viewing it does not initiate recovery. The panel remains available during concurrent viewing, and the existing serialized recovery process still prevents duplicate returns.
- Correct string handler cleanup for manual holds, pulse and auscultation. Add server recovery for abandoned head tilt and carry assist sessions, using server receive times to avoid clock-offset expiry. Recovery-position head tilt is preserved when a manual provider releases.
- Retire an earlier assessment's frozen pose before a new continuous maneuver or CPR takes ownership. Reset playback speed, play the CPR release and queue the native unarmed crouch. Add native exit connections to both CPR loop states.
- Cancel local panels and continuous actions when their provider dies, becomes unconscious or is replaced. Patient death alone does not erase equipment or clinical evidence or prevent releasing a manual action.

Version remains 1.2.2, with build metadata 1.2.2.0. Release packages continue to exclude the experimental drag handle.

## Validation

Both branches passed 108 focused checks, with one optional development package check skipped. Strict HEMTT checks and full addon config compilation passed. Each release build produced 14 PBOs using HEMTT 1.21.0 with `--no-bin --no-sign --no-archive`. Six packaged functions and both CPR exit graphs were checked in the actual PBOs. The new tests reproduce five failures against the preceding code: duplicate pending entry, zero-time drag snapping, dead-patient ventilator entry and navigation, and stethoscope string handler cleanup.

Focused SQF execution covers three simultaneous chest viewers, repeated entry attempts, same-timestamp dragging, stale unloads and restoration, dead-patient ventilator access, string input IDs, provider death, respawn, disconnect, clock offsets and replacement sessions. CPR coverage includes the release followed by native idle and stopping and restarting after patient death. Existing BVM, bag observer, treatment pose and chest interaction checks also run.

Native UI, animation, objects and networking are simulated in execution tests. Arma multiplayer playback, Windows asset binarization and signing must still be checked in game and on the release machine. The earlier `test_fork_phase145_zone3_reboa_smart_bandage.py` stops at an existing AAJT source-location assertion before its death checks; that legacy check is not counted as passing.

For multiplayer verification, update every client and the server, then restart Arma and the mission. Have three providers open the same chest panel, close and reopen in different orders, and check drag resistance. Repeat with a connected ventilator before and after patient death. Stop CPR during entry, compressions and pause, then move and begin another treatment. Test Head Tilt–Chin Lift release and provider death or respawn while each menu or manual hold is active. Confirm that the next provider can use the patient and recover equipment.
