# ACM Extended 1.2.2: BVM startup cancellation

## Causes and corrections

- A short BVM setup treatment emits its completion event after the continuous BVM action has started. With Direct Pressure active, the general treatment completion hook could reopen the medical menu. The continuous controller then interpreted that dialog as a cancellation and stopped BVM on the next frame.
- Treatment completion now leaves an active continuous maneuver in control of the provider. A menu reopen or stance release queued by an earlier treatment also checks whether a continuous action has started before changing the interface or pose. Ordinary treatment completion and the real BVM cancellation still clean up normally.
- The BVM server watchdog previously compared the provider's CBA mission timestamp directly with the server's clock. With a clock offset, a live session could expire as soon as the startup grace ended. The watchdog now observes heartbeat changes and measures their age using the server's own receive time.
- A paused session continues to reserve the patient and publish its heartbeat. Death, disconnect, ownership loss and a genuinely stalled heartbeat still release the reservation. Old cleanup cannot release a newer session.

Version remains 1.2.2. Breath timing and oxygen consumption are unchanged.

## Validation

The BVM startup followup passed 95 focused checks on each branch, including complete startup, pause/resume, cancellation, CPR, Carry Assist, shared menus, strict HEMTT diagnostics and config compilation. Both branches built 14 release PBOs using `hemtt release --no-bin --no-sign --no-archive`. Windows asset binarization, signing and live multiplayer playback were not tested here.

The new SQF execution tests reproduce both cancellation paths against the previous code. They run the actual BVM startup and continuous controller, verify sustained breaths with and without CPR, exercise standard and oxygen variants, and check pause, resume, cancellation, restart, earlier queued menu callbacks and heartbeat expiry with different client and server clocks.

Engine UI, animations, network delivery and physiology effects are simulated. Arma multiplayer verification remains necessary. Update the server and every client, restart the mission, and verify that BVM stays active after starting from the medical menu, including after Direct Pressure. Check pause, resume and stop, then repeat with another provider performing CPR.
