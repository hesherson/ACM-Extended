# B310 deployed-equipment persistence

B310 supplies a trusted server adapter for deployed Tempus Pro, Tempus LS, ACCUVAC and the Ventway representation/custody. Version 1.2.4.1, protocol 5; use the same complete build on every machine. This does not install a mission database or autosave service.

## Ownership and durable IDs

`ACME_eqDevices` contains devices allocated by the equipment integration. Before capturing, bind each live device, connected patient, linked external world Pro, ventilator supplier/recovery operator and original supply vehicle to a unique ID owned by the mission save system:

```sqf
["bind", _device, "mission-device-000042"] call ACME_fnc_clinicalObjectRef;
["bind", _patient, "mission-patient-000007"] call ACME_fnc_clinicalObjectRef;
```

Check the Boolean result. Allocate IDs from the mission's durable object registry; do not restart an array-index counter or use network IDs as cross-restart identity. A missing durable reference fails capture rather than silently losing a device or its recovery path. Statically placed objects outside `ACME_eqDevices` stay with the mission's existing object persistence.

The new adapter owns recreation of the devices in its payload. Exclude those objects from the ordinary world-object writer/recreator. Continue using the existing cooler/fridge/cargo adapters for those objects; cooler cargo is not copied into this payload.

## Coordinated capture

Quiesce gameplay and external inventory/medical actions. Use the B288 owner-local checkpoint and barrier protocol for all affected participants, including ventilator suppliers and recovery operators. Capture patient clinical state using the medical serializer, and save native cargo/extended inventory through the existing adapters. Nothing here freezes arbitrary third-party actions.

On the server, after participant preflights and while the barrier remains valid:

```sqf
private _world = call ACME_fnc_equipmentWorldSnapshot;
if (_world isEqualTo []) exitWith { /* Retain the previous checkpoint; retry. */ };

// Obtain the exact owner-local clinical/inventory captures and their proofs.
// Immediately before committing, require BOTH their normal barrier validation
// and this world validation:
private _worldOK = [_world] call ACME_fnc_equipmentWorldCaptureValid;
if (_worldOK) then {
    // Commit _world and the matching clinical/inventory/cargo captures together
    // through the mission's existing writer, only if ALL component checks pass.
};
```

`[]` means failed capture. `[1,[]]` means a valid empty deployed world. Pending setup, pickup, refunds or cooler loading now also block the server-wide journal readiness check. A device marked busy, missing binding, unsupported row or changed world invalidates its checkpoint. Patient and carried-device setup admissions honor the participant persistence fence.

The exported array contains only arrays, strings, numbers and Booleans, suitable for the mission's serializer. Preserve numerical precision. Schema: `[1, rows]`; each row is `[deviceID, kind, positionASL, direction, up, manuallyPlaced, patientReference, observationState, pairedProReference, ventCustody]`. Observation state is `[powered, fiveProSensorFlags, lsPads, lsECG]`. References retain the existing clinical incarnation/stable-ID contract. Vent custody retains supplier ID/UID, original supply vehicle and recovery operator ID/UID.

## Restore order

1. Keep gameplay quiesced. Restore the global donor registry, mission units, native cargo and extended inventory using their existing adapters. Bind recreated patients, suppliers, operators and vehicles to the saved IDs on the server and on any owner performing clinical reference decoding.
2. Restore patient clinical state on the actual patient owners and wait for its completion/replication. Ventilator settings and battery live in that clinical state. A saved ventilator must already be marked mounted by that restore; this adapter refuses to create an unfunded ventilator for an unmounted patient.
3. Before ordinary gameplay or object recreation, invoke the world importer once on the server:

```sqf
private _result = [_savedWorld] call ACME_fnc_equipmentWorldRestore;
_result params ["_ok", "_objects"];
if (!_ok) exitWith { /* Keep gameplay paused and inspect the adapter ordering. */ };
```

The importer validates the entire payload and resolves required durable references before allocation. It refuses a live deployed registry, occupied patient slots, conflicting IDs, existing ventilator custody or missing required objects. A failed allocation deletes only staged objects and publishes no bindings or patient slots. Successful import publishes the new stable bindings and canonical patient/device relationships. It starts observation feeds on patient owners; public object variables supply the normal JIP state. Actual replication/JIP still require native multiplayer acceptance.

Retries of the identical import return the existing objects without moving or resetting them. A different payload is refused. Deleted, picked-up or rebound objects cannot be resurrected by replaying that import. The import journal deliberately remains for the entire mission; do not clear it to reload an older checkpoint over live gameplay. Start a fresh mission incarnation to restore another complete checkpoint.

Pro/LS pairing is resolved after both devices exist. Pairing respects range and patient compatibility; a pair that is no longer compatible detaches. Missing required references fail preflight. External pair targets must be recreated world Pro objects; a carried Pro must be paired again after restoring its owner.

LS charging, shock authorization, pacing, metronome and browser runtime state are cleared. Cached vitals and NIBP results are discarded, and current observations are reacquired. Browser display preferences/alarm-profile JSON are intentionally not exported in this schema because the same opaque state carries therapy controls. Power and physical sensor selections persist. This build does not add a new monitor battery simulation or replay elapsed offline clinical treatment.

Ventway restores one native attached-custody record, preserving the original supplier and recovery/vehicle path without another inventory debit. Its battery/settings remain those from the matching restored patient state. Offline timing continues to follow the existing explicit adapter policies; world restore invents no elapsed interval. Oxygen supply sessions remain cleared by clinical restore and require normal reconnection. Model changes retain the device's durable binding, and a failed model allocation retains the previous representation.

## Acceptance still required

Run a dedicated-server save/restart/JIP test with the actual mission writer, two clients and a headless client where used. Verify transforms on terrain and raised surfaces, patient ownership migration, pickup after import, LS safe state, Ventway recovery after patient deletion, oxygen-model replacement, cooler contents and an interrupted import. The automated execution harness substitutes native object, geometry and RPC boundaries. It cannot certify Arma physics, replication order or mission-specific writer atomicity.

The Tempus front-panel artwork, physical docking/cables, worn HPMK and long-term collection-date shelf life remain separate work.
