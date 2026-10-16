# 1.2.4.1 / B273 — Transfusion menu update

- Refreshed the transfusion menu with consistent panels, stable Fluids/Infusions sections and nested bag actions. Kept the shared body map and exact access selection.
- Linked the two independently selectable Y-line bag rows with a neutral bracket and added read-only Line Details.
- Added Spike Bottle for unopened 50 mL propofol bottles. Each bottle requires one IV line, appears in Prepared Infusions and uses the existing Give Infusion and roller clamp flow. Hanging does not consume a second line.
- Propofol now uses its own emulsion carrier without saline resuscitation credit. New saline admixtures are blocked; syringe boluses remain available.
- Kept roller-clamp artwork, controls, calculations and handlers unchanged. Fixed nested Move/Remove selection and retained bag identity after list filtering.

Version remains 1.2.4.1 and network protocol remains 1. This draft candidate still requires native Arma and multiplayer acceptance. See [the acceptance record](../audits/B273-transfusion-menu-acceptance.md).
