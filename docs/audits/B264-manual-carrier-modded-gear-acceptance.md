# B264 — Manual carrier and third-party uniform/equipment acceptance

**Candidate:** ACM Extended 1.2.4.1, build B264, protocol 1; this is *not* public release approval.

## Defects targeted

1. Eight-second manual removal timeout could run before a provider-animation handoff and the patient-owner gear transaction completed. Two stale or repeated callbacks generated misleading `Plate carrier automatically returned (remove-timeout)` entries even when no carrier was actually taken off.
2. Full `setUnitLoadout` in the Hang Bag primary/launcher handoff and an old carrier-restoration compatibility path rebuilt modded uniforms. Hidden selections configured by third-party gear addons were not represented in those loadout arrays (gloves, boots, camouflage, sleeve length, and sometimes missing hands/feet).
3. Patient-owner transfer could strand removal as "removing"; on unsuccessful restore, the old code cleared custody even when the returned vest was rejected.

## Architecture

- Persistent Remove now has patient-only Grab/Remove/Release; the provider's optional medic4 pose never gates gear availability.
- A patient-authoritative, lease-checked success worker is callable from both the original completion callback and an owner-local watchdog after migration. Failed starts use the same exact-lease abort, not a success-shaped return.
- No new blanket scans, external uniform/texture overrides, or replacement of other addons' hiddenSelection state.
- Hang Bag snapshots only weapon slots, removes each of those weapons without replacing the unit loadout, and restores the original weapon, attachments and loaded magazine ammo. It retains unmatched weapon snapshots instead of overwriting different, newly equipped weapons.
- CarrierInventoryRestore's **legacy** non-live snapshot path no longer rewrites the entire loadout. All modern live-custody carrier operations still use the existing cargo snapshot/debit/restore functions.

## Mandatory dedicated-server acceptance

Use the same complete B264 PBOs and keys on server, two clients and HC. Repeat in the actual unit modpack (with the addon that sets hidden selections), and collect all three RPTs.

1. Spawn an unconscious and a dead patient with a packed plate carrier. Click **Remove Plate Carrier** once on each. Carrier must leave and park on the correct side; the patient must complete Grab/Release. Activity log records *one* `Plate carrier manually removed`; no `remove-timeout` entry.
2. Remove/replace 20 times; manually cancel, move/carry, wake, Get Up, put in a vehicle. Every auto-return happens at most once per physical return. Do not clear a newer carrier lease.
3. Server-owned AI, client-owned player, headless-owned NPC, Zeus-controlled NPC. Transfer patient locality during each stage of removal/return; either complete the same lease correctly or give a truthful failure without permanent stuck state.
4. Force missing or delayed patient preparation (stalled animation lease): bound to 20 seconds, report an actual removal failure and leave equipment unlost. Force a restore rejection: preserve cargo, manual state, lease and retryability.
5. Use custom model uniforms with gloves, boots, camo, rolled-up sleeves and hidden selections. Verify those visuals remain *identical* after repeated carrier removal/replacement, Semi-Fowler/head elevation, Hang Bag raise/lower and disconnect/owner transfer.
6. For Hang Bag, test rifles and launchers with optic, suppressor, pointer, bipod, chamber/magazine with partial ammo and underbarrel grenade. Restore precisely the original slots and ammo without touching uniform, vest, pack or headgear. If a mod denies replacement, expect a logged deferred restore and retained original snapshot instead of silent loss.
7. Change weapons while hanging a bag with another addon: B264 must not overwrite a weapon placed in an occupied slot. Observe the RPT diagnostic and retry/correct the external conflict.
8. Test full/partially emptied removed carrier inventory, use medical items while carrier is parked, add supplies to its temporary holder; return the *current* items and magazine ammo exactly once. No stale snapshot may refill used supplies.
9. No RPT `[ACME MANUAL PC B264]` or `[ACME HANG B264]` errors in normal cases; deliberate invalid cases must have one actionable diagnostic and no duplicate action logs.

## Release gate

GitHub strict-full-suite and static/HEMTT check, local Windows HEMTT release/PBO+signature check, two-client/HC live acceptance, and clean RPTs. Regress B263 modal chest seal/thoracostomy and B261 fluids, and check PR #42/#43 contribution semantics on the modpack; do **not** merge unrelated balancing/mass PRs as a side effect.
