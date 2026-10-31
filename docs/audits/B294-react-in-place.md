# B294: convert existing transfusion cards in place

Candidate **1.2.4.1 / B294**, multiplayer protocol **2**, **19 addons**.
Baseline `383c50dd0e466f0cda17e0d82f60e518ceee5f34` (B293).
Local browser protocol **2**, independently versioned from multiplayer.

## User correction and scope

B293 inserted an unnecessary fluid-management overview before the existing
transfusion menu. B294 removes that display and its interception of the native
entry point. There is no new screen, access chooser, Manage access step or
Native controls handoff. Open the usual transfusion action to reach the existing
menu directly.

The optional React surface replaces only the original two-slot **fluid-card
viewport**. Its position and dimensions come from the existing native list
layout. It reuses the original card names, details, status, temperatures, PAA
artwork, volume fraction, graduation marks, selection and scroll window. Native
scroll rails remain in their gutter. Text uses bundled Roboto Condensed.

Body map, access/route selection, inventory, prepared sets, infusion cards,
clamps, action buttons, pages, close and narc-box screens retain their existing
native positions and behavior. These have **not** yet been converted to React.
Further migration should replace existing surfaces in place, preserving each
workflow. The shared patient/session boundary remains suitable for future
BATDOK/Tempus Pro adapters; no device simulation, measured-data feed or waveform
is claimed in this batch. See the [architecture](../design/react-medical-ui-architecture.md).

## Lifecycle and authority

- The browser is created inside native display 86000, not a separate dialog.
  It uses the native refresh worker; no additional SQF polling worker is added.
- Native cards remain available during browser loading. A six-second startup
  timeout, invalid captured context or setting disable hides/disables the browser
  and restores native cards **inside the same display**. Failure does not reopen,
  close, or navigate a menu. The current opening stays native after a failure.
- Reload creates a fresh session, request sequence and row map. Commands are
  bounded JSON with only ready, select, wheel and key operations. Version-1
  overview commands are rejected. Selection uses opaque tokens mapped privately
  to native immutable identities, not browser-supplied row numbers or bag UIDs.
- A changed route or visible card identity revises row tokens. Volume-only
  changes preserve the binding. Native selection independently resolves current
  list identity, actual bag custody and line epoch before changing selection.
- Captured provider/patient, clinical epoch, both kit epochs, provider-locality
  period, patient owner, proximity and current native menu target are checked.
  Dead casualties remain accessible. Native action popups/clamp/narc dialogs
  block browser selection.
- There are no new inventory or clinical state writes. The native buttons keep
  their original treatment admission/transaction handlers. No raw patient
  namespace, unmeasured physiology or remaining medication amounts are exposed.
- Unchanged snapshots are suppressed, with a two-second freshness heartbeat.
  Client input stops after 3.5 seconds without an accepted snapshot. Commands are
  acknowledged exactly once; a dropped acknowledgment expires pending input
  after two seconds without automatically retrying any action.
- Rendering uses change-only native UI writes. Hidden native card metadata and
  Y-bracket endpoints continue to update without repeatedly showing/hiding their
  hit targets. The browser stays within the original fluid-card rectangle.

## Enable and deploy

The existing client-only CBA key is preserved and defaults **off**:

**Addon Options > ACM Extended: Systems > Interface > React transfusion cards
(experimental)**

An existing saved enabled value now selects the in-place renderer. With the
option disabled, the original menu and cards are used. Close/reopen the native
menu after changing the option. Arma **2.20+** and the mission's existing local
HTML permissions are required. The mod does not alter mission whitelists.

Close Arma/local servers, preserve local edits, then run:

```powershell
Set-Location 'F:\ACM-Extended'
git fetch origin
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B294.ps1
```

Deploy the same complete B294 build on server, clients and HCs. Retain the
existing server profile/persistence adapter and avoid a duplicate standalone
DD1380. The deployment helper verifies all artifacts and signatures and keeps
its existing journal/recovery behavior.

## Reproducibility and validation

React/ReactDOM 18.3.1 and esbuild 0.25.12 remain pinned. The HTML contains inline
JS, CSS and the full-coverage Roboto Condensed variable WOFF2 font. PAA textures
come from Arma's local texture API. React-family and font license texts ship
beside the HTML. No CDN, HTTP request, browser storage or remote data dependency
was added. Run the build/check/test commands in `frontend/medical-ui/README.md`.

Automated SQF-VM tests exercise context fences, obsolete commands, token
selection, replay rejection, native keyboard/wheel delegation, row rebinding,
empty access, reload, timeout and same-display cleanup. Native input/custody
regressions remain active. Node tests execute the version-2 store, bounded card
schema, acknowledgments, freshness and immutable snapshots. Root gates require
an offline, reproducible bundle and prohibit browser bridge menu navigation or
additional polling workers.

The compiled HTML was exercised in Chromium 143 in opaque-origin sandbox
iframes at 360x227, 272x171 and 210x132 card-viewport sizes. Card selection,
native key commands, local texture requests, font loading and empty-access
presentation passed without document overflow. This is browser QA, not Arma
acceptance. The signed downloadable build uses `hemtt release --no-bin` and
does not perform native model/animation binarization.

Local validation results: **242 targeted pytest cases**, **690 root pytest
cases**, and **30 Node cases** pass. Strict HEMTT check passes **2,138 SQFs /
15 stringtables / 22 rapified configs**; the native-owner audit reports **zero
violations**. Bundle reproduction and build identity checks pass.

Native acceptance remains required for embedded browser sizing/compositing,
focus/ESC/wheel delivery, PAA textures, slow/blocked HTML startup, setting changes,
action popups, patient switching, ownership migration, same-vehicle proximity,
low FPS, multiplayer/HC and save/restart. Verify no extra screen appears and the
menu's existing actions remain in their original positions. This remains an
opt-in draft candidate; do not treat the browser tests as engine certification.
