# ACME medical UI

B294 replaces the fluid-card viewport **inside the existing transfusion menu**.
The B293 overview and access handoff were removed after user feedback. React
renders the native two-card window; the body map, access selection, inventory,
action buttons and navigation continue in the existing native menu.

See [B294 scope, deployment and acceptance](../../docs/audits/B294-react-in-place.md)
and the [BATDOK/Tempus Pro architecture](../../docs/design/react-medical-ui-architecture.md).

`bridge.mjs` retains a device-independent session/store boundary. This view has
no measured-data or waveform adapter yet. Native SQF keeps clinical authority,
physical inventory custody, route identity and selection. Row tokens are opaque
references to native card identities, never row numbers supplied by the client.

React/ReactDOM 18.3.1 and esbuild 0.25.12 are pinned. The generated HTML is bundled
locally with JS, CSS and the Roboto Condensed variable font (Google Fonts OFL).
Native PAA artwork is requested through the local Arma texture API. No CDN,
website, Node installation or internet connection is needed in game.

Run `npm ci --ignore-scripts --no-audit --no-fund`, then `npm run build`,
`npm run check` and `npm test` in this directory. Commit both generated assets
under `addons/acm_extended/ui/react` and `bundle-manifest.json`. Font license and
React-family license texts ship beside the HTML. The WOFF2 font retains the full
upstream glyph coverage; it was losslessly converted from the Google Fonts
RobotoCondensed[wght].ttf using fontTools and Brotli.
