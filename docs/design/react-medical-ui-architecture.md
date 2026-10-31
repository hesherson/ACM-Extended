# Shared React medical UI: ACME, BATDOK and Tempus Pro

Status: preparation and architecture, 2026-10-31. This records the agreed
future-device constraint; it does not implement a React bridge or ship new
BATDOK/Tempus Pro devices. Runtime remains the B292 candidate.

## Decision

Build one device-independent medical presentation contract and one validated
SQF bridge. ACME menus, the future in-game BATDOK application and the future
Tempus Pro monitor are separate views over that contract. React owns layout
and local presentation. Existing native owners retain physiology, equipment,
treatment execution, multiplayer authority and persistence.

The browser is a subscriber and request origin, never the authoritative
medical record. A frontend device name grants no clinical capabilities.

| View | Primary responsibility | Shared data and services |
| --- | --- | --- |
| ACME medical menus | Assessment and treatment workflow; IV, transfusion and narc-box presentation | Captured patient, permitted observations, inventory presentation, validated native treatment actions |
| Tempus Pro | Device-specific monitor layout, channels, trends, alarms and TC3/card view | Connected monitor source, waveform streams, measured observations, native device capabilities, DD1380 record |
| BATDOK | Authorized multi-patient roster, body map, trends, documentation and handover | Per-patient observations, explicit monitor associations, treatment events, DD1380 record |

## Existing implementation boundaries to reuse

- Monitor channel availability and display readings are currently selected in
  [displayAEDMonitor](../../addons/circulation/functions/fnc_displayAEDMonitor.sqf).
  Preserve its distinction between attached pads, pulse oximetry and capnography.
  The new UI must not expose underlying simulation values merely because it
  can read them. Unattached, stale, unavailable and artifact states need explicit
  presentation; a missing value is not a zero reading.
- Waveform generation already exists separately from drawing in
  [the circulation functions](../../addons/circulation/functions).
  Adapt the actual simulation-derived samples and timing, not a decorative
  animation inferred only from displayed BPM. Existing display-height values
  are not calibrated millivolts; preserve their declared units until an explicit
  calibration/conversion exists.
- Native action routing uses explicit operations in
  [ownerDispatch](../../addons/acm_extended/functions/fn_ownerDispatch.sqf).
  That trusted internal dispatcher is not by itself a browser-facing permission
  boundary. Add a narrow bridge admission layer before calling native endpoints.
- DD1380 already has owner-side
  [document requests](../../addons/card/functions/fnc_requestDocument.sqf) and
  [revision-checked saves](../../addons/card/functions/fnc_receiveData.sqf).
  All card presentations use that same document. Tempus TC3 and BATDOK must not
  create competing copies of a casualty's card or bypass edit conflicts.
- Reuse [clinical object references](../../addons/acm_extended/functions/fn_clinicalObjectRef.sqf)
  and the [persistence adapter](../maintenance/B288-persistence-adapter.md).
  A network object ID alone is not durable identity across a restarted mission.

## Contract to implement first

The browser contract has its own version, independent of ACME's multiplayer
protocol and public mod version. These are proposed fields, not existing APIs.

| Record | Required meaning |
| --- | --- |
| Patient reference | Mission incarnation, current object reference, optional mission-bound durable ID, and clinical epoch. A patient association is captured, not read later from the currently selected menu target. |
| View session | Bridge version, fresh session ID, local provider binding, view kind, and current patient/authorized-roster binding. Opening, reloading or changing patient retires the former session. |
| Device association | Source ID, source kind, attached patient reference, binding revision, power/link state and explicit channel/action capabilities. Reattaching a source starts a new binding revision. |
| Observation | Metric, value or null, units, source ID, acquisition time, clock domain and quality/availability. Manual observations retain manual provenance. |
| Treatment event | Native committed event ID, captured patient, provider identity, actual event time, action and permitted details. Request time is not proof of administration. |
| Card document | Captured patient, authoritative DD1380 revision and a frontend draft. A conflicting save requires review against the new revision. |
| State envelope | Contract version, session ID, stream/subscription identity, sequence, observation time and snapshot/delta distinction. Unknown baselines request a fresh snapshot. |
| Action request | Session and request IDs, captured patient/clinical epoch, relevant device/kit binding, expected revision when applicable, fixed operation name and bounded typed arguments. |
| Action result | Matching session/request/patient identity, committed/rejected/pending status, reason and authoritative revision or receipt when available. |

Numeric fields must be finite and constrained; IDs, strings, rosters, deltas,
history windows, samples and pending requests need explicit limits. Reject
unknown schema versions and operation names. Additive capabilities may be
negotiated without assuming every frontend exposes every device function.

Do not conflate a clinical epoch with the whole documentary encounter: full
heal increments the clinical epoch but preserves DD1380 documentation; respawn
starts a new card. Rebind the view after clinical reset without erasing the
surviving native document. Transport/session IDs must never be persisted as
active treatment handles.

## Observations, trends and multi-patient access

The adapter exports only measurements and assessment results that the provider
is allowed to see. It must preserve ACME's intended uncertainty, including
undiscovered injuries and unavailable medication-content information. Do not
serialize the entire patient variable namespace or the debug overlay into React.

Keep patient and device identities separate. A monitor can be detached or moved
between casualties; an old packet cannot populate the newly attached patient's
screen. BATDOK may subscribe to multiple authorized patient/device feeds, with
a separate bounded sequence and freshness record for each feed. Roster access
and remote telemetry authorization require an explicit game-side policy; a
frontend list or the current close-range medical menu does not supply one.

