# B274 — Transfusion menu corrections

Candidate **1.2.4.1 / B274**, protocol **1**, based on B273 `c3b1759981384d80cf609b816230b42b5244e73b`.

## Requested behavior

The body map, exact IV/IO/EJ selection and two independently selectable Y-line bag rows remain. The window returns to black and grey styling. The patient name is centered at the top, and Stop Transfusion returns to its previous position. The additional ACME TRANSFUSION and Line flow and service headings are removed.

Prime/Flush sits beside Bag Actions. The selected line details remain visible in the main window without an extra nested action. Prepare Infusion returns beside Hang Set. Give Infusion is the only button beneath Prepared Infusions.

Successfully spiking an ordinary bag or Y tubing selects Prepared IV Sets. These provider-held sets remain prepared and do not appear in active Fluids before Hang Set attaches them to the patient. The saline selection before Y-line preparation temporarily filters the raw inventory list to eligible saline; other fluids, cooler blood and used blood are hidden during that selection and return when it ends. The active Fluids list continues to show the patient's actual attached bags. List rows retain their underlying inventory and physical bag identities after filtering. Directly spiked propofol continues to appear in Prepared Infusions.

The additional side text in the roller-clamp window is removed. Its existing bottom statistics, wheel, drag area, toggle, drop-set selector, rate calculations and owner-ACK opening flow remain.

Direct propofol bottle preparation retains the B273 one-bottle/one-line consumption and paired prepared records. The dedicated emulsion carrier, owner validation and no second line on Give Infusion remain unchanged.

## Native acceptance

Use matching complete B274 packages on the server, clients and HCs. Automated source checks, SQF-VM fixtures and signed Linux packaging cannot verify native Arma rendering, input or dedicated-server locality.

1. Open the menu at 4:3, 16:9, 21:9 and 32:9. Confirm the centered patient title, restored Stop location, black/grey panels, inline line details and no extra headings. Verify body overlays and all eligible IV/IO/EJ hotspots still align.
2. Open and close Bag Actions; use Prime and Flush at each eligible access. Confirm no overlap, correct physical bag targeting and live details while line service changes.
3. Spike ordinary bags and Y tubing from self, patient and vehicle inventory. Confirm the Prepared IV Sets view becomes selected, the set appears once, and no active Fluids row appears until Hang Set succeeds. Repeat with canceled progress, missing stock and owner rejection.
4. Begin the saline selection before Y-line preparation while other fluids, cooler blood, used blood and propofol are in the source inventory. Confirm only eligible saline is selectable, each remaining row resolves to the correct physical item, and all other items return when the selection closes or finishes. The active Fluids list must still show the patient's actual attached bags. Change inventory source and reopen the menu during selection.
5. Confirm Prepare Infusion is beside Hang Set and Give Infusion is the only button below Prepared Infusions. Spike and give propofol; verify one bottle and one IV line consumed during preparation, no second line on attachment and no duplicate prepared set.
6. Open the roller clamp after accepted attachment. Confirm the side text is absent and bottom statistics still update. Use wheel, drag, toggle and drop-set controls; verify displayed rate and medication/volume delivery match. Repeat pause/resume, depletion and access removal.
7. Repeat selection, preparation and attachment with two providers, delayed ACKs, patient locality transfer and a headless client. Verify rejected operations preserve prepared custody and accepted operations settle once.

This candidate remains on the existing draft branch. Native acceptance, main merge and public release are separate from automated verification.
