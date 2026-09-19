# ACM Extended 1.2.2: bag visibility and CPR stop followup

## Problems confirmed

The earlier bag fix queried `owner` on observing clients. Remote object ownership is resolved by the server; using that client result to validate a packet could reject the held bag and its line. The shared frozen treatment pose receiver used the same invalid check. The earlier execution tests supplied the same owner ID on every machine and missed this distinction.

CPR startup and cancellation still compared CBA's string key handler IDs with numbers. Cancellation could abort before disabling the AnimDone loop, releasing the provider and requesting the exit animation. CPR and BVM also used numeric/string comparison operators on boolean status values, interrupting their update loops.

## Changes

- Identify the sending machine with `clientOwner`. Resolve remote owners only on the server. Observing clients validate the existing episode and local ownership without querying a remote owner.
- Apply the same correction to Feel Pulse and Auscultate Chest held poses. Existing hold samples, transitions, bag models, placement, fluid textures and custom IV rope remain in use.
- End a held bag session when its original client loses ownership, removing its local props and publishing the end of the visual episode.
- Stop CPR animation re-entry immediately when cancellation is requested. Remove the captured loop and release the patient before cleaning up string input handler IDs, then request the existing native medic exit animation.
- Disable the compression loop before switching to the paused pose. Resume uses the existing single AnimDone handler.
- Track CPR sessions through cancellation, respawn, disconnect and ownership changes. Paused sessions retain the patient reservation; the server releases an abandoned session after ten seconds without its controller heartbeat. Session sequences survive a change of owner so old cleanup cannot release a newer session.
- Correct boolean status comparisons in CPR and BVM, including oxygen status updates. CPR cancellation preserves another provider's BVM session and the existing CPR to BVM handoff.

Version remains 1.2.2, with HEMTT metadata 1.2.2.0. Both main and dev include the correction.

## Validation

Both branches passed 72 focused checks, with one optional development package check skipped. These include 65 SQF execution cases, strict HEMTT diagnostics, full addon config compilation and release package checks. The revised harness reproduces the original bag rejection and CPR string comparison error against the previous commit, then passes against the corrected code.

The tests execute complete CPR entry, input callbacks, pause/resume and cancellation paths. They also cover repeated starts, cancellation during entry, stale callbacks, CPR/BVM handoff, simultaneous providers, respawn, disconnect, ownership changes and server cleanup. Observer tests now distinguish non-server clients from a listen server instead of assuming ownership information is available everywhere.

Each branch built 14 PBOs with HEMTT 1.21.0 using `--no-bin --no-sign --no-archive`. Eight additional checks per branch confirmed the corrected sender, observer, CPR lifecycle and BVM code are present in the PBOs. Existing Hang Bag animation and custom rope contracts also passed.

The older `test_b90_critical_provider_cpr_bvm.py` could not complete because it refers to the already removed `overrides/fn_treatment.sqf` path. It is not included in the passing count.

Native animation, object creation and network operations are simulated in execution tests. Full Windows asset binarization, signing and actual Arma multiplayer remain unverified here. Update the server and every client, restart the mission, and check held bags from another client and after joining. Check CPR stop during entry, active compressions and a pause, followed by a new CPR session and by BVM. The provider should leave the CPR animation and the patient should be available to another provider.

## References

CBA routes client requests through the server because [only the server resolves remote object owners](https://github.com/CBATeam/CBA_A3/blob/master/addons/events/fnc_targetEvent.sqf). Its [key handler API returns string IDs](https://github.com/CBATeam/CBA_A3/blob/master/addons/events/fnc_addKeyHandler.sqf). The exit retains ACE's [existing animation helper](https://github.com/acemod/ACE3/blob/master/addons/common/functions/fnc_doAnimation.sqf).
