# ACME React UI design rules

Use Hallmark's Dusk material for ACME-authored React menus. The reference is https://www.usehallmark.com/themes/dusk/ and the method is https://github.com/Nutlope/hallmark/blob/main/skills/hallmark/SKILL.md (v2.0.0 as inspected for B298).

Keep existing screens, native geometry, Roboto Condensed, content, clinical colours and native handlers. Tokenize the surface before touching its composition. Do not replace an established workflow to satisfy a marketing-page layout rule. Device replicas keep their own device-specific references.

All shared colours and fonts live in tokens.css. Application rules are scoped below .acme-medical-surface inside ACME's own document. Slate neutrals carry the surface; periwinkle marks focus/selection. Native clinical and piggyback/warming colours retain their meanings. Do not apply these rules to ACE classes, global Arma base controls, native medical-menu rows, or third-party UI.

Dusk material uses a smoked tint, a lit inner top edge, a restrained shadow, and the existing native radius. Default material is dense enough to preserve label contrast over light and dark backing. Do not reduce opacity just to make glass conspicuous. No glow, pulsing, reveal, parallax or animated layout is added to a working medical menu.

CSS backdrop filtering is an internal-browser capability. The attribute data-acme-backdrop="internal" may be used only when an actual backdrop is rendered inside the same ACME browser surface. The present in-game fluid pane does not set that marker and uses the readable material fallback. A transparent browser canvas is not access to the game framebuffer. Do not add DynamicBlur, camera effects, screenshots, PiP cameras, or global postprocessing to imitate panel blur.

Keep the browser canvas transparent with explicit control colours; do not rely on the browser's automatic dark form/canvas treatment. Unsupported backdrop-filter must leave a usable surface. Keep native same-display fallback, first-paint handoff, geometry caching, bounded snapshots and all session/identity checks.

For a restyle, record the source and preserved contracts, review the actual compiled UI, run Hallmark's app-scope lint/render checks, check contrast over multiple backings, exercise repeated snapshots/focus/input, and compare native changes against the baseline. Record limitations and every intentional exception. Browser fixtures and compositor models are not Arma acceptance.
