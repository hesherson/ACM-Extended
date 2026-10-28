# B288 persistence adapter contract

B288 remains version **1.2.4.1**, network protocol **2**. Use the same complete build on the server, clients and headless clients. These APIs provide ACME state to a mission's save system; enabling persistence in a mission does not install an adapter automatically.

## Equipment saves

Native loadout/cargo arrays contain item classes and opaque magazine IDs. They do not contain prepared drugs, exact bag contents, partial vial stores, cooler exposure, ventilator settings or removed-vest custody.

`CBA_loadoutGet` now supplies these extended metadata keys together:

| Key | Contents |
| --- | --- |
| `ACME_inventory_v1` | Prepared IV/Y sets and syringes, contents, volume and patient ties |
| `ACME_coolers_v1` | Each identified cooler's coolant age and per-bag warm exposure |
| `ACME_equipment_v1` | Partial vials, used bags, carried ventilator state, removed vest and nested cargo |
| `ACME_blood_v1` | Ordinary loose-blood class/count records and warm exposure |
| `ACME_checkpoint_v1` | `[1,true]` for a complete local capture, `[1,false]` if busy or invalid |

An empty metadata array is a failed capture, not an empty inventory. The hook cannot cancel an arbitrary external file writer. An unattended adapter must honor readiness and retry; never replace a good saved checkpoint with failed metadata.

For owner-local export, use:

```sqf
[_unit, {
    params ["_ok", "_extendedLoadout", "_args", "_reason"];
    if (!_ok) exitWith {
        // Keep the previous saved checkpoint. Retry after the reported cause.
    };
    // Pass this exact _extendedLoadout to your mission's writer here.
    // Do not obtain another native loadout on a later frame.
}, [], 30] call ACME_fnc_persistenceLocalCheckpoint;
```

The callback receives `[nativeLoadout,metadataHashMap]`. Serialize the metadata explicitly using the mission's supported format; do not assume a native-loadout-only serializer will preserve the HashMap. `ACME_fnc_persistenceCheckpoint` is a compatibility alias for this local API. This callback is not an atomic world save or remote-owner acknowledgement.

Restore through the matching CBA extended-loadout setter once, on the inventory owner. The hook imports metadata after the completed kit-replacement boundary. For an adapter that already applied its native loadout and called the appropriate kit lifecycle boundary, `[_unit,_metadata] call ACME_fnc_persistenceRestoreExtended` starts the metadata import. Do not reapply the native loadout to retry an incomplete import.

`ACME_persistenceLastRestoreOK` becomes true only after the imported custody settles. Initial `true` from the import function accepts the retry job; it does not prove that native items have appeared. A timed-out job retains unresolved evidence. Retrying the same metadata in the same kit/locality period continues its funding journal; a later kit cannot receive the former kit's refund. Normal Arsenal/fresh-kit resets remain intentional and separate from explicit restore.

Bag returns are funded independently of their UI result. Unknown native placement, an unavailable original machine, or a deleted recipient can leave an explicit held product. Such a journal blocks a checkpoint; a timeout is not permission to refund or deliver another copy. This pass does not automatically redirect an orphaned return into a respawned/replacement unit. Resolve the original outcome or use a deliberately reviewed mission/admin recovery policy before saving that transaction.

Removed vest contents are recreated with their patient association. Human-held treatment sessions do not resume. The vest returns through the normal custody routine after imported native grants settle; failed placement keeps its associated cargo for retry instead of deleting it or restoring a stale pre-looting copy.

Carried ventilator settings remain one state block per medic, as in the existing device implementation. Import preserves its battery and settings when the native item exists, and leaves the device powered off. It does not invent a per-item identity for multiple carried ventilators.

## Coordinated multiplayer saves

The mission must first quiesce gameplay, inventory transfers and external ACE/mod actions for every participant. ACME cannot freeze the engine or a third-party persistence script.

Run a full owner-local snapshot preflight for each participant before beginning the lease. This lets nested-item adoption and known expired supply bindings settle while reservations are still allowed. Discard these preliminary captures; obtain fresh captures under the lease. `[] call ACME_fnc_persistenceJournalsReady` checks all known server journals, including funded returns whose original actor was deleted. Both lease creation and final validation require this server-wide preflight; owner-local proof is still required separately.

On the server:

```sqf
private _lease = ["begin", _units, [], 30] call ACME_fnc_persistenceBarrier;
if (_lease == "") exitWith { /* Keep the previous save and retry. */ };
```

The lease rejects already busy participants, fences covered new ACME admissions and lets existing acknowledgements settle. Obtain each unit's local checkpoint on its actual owner after its published lease arrives. Return each exact result to the server through the mission's transport, then validate the complete set:

Immediately before the final server validation, run `[_unit,_capturedExtendedLoadout] call ACME_fnc_persistenceCaptureValid` on each actual owner and require `true`. It compares the current native inventory and stable component facts, then publishes proof tied to the lease. The local checkpoint API creates an initial proof automatically; a delayed save must revalidate it. Captures obtained through ordinary CBA getters also require this explicit owner proof. Allow its publication to reach the server before validation; retry validation while the bounded lease remains valid.

