# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

Impeccable uses the web platform for the embedded React interface. ACME itself runs inside Arma 3 and uses native Arma dialogs and HUD controls alongside content rendered through `CT_WEBBROWSER`.

## Users

Players providing medical care in Arma 3 use ACME to assess casualties, choose and perform interventions, manage supplies and equipment, monitor changes, and prepare patients for evacuation.

## Product Purpose

ACME extends ACM and ACE medical workflows with additional treatment, monitoring, and evacuation tools. The interface helps providers find the right action for the current patient and confirm the effect of their treatment.

## Operating Context

- Give field treatment and prolonged care equal priority. Field treatment needs immediate access to patient status and urgent actions. Prolonged care needs room for monitoring and treatment detail. Give each workflow a layout that fits its job and apply the same grid to both.
- The redesign covers ACME-owned in-game UI, including native dialogs, HUD controls, embedded React panels, and device interfaces.

## Capabilities and Constraints

- Use an **8 px base layout grid** for spacing and control alignment across ACME-owned UI. Apply it directly in the embedded interface and use an equivalent scaled grid for native Arma layouts so spacing follows the player's interface size. Use the same spacing steps in both renderers when they share a screen.
- Preserve the native SQF authority for treatment actions, patient and access selection, and inventory custody. Where a React view replaces a native presentation, maintain the native fallback and keep both renderers aligned.
- Check migrated screens at 4:3, 16:9, 21:9, and 32:9 and at small, normal, and large interface sizes, following existing transfusion acceptance coverage. Keep controls reachable by their supported input methods and labels readable at narrow sizes.
- Screen inventory, migration order, and per-screen layout details remain open.

## Evidence on Hand

- [Existing transfusion UI rules](frontend/medical-ui/design.md) and [renderer integration](frontend/medical-ui/README.md) document the existing hybrid screen and its clinical and input boundaries.
- [Shared medical UI architecture](docs/design/react-medical-ui-architecture.md) records the embedded-browser contract and distinguishes implemented features from planned device work.
- [Native transfusion input acceptance](docs/audits/B278-transfusion-input-acceptance.md) provides existing test cases for screen ratios, interface sizes, keyboard and mouse input, and long labels.
