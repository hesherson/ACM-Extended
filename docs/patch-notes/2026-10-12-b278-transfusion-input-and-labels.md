# B278 — Transfusion recovery, input, medication labels and card alignment

Stable version remains **1.2.4.1**; candidate build is **B278**, with network protocol **1**.

- Fresh Y tubing can be prepared independently of patient access. Existing patient Y tubing and historical loose-bag flags do not block an inventory recipe.
- Prepared IV Sets switches immediately and remains usable after closing/reopening the menu. Transfusion/Body Map/Narc Box transitions retain the selected patient and body part, discard stale temporary bag-editor state and retire only the prior menu's presentation session.
- Returning from piggyback preparation no longer aborts the menu refresh on a numeric carrier-volume comparison. Delayed first-layout readiness also recovers faded controls on the existing refresh worker.
- Single-medication infusions use the medication's full name. Mixed infusions use distinct medication shorthands, including **CaCl** for calcium chloride and **CaGlu** for calcium gluconate.
- Rounded card geometry uses physical pixel dimensions, a reserved scrollbar gutter and one card viewport. Native artwork, vial size and card positions remain aligned during scrolling.
- Infusion/line details appear beneath the Infusions section on the left. The standard body/IV/IO artwork and existing roller-clamp controls remain in use.
- Pressing H during chest-seal preparation cancels that pending session. Readiness and deferred display callbacks reject canceled or superseded sessions, allowing a fresh attempt without replacing a newer medical menu.

Native Arma rendering/input and dedicated-server acceptance must be verified with matching B278 packages on server, clients and headless clients.
