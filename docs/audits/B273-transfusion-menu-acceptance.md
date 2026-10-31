# B273 — Transfusion menu and direct propofol bottles

Candidate **1.2.4.1 / B273**, protocol **1**, based on B272 `e171dd8f2204063964a2f4f65e64332560f25824`.

## Menu behavior

The existing body-map artwork, overlay rectangle and exact IV/IO/EJ site hotspots are retained. Fluids and Infusions occupy separate left sections; inventory, its existing source selector and Prepared Infusions occupy the right section. Bag Actions and Infusion Actions expose the existing treatment, move, pull/remove and pressure-cuff handlers in local nested menus. Pause and Prime/Flush remain access-level actions beneath the body map. Line Details opens a read-only view of the selected access, bags, medication remaining, Y reserve/service state, warmer and cuffs.

The shared window remains letterboxed on wide displays. The final layout owns control positions after initial capture, so the legacy controller cannot rewrite them each tick. Empty sections keep their headings and stable positions. Native action dismissal is deferred one frame, preserving hidden-list selection while the existing action runs. Move uses the retained selection index, rather than a filtered visible row; an infusion move does not select an unrelated fluid.

Y hardware still uses two independently selectable rows in Fluids. A thin neutral bracket links only the Blood/Fresh Blood (or its empty slot) and Saline reserve (or its empty slot) belonging to the exact body part, IV/IO mode and site. Visible `lbValue` mappings determine membership. Ambiguous duplicate branches, an intervening unrelated row or a scrolling list suppress the bracket and retain native Y labels. One surviving branch has a short hook. The Fluids heading also identifies the selected Y line.

The roller-clamp dialog, artwork and all 15 clamp-related functions are byte-for-byte unchanged from B272. The existing owner-ACK handoff opens that dialog only after an accepted infusion attachment. There is no new UI refresh worker.

## Propofol preparation and custody

An unopened `ACM_Vial_Propofol` appears in the existing inventory source list. **Spike Bottle** consumes one physical 50 mL bottle and one `ACME_IVLine`, using standard supply receipts. It creates a linked prepared set and Prepared Infusion containing **500 mg propofol at 10 mg/mL**, initially clamped. The internal prepared-set record is hidden from the plain Prepared IV Sets list; the bottle appears once in Prepared Infusions. Partial open-vial ledgers cannot synthesize an unopened bottle.

Self, patient and vehicle sources follow the selected inventory holder captured when spiking begins. Shared patient/vehicle stock uses the existing owner-arbitrated vial lease, revalidates its exact token before debit, and releases only that request. Failure to obtain the line refunds the exact bottle receipt. The existing source policy allows a holder to draw from its own stock without the shared lease; simultaneous self use versus another provider remains a native acceptance case.

**Give Infusion** uses the existing prepared-attach transaction and exact access validation. It consumes neither another bottle nor another IV line. Owner validation requires the matching paired records, marker, carrier, 50 mL volume and 500 mg component. Rejection retains prepared custody; accepted or duplicate ACKs settle the existing records once. A missing medication replica cannot fall back to hanging the bottle as a plain fluid.

The dedicated `ACME_Propofol` carrier drains through the existing medication admission path without saline, plasma or blood resuscitation credit. Pull/removal discards a used bottle instead of recreating unopened stock. New propofol admixtures into saline are blocked in both the menu registry and owner registration. Existing running legacy mixtures retain delivered history, and syringe bolus use remains available.

## Native acceptance still required

Use matching complete B273 packages on server, clients and HCs. Automated source checks, SQF-VM fixtures and signed Linux packaging cannot verify native Arma rendering, input or dedicated-server locality.

1. Open the menu at 4:3, 16:9, 21:9 and 32:9. Select each arm, leg and eligible head access in IV/IO mode, including multiple sites. Verify body overlays align, captions fit, lists scroll, empty states remain stable and nested controls do not overlap.
2. Create a Y line with Blood and Saline. Select each bag separately; pull/refill each branch, prime/flush, transfer another unit and remove the tubing. Verify bracket membership follows the exact site, empty placeholders and branch changes without linking another bag. Test duplicate/overflow fallback and pressure meters inside collapsed/expanded actions.
3. Select an active infusion, switch focus through inventory and body selection, then use Adjust, Move, Remove and cuff controls. Repeat with the fluid list filtered down to one visible row. Verify the selected physical bag is the only target and Place uses the destination access. Open Line Details throughout line service.
4. Spike propofol from self, patient and vehicle inventory. Verify one bottle plus one IV line consumed, one Prepared Infusion shown, no plain-set duplicate and no second line consumed when given. Repeat with no line, missing stock and a changed selector during spiking. Race two providers and syringe drawing against shared stock; include holder self use.
5. Reject attachment on invalid/occupied/Y access, delay/drop request and ACK, close/reopen the menu, repeat Give and transfer patient locality. Verify custody/refund, one physical carrier and one medication entry. Reset/full-heal during the request and verify no stale attachment.
6. Use the unchanged clamp wheel, drag area, toggle and drop-set selector. Compare displayed rate and dose/mL delivery, pause/resume, depletion, access removal, pull and discard. Verify propofol volume does not increase resuscitation saline/blood/plasma, saline admixture is unavailable, and syringe propofol boluses still work.

This candidate remains on the existing draft branch. Native acceptance, main merge and public release are separate from automated verification.
