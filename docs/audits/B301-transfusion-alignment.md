# B301: transfusion alignment, source selection, warming and connector stability

Candidate 1.2.4.1 / B301, multiplayer protocol 2. Baseline B300 `4944aaa6bae41fb06a4576c925805d657d386294`. Existing PR #31 remains draft and unmerged.

## Corrections

The native thermal label used a non-ASCII middle dot that became mojibake in the browser. Its owned separator is now an ASCII slash. The warmer presentation had excluded medication carriers such as propofol; it now displays orange Warming plus the existing native-clock dot cycle for a carrier that is actually flowing. The read-only secondary flow query passes the same gravity-only secondary argument as the physical flow path. A primary held by its secondary, a stopped/clamped/disconnected line, nonperfusing patient, or empty bag cannot claim active warming. The downstream warmer still reports Inline on a held primary. Medical dosing, carrier volume, temperature effects and physical flow functions are unchanged.

Action popovers hid card faces and prevented endpoint geometry from being recomputed. Endpoint computation now depends on the current physical row identity, independently of face visibility. Y and piggyback rails keep live anchors when Bag Actions or Infusion Actions opens. Removed carriers drop their endpoints instead of retaining stale lines. Rails sit outside the column and its outward scrollbar.

The old Target line and switch icon have zero authored size and remain hidden/disabled at layout time. The existing Inventory tab displays Inventory (Self), Inventory (Patient), or the existing vehicle source. Its click calls the original native source switch, preserving inventory enumeration, custody, unavailable-vehicle handling and refresh semantics. Returning from Prepared IV sets restores the current source first; the next press cycles source. The inventory builder below its source-label prefix remains byte-exact to B300.

Both side columns use equal widths and mirrored x anchors. Fluids and Inventory share header, top button, two-row list, footer action and separator y positions. Active/Prepared Infusions share heading, two-row list and bottom action rows. Extra inventory items remain accessible by the existing scrolling and key navigation. All cards are centered in their viewports; native and React fluid rectangles match. The existing line-details panel occupies a single centered footer below the body. Blood Y setup and its alternate Spike Bag action share one footer slot exclusively; the prepared-set Hang/Prepare pair occupies that same row.

The original flat palette, larger square fluid icons, rounded corners, thin IV/IO contours, outward flags and site dots remain. No glass, blur, camera/world effect, new screen or ACE styling is introduced. Original body-map geometry and medical artwork are unchanged. React remains experimental and OFF by default. BATDOK/Tempus Pro interfaces remain separate future device interfaces.

## Validation and acceptance limits

Tests execute production warming presentation across the native dot cycle, held primary state, native source cycling, false-refresh behavior, prepared-tab return, card rendering, Y/piggyback rails under each popover, removed-carrier cleanup, card/browser geometry and four aspect ratios. Scope contracts pin ACE sources, original art, physical attachment handlers and inventory custody. Existing cases retain their identities; current geometry expectations follow the requested layout, while historical B297/B300 scope tests inspect their published B300 snapshot.

The root suite passes 690 cases and the React suite passes 43. Strict HEMTT checks 2,140 SQFs, 15 stringtables and 22 configs; native-owner audit reports zero violations. The compiled offline browser passes at 360x227, 272x171, 210x132 and 522x226. At each size 25 successive snapshots preserve DOM identity, focus, texture elements/cache and font size while orange warming dots advance. Font readiness, empty output, input routing and fallback remain covered. The client bundle is unchanged and reproducible.

Signed package validation checks all 19 addon signatures, B301 stamps, packed changed runtime files, authored compiled geometry and exact source-patch tree reconstruction. Both ZIPs pass integrity checks. The final affected-suite count and package hashes are reported with the delivery.

Arma cannot run in this container. Native font rasterization, draw order/input, actual UI scales, live warmer/flow and dedicated-server behavior still require in-game acceptance. Browser checks are not native screenshots. Container packages omit Arma Tools model/animation binarization; the supplied Windows helper runs native HEMTT release. Fully close Arma before deployment; install the complete matching build/key on server, clients and HCs. Retain the existing persistence profile/adapter and avoid duplicate standalone DD1380.
