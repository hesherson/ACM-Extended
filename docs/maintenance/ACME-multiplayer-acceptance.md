# ACME Multiplayer Acceptance

The `ACME_Acceptance.VR` scenario runs with the current signed ACM Extended build, CBA and ACE. It uses the existing VR Test Zone terrain setup and adds a separate course with four playable slots and a QA table at spawn. Restart the mission for a fresh run. Use the same mod build and settings on the server and every client. A LAN host is useful for rehearsal. Record release acceptance on a dedicated server.

## Start the mission

For solo debugging, open **Tutorials → ACME Debugging**, directly below **ACME Testing Zone**. It uses the same fixtures and QA table, with the ACME debug tools enabled for that session.

Select **ACME Multiplayer Acceptance** under **Virtual Reality** in Multiplayer. For a dedicated instance, put `ACME_Acceptance.VR.pbo` in the server's `MPMissions` directory and select it from the lobby. The rotation template is `ACME_Acceptance.VR`.

For treatment handoffs, use two players and have one opt into the casualty role. For a two-provider SkedCo lift with a player casualty, use three players. Talon II's three-provider lift needs three medics and an AI casualty, or four players with a player casualty. The Hatchet lane is optional and requires the Hatchet mod on all participants. It exercises the current seat handoff only.

Select **Prepare AI patients** at the QA table to start the injury and unconsciousness cases. The player casualty can opt into the case using their own action at the Transfer marker. Each patient can be prepared once. Restart the mission between runs to clear prior wounds, litter custody, and equipment state.

The map diary contains the eight checkpoints. Use **Next checkpoint** at the table to select one, then **Record PASS** or **Record FAIL** after observing the result. The table reports state for diagnosis. Visual fit, animations, camera control, and usability are recorded by the tester. Preserve the RPT interval and a screenshot or recording for a visual failure.

## Evidence

- `[ACME QA] READY` identifies the run, build, world, server type and fixture counts. `[ACME QA] CLIENT_READY` identifies the slot and late-join status.
- `[ACME QA] OBSERVATION` captures the recorder's client state. `[ACME QA] RESULT` captures the corresponding server state, including litter, blanket, plate-carrier support and chest drawer state.
- `[ACME Transport]` reports the existing SkedCo and Talon II diagnostics. Record the server RPT and the patient owner's client RPT for ownership or handoff failures.

The patient rows record role, alive/unconscious flags, animation, locality, position, vehicle, attachment parent, litter type, stow state, HPMK state, head elevation, support-prop presence and vest class, in that order.

## Performance windows

From the mission lobby choose one of the four 24-AI workloads, with 0, 1, 5 or 10 unconscious casualties. Keep the player count and mod/settings preset constant. After warm-up, use the table to start a 120-second server capture, or enable the 30-second warm-up and capture through the lobby parameter. Keep menus closed during the steady window. Use an independent functional-lane run to measure treatment, cooler loading and equipment transfers.

The server writes `PERF_META` and `PERF_SAMPLE` records under `[ACME QA]` using the existing ACME performance capture. Keep the original server RPT for comparisons. Use a normal lobby to set workload parameters. Engine `-autoInit` uses the default mission parameters and is useful for a startup smoke test. [Arma startup parameters](https://community.bohemia.net/wiki/Arma_3%3A_Startup_Parameters#autoInit)

## Build the PBO

From the repository root, stage the shared scenario under the multiplayer mission name and package it with Bohemia FileBank. The result is a separate mission PBO. Use a new staging directory for each build.

```powershell
$mission = Join-Path $stagingDirectory 'ACME_Acceptance.VR'
Copy-Item -LiteralPath 'addons/mission/ACME_Debugging.VR' -Destination $mission -Recurse
& $fileBank -property prefix=ACME_Acceptance.VR -dst $outputDirectory $mission
```