```sqf
private _valid = ["validate", _lease, _captures] call ACME_fnc_persistenceBarrier;
// _captures = [[unit, returnedExtendedLoadout], ...], one per participant.
if (_valid) then {
    // Persist these captures and required world metadata in one mission checkpoint.
};
["end", _lease] call ACME_fnc_persistenceBarrier;
```

Validation checks the matching lease, all participants, required schemas, owner proof, kit/locality/clinical epochs, native loadout baselines and authoritative transaction readiness. Advancing exposure/collection ages do not count as changed physical contents; exact volumes, settings and virtual stores do. The bounded watchdog releases abandoned leases. A failed, expired or incomplete validation must not become the new saved checkpoint. This is an adapter protocol, not automatic Antistasi/Liberation integration; those missions' actual writers and object recreation order still need an adapter and native acceptance.

## Medical state and object references

Continue saving medical state through `ace_medical_fnc_serializeState` and restoring through `ace_medical_fnc_deserializeState` on the patient owner. Raw equipment metadata does not replace the medical serializer. B288 rebaselines the acid/base maintenance clock, including old snapshots with a raw `acidLastTick`, so a restarted mission clock cannot stall those updates.

Object references include a mission incarnation and an optional mission-defined durable ID. Before saving, bind relevant providers, vehicles and devices on the saving machine; bind recreated objects on the restoring machine before restoring patients:

```sqf
["bind", _object, "mission-owned-unique-id"] call ACME_fnc_clinicalObjectRef;
```

The mission owns those IDs and their uniqueness. An optional `ACME_clinicalObjectResolver` callback accepts `[id]` and returns the correctly marked object. Unresolved cross-restart references detach safely; an unrelated object with a recycled network ID is never an automatic replacement. Legacy netId-only references require explicit same-session attestation to resolve. Scalar physiology still restores when a reference cannot be resolved. Active human input sessions and runtime handlers are rebuilt or canceled rather than saved as live handles.

## World objects and native donor blood

Save recreated object transforms and ordinary cargo through the mission's normal object persistence. Export/import ACME state separately:

| Object/state | Export | Import |
| --- | --- | --- |
| Deployed cooler | `[_box,"box"] call ACME_fnc_coolerSnapshot` | `[_newBox,_saved,_offlineSeconds] call ACME_fnc_coolerRestore` |
| Blood fridge | `[_fridge] call ACME_fnc_bloodFridgeSnapshot` | `[_newFridge,_saved,_offlineGameMinutes] call ACME_fnc_bloodFridgeRestore` |
| Opaque crate equipment | `[_crate] call ACME_fnc_inventorySnapshot` | `[_crate,_saved] call ACME_fnc_inventoryRestore` |
| Loose blood exposure | `[_holder] call ACME_fnc_bloodExposureSnapshot` | `[_holder,_saved] call ACME_fnc_bloodExposureRestore` on server |
| Global native fresh-blood donor registry | `[] call ACME_fnc_freshBloodSnapshot` on server | `[_saved,_offlineSeconds] call ACME_fnc_freshBloodRestore` on server |

Check every result. Holder/crate imports require the corresponding saved native items first. New deployed objects must not carry copied live tokens or transaction bindings. Fridge state includes stock, defaults, restocking policy and remaining game-time delay; pending grants make an export busy.

Native donor bag classes encode a configured donor ID (`ACM_FreshBloodBag_500_17`, for example). Save the global donor registry once in the coordinated mission checkpoint. Restore it at startup, before saved native donor bags become usable or new donors are collected. The importer refuses to overwrite a populated live registry with different saved donors. The compatibility seed at ID zero is permitted. A per-unit native bag class/ID alone cannot prove which historical donor it meant, so unsupported aggregate saves are refused rather than silently assigned current donor facts.

Hung fresh blood, prepared sets and used bags also carry immutable donor status/type and normalized collection age. A missing record is explicitly fenced. It cannot fall back to a newly reused donor ID, and an unresolved hung fresh bag does not drain or credit blood. Manufacturer capacity remains at IV bag index 9; portable donor facts use index 10.

Offline aging defaults to paused. The mission may supply validated elapsed offline seconds for coolers/donor records, or elapsed offline game minutes for fridges. No importer guesses elapsed real time from a previous mission clock.

## Identity storage and limits

Keep the server profile with the mission's save data. The opaque-carrier allocator reserves blocks in `profileNamespace` before using them, so ordinary restarts do not recycle IDs. There are **65,534 IDs across that profile**, including abandoned reservations. Exhaustion fails closed and retains funded work. Migrate through explicit metadata import into a fresh profile when needed; resetting a profile and loading raw old tokens is unsupported. See [the inventory contract](B288-inventory-persistence.md).

Ordinary same-class blood bags have class/count identity. Indistinguishable swaps performed by arbitrary external scripts cannot be reconstructed exactly; exposure reconciliation remains conservative. All production execution tests substitute native inventory, network, display or disk boundaries. Native save/restart, real replication order, rendering and the chosen mission adapter remain acceptance requirements.

Nested worn containers and removed-vest cargo retain opaque equipment metadata recursively. Loose blood inside those nested cargo trees is currently refused by the equipment checkpoint: its ordinary cold-chain exposure is not included in that tree format. Move it to a supported tracked inventory/cooler before the coordinated save, or implement a mission adapter that preserves its exposure explicitly. Refusal keeps the previous valid checkpoint; it never records the bag as fresh.
