# B265 — equipment transaction integrity (1.2.4.1 candidate)

## Changes implemented

- Hang Bag refuses a new removal while the previous weapon return remains unsettled. A repeated preparation callback does not replace its snapshot or remove weapons twice. The native launcher's own in-flight equipment check remains permitted.
- Primary and launcher slots settle independently. A failed attachment return can complete later only while the partial weapon fingerprint still matches what ACME created. Another weapon, a changed attachment or a fired magazine is not overwritten or refilled.
- Legacy removed-vest snapshots decode ordinary items, individual partial magazines, attached weapons including both muzzle magazines, and nested containers. Invalid structure and bounded expansion are rejected before equipment changes. Actual destination cargo must round-trip completely before custody is marked settled.
- Manual replacement timeout carries its original lease through patient-owner forwarding. A timeout cannot undo a later removal or an already completed replacement.
- Deferred evacuation respawn restore checks unit, locality, life/player state, saved preset, live equipment and generation again before writing. It invokes CBA extended-loadout hooks with magazine refill disabled instead of directly rebuilding the full unit.
- Main's two community Hang Bag contributions are merged into the development history, retaining B264's existing guarded implementations. This does not merge the cumulative development branch into main.

## Regression repair

The retained B264 full CI report is failing. Fifty of its failing cases encounter a shared test adapter replacing `netId _p` inside `netId _patient`, generating invalid SQF (`"patient"atient`). The adapter now matches complete identifiers; unchanged clinical/pose assertions execute instead of dying at parse time. The compatibility test now tests the executable-string substring used by its real runtime check. The explicit diagnostic-emitter allowlist is updated for the existing event-bounded B263/B264 diagnostics, not broadened to arbitrary output.

The historical chest-workspace fixture delegates cargo reads/writes through actual production snapshot/populate/comparison functions with explicit engine boundaries. SQF-VM numeric/config/cargo/animation adapters are not claimed as rendered Arma or delivered network validation.

## Live dedicated-server gate

Use the same complete B265 files on server, two clients and HC, including the actual hidden-selection uniform addon.

1. Hang Bag raise/lower repeatedly with a rifle, launcher, attachments, partial main magazines and underbarrel magazines. No changes to uniform, gloves, sleeves, boots, camouflage, vest/backpack or unrelated items.
2. Force one attachment restoration failure; retry without changes, then retry after firing, swapping an attachment or installing a different weapon. Only ACME's unchanged partial slot may complete. The other slot must not resurrect after being settled and removed by the player.
3. Attempt a second Hang Bag with unresolved weapon custody. No additional weapon may be removed or silently lost. Normal prepared launch must not reject its own pending snapshot.
4. Restore legacy carriers containing duplicate items, partially loaded magazines, packed attached weapons and nested containers. Force a cargo insertion refusal. Either every item returns exactly or original evidence remains unsettled; no silent loss or refill.
5. Delay an old Replace Plate Carrier timeout until a new Remove begins, including owner migration. Old callbacks must not touch the current carrier or lease.
6. Respawn and immediately change kit, apply another preset or transfer ownership before the deferred restore runs. A stale restore must not overwrite the newer equipment. Test participating CBA loadout metadata integrations.
7. Regress chest seal, thoracostomy, Semi-Fowler, wake/Get Up, carry/drag and vehicle transitions with both living and dead casualties. No duplicate gear, missing uniform parts or abandoned equipment custody.

## Scope and remaining acceptance

No per-frame full-loadout restore watchdog was added. No arbitrary third-party object variables are copied. CBA hooks support cooperating addons but cannot reconstruct missing original metadata or guarantee every custom uniform integration. Coordinating *all* intentional Arsenal replacements with every pending external equipment transaction remains a separate integration task; the new entry/restore guards do not claim that broader work is finished.

Require full regression/static checks plus Windows HEMTT release/signatures and live modpack acceptance before public deployment. Main is not advanced or published by this candidate.
