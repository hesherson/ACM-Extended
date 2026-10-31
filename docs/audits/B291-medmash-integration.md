# B291 medical feature integration

Candidate identity: **1.2.4.1 / B291**, protocol **2**, based on B290 commit
`07e972b1480c6a6e41dcc2399d3a1998af207d6a`.

## Source and scope

The user explicitly approved incorporating the content previously held on dev.
The source is [PR #2, Port medmash medical extras](https://github.com/hesherson/ACM-Extended/pull/2),
head `871e1e7e4b9652c2c195551efaf1350e88b4719d`, with the later clinical fixes in
dev `a277ce1c6c03ffbae49a9548eedb180a961fae70`. The selected content is adapted
to B290 rather than replacing current files with the older dev branch.

The complete package adds five source addons: `burns`, `infection`,
`ophthalmology`, `card` and `card_main`. The first three retain their ACM public
namespaces; cards retain `DD1380_card`, `DD1380_main` and their original virtual
asset paths. Imported author and asset credits are preserved. The original PR
removed the legacy FAK addons; they remain excluded. ACME's existing external
EFAK inventory and oxygen compatibility remains capability-gated.

DD1380 is now bundled. Do not load a second standalone DD1380 copy alongside
this build; the copies share public patch, function and asset namespaces.
The imported DD1380 modules retain their declared Arma 3 minimum of 2.20.

The two DD1380 addons declare HEMTT's per-addon `ignore_pboprefix` option so
their public virtual paths remain intact. The offline prefix gate checks those
two exact mappings and declarations; ordinary native prefix checks remain in
force. No other strict HEMTT checks are disabled.

## Behavior and ownership

- Burn wounds, dressings and cream connect to the current wound system. Systemic
  and airway effects feed the existing native vital and temperature owners.
- Infection and sepsis consume current antibiotic medication records and supply
  distinct fever, cardiovascular, respiratory, metabolic and coagulation inputs.
- Ocular trauma, shields and eyewash run on the casualty owner. New ocular
  injuries are enabled by default and remain configurable by the mission.
- Eye-shield attempts reserve real supplies and settle against the owner result.
  Rejected or cancelled attempts return only their own reservation; duplicate
  delivery cannot create another shield. Checkpoints wait for funded requests
  to settle rather than saving a partial inventory/medical transition.
  An expired orphan with no recoverable outcome is retired as spent; it cannot
  generate a refund or additional equipment from an uncertain result.
- Ordinary disease effects can recover. Hardcore structural sequelae and their
  evacuation requirement remain latched until definitive reset.
- Clinical persistence carries durable disease state and card contents. Owner
  reconciliation restores active processing without duplicating workers or
  retaining stale local timing state.
- DD1380 uses authored source configuration. A card session captures its patient,
  clinical epoch and edit revision; page changes retain a local draft, and final
  submission cannot silently overwrite a newer card.
- Installation diagnostics require all 19 exact component stamps. Deployment
  adds the five new PBOs to both managed targets and retains rollback behavior
  when upgrading from the old 14-addon installation.

## Native acceptance

Automated checks do not certify rendering, scheduling, multiplayer transport,
animation/audio or actual engine save/restart behavior. Before public release:

| Scenario | Expected result |
| --- | --- |
| Blast burns, wound dressing/cream and existing penetrating trauma | Correct wound depth and treatment; no new penetrating fatal-trauma classification for burn-only wounds. |
| Normal versus hardcore burn/sepsis/ocular recovery | Normal effects resolve; permanent hardcore causes retain evacuation status until definitive reset. |
| Antibiotic from current medication records | Infection sees actual administered medicine and consumes the real treatment item. |
| Left/right shield, eyewash, HMD changes | Correct eye and overlay, preserved equipment, owner-side treatment and clean effects on death/control change. |
| Two shield attempts, cancel/retry, delayed packets and kit change | One shield per accepted placement; rejected reservations settle once and cannot apply after cancellation. |
| Owner transfer, reconnect and clinical restore | Disease state remains coherent, active workers resume once, and local timing is rebased. |
| Two medics edit one card; change selected patient; flip pages | Patient remains captured, one final submission, explicit revision conflict, no cross-patient overwrite. |
| Full heal and respawn | Disease resets through native owners; card documents follow the documented lifecycle. |
| B290 installation upgraded to B291 | All 19 PBOs installed; interruption rolls back exact old files and removes only newly introduced artifacts. |

The imported eye-cover model is a source MLOD asset. Arma 3 Tools was unavailable
in the container; native model binarization and in-engine model acceptance need
verification in the Windows build and Arma. Existing asset paths and model
configuration are retained.

## Deployment

Close Arma and local servers, update the candidate branch, then run:

```powershell
Set-Location 'F:\ACM-Extended'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B291.ps1
```

Use the same complete B291 build on the server, all clients and headless clients.
Retain the server profile and existing clinical/inventory persistence adapter.
The candidate remains a draft; automated results do not authorize a public release.
