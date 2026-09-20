# ACM Extended 1.2.2: restore ACM BVM flow

## Changes

- Restored ACM's active BVM control flow: `BVM_Medic` reserves the patient, `BVM_provider` controls pause and resume, and the native breath loop supplies breaths. Removed the added heartbeat transmission, server expiry worker and per-frame replicated session check.
- An accepted BVM start fully releases that provider's Direct Pressure before installing BVM input handlers or entering its animation. Its pressure marker, worker, keys, mouse hint and delayed pose requests are retired. Pressure held by a different provider is unaffected. An unavailable patient or rejected BVM start leaves existing pressure intact.
- BVM setup uses the native treatment path without the added pressure pause/resume branch. The provider must start Direct Pressure again after finishing BVM.
- New Direct Pressure on any body region is rejected while that provider is performing a continuous maneuver. A stale pressure cancellation cannot clear BVM's controller, replace its animation or remove its mouse hints.
- Retained corrected input handler cleanup and local cancellation, along with provider death, respawn and disconnect cleanup. Cleanup tokens protect replacement sessions but do not determine whether live breaths run.
- Retained the existing oxygen consumption, native breath timing, CPR compatibility, pause/resume and CPR swap. ACM's patient eligibility rules remain: if the patient wakes and is not in ACM's lying state, bagging ends.

This supersedes the earlier BVM heartbeat/watchdog behavior described in the September 19 and 20 patch records. Version remains 1.2.2.

Compared against the [original ACM BVM source](https://github.com/BlueTheKing/ACM/blob/b09febbda10161bdbf965b0a851250fdcc709d69/addons/breathing/functions/fnc_useBVM.sqf) at commit `b09febbda10161bdbf965b0a851250fdcc709d69`.

## Validation

The native BVM restoration passed 108 focused checks on each branch, including repeated Direct Pressure to BVM transitions, native breath delivery, pause/resume, cancellation, rejected starts, provider lifecycle cleanup, CPR, Carry Assist, shared menus, strict HEMTT diagnostics and config compilation. Both branches built 14 release PBOs with `hemtt release --no-bin --no-sign --no-archive`. Windows asset binarization, signing and live Arma multiplayer behavior were not tested here.

The new roundtrip test fails against the previous committed BVM startup because Direct Pressure remains active.

The focused tests exercise the real Direct Pressure teardown and BVM startup together, including removal of pressure ownership, input handlers and workers, sustained breaths, pause/resume, cancellation, repeated starts, stale callbacks and rejected starts. Engine rendering, animation playback and network delivery are simulated, so multiplayer verification remains necessary.

Update the server and all clients, restart the mission, then start Direct Pressure and select BVM. Confirm that pressure ends and bagging continues. Pause, resume and stop BVM, restart pressure, then repeat. Also verify another provider's pressure remains active while you use BVM.
