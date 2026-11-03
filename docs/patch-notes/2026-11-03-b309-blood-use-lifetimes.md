# B309 — blood use clocks and equipment transaction cleanup

Integration candidate, version 1.2.4.1 / B309 / network protocol 4. Baseline:
`5a017cff32c977004e639d026bc24380e5ad5032` (B308). Use the complete matching
build on server, clients and HCs. The source bundle includes B306–B309 over B305.

## Blood use window

B308 added real-time cooler and loose-blood timing. B309 carries the four-hour
use window through spiking, preparation, attachment, pausing, clamping,
disconnecting, moving, pulling, re-hanging, Y-set rebuilding and piggyback
staging. Inline warmers cannot extend this deadline. This applies when
**Persistent campaign: real-time blood storage** and blood spoilage are enabled.

- Prepared stock gets one clock when spiked. Available loose-blood exposure and
  pending exposure seeds contribute conservatively using the oldest matching
  class, because indistinguishable native inventory items have no per-bag ID.
- The exact clock follows a prepared carrier onto the patient. The patient owner
  rechecks expiry immediately before attachment, including delayed requests.
- Expired attached blood remains attached and retains its remaining volume,
  capacity, UID, donor facts, apparatus marker and foreign metadata. The canonical
  fluid integrator blocks drainage, blood credit and warming. The UI shows
  **SPOILED**, and the bag can be removed for disposal.
- Pull/Remove Bag retains clocked blood as an exact-volume Used inventory row.
  It cannot become a new, untimed native blood item. Expired Used/Prepared rows
  remain visible and cannot be attached. No expiry path drops an item onto the
  ground or silently deletes the remaining contents.
- Spoilage latches permanently once processed. Disabling the policy later does
  not revive an already spoiled unit. With the preset off, unspoiled blood keeps
  the previous behavior; this does not impose a new clock on ordinary missions.
- Expiry normalization uses the existing one-second inventory recovery pass.
  There is no additional PFH. Clock metadata changes only on admission, transfer,
  save/restore or the transition to spoiled, rather than on every elapsed second.

Native bag extensions are appended after existing fields, preserving foreign
tails. Manufacturer capacity, donor evidence and `bagOnly` provenance remain
separate from the clock. Older seven-field bags and older persistence snapshots
remain accepted. Their unknown historical use age cannot be reconstructed; a
legacy unclocked bag starts when next processed under the preset.

## Persistence adapter details

Snapshots save exposure ages, not a previous mission's raw time. Restore rebases
the live clock to the current mission. Existing same-kit receipts still prevent
repeated equipment imports from refilling or renewing already restored stock.
Keep each restore request and its offline elapsed time immutable across retries.

Existing calls continue to pause aging during server downtime. A mission backend
may explicitly supply validated offline seconds through these optional arguments:

| Data | Restore call |
| --- | --- |
| Attached patient blood, with native medical JSON | `[_patient,_medicalJson,_offlineSeconds] call ace_medical_fnc_deserializeState` |
| Used blood in equipment metadata | `[_holder,_equipmentSnapshot,_offlineSeconds] call ACME_fnc_equipmentRestore` |
| Prepared inventory carriers | `[_holder,_inventorySnapshot,_rebindMap,_offlineSeconds] call ACME_fnc_inventoryRestore` |
| Raw attached-bag map normalization | `[_savedBags,"restore",_offlineSeconds] call ACME_fnc_clinicalFreshBlood` |

The optional native-medical argument ages blood use clocks only. It does not
fast-forward every injury, drug or disease process. The default CBA extended
checkpoint path retains its existing paused-offline policy. No new autosave or
cross-session backend is installed. Continue using the B288 coordinated adapters
for native loadouts, coolers, donor records and injury state.

Whole blood in this model is refrigerated. No frozen product/thawing system or
new collection-date shelf-life ledger is introduced. Cooler defaults remain
48/24/72 real hours, independently configurable in the B308 preset. A four-hour
administration ceiling is consistent with [Canadian Blood Services guidance](https://profedu.blood.ca/en/transfusion/clinical-guide/blood-administration).
These are simulation rules, not a substitute for a service's transfusion protocol.

## Equipment transaction fixes

- Setup rechecks the provider's life/consciousness, vehicle state and placement
  distance after the inventory debit. Automatic placement also rechecks whether
  the patient entered a vehicle. An invalid completion refunds the item.
- A deleted provider no longer strands the patient reservation. An unfinished
  pickup releases the original device's busy flag; therapy remains disarmed.

B308 patient spots, shared cooler models/sounds, ACCUVAC orientation, transparent
monitor buttons and medical categorization are retained. Front-panel source art
is unchanged; its baked label blur still needs replacement artwork. Physical
Pro/LS docking and worn HPMK presentation remain separate work.

## Acceptance

Read the included validation report. Source, SQF-VM and artifact checks do not
execute Arma networking, engine controls, rendering, native animations or Windows
PowerShell. Check blood expiry while paused/held, full inventory retention,
prepared/Used/Y/piggyback round trips, restore with offline aging, locality/JIP,
and provider deletion/death during equipment transactions on a dedicated server.
