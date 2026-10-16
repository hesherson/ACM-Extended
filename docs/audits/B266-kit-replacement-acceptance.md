# B266 — Explicit kit replacement and stale Hang Bag cleanup

Candidate **1.2.4.1 / B266**, protocol 1. Base: B265 `4a211f12b4fae689455fc5e15870f8de7e96a499`.

## Implemented

- A completed, owner-local kit replacement advances an equipment generation and retires prior Hang Bag weapon snapshots. The new kit is authoritative: old temporarily removed weapons are not added to its empty slots.
- Active and pending Hang Bag reservations are released using their original patient/episode. Kit-reset cleanup does not play an exit animation, select weapons, rebuild equipment or reopen Transfuse Fluids. The normal same-kit lower/return behavior is unchanged.
- Delayed lowering teardown, deferred stance release and deferred transfusion-menu reopen all check the captured kit generation. Late preparation/cancel and owner-targeted weapon returns reject earlier-kit records.
- ACE Arsenal full load and applied clipboard-import boundaries reset the actual edited `ace_arsenal_center`, not an unrelated `ACE_player` viewing that unit. Editor/library-only imports and nonowner callbacks are ignored.
- CBA extended-loadout completion hooks work on each actual local unit, including AI on server/HC, and reset obsolete prepared-syringe/open-vial bookkeeping at that same explicit boundary.
- Deferred evacuation restoration also checks equipment generation, so even an intentional new kit with an identical ten-slot array invalidates an older pending restore.
- A source regression prohibits whole-unit loadout setters in ordinary Extended medical functions. No periodic inventory-difference scanner or restore-snapshot watchdog was introduced.

The new coordinator is registered by the native core `XEH_PREP.hpp`. It does not overwrite ACE/CBA functions or copy arbitrary third-party object variables.

## External setter contract

On the unit's owner, **after a successful intentional full-kit replacement**, emit:

```sqf
["ACME_equipmentKitReplaced", [_unit]] call CBA_fnc_localEvent;
```

This is a trusted local integration notification, not a remote command or a new setter. It retires the prior kit's temporary Hang Bag weapon records and its virtual medication records. Do not emit it for single-item changes, magazine use, opening/closing an inventory, or saving/importing a preset library.

ACE Arsenal and CBA extended-loadout paths are wired automatically. CBA's raw ten-element overload and direct `setUnitLoadout` calls do not emit its extended hooks: mission/third-party scripts using those setters need the notification above. Do not apply a foreign unit's replacement on a nonowner and then expect this handler to repair it remotely.

## Dedicated-server acceptance

Use identical B266 PBOs on server, clients and HC. Retest with the actual uniform and weapon addons.

1. Start Hang Bag, then apply a different kit with empty weapon slots. No old rifle/launcher may appear, and no old menu/animation may reopen. Repeat while waiting for a patient claim and while the bag is lowering.
2. Apply a kit after the normal lower queued its final stance/menu callbacks, then deliver those callbacks late. They must not touch the replacement kit or UI. A same-kit lower must still animate, restore and reopen normally.
3. With an incomplete weapon return, apply a new kit. The old hidden snapshot must not block another new-kit Hang Bag or recreate the original equipment. A late owner-targeted restore remains harmless.
4. Open ACE Arsenal for a different owner-local unit. Apply/load/import a kit. That unit's equipment/medication ledgers change; the viewer and other patients are untouched. Repeat on AI/server/HC through CBA's extended setter.
5. Browse/close Arsenal, take/put one item, fire a magazine, or import a list of presets. These must not invalidate a live kit. Editing in Eden must not run mission equipment cleanup.
6. Queue evacuation respawn restoration, then load an identical-array kit with changed metadata before its callback. The older restore must be rejected even though the array comparison alone cannot distinguish them.
7. Disconnect and transfer locality during pending/lowering states. Verify exactly one patient claim release, no duplicate weapon return and clean RPT.
8. Repeat the B265 weapon/legacy-cargo and B264 manual-carrier tests without intentional kit replacement. Ordinary treatment must remain unchanged.

## Limits, not release approval

This batch covers explicit kit replacement for **Hang Bag and personal medication state**. It deliberately does not delete or settle a patient's parked carrier's live contents or chest-procedure custody during an external kit replacement; coordinating that separately owned physical inventory remains follow-up work. It does not claim to intercept arbitrary raw loadout writers without their notification.

Real `addWeapon` automatic magazine selection, hidden-selection rendering, Windows release/signatures and dedicated-server behavior require engine testing. Passing SQF-VM/static/CI checks is not public-release approval. No change to main or mass/weight PRs is included.
