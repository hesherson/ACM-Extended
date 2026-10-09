# B267 — patient carrier custody across explicit kit replacement

Candidate **1.2.4.1 / B267**, protocol **1**, based on B266 `f5a2f5e80c697eb3598585270635baf2600cf241`.

## Implemented behavior

An explicit, completed, owner-local kit replacement now also retires the old patient's removed-carrier custody. The replacement kit remains authoritative: an old removal, return, readiness acknowledgement or forwarded equipment request cannot strip or refill it.

The carrier's current supplies stay in the **same original ground inventory object**, preserving actual looting/treatment changes, individual magazine ammunition, packed weapons, nested contents and existing container metadata. The old carrier's **empty wearable shell is exposed separately** in a standard ground holder. These are independent world items, not an automatic merge into the replacement outfit. Clearing the patient's references prevents later patient deletion from deleting these retired possessions through ACME's patient-prop cleanup.

Manual, chest-seal and Semi-Fowler carrier contexts use the same transition. A manual carrier explicitly borrowed for head support retires once, not as two duplicated vests. A different or unidentified holder, multiple unrelated records and malformed legacy data are rejected without deleting the recovery evidence.

Legacy snapshots are decoded by the same validated parser used for normal vest restoration. An absent holder previously marked live never triggers restoration of historical supplies: spent/deleted contents stay gone. If a verified physical holder exists, its real contents win even if an old bookkeeping flag disagrees.

A failed engine insertion/creation of the wearable shell leaves the original live supplies, visual prop and recovery record intact. It does **not** report a successful shell or put old equipment on the new patient. Shell-failure recovery remains an explicit operator/integration task rather than an unbounded retry loop.

## Callback authority

- Carrier custody records carry their kit generation; returned snapshots must still match the current record.
- Pending no-animation removal, bare-chest preparation and deferred normalization/return callbacks recheck the captured kit generation.
- Forwarded carrier/chest-entry/manual/head-elevation acquisition requests retain their original kit generation through locality reroutes. This is an ordering guard, not network sender authentication.
- Obsolete chest-seal/thoracostomy panels close on their patient's kit change; only old procedure membership/animation ownership is retired. Completed clinical interventions, tubes and wounds are not reset.
- New helpers are native core PREP functions, not late overwrites of ACE/CBA bindings. No full-unit medical loadout setter, inventory-difference polling or arbitrary third-party variable-copying was introduced.

## Supported integration boundaries

B266's completed ACE Arsenal and CBA extended-loadout paths invoke this owner-local coordinator. An external script using a raw full-kit setter must still emit the documented notification **after successful replacement**, on that unit's owner:

```sqf
["ACME_equipmentKitReplaced", [_unit]] call CBA_fnc_localEvent;
```

Do not emit this for firing, looting, single-item changes, opening/closing Arsenal or importing a saved-preset library. Unhooked raw setters, unrelated inventory mods and mission cleanup policies are not magically intercepted.

## Automated coverage

The B267 tests execute actual production custody/archive/legacy parser and snapshot/populate/comparison functions with explicit engine boundaries. Six selected race cases also execute against unchanged B266 source to demonstrate the old behavior: reuse of an old snapshot against new same-class custody; delayed nonanimated removal stripping a replacement; stale bare-chest readiness; stale denied-roll restoration; and two forwarded acquisition operations crossing a kit boundary.

Mocks do not prove rendered uniform selections, engine nested-container behavior, actual global-object replication, network packet delivery or mission garbage collection. The final validation evidence/CI result must be checked separately.

## Mandatory engine and dedicated-server acceptance

Use identical complete B267 PBOs and keys on server, two clients and a headless client, including the operator's real uniform/weapon/loadout mods.

1. Remove a loaded carrier through manual removal, chest seal and Semi-Fowler, then deliberately apply a different patient kit. The new uniform, gloves/boots/sleeves, vest and all new items must stay unchanged. The old live supplies must remain in their original ground inventory and one old empty vest must be independently recoverable.
2. Consume, loot, add and rearrange supplies while the old carrier is parked, including partial magazines, packed weapons and nested containers. Retired contents must equal what actually remained, not the original worn snapshot. Verify mod-specific container state that the unit uses.
3. Repeat with an intentionally empty new vest slot, repeated ACE/CBA completion notifications, a borrowed manual head-support carrier and a deleted old live holder. No old vest is automatically reworn, no shell is duplicated and no destroyed/used supplies are recreated.
4. Deliver old removal/normalization/readiness/owner-command callbacks after applying a new kit, then after starting another new-kit chest procedure. Old work must not alter the new equipment or acknowledge its preparation. Completed chest seals/tubes and physiology remain intact.
5. Change patient owner among server, client and HC during the transition; close/reopen the old chest interfaces rapidly. Exactly one owner retires custody; no duplicate world shell, stuck provider or late restoration. Repeat on dead patients.
6. Force shell creation/cargo rejection. Supplies and recovery metadata must survive without changing the new kit; no automatic-success message. Verify deliberate operator recovery of that record. Test malformed/ambiguous legacy records without silently discarding them.
7. Despawn the original patient after successful retirement. ACME must not delete the retired world supplies/shell through the patient's Deleted handler. Separately test the mission's own cleanup system and vehicle/transport behavior.
8. Regress ordinary carrier removal/return, patient movement/wake/Get Up, carry/drag, chest seal, thoracostomy and Semi-Fowler **without** kit replacement. Existing behavior and present-day supplies remain correct.

Automated success is not public-release approval. Windows HEMTT release/signature verification and this native multiplayer/modpack matrix remain required. No merge to main, balancing PR or public deployment is included in this batch.
