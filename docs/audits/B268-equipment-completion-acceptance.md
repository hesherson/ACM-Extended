# B268 — authoritative kit completion and delayed carrier access

Candidate **1.2.4.1 / B268**, protocol **1**, based on B267 `5526413eb2567d7fb6031b4f5feff68019d5a54b`.

## Kit replacement boundary

ACE Arsenal's clipboard-import notification is emitted after any parsed array, including an empty array that never invokes a loadout setter. Treating that button notification as an applied kit archived parked patient equipment, retired Hang Bag custody and erased virtual medication records without a replacement. A valid saved/clipboard load also reached the coordinator twice: once through CBA's extended setter and once through ACE's later UI notification.

B268 uses the actual unit from `CBA_loadoutSet` as the sole ACE/CBA replacement notification. ACE's post-button notifications no longer initiate a reset. Parsed clipboard arrays that never invoke the setter, button-only events, preset-library imports, ordinary Arsenal browsing and single-item inventory changes leave current custody and medication state intact. Two separate extended-setter calls remain two distinct boundaries even when their loadout arrays are identical. Respawn and the explicit owner-local integration event remain supported on their existing paths.

This contract is supported from the project's declared minimum CBA/ACE 3.18.0. The supplied ACE source routes both saved loads and applied clipboard imports through the extended CBA setter; ordinary mission Arsenal open/close do not invoke that setter. Official minimum-version sources confirm the same behavior:

- [CBA extended setter](https://github.com/CBATeam/CBA_A3/blob/v3.18.0.241008/addons/loadout/fnc_setLoadout.sqf)
- [ACE saved-load button](https://github.com/acemod/ACE3/blob/v3.18.0/addons/arsenal/functions/fnc_buttonLoadoutsLoad.sqf)
- [ACE clipboard-import button](https://github.com/acemod/ACE3/blob/v3.18.0/addons/arsenal/functions/fnc_buttonImport.sqf)

CBA emits its post-set event after invoking the engine setter. This is a completed supported setter path, not independent proof that the engine accepted every malformed or mod-specific item. ACME does not override that setter or infer kit replacements from inventory differences. Engine refusal of an attempted CBA setter remains a native limitation; no universal success detector is claimed.

Raw full-kit writers must still notify the owner after applying their intended replacement:

```sqf
["ACME_equipmentKitReplaced", [_unit]] call CBA_fnc_localEvent;
```

## Delayed chest-access authority

Pending ACCESS preparation now carries its original kit, patient ownership generation and shared access-request episode. Concurrent provider leases share that preparation; losing the last lease retires it. Cancellation followed by a new same-kit request cannot revive an older removal or readiness callback. Front normalization, bare-chest readiness, animation-free removal and restore-wait retries retain this authority. Chest-seal outer readiness/normalization waiters retain it too. A new owner may explicitly resume an unfinished same-kit workspace while preserving its original posture, grounded policy, membership and live carrier custody; retained failed-archive evidence cannot be adopted into a later kit.

Removal rechecks the patient vehicle boundary at the actual commit. Loading the casualty during a provider/lay-flat wait preserves seated equipment and completes the valid request through the existing vehicle-care path. Ownership changes retire machine-local preparation markers; kit replacement retires the old request alongside its leases. Current carrier contents and completed clinical interventions remain governed by the existing B267 custody transition.

## Verification and native acceptance

The validation evidence records pinned-SQF-VM before/after reproductions, retained regression modules, strict native owner/build checks, HEMTT checks and the exact final GitHub full-suite result. The tests exercise production handlers and cargo/custody algorithms with explicit adapters for native engine/UI/network boundaries. They do not render uniforms or reproduce real Arma network scheduling.

On identical B268 server/client/HC packages, verify:

1. Prepare syringes/open a vial, start Hang Bag or remove a loaded patient carrier, then import `[]` and another parsed array of unsupported length. No equipment epoch change, medication loss, weapon return, carrier archival or treatment cancellation should occur.
2. Apply a valid saved kit and valid clipboard kit, including to a different owner-local unit. Each actual application resets that unit once. Repeat two real applications with identical arrays; each must retire its own earlier equipment generation. Browse/close Arsenal and change one item without replacing the kit.
3. Cancel chest-access preparation while Semi-Fowler is lowering, then deliver its old callback. The worn carrier and readiness state must remain untouched. Start a new preparation before delivering the old callback; only the new request may complete.
4. Keep a second access lease active while cancelling the first. Shared preparation must still complete for the remaining provider. Cancel the last member; old work must retire.
5. Load the casualty into a vehicle during delayed removal and during the provider presentation wait. The worn carrier stays on; valid vehicle care proceeds. Repeat with pre-existing removed-carrier custody and check its ordinary vehicle restoration.
6. Transfer patient ownership away and back before a deferred callback. Old work must not remove gear or publish readiness, and a fresh request must not be blocked by old local busy markers.
7. Regress manual remove/replace, CPR, auscultation, chest seal, thoracostomy, Semi-Fowler, normal wake/transport returns, real modded uniforms and weapon addons, with clean RPT.

Windows release/signature checks and native multiplayer acceptance remain required. Automated validation does not certify public-release readiness. The known Hang Bag native automatic-magazine behavior remains a separate follow-up requiring exact magazine/container conservation.

Remaining separate follow-up: ACCESS owner-event stop-before-start packet ordering has no closed-token tombstone yet. B268 fences accepted preparation and its delayed callbacks; it does not claim to certify every remote packet ordering or hostile-client authorization path.
