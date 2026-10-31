# B278 — Transfusion input and presentation acceptance

Candidate **1.2.4.1 / B278**, protocol **1**, based on B277 `18d16a5732b8d878d6e6c2f9dfdc3381e6235050`.

## Native acceptance

1. With no IV/IO established, select an unopened blood unit and prepare a Y set. Repeat while an existing patient access already has Y tubing and while a different unit of the same item class has been spiked. Only required supplies and active preparation should restrict staging; patient attachment still requires valid access.
2. Open Prepared IV Sets, close transfusion, reopen, and switch repeatedly between Loose Bags and Prepared IV Sets. Prepare multiple generic/Y sets and confirm immediate selection of their prepared view, exact supplies, stable row selection and no disappearing bags.
3. From Transfusion, use both page-navigation buttons to enter Body Map and Narc Box. Return through both routes, preserving patient/body part and avoiding stale infusion-preparation state. Separately finish/cancel infusion preparation at distinct IV/IO sites and check its existing exact-site return behavior. Repeat while another menu is opened before a queued transition; obsolete callbacks must not close or replace the newer display.
4. Run calcium chloride and calcium gluconate separately and together with another compatible medication. Verify full single-medication titles, distinct CaCl/CaGlu mixture labels and occupied-site tags, dose details and tooltips. Prepared and attached presentations must describe the same medication without changing carrier type, doses, reserve or custody.
5. Use small/normal/large interface sizes at 4:3, 16:9, 21:9 and 32:9. Check circular matching corner radii, complete labels, modest vial icons, aligned card/art/text while scrolling, a separate unobscured scrollbar, and left-side inline infusion details. Test mouse-wheel and keyboard selection to the first/last row and after filtering/reordering supplies.
6. Exercise existing Y priming/flushing, connected bag selection, piggyback flow, warmer add/remove, pending bag move cancellation and the unchanged roller-clamp wheel/drag/drop selector. Repeat on a dedicated server with two clients and patient locality transfer.
7. Complete piggyback preparation using ordinary saline carriers with one/multiple medications. Confirm controls remain visible immediately and after repeated closes/reopens. Repeat when native anchors are delayed during opening; opacity recovery must preserve hidden/disabled states and never duplicate medication or bag custody.
8. Apply Chest Seal and press H before preparation finishes, including holding/releasing H near readiness. Confirm the replacement medical menu stays usable and a fresh chest-seal attempt remains open. Repeat with delayed owner responses, two providers, provider/patient locality transfer, disconnect and late callbacks from the canceled attempt.

## Automated evidence

- The five integrated B278 regression suites passed **87 cases**, including immutable B277 negative controls for the Y-tubing gate, post-piggyback refresh abortion, delayed first reveal and chest medical-menu cancellation.
- All **157 phase scripts** passed. Structural scanning passed **1,904 SQF files and 14 config.cpp files**.
- Strict HEMTT checking passed **16 addon configs, 1,904 SQF files and 12 stringtables**. The strict native-owner audit found **zero violations**; build identity and whitespace checks passed.
- The complete current selection and full sharded CI/release results are recorded on draft PR #31 for the final published commit. Source/VM tests and offline geometry checks cannot verify native Arma rendering, physical input or multiplayer transport.

Detailed reproduction records: [piggyback blank-menu recovery](B278-piggyback-blank-menu.md) and [chest medical-menu cancellation](B278-chest-medical-menu-cancellation.md).

## Deployment

Use the existing `F:\ACM-Extended` checkout and `tools/Deploy-ACME-B278.ps1` with Arma closed. The helper retains explicit build identity, preflight, strict HEMTT checking, signed release creation and journalled installed-file verification. Use matching complete B278 packages on every participant.
