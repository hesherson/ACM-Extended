# B287 cooler save and restore

Coolers retain their coolant age and each blood bag's accumulated warm exposure. Persistence stores durations rather than mission timestamps, so restarting the mission clock does not refill coolant or make blood fresh. Offline time is paused unless the mission explicitly supplies an elapsed offline duration.

## CBA extended loadouts

`ACME_fnc_coolerPersistenceInit` registers `CBA_loadoutGet` and `CBA_loadoutSet` once. The `ACME_coolers_v1` extended metadata key follows `CBA_fnc_getLoadout` / `CBA_fnc_setLoadout`, including ACE Arsenal's extended loadout saves. The native inventory loadout and this metadata must be saved together. This does not add a global profile autosave or a save file shared between missions.

A save must wait for physical cooler custody to settle. `ACME_fnc_coolerSnapshot` returns `[]` when any cooler allocation, escrow, adoption, box request, mutation, restore funding or native identity is unresolved. Packing boxes and retired shells are also refused: their contents cannot be saved independently from the transaction's native carrier. A valid empty inventory returns `[1,"holder",[]]`. CBA records the failed snapshot as `[]`; `ACME_coolerLastRestoreOK` is false when it cannot be restored. Mission save adapters must check the result and retry instead of treating `[]` as an empty cooler.

Native `getUnitLoadout` / `setUnitLoadout` arrays and raw cargo lists cannot retain virtual contents by themselves. Antistasi, Liberation or another mission that saves only those arrays needs a save adapter. ACME does not claim automatic compatibility with every external persistence system.

## Holder API

Run export on the authoritative inventory owner after transfers have settled:

```sqf
private _coolers = [_unit,"holder"] call ACME_fnc_coolerSnapshot;
if (_coolers isEqualTo []) exitWith {
    // Delay this save and retry; do not record empty contents.
};
// Store _coolers alongside this unit/crate's native loadout/cargo in the mission save.
```

Recreate the native inventory first. Then run import locally on its owner:

```sqf
private _restored = [_unit,_savedCoolers] call ACME_fnc_coolerRestore;
```

The source loadout's exact cooler magazine class and opaque token must be physically present. The importer removes that exact item, checks removal, and funds a fresh server identity. It never adopts a saved token into the current server registry, where that number could already identify another live cooler. Other players' registry records remain untouched.

A journal retains removed funding if issue cannot yet enqueue. Repeating the same call retries that funding without consuming another item or applying offline time twice. Pending funding is bound to its original kit and provider-locality period; a later kit or locality period cannot resume it, and its evidence is retained for investigation. After an application completes, repeating its metadata without source items is inert. Intentionally applying the full saved native loadout again supplies new source items and constitutes a new funded application with the current admission period.

`true` means every imported item is funded into the normal inventory issue journal. Registration, replication and native placement still complete through that journal; it is not a network acknowledgement or proof that the icon is already visible. `false` means the caller must inspect/retry the failed application. A different snapshot cannot replace an incomplete funding journal.

## Deployed box API

On the server, export a deployed box:

```sqf
private _boxState = [_box,"box"] call ACME_fnc_coolerSnapshot;
```

This first reconciles the box's real cargo with its canonical per-bag exposures. Save its transform and non-blood cargo through the mission's ordinary object persistence.

After recreating a **new** box of the same cooler class, restore on the server:

```sqf
private _restored = [_newBox,_savedBoxState] call ACME_fnc_coolerRestore;
```

Do not copy the old box's `ACME_boxCoolerToken` or active ledger binding onto the new object. Import refuses to overwrite a box already bound to a live deployed token. The importer replaces blood item cargo while preserving other item cargo; it does not clear weapons, magazines or backpacks. A later normal pickup creates the box's new inventory identity. Repeating the same box import does not reset its clocks.

## Explicit offline aging

The optional third import argument is elapsed offline seconds, default `0`:

```sqf
private _restored = [_newBox,_savedBoxState,_validatedOfflineSeconds] call ACME_fnc_coolerRestore;
```

The duration must be a finite number between `0` and `1e9`. The mission owns the choice of wall clock and its validation. ACME first spends the remaining coolant duration, then adds only the expired portion at the configured insulated warming rate. The importer does not infer real time from a previous mission's timestamps.

## Snapshot format and validation

Version 1 is `[1,scope,records]`, where scope is `"holder"` or `"box"`. Each record is `[savedIdentity,savedToken,baseCoolerClass,coolantAgeSeconds,bloodEntries]`. Each blood entry is `[bagClass,warmExposureSeconds]`. Box snapshots contain exactly one record with token `0`; holder snapshots are bounded to 128 records.

All records are validated before inventory or cargo changes: known cooler type, existing blood class, native token range, finite nonnegative age/exposure, volume capacity and unique identities/tokens. No save input is compiled. Payloads contain no object references, holder network IDs, or absolute mission-clock timestamps.

Automated persistence tests execute the production export, validation, import and CBA callbacks under SQF-VM. Native cargo operations and asynchronous issue transport are explicit test boundaries. In-game save/restart, multiplayer replication and the chosen external mission save adapter still need native acceptance.
