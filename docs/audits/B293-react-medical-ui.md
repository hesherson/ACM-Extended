# B293: first local React medical panel

Candidate: **1.2.4.1 / B293**, multiplayer protocol **2**, **19 addons**,
based on `a2a34fa990f0b8382ec61678e039a904ba82feeb`.
Browser presentation protocol: **1**, independent of the multiplayer protocol.

## Implemented scope

The transfusion entry point can now open a real, locally bundled React fluid
overview. It lists established IV/IO routes and connected bags, with visible
volume, native graduation marks, native running status, piggyback role and
LifeWarmer presentation. An empty established route remains selectable.

This is the first migration slice. **Manage access** hands the captured route
to the existing native transfusion workflow. Bag preparation, medication,
clamps, blood products, inventory transactions and treatment execution remain
native. The narc box and the complete transfusion editor have not been converted.
There are no new BATDOK/Tempus Pro device simulations or monitor waveforms in
this build.

The shared client/store and SQF presentation bridge are independent of device
layout. State carries a version, view, session, sequence and captured patient
reference/clinical epoch. Capability, observation and source fields are explicit;
this first slice offers only native-transfusion navigation, with empty
observations/sources rather than invented measurements. Future device views
follow the [shared architecture](../design/react-medical-ui-architecture.md).

## Lifecycle and authority

- Browser messages are bounded JSON data with a fixed operation/argument schema.
  No SQF compilation, remote event interface or provider supplied in JSON exists.
- Each display captures its provider, patient, clinical epoch, both kit epochs,
  provider-locality period and patient owner. Reset, provider change, range loss,
  persistence freeze or owner change invalidates the view.
- Reload creates a fresh session. Duplicates and messages from former sessions
  cannot navigate. Handoff rechecks the captured context/access on the deferred
  callback and cannot close a newer browser or unrelated dialog.
- Native navigation bypasses React explicitly, so it cannot loop back into the
  overview. A rejected access request releases the client pending state and
  waits for a new snapshot; it does not retry a treatment.
- There are no new inventory debits, clinical state writers, waveform workers
  or global idle browser workers. Each open display polls at 0.5 s, suppresses
  unchanged snapshots and emits a 2 s freshness heartbeat. The client marks a
  feed stale after 3.5 s without a snapshot and disables navigation.
- Browser startup failure falls back after 6 s. Native controls and Close
  buttons remain outside Chromium; native ESC handling closes the display.
  Closing retires only that display's worker/context. Dead casualties remain
  accessible through the same provider/proximity rules.
- The projection permits at most 24 established access routes and 128 bag
  cards, with bounded strings and native graduation lists. It exports no raw
  patient variable namespace, hidden physiology or remaining medication amount.

## Enable and deploy

The client-only CBA setting defaults **off**. After deployment, enable:

**Addon Options > ACM Extended: Systems > Interface > React fluid overview
(experimental)**

Open the existing transfusion action as usual. The overview opens first; select
an access and choose **Manage access** to continue with the native controls.
**Native controls** is available even if the HTML content does not initialize.
Disabling the option restores the native opening path on subsequent opens.

Arma **2.20+** is required; the Extended patch now declares that minimum. Local
HTML remains subject to mission `allowedHTMLLoadURIs[]`. The mod does not loosen
mission whitelists or request remote web access. No Node.js, internet, native
browser extension or Rust DLL is needed on player/server installations.

Close Arma and local servers, preserve local edits, then:

```powershell
Set-Location 'F:\ACM-Extended'
git fetch origin
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B293.ps1
```

Use the same complete build on server, clients and HCs. Retain the existing
server profile/persistence adapter and avoid a duplicate standalone DD1380.

## Source/build reproducibility

Frontend source is in `frontend/medical-ui`. React/ReactDOM 18.3.1 and esbuild
0.25.12 are pinned in the lockfile. The committed single-file HTML contains
inline JS/CSS, with no CDN, fetch, browser-storage or external asset dependency.
React, ReactDOM and Scheduler license texts are distributed beside the HTML.

```sh
npm ci --prefix frontend/medical-ui --ignore-scripts --no-audit --no-fund
npm run build --prefix frontend/medical-ui
npm run check --prefix frontend/medical-ui
npm test --prefix frontend/medical-ui
```

The build/check verifies byte-for-byte reproduction and source/asset fingerprints;
CI reproduces the bundle from the pinned packages. Frontend and `.hemtt` changes
now trigger the source/regression workflow too.

HEMTT 1.22's wiki snapshot lacks `ctrlWebBrowserAction`. The repository supplies
only that native command's documented Control/Array signature and Arma 2.20
minimum in `.hemtt/commands/ctrlWebBrowserAction.yml`. It does not create an
engine command or disable SQF linting. Browser callbacks are declared directly
on the browser control; unknown-event checks remain enabled.

## Validation and remaining native acceptance

- **90 targeted pytest cases pass**, including 42 new SQF bridge/lifecycle and
  projection cases, three frontend/packaging gates and existing native
  transfusion input/presentation regression cases.
- The client gate executes **20 Node tests** for identity, sequencing, stale
  data, rejected/duplicate commands, immutable snapshots and bounded payloads.
- **690 root pytest cases pass**. Strict HEMTT check passes **2,138 SQFs / 15
  stringtables / 22 rapified configs**; native-owner audit has zero violations.
- The actual compiled HTML was exercised in Chromium 143 inside an opaque-origin
  sandbox iframe. Desktop 1280x760 and landscape 844x390 rendered; access
  selection, empty IO presentation, captured-route command and rejection passed.
  This is browser QA, not a run inside Arma.
- A signed `hemtt release --no-bin` candidate builds all 19 PBOs. The downloadable
  container build does not perform native model/animation binarization.

Before enabling by default, test the native CT_WEBBROWSER callbacks and JSON API,
mission whitelists, startup fallback, ESC/focus, UI scaling, reopen/patient
switching, same-vehicle/airborne proximity, death, ownership migration, low FPS,
two clients/HCs and save/restart in Arma. Measure actual frame time and bridge
cost. These engine/transport checks remain outstanding; automated checks do not
certify them. The candidate remains draft and unmerged.
