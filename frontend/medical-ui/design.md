# ACME transfusion UI rules

Use the established flat charcoal palette and existing rounded corners. No simulated glass, reflection, backdrop filter, glow, animation or global world effect. Apply changes only to ACME-owned transfusion controls; ACE and original medical artwork are outside scope.

Keep existing clinical and inventory workflows, handlers, native layout authority and the optional React fluid-card renderer. Native owns all empty captions so font, size, colour and alignment match across sections without a renderer handoff. React renders occupied cards only and preserves font calibration, mounted controls, focus, bounded updates and native fallback.

Both renderers use the same square fluid-icon size, independent of caption line count. Title, details, status and progress track share their existing left edge. Stop and Bag Actions form an equal-width top-row pair; Prime/Flush retains its lower row. Preserve the original device-specific references for future BATDOK/Tempus Pro screens.
