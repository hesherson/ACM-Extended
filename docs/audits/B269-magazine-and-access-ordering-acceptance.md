# B269 — Hang Bag magazine conservation and ACCESS ordering

Candidate **1.2.4.1 / B269**, protocol **1**, based on B268 `6bd704c80b31ba92fb7242cd1cdf42058c877ede`.

## Hang Bag weapon return

Native `addWeapon` can load a compatible spare magazine automatically. Restoring a saved weapon before handling that behavior could consume a spare and prevent restoration of the saved loaded magazine. B269 temporarily removes compatible spare magazines from each original uniform, vest and backpack container before creating the missing primary or launcher. It records the observed removals as replicated per-slot cargo debt, restores the saved weapon attachments and loaded magazines, then repays the exact magazine class and round-count multiset to each original container.

Both weapon muzzles are covered by `compatibleMagazines`. The second saved loaded-magazine slot uses the weapon's second configured muzzle, including weapons whose primary muzzle has a name other than `this`. An absent loaded magazine and a loaded magazine with zero rounds remain distinct. Empty spare magazines are included through `magazinesAmmoCargo`; unrelated cargo and the loaded magazine of a retained handgun are untouched. Defaults on a newly created gun are removed before restoring saved attachments. Existing foreign or changed weapon slots retain the earlier conflict policy: they are not overwritten.

Suppression, weapon creation and repayment run without scheduled suspension. A rejected removal prevents weapon creation. A rejected return retains cargo debt and recovery snapshots, so another owner can retry repayment without creating the saved gun or loaded magazines again. Pending debt blocks another Hang Bag preparation. A deleted original container cannot receive repayment; its debt remains for inspection rather than being silently declared complete. No fallback ground container or automatic recovery watchdog is introduced.

Unexpected repayment deltas freeze further cargo changes and retain an anomaly marker. Any observed positive return discharges that attempted debt, preventing another retry from duplicating it; unattempted debt remains. An already marked anomaly performs no further restoration mutations. Deliberate full-kit replacement retires old Hang Bag snapshots, cargo debt and the anomaly marker with their original kit; old cargo is never repaid into the replacement kit.

This preserves magazine class, round count and container identity, not engine magazine-object IDs. Native commands and modded weapon acceptance still require in-engine verification. The command choices fit the project's minimum Arma 3 version 2.18: negative `addMagazineAmmoCargo` counts are supported from 2.14; no 2.22-only `removeWeaponItem` dependency is added.

- [Bohemia addMagazineAmmoCargo](https://community.bohemia.net/wiki/addMagazineAmmoCargo)
- [Bohemia confirmation of exact-round negative removal](https://feedback.bistudio.com/T174830)
- [Bohemia compatibleMagazines](https://community.bohemia.net/wiki/compatibleMagazines)
- [Bohemia magazinesAmmoCargo](https://community.bohemia.net/wiki/magazinesAmmoCargo)
- [Bohemia magazinesAmmoFull empty-cargo limitation](https://community.bohemia.net/wiki/magazinesAmmoFull)
- [Bohemia addWeaponItem](https://community.bohemia.net/wiki/addWeaponItem)

## ACCESS event ordering

An owner-local stop now records its exact lease ID even if the corresponding start has not arrived. A later start with that canceled ID cannot enroll, begin preparation, remove equipment or publish readiness while the record is retained. Ordinary stops, watchdog expiry, manual replacement/auto-return, hard-heal clearing and successful kit archival record their retired IDs without changing those paths' equipment-return policies. Failed kit archival retains its existing custody and membership evidence. Failed manual physical return retains recovery custody and allows an explicit restoration retry despite the cancellation record.

Repeated starts for an active ID on the same owner preserve the accepted shared request token and readiness timestamp. A fresh invocation after ownership changes may explicitly resume an active same-kit lease with new authority. B268's captured kit, locality and request guards continue to reject stale callbacks. Canceling one concurrent member preserves shared preparation; canceling the current ready member assigns readiness to a surviving member without resetting the shared timestamp or token.

Cancellation memory is public, bounded to **64 IDs for 180 seconds**, with FIFO eviction. Duplicate stops do not extend expiry or reorder a retained ID. An expired or evicted ID may be admitted again. This is bounded event-ordering memory, not sender authentication or a permanent replay ban. Public variables preserve records across owner handoff when delivered; arbitrary replication order and migration are not an atomic transaction. The existing single `readyLease` field also remains a limitation for multiple simultaneously waiting viewers; this batch repairs cancellation of its current member without redesigning multi-viewer readiness.

## Verification and native acceptance

The evidence records executed production SQF decisions and controlled B268 comparisons with explicit adapters for native weapon/container commands, UI, callback delivery and ownership. Retained tests, strict owner-write checks, build identity checks, HEMTT and the full GitHub suite provide automated coverage. Adapter behavior is not proof of real engine cargo mutation, network delivery or uniform rendering. The final evidence identifies the exact tested source tree and commit separately from the PR's synthetic merge checkout.

On matching B269 server, client and HC packages, verify:

1. Restore primary and launcher weapons with saved attachments, partially loaded magazines and underbarrel ammunition. Include duplicate class/round-count spares in all three containers, empty spares, empty loaded magazines and unloaded saved weapons. Compare each original container and both loaded slots before and after.
2. Use a modded rifle with a named primary muzzle, a grenade launcher and default linked attachments. Keep a loaded handgun using the same magazine class. Confirm saved attachments and both loaded slots return while the handgun and spare inventory remain unchanged.
3. Reject a weapon attachment or cargo operation through a controlled native/modded failure. Confirm restoration remains incomplete, preserves recovery evidence and blocks another preparation. Retry after the obstruction is removed; repeat after ownership transfer and with a foreign successor weapon. Deleted original containers must retain unresolved debt.
4. Replace the whole kit while Hang Bag restoration has pending debt. Deliver old restoration work afterward; the new kit must remain untouched and old debt must not be repaid into it.
5. Deliver STOP before START for CPR, breathing checks and thoracostomy, with worn and already removed carriers. Replay the same START and duplicate STOP. No canceled preparation may remove gear or publish readiness within the retained interval.
6. Run two ACCESS members, cancel each joining order in turn and confirm the survivor keeps shared preparation and readiness. Cancel the last member and deliver old callbacks. Regress CPR/BVM handoff, manual return, watchdog expiry, hard heal and successful/failed kit archival.
7. Transfer ownership during preparation, deliver retained cancellation records before a stale start and explicitly resume a valid surviving same-kit request. Separately test delayed public-variable delivery; no atomic cross-owner delivery guarantee is claimed. Check expiry at 180 seconds and FIFO eviction after 64 IDs.

Native Windows release/signature checks, real dedicated-server/two-client/HC acceptance and clean RPT review remain required. This candidate is not certified for public release or every network ordering.
