# B289 IV apparatus and fluid attachment

Candidate **1.2.4.1 / B289**, protocol **2**, based on B288 commit `145542a9aa39c0504c34eff486d47011843d6a8b`. Medmash remains on dev. This change does not imply native Arma acceptance or release approval.

## Requested behavior

- A connected ordinary fluid line accepts a different ordinary secondary fluid, including blood and fresh blood. A closed clamp or a dead patient does not prevent mechanical connection; attaching a secondary preserves the existing flow settings. When flow is available, the secondary runs first and then releases the primary. Existing medication-infusion, Y-set, collection-kit and bottle workflows retain their specific handling.
- An established IV with installed administration tubing and no connected bag has a selectable **IV line · No bag attached** entry. Choose a fluid and **Attach Bag** to connect it without paying for another IV line.
- IV tubing, Tegaderm, extensions and saline locks each require a real inventory item. All four use mass `0.1`. New items are `ACME_Tegaderm`, `ACME_IVExtension` and `ACME_SalineLock`; tubing remains `ACME_IVLine`.
- When a field IV has a secondary catheter through its saline lock, pulling removes the secondary assembly first. The primary catheter, saline lock and its base dressing remain protected until that secondary is out.

## Ownership and inventory behavior

The empty-line entry is a view of installed apparatus, not a zero-volume native fluid bag. Its selection carries the line's installation identity and patient generation. Removing and reinstalling tubing on the same catheter creates a different installation identity. UI callbacks and the patient owner both reject obsolete line selections.

Direct attachment moves the selected physical fluid into certified bag-only custody, then uses the existing prepared-inventory and owner-hang transaction. Only the selected bag is debited; the administration line was already consumed when it was installed. A rejected or interrupted connection retains the fluid without granting another line. Bag-only carriers contain the bag's exact native mass, show **IV line required**, and can only be hung on installed tubing.

Bag-only provenance is retained in native bag field `11` and, after an exact-volume pull, used-bag field `9`. Those fields survive return delivery and medical/equipment serialization. Staging a pulled bag-only product for a piggyback branch consumes one actual IV line; missing stock leaves the product intact. Pulling and reconnecting it to another installed line preserves the original line at its original access. A whole-line Move action cannot relocate apparatus that belongs to that access.

Ordinary used bags that already include their administration set can enter the piggyback workflow without another line debit. Conversion preserves remaining volume, blood type and portable fresh-blood facts, and waits for native inventory custody before dispatching attachment. Delayed conversion never redirects into a different patient, access or primary bag.

Accessory placement uses the existing exact supply receipt and provider-binding protocol. The patient owner validates the item class, catheter, episode and request before accepting the work. A rejected request refunds its original source once; an accepted procedure consumes the opened item once. Removal dependencies are checked again at completion, so a delayed primary-removal request cannot bypass a newly installed secondary catheter.

## Validation and native acceptance

Regression coverage exercises the production list/card/input path, supply take/bind/owner/reply/refund chain, piggyback reserve/attach/ACK chain, installed-line attachment and carrier custody, removal dependencies, line replacement, and return/save metadata. Native inventory, display, networking and persistence primitives remain explicit simulation boundaries.

Native acceptance must check:

1. Install each accessory with and without stock; confirm one actual item is consumed per successful installation.
2. Select an empty installed line, attach each ordinary fluid, and repeat with a remote casualty owner, full inventory, delayed acknowledgements and changed selections.
3. Piggyback unlike fluids and blood products, including partial used stock, and confirm secondary-first flow without duplicated bags.
4. Pull and rehang bag-only products; verify no administration line appears in inventory and no unrelated site gains tubing.
5. Assemble a field IV, attempt to pull its primary, then remove its secondary and confirm primary removal becomes available afterward.
6. Save/restart through the mission's existing ACME persistence adapter with installed lines, bag-only products and active return custody.

Use `tools/Deploy-ACME-B289.ps1` and the same complete B289 build on clients, servers and headless clients. The existing B288 persistence-adapter contract still applies.
