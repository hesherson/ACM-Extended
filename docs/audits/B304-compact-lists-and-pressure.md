# B304 — Compact transfusion queues and pressure pumping

Build 1.2.4.1 / B304, multiplayer protocol 2, based on B303 `97950dbb803c5b03103dc195f8e0181320168fa1`. This changes ACME's existing transfusion presentation and pressure-cuff behavior. It adds no screen and changes no ACE medical-menu theme. B303 registered medical-litter collection is retained byte for byte.

## Compact queues

Fluids, Prepared IV sets and Prepared Infusions show five entries per viewport, with scrolling beyond five. Fluids and Prepared IV sets use the available space above the existing lower action row; Prepared Infusions keeps its existing viewport. Normal Inventory and active Infusions retain their two-row layouts. The existing buttons, patient image, separators, footer log, inventory source switch, dosing and custody logic stay in place.

The three queues use compact two-line captions and proportionate visible icons. Full name, quantity, status and warmer information remain in the existing hover tooltip. Native cards allocate a bounded 19-card pool once per display; unchanged refreshes do not rebuild or resize it. Each slot retains an exact native row/UID binding. Existing Y/piggyback connectors follow the new row endpoints.

The optional React fluids layer receives the same five-slot geometry and selection bindings. Page keys move by five entries, native fallback restores all five slots, and the bridge accepts only the supported two/five-slot capacities. Six-field legacy two-slot presentation packets remain supported. Existing React settings remain OFF by default; there is no new opt-in or screen.

## Pressure cuff

Both bag and infusion pressure action menus stay open after pumping. Other actions retain their previous dismissal behavior. Each unique owner-validated click adds 25 percentage points, capped at 100%; duplicate network delivery still cannot pump twice. Existing access, provider, epoch, request-age, item and physical UID checks remain intact.

Elapsed time never reduces pressure. The cuff records pressure and actual remaining bag volume at the last pump. Current pressure is the recorded pressure multiplied by current remaining volume divided by that recorded volume, bounded between zero and recorded pressure. A cuff at 80% with 1,000 mL remaining reads 72% after 100 mL actually leaves that bag. A paused or held bag keeps its pressure. Re-pumping adds to the current derived level and anchors it to the current volume. This is a volume-proportional game model, not a calibrated pneumatic simulation.

Flow, blood's existing temperature/pressure envelope, the pressure bar and line details all read the same physical volume anchor. Fluid that actually leaves the bag consumes pressure; a requested rate, elapsed time or another bag's delivery does not. No additional timer, flow writer or per-tick network broadcast is introduced. Blood caps, perfusion gates, gravity-only piggyback behavior and the existing single volume writer are retained.

Legacy two/three-field cuffs migrate once on the patient owner without retrospective pressure loss. Four-field anchors survive snapshot encoding and clock rebasing. Snapshot validation rejects nonnumeric, zero or negative anchors. Removed/empty bags retain the existing cuff cleanup.

## Verification

Production-code SQF-VM cases cover five-slot layout and scroll identity, unchanged-refresh stability, actual-volume pressure, low-pressure continuity, repeated pumping/replay protection, legacy migration, idle publication suppression and snapshot validation/roundtrips. Existing UI, piggyback, preparation, blood-envelope and persistence regressions are rerun. Node tests and Chromium verify the React handoff, stable focus/artwork/fonts and five-row geometry at four viewport sizes. Strict HEMTT and native-owner-write audit are required.

Local results: 690 root checks, 306 existing pressure/access/blood/piggyback regressions, 206 UI/persistence regressions, 380 additional UI regressions and 56 B304 cases pass. The Node suite has 52 passing cases. Chromium passes all four viewport scenarios. Strict HEMTT compiles 2,150 SQFs and checks 15 stringtables and 22 configs; the native-owner audit reports zero violations. No acceptance claim is made for native Arma.

Native Arma rendering, hover hit targets, pressure-menu input and multiplayer locality transfer still require in-game acceptance. The container release omits Arma Tools model/animation binarization; the Windows deployment helper performs a native release. Deploy the complete matching addon/key set to server, clients and headless clients together, with Arma closed.
