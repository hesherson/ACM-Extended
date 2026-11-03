# B308 — patient equipment and shared blood coolers

Public version 1.2.4.1, candidate B308, network protocol 3. Based on B307
`3cc73d55fd35c1ad701b806395f48a468403526a`. Install the complete matching build
on the server, every client and each HC. This candidate is not published to GitHub.

## Patient setup

ACE patient interaction → Medical Equipment offers setup of the carried Tempus
Pro, Tempus LS, ACCUVAC, Ventway and individually named blood coolers.
Directions are anatomical: the patient's right, regardless of the medic's heading.

| Equipment | Default position relative to the patient's pelvis |
| --- | --- |
| Ventway | 0.65 m right, 0.70 m toward the head |
| ACCUVAC | 0.65 m left, 0.70 m toward the head |
| Tempus Pro | 0.80 m right, 0.10 m toward the feet |
| Tempus LS | 1.30 m right, 0.40 m toward the feet |
| Blood cooler | 0.85 m left, 0.85 m toward the feet; additional carriers extend outward |

Setup uses the actual surface beneath each spot, including raised floors; an
unavailable surface cancels placement and refunds the item. A monitor already
placed manually and connected to this patient is reused in place. Picking up and
placing a monitor transfers its state and retires the source connection. LS
therapy authorization and pacing must be started again after movement.

Inventory movement is serialized on the server, with owner-local edits, receipts,
retries and guarded refunds. A second provider cannot fund a second device in an
occupied default slot. Existing Ventway custody remains authoritative; its prop
changes between circuit and oxygen-circuit variants and provides a nearby readout.
The deployed ACCUVAC supplies the existing reusable suction workflow.

## Monitor controls and presentation

- Tempus Pro → Patient Connections: attach/remove ECG leads, SpO2, NIBP cuff,
  capnography line and temperature probe; Measure NIBP requires cuff and power.
  Detached sensors blank their corresponding values and waveforms. SpO2 may
  provide pulse without ECG leads.
- Tempus LS → Patient Connections: attach/remove defibrillator pads and separate
  ECG monitoring leads. Removing pads clears charging/pacing and blocks therapy;
  ECG-only monitoring remains possible. Pair with Tempus Pro excludes devices
  assigned to another patient. These actions model connections; they do not
  introduce a new inventory consumable for each sensor.
- Physical key overlays are transparent in normal, hover and focused states;
  tooltips remain. Close-up cameras explicitly focus on the device. Both carried
  Tempus items now use the medical inventory category.
- The ACCUVAC mesh is rotated upright in all ten LODs, including geometry,
  PhysX, memory and shadow data; point normals rotate with the mesh.

The supplied Pro/LS body textures are 4096×2048 DXT1 atlases with ten mip levels.
Their front panels occupy only part of the atlas, and the small labels are
already blurred/baked in the supplied artwork. Camera focus could add blur and
is corrected here. Texture dimensions alone cannot recover the lost label detail;
the original textures are retained. A sharper, redrawn front-panel atlas and
native UV/material inspection remain necessary for a substantive artwork upgrade.

## Shared coolers and spoilage

The set-down submenu shows the configured carrier name, including 1U/2U/4U,
with a separate numbered entry for each actual carrier. Anybody nearby may use
Open Blood Cooler on a deployed functional cooler to view and move its blood
through the same bay manager used for carried coolers.

Opening uses the matching 1U/2U/4U open model; closing returns to the matching
closed model. One canonical cargo container and ledger remain in place while
the local presentation changes. Multiple viewers keep the cooler open until the
last viewer closes, leaves, dies or times out. Door transitions reuse the blood
fridge open/close sounds. Packing is blocked while viewers are active.

Expired blood becomes an inert spoiled item of the original volume. Spoiled bags
stay in carried cooler slots or deployed cooler cargo. Loose bags are replaced
in their existing uniform/vest/backpack container, including full containers;
spoilage never ejects them onto the ground. Spoiled contents still occupy capacity
and cannot be drawn for transfusion. Manual removal/discard remains possible.

## Persistent campaign blood timing

In CBA settings → ACM Extended: Persistence → Blood storage, enable
**Persistent campaign: real-time blood storage**, then restart the mission.

| Carrier | Default coolant duration | Administrator range |
| --- | --- | --- |
| 1U | 48 hours | 1–120 hours |
| 2U | 24 hours | 1–120 hours |
| 4U | 72 hours | 1–120 hours |

Outside effective cooling, accumulated warm exposure is limited to four real
hours. After coolant depletion, cooler contents accrue exposure at real time.
Refrigeration pauses exposure; it does not reset prior exposure. With this preset
off, existing compressed mission timings remain: 30 minutes loose and 0.2×
post-coolant exposure inside a cooler. The separate spoilage enable/disable
setting still applies.

These are configurable carrier profiles, not an ambient-temperature or ice-pack
thermal simulation. Manufacturer validation depends on carrier model, packing,
conditioning and environment. The model here is refrigerated whole blood, which
has no frozen-product thaw stage. This change does not add frozen plasma, a new
per-bag collection-date/21–35-day shelf-life ledger, or a new expiry mechanism for
already-spiked active infusion bags.

The setting controls blood durations. Existing injury/cooler/blood persistence
adapters still require the unit's persistence backend; it does not install an
autosave service. Follow `docs/maintenance/B288-persistence-adapter.md`, including
offline elapsed time, and checkpoint only after equipment transfers settle.

Timing references: [Peli BioThermal carrier range](https://pelibiothermal.com/sites/default/files/2023-06/Golden%20Hour%20Range%20Product%20Sheet_0.pdf),
[JTS whole-blood guidance](https://jts.health.mil/assets/docs/cpgs/Whole_Blood_Transfusion_15_May_2018_ID21.pdf),
[Canadian Blood Services administration guidance](https://professionaleducation.blood.ca/en/transfusion/clinical-guide/blood-administration).

## Native acceptance still required

The downloadable build is an integration candidate. This environment cannot run
Arma, Windows PowerShell or native Addon Builder. The candidate retains editable
MLOD models; the source installer performs the normal Windows HEMTT release.

Verify on a dedicated server: all headings and casualty poses; slopes/raised
floors/vehicle floors; surface edge cancellation; manual monitor placement;
multiple providers; pickup during power/therapy; patient/locality changes; JIP;
multiple cooler viewers; full inventory spoilage; pack/unpack; cross-session
restore including offline aging; panel camera/key alignment; upright ACCUVAC
collision and physics. Source/VM checks do not establish these engine behaviors.

The worn HPMK visual and physical Pro/LS docking remain outside this change.
The existing protected HPMK clinical workflow stays active. No universal mod
compatibility or complete native multiplayer validation is claimed.