Record trends and committed treatment events at the authorized game-side source,
not only while a particular browser is open. On subscription, return bounded
history with provenance and gaps. Never invent observations for disconnected
periods, interpolate a recorded NIBP measurement into continuous invasive
pressure, or replay stale data as a live measurement.

Reuse existing persistence APIs for durable clinical/card state. Persisted trend
history needs its own versioned, bounded adapter and clock rebasing before it
can be enabled; no browser storage or automatic world persistence is implied.

## Waveforms and audio

Use a shared Canvas renderer behind the React components. A trace subscription
captures patient, clinical epoch, source ID, association revision, channel/lead,
stream generation, sample sequence, sample interval, units and acquisition
clock. A gap is represented as a gap; renderer interpolation must not manufacture
missing clinical events.

Tempus Pro uses a left-to-right sweeper over a stationary trace, matching the
intended ACME/LifePak drawing method. Sweep duration and display scaling belong
to the device view. Sample acquisition, clinical waveform generation and channel
availability belong to the source. Separate waveform sample timing from browser
frame timing; do not rerender the React component tree for every sample.

A new patient, lead, device binding, stream generation or clock incarnation
invalidates old trace buffers. Reopening obtains a fresh bounded history and
time anchor. Late/out-of-order batches must not rewind the active sweep or
splice the old casualty's trace into a new one.

Keep a single selected audio authority for monitor tones and alarms. Reuse the
existing native audio path until a replacement is explicitly implemented and
validated. Opening a second view, mirroring a monitor into BATDOK or redrawing
a QRS must not emit another beat or shock sound. React rendering is not a new
physiology clock or an independent rhythm/beep generator.

## Commands, recovery and browser lifecycle

The SQF bridge resolves the caller from the registered view; it does not trust
a provider identity supplied in JSON. Validate current patient, clinical epoch,
provider state, interaction policy, equipment/kit period, device association,
revision and native action conditions before admission. Allowlist operation
names and argument shapes; never compile browser-supplied SQF/function names.
Validate again at the actual native owner boundary where the action requires it.

Use existing native transactions for medicine, bags and equipment. The bridge
must not introduce a second inventory debit or infer success from a clicked
button. A request ID has bounded replay/receipt handling; a timed-out action is
pending/unknown until reconciled, not automatically refundable or safe to repeat.
Returning an acknowledgement must not apply the action again.

Patient switching, ESC, browser reload, control change, unconsciousness, death,
device loss and locality transfer retire view subscriptions and pending UI
bindings. Cancel only the current view's eligible native interaction, using its
captured identity. Retire drawing/subscription workers without stopping ongoing
physiology or another provider's treatment. Reopening requests current state;
no stale browser closure may affect a replacement session.

## Packaging and layout

Use Arma's local CT_WEBBROWSER content and ship the compiled app with the mod.
Plan for its content-security sandbox: inline scripts/styles or supported data
and game-resource loading, no CDN, external fetch dependency, localStorage or
IndexedDB. No additional native DLL/Rust component is required by this design.
Check mission HTML whitelists and supported engine/browser capabilities during
the first in-game proof. Keep the native UI as an available fallback while the
bridge is experimental.

Shared React components cover observation labels/units/quality, lists, trays,
dialogs, body-map markers, trends and cards. Device shells retain their own
front-panel layout, colors, physical-control semantics and supported functions.
Tempus branding/layout is not permission to display unsupported channels or
enable a defibrillation function absent from the actual simulated device.

Preserve the BATDOK phone-landscape requirement: the full body diagram fits
without page scrolling; lists and side panels scroll within their assigned
areas. Reuse semantic data and components from browser demos only after adapting
their data loading, asset handling and lifecycle to the local Arma sandbox.

## Delivery order and acceptance

1. Implement the versioned contract, runtime validation and subscription/action
   lifecycle. Prove real patient observations and one bounded validated action
   in an in-game React panel, including native fallback.
2. Migrate the transfusion/narc-box presentation through the same bridge. Preserve
   current native inventory, preparation and treatment transactions.
3. Add the Tempus Pro device shell and shared trace renderer, with real simulated
   channel availability, sweep behavior, existing audio and the DD1380-backed TC3 view.
4. Add BATDOK's authorized multi-patient roster, source associations, body map,
   history, shared card and handover presentation. Establish the remote-observation
   permission policy before enabling roster subscriptions.
5. Consider external TAK/export or physical-device adapters separately. A future
   adapter consumes the same versioned records and requires its own transport,
   permissions and protocol implementation; this plan promises no vendor/Bluetooth
   interoperability or external service integration.

Before replacing native panels, exercise schema errors, duplicate and reordered
messages, stale patients/epochs, source reattachment, two providers, browser reload,
ESC, death, owner migration, disconnect/reconnect, low FPS, save/restart, long
sessions and UI scaling in Arma. Measure bridge traffic, frame time, memory and
browser startup cost; React itself is not a performance guarantee. Hidden panels
must stop drawing and unsubscribe. History and waveform buffers must stay bounded.

## Engine references

- [Arma 3 update 2.20: CT_WEBBROWSER introduced on Main Branch](https://dev.arma3.com/post/spotrep-00118)
- [CT_WEBBROWSER local-content sandbox and JavaScript API](https://community.bistudio.com/wiki/CT_WEBBROWSER)
- [ctrlWebBrowserAction](https://community.bistudio.com/wiki/ctrlWebBrowserAction)

This preparation does not change game files, the 19-addon installation, public
version 1.2.4.1, B292 build identity or multiplayer protocol 2. Device simulation,
browser bridge, React implementation and native acceptance remain future work.
