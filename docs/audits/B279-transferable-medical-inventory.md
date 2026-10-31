# B279: transfusion controls and transferable medical inventory

Version: **1.2.4.1 / B279**, network protocol **1**. Baseline: `e9eb2661647a30d7cff4c7ac3d942144c8525a5a` (B278).

## Resulting behavior

- Stop Transfusion materializes the native default-open flow state when a valid IV/IO lacks its saved flow row, then toggles the selected access on the patient owner.
- Y tubing retains its original blood selection, flush-saline selection, and final assembly steps. Stage changes refresh immediately; card selection resolves the current native inventory row by identity.
- Fluid cards use a common centered width, aligned captions and status, a right-aligned LifeWarmer readout, and bag graduation marks. A 250 mL bag has 50 mL intervals. Newly created bags retain their nominal capacity even after medication solution is added.
- Infusion cards, line details, the injection tally, and completion confirmation show the medication amount added. Internal remaining-dose and delivery calculations retain their existing semantics.
- Inventory and Prepared IV Sets have visible grey tabs. Prepared-set cards identify the fitted administration line; the native body map has a charcoal gradient backdrop.
- Prepared IV sets and filled medication or medicated-flush syringes have physical inventory carriers. Native Gear transfers move their identity between people, containers, and ground holders. The recipient's existing transfusion and Narc Box workflows project the exact associated contents.

## Custody and receipts

The carrier's magazine ammo is an opaque, non-recycled identity. Medication volume remains in the associated record; native ACM syringe magazines retain their existing hundredth-mL representation until they are converted into a carrier.

The server serializes identity allocation and claims. After a native transfer, the receiver adopts canonical custody before contents become editable or usable; a stale transfer snapshot cannot replace a donor's newer contents. A provider removes the exact native carrier before starting a patient transaction, and terminal receipts consume or return that same identity. Prepared-set payloads carry both the set and its linked infusion record, including blood identity, temperature, component doses, and exact staged volumes.

Partial medication pushes reserve the carrier until all patient receipts settle. Rejected aliquots merge back into the same syringe identity. Private plunger updates remain local; final settlement publishes the resulting contents. Death does not erase tangible medical supplies from the corpse.

Retries are idempotent and use backoff. Allocation, claim, and settlement tolerate network-event/public-state ordering. Unaccepted claims return canonical contents rather than overwriting them with a stale recipient snapshot. Fresh equipment generations reject late refunds into a replacement kit. Full inventories spill the same carrier into a ground holder.

The inventory worker tracks participating owners rather than scanning all mission units. Tokens 1 through 65534 are never reused within a mission; exhaustion retains the funded pending preparation and blocks further allocation instead of recycling identity.

An exhausted allocation emits one failed acknowledgement and one server diagnostic per mission. Replayed failures do not republish blocked state. An unchanged same-kit metadata commit keeps that blocked preparation intact; changed contents or a fresh kit may make one repair attempt.

Carrier metadata is mission-scoped. Campaign/savegame persistence across a mission or server restart is outside this change.

## Automated verification

The B279 regression modules execute production SQF with native inventory, UI, and transport commands represented at their engine boundaries:

- `test_b279_transfusion_ui.py`: owner flow toggle, immutable B278 negative control, card selection and Y stages, graduation geometry, nominal capacity, and added-dose presentation.
- `test_b279_inventory_ledger.py`: allocation, transfer, exact reservation, claim and settlement, reordered delivery, duplicate receipts, stale contents, and kit-generation isolation.
- `test_b279_syringe_inventory.py`: native-magazine conversion, exact solution and tag transfer, partial refunds, receipt-gated finalization, and private/public update boundaries.

Historical cases retain their identities and behavioral assertions; their isolated VM fixtures include the new native-custody boundary where required. Complete-suite results and packaging evidence are recorded in [PR #31](https://github.com/hesherson/ACM-Extended/pull/31).

## Native acceptance

This remains a controlled-test candidate. Native Arma rendering/input, Windows binarization, and dedicated-server/client/headless-client acceptance require execution in the user's environment.

1. Verify each Y step and Stop/Resume from freshly opened and reopened menus, including missing or legacy flow state.
2. Check card centering, equal bar length, readable 50/100/250/500/1000 mL graduations, tabs, and thermal/status alignment at the deployed UI scales.
3. Transfer single-bag, Y, propofol, and medicated prepared sets between two players, through vehicle cargo, and through ground holders. Hang or give them from the receiving player's existing menu and compare their exact contents.
4. Transfer tagged medication and medicated-flush syringes, including diluted/compound and partially used syringes. Verify recipient labels and contents, accepted partial doses, rejected doses, and interruption during measured pushes.
5. Exercise full inventories, provider death, Arsenal/import equipment replacement, and late patient acknowledgements. Verify that no second usable carrier or old-kit refund appears.
6. Run with identical complete B279 packages on the dedicated server, clients, and headless clients, including the actual modpack and mission.

## Windows deployment

Close Arma and local servers, fetch the tested B279 commit, then run:

```powershell
Set-Location F:\ACM-Extended
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B279.ps1
```

The helper checks the clean source and build identity, performs strict HEMTT validation and native release packaging, and deploys through the existing journalled installer. Confirm **1.2.4.1 / B279** in game.
