# ACME transfusion UI rules

Use the established flat charcoal palette and existing rounded corners. No simulated glass, reflection, backdrop filter, glow, decorative animation or global world effect. Apply changes only to ACME-owned transfusion controls; ACE and original medical artwork are outside scope.

Keep existing clinical and inventory workflows, handlers, native layout authority and the optional React fluid-card renderer. Native owns all empty captions so font, size, colour and alignment match across sections without a renderer handoff. React renders occupied cards only and preserves font calibration, mounted controls, focus, bounded updates and native fallback.

Both renderers use the same square fluid-icon size, independent of caption line count. Title, details, status and progress track share their existing left edge. Stop and Bag Actions form an equal-width top-row pair; Prime/Flush retains its lower row. Preserve the original device-specific references for future BATDOK/Tempus Pro screens.

The transfusion columns mirror around the unchanged body map: matching heading anchors, two equal top buttons, two-row card viewports, footer actions and gray separators. Both lower infusion panes share the same list and action rows. Keep all items available through the existing wheel/key scrolling and outward scrollbars. Selected-line details occupy one centered footer below both columns. Menus replace their own card faces while live UID endpoints continue to anchor Y/piggyback connectors.

The Inventory tab owns source selection and shows Inventory (Self), Inventory (Patient), or the existing Inventory (Vehicle) where available. Returning from Prepared IV sets shows the current inventory source before another press advances it. The old Target line and switch icon are hidden and inert.

LW Quantum uses an ASCII slash separator. Flowing carriers, including medication carriers, display orange Warming with dots from the existing native clock; held/paused primaries display Inline. The secondary's read-only flow query must match the gravity-only secondary path. React receives these snapshots without a new timer or CSS animation.
