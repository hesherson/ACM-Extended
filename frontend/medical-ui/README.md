# ACME medical UI

The first implementation is a local React transfusion overview with validated
native-access handoff. It is opt-in and bundled into ACME; it is not a website
or a replacement physiology/inventory engine.

See [B293 usage, build and acceptance](../../docs/audits/B293-react-medical-ui.md)
and [the shared BATDOK/Tempus Pro architecture](../../docs/design/react-medical-ui-architecture.md).

`bridge.mjs` is the device-independent session/store boundary. `App.jsx` is the
first device-independent fluid presentation. The server bridge serializes only
the permitted presentation projection; observations/sources are empty until
an actual measured-data adapter is implemented.

The generated HTML and license file are committed under
`addons/acm_extended/ui/react`. Arma installations consume those files directly.
Only frontend development/CI needs Node.js and npm. Rebuild with `npm run build`
after editing source; `npm run check` reproduces the committed assets.
