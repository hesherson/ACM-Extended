# B312 Tempus field mounts, USB and patient cables

Version 1.2.4.1 / B312 / network protocol 6. Use the same complete build on the server, clients and headless clients.

## In-game use

Two original ACME field mounting trays are available in Eden/Zeus: `ACME_TempusPro_Mount` and `ACME_TempusLS_Mount`, under Things / Storage. They are simple open trays with retaining rails, not replicas of Philips SmartMount products. They provide physical attachment only; they do not add charging or free power.

1. Set down the Pro or LS using the normal equipment action. Its default patient position is unchanged.
2. Place the matching field mount within 2.5 m of that deployed monitor. Interact with the mount, select **Mount Monitor**, then choose the numbered device. The operator must be on foot, awake and within 3 m of both objects.
3. Use **Release Monitor** on the tray or **Release from Mount** on the monitor. The normal **Pick Up** action also releases the monitor before the existing funded inventory transfer.
4. To add a physical data connection, bring deployed Pro and LS within 2.3 m. On the LS, choose **Connect USB Data Cable** and select the Pro. The connection releases if the devices separate beyond 2.5 m. **Disconnect USB Data Cable** unplugs it.

The existing wireless Pair action remains available. A USB unplug retains that pairing. Powered-off devices retain their physical USB connection; a valid pair is re-established when both devices are powered again. A different-patient conflict breaks the connection. The monitor's actual patient connections/sensor flags determine which patient cable bundles appear, including separate LS pad and ECG bundles. There is no new consumable cable item.

Philips describes separate device mounts and direct USB or indirect mount-to-mount USB linking in the [Tempus Pro operator manual, section 11.3](https://www.documents.philips.com/assets/Instruction%20for%20Use/20241213/e8ab40402d9a4339a0dcb245010cf93e.pdf?feed=ifu_docs_feed). B312's trays are generic field props and do not implement a SmartMount power or data station.

Only devices allocated by the integrated Set Down/Set Up flow carry the world-equipment kind used by these new mount/USB menus. Raw independently recreated mission props remain under their mission adapter's ownership. A mission designer may attach a field mount to a vehicle using the usual native `attachTo` workflow and a deliberately chosen offset; no vehicle-specific layout is assumed.

## Safety and lifecycle

Mounting moves the existing object; it creates no monitor and grants/removes no inventory item. Matching tray/device kinds and occupancy are checked on the server. Mounted simulation is disabled, and normal release restores the captured prior simulation state at the current ASL pose. Mount deletion has a release handler and the server reconciler retires a broken attachment. If an external carry system has taken over the object, ACME clears its own mount claim without detaching that external parent or changing its simulation.

Mount and USB RPCs validate the sender's ownership of a human-class operator, class/kind, distance, awake/on-foot state, pending transfer/busy state and affected patient persistence fences. Each physical episode has a public generation counter. Late requests from an earlier mount/USB episode cannot undo a later one. Trusted server-local calls may omit the counter; remote callers must include the current station/device counter, as the supplied actions do.

An inventory pickup of an object currently attached to an unsupported external carrier is refused until it is released. Restore staging objects are fenced against pickup until the whole import commits, including the frame before queued native deletion completes after rollback. Canonical patient slots are reconciled when native connection state changes, so disconnected monitors no longer leave stale default-slot occupancy.

The Ventway representation swap now transfers its own durable binding before deleting its old prop. [Arma defers the transition to `objNull` until the following frame](https://community.bistudio.com/wiki/deleteVehicle); waiting for an immediate null in the same call could reject the replacement's ID binding.

## Cable presentation and performance

Patient leads and USB are local, non-physical simple-object segments. They apply no rope force, alter no vitals or therapy and send no visual RPCs. A client checkbox, **ACM Extended: Equipment / Show equipment cables**, controls their display.

The worker scans nearby tagged world devices twice per second, considers at most eight devices within 20 m, and draws at most 16 bundles / 128 segments. It updates at 10 Hz and reuses transforms until an endpoint moves more than 2 mm. Failed allocation backs off for two seconds; disconnect, hiding, moving out of the scan and disabling the setting clean up the cache. No visual worker runs on a dedicated server or headless client.

The supplied port fractions and anatomical endpoints are approximate visual anchors pending native calibration. Each active sensor gets one bundle; individual electrode branches, pads, cuffs, clips and capnography accessories are not new modeled objects in this pass. Curves retain ASL coordinates and short slack, but do not solve terrain/object collisions and may intersect intervening geometry. Patient bundles are hidden while the patient is in a vehicle. These limits do not alter the logical connection or its monitoring/therapy behavior.

The cable's unit-cylinder origin is centered; its axis is model Y. Each segment is positioned at its midpoint and oriented before scaling, because [direction changes can reset object scale](https://community.bistudio.com/wiki/setObjectScale). The two tray models and cable mesh are generated by `tools/build_equipment_mount_models.py`; all are small visual-only MLOD meshes with outward normals and `autocenter=0`. Existing Tempus body models/textures, browser screens and hit areas are preserved.

## World persistence schema 2

The existing APIs remain:

```sqf
private _world = call ACME_fnc_equipmentWorldSnapshot;
private _valid = [_world] call ACME_fnc_equipmentWorldCaptureValid;
private _result = [_savedWorld] call ACME_fnc_equipmentWorldRestore;
```

New captures return `[2, rows]`. Each row has the existing ten fields followed by a durable mount reference and a durable USB Pro reference. Old `[1, rows]` captures still import as unmounted/unwired objects. Empty success is now `[2,[]]`; `[]` remains failed capture.

Bind every saved field mount to its own unique mission-owned ID, as with the existing device/patient bindings:

```sqf
["bind", _mount, "mission-mount-000012"] call ACME_fnc_clinicalObjectRef;
```

Continue the B288/B310 coordinated save protocol: quiesce gameplay and external actions, capture owner-local clinical/inventory state, validate the participant barrier and the exact world capture, and commit all components together. Unsupported external attachment/carry state, broken mount/USB claims, duplicate slots/ports or missing durable IDs fail the world capture rather than silently flattening the relationship.

On startup, recreate empty native mounts and their transforms through the mission's ordinary object writer, bind them on the server, then restore participant clinical/cargo state before invoking world restore. Do not copy old live occupancy/attachment variables onto the recreated mount. Continue excluding ACME-owned deployed devices from that ordinary object recreator: the world importer owns those devices. Missing, occupied or wrong-kind mounts fail preflight before allocation. Staged mount failure rolls back before publishing device IDs or patient slots. Valid USB graphs are bound after device creation with range/patient checks. LS shock/pacing remain disarmed as in B310.

Runtime generation counters and local cable objects are not saved. They are rebuilt from the restored relationships. Identical import retries keep existing objects and do not rewind their live state; the existing per-mission import journal still prevents a picked-up/deleted device from being resurrected. JIP clients derive cable presentation from public state, rather than receiving saved visual object IDs.

This remains an adapter contract. The mission-specific writer, native load/save ordering and offline policy must still be connected and accepted. Existing blood/cooler/injury adapters remain separate and authoritative.

## Native acceptance still required

Test a dedicated server with two clients and an HC where used: mount/release/pickup, mounted vehicle movement, deleting a tray, ACE carry/drag takeover, delayed or duplicate requests, low server FPS, USB separation/power cycles/different patients, all sensor toggles, raised surfaces and cable clipping, JIP, an interrupted restore and a complete save/restart. Confirm tray fit and port endpoints against the supplied models in Arma. Source execution and native model parsing do not certify native rendering, attachment replication, real engine event order or a third-party persistence writer.
