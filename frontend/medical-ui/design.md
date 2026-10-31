# ACME transfusion UI rules

Use the established flat charcoal palette and existing rounded corners. No simulated glass, reflection, backdrop filter, glow or global world effect. Functional motion is confined to flow stripes, nearby graduation numbers and ready-action backgrounds. Apply changes only to ACME-owned transfusion controls; ACE and original medical artwork are outside scope.

Keep existing clinical and inventory workflows, handlers, native layout authority and the optional React fluid-card renderer. Native owns all empty captions so font, size, colour and alignment match across sections without a renderer handoff. React renders occupied cards only and preserves font calibration, mounted controls, focus, bounded updates and native fallback.

Both renderers use the same square fluid-icon size, independent of caption line count. Title, details, status and progress track share their existing left edge. Stop and Bag Actions form an equal-width top-row pair; Prime/Flush retains its lower row. Preserve the original device-specific references for future BATDOK/Tempus Pro screens.

The transfusion columns mirror around the unchanged body map: matching heading anchors, two equal top buttons, two-row card viewports, footer actions and gray separators. Both lower infusion panes share the same list and action rows. Keep all items available through the existing wheel/key scrolling and outward scrollbars. Selected-line details occupy the original compact left footer. Menus replace their own card faces while live UID endpoints continue to anchor Y/piggyback connectors.

The Inventory tab owns source selection and shows Inventory (Self), Inventory (Patient), or the existing Inventory (Vehicle) where available. Returning from Prepared IV sets shows the current inventory source before another press advances it. The old Target line and switch icon are hidden and inert.

LW Quantum uses an ASCII slash separator. Flowing carriers, including medication carriers, display orange Warming with dots from the existing native clock; held/paused primaries display Inline. The secondary's read-only flow query must match the gravity-only secondary path. React receives these snapshots without a new timer or CSS animation.

B302 uses 0.187-safeZoneH list viewports with two 0.090-high cards in every pane, matching the prior infusion-card height. The original square icon cap stays readable. Paired buttons use a 0.004-canvas gap, equal to the details panel's left padding. The Inventory button explains source switching in its native hover tooltip.

Flow is a Boolean physical observation from the native bag presentation, not a caption heuristic or timer-based volume prediction. Only flowing cards animate a seamless white stripe texture clipped to the existing measured fill. Held, stopped, empty, disconnected, nonperfusing and stale bags cannot claim moving flow. Native and React share the texture and 0.8-second motif travel; existing native data refresh remains 4 Hz while cached decoration updates at 20 Hz using the same idempotent UI worker.

Graduation numbers use the same symmetric smoothstep proximity curve in both renderers: up to 35% larger at the actual volume endpoint, returning to normal within 70% of one tick interval. Positions, tick spacing, card geometry and original added-medication labels remain fixed. Ready clinical actions pulse only their rounded background opacity; hidden, disabled and unrelated controls remain still. Start/Pause retains the original single native flow-toggle handler, with Pause IV/IO Transfusion replacing the running-state Stop wording.
