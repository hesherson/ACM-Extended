# Stable 1.2.4.1 B216 treatment and training updates

Base: B215, `d89b6a3347235cdb684b543b6c678b708f8d765b`.
Public version remains **1.2.4.1**; runtime and every package component identify as **B216**.

## Assessment and chest access

Measure Respirations is in Airway / Breathing. With dropdowns enabled, it is in Breathing immediately after Check Breathing whenever both actions are available. The existing watch, breath indicator, real-time measurement interval, animation sequence and activity wording remain unchanged.

AED pad application enters the existing chest-access preflight, including its plate-carrier removal and provider/patient sequence. Only the exact AED pad action is added; inherited monitoring actions do not unnecessarily undress the casualty.

## Chest seals

Ordinary chest-seal minigame burping and removal no longer invoke hemothorax drainage. Air-pressure relief remains. The distinct thoracostomy seal aftercare retains its existing blood drainage and volume reporting; it does not cure the source of bleeding.

Ordinary burping writes `Burped chest seal` to quick view once per active minigame session, across wounds and sides. Closing and reopening creates a new session that can produce one new entry. Session tokens, clinical reset epochs, owner-local receipts and bounded replay checks reject late or duplicate events, including ownership handoff. Separate providers retain independent session identity. Opening a minigame without burping does not log a treatment.

## Provider animations and recovery

All six AAJT application/removal actions now own a repeating empty-handed medic4 work pose through the actual ACE treatment timer. This uses the same medic4 family as Flip, the shared 1.5x rate, existing prone substitution and one weapon-holster preflight. Native weapon/end queues and the generic 2.4-second torso-bandage presentation are suppressed for those exact actions. Completion and cancellation are bound to the treatment episode and pose epoch; a stale callback cannot stop a successor pose or apply/remove a device.

Recovery is compatible with fitted OPA, NPA, SGA, ETT and surgical airway tubes. Active CPR, BVM and ventilation still prevent or retire recovery. Basic OPA/NPA insertion also preserves an already established recovery position. Inserting an i-gel retains its existing supine access sequence, after which recovery can be established again. The existing secretion workers remain authoritative: OPA/NPA alone do not prevent secretions, recovery drains lesser obstruction, and severe existing obstruction still requires treatment.

## Blood refrigerator

The existing refrigerator now uses one persistent object and its native `Door_1_noSound_source`, at 2x hinge speed, with the existing separate open/close sounds once per transition. ACE world-menu detection is corrected. Door presentation works independently of the cold-chain simulation setting.

Taking blood reserves/decrements stock once on the server, delivers the unit through ACE inventory handling, and runs the same provider Putdown/return sequence as head elevation/lowering. A bounded take lease holds the door through that sequence, including after the interaction menu closes. The door closes when the last viewer/taker finishes. Interrupting presentation does not remove a granted unit. Existing animation owners are respected, and stale cleanup cannot cancel a newer provider sequence. Owner-specific request watermarks and recipient receipts cover duplicate requests and ownership cycles.

Native source references: [Bohemia vehicle animation-source listing](https://community.bohemia.net/wiki/Arma_3:_createVehicle/vehicles) and [animateSource syntax and speed](https://community.bohemia.net/wiki/animateSource).

## Existing patient spawner

The existing training computer is modified directly. Single and mass casualty menus share Civilian / BLUFOR parents, triage choices and CBRN. Selecting a faction, triage or count parent still spawns random casualties; selecting a named case creates that case without unrelated random injury scatter. BLUFOR retains the existing immediate plate-carrier behavior and junctional caps; civilians are unarmored. The UI submits one authoritative creation request to the server.

| Category | Specific cases |
| --- | --- |
| Routine | Minor abrasions; minor arm laceration |
| Priority | Isolated leg fracture; moderate TBI; simple pneumothorax; mild blast lung |
| Immediate | Tension pneumothorax; hemothorax; severe TBI; severe blast lung; major limb hemorrhage; obstructed airway / secretions |
| Expectant | Herniating TBI; critical blast polytrauma; massive hemothorax / shock |
| CBRN | CS exposure; chlorine inhalation; sarin poisoning; severe sarin poisoning |

Every CBRN preset wears `G_AirPurifyingRespirator_01_F`. These represent an already exposed casualty: the native CBRN system receives an absorbed dose, and the mask does not erase it. There is no spawned hazard zone. Clinical seeds use existing native setters/physiology so subsequent treatment operates normally. Low-acuity cases remain conscious; Immediate/Expectant cases start unconscious. Triage names describe the training case, not a permanent override of physiological triage.

## Verification

All **2,552 required checks pass** (75 ownership, 1,788 networking/feature execution, 689 behavioral), including 208 new B216 cases. HEMTT check and release pass, compiling 1,715 SQF files. The three missing stringtable references reported by B215 are resolved. All 14 PBO signatures and B216 component stamps verify; the strict native-state ownership audit reports zero violations. The compiled native move inheritance check passes, and 73 packaged SQF sources match the reviewed files byte-for-byte.

A complete suite run followed by targeted revalidation of three reviewed test-contract updates reports no new regression or missing existing testcase against the retained, verified B215 baseline. Those contracts now reflect session-scoped ordinary burping, Head/Body Breathing visibility, and support exclusions limited to recovery positioning. All original testcase identities remain intact; the initial full reports and actual 10-case rerun are retained with merge provenance. No production code changed after the complete run. Current outcomes: 7,111 passed, 301 failed, 44 errors, 27 skipped. The failures/errors are historical baseline outcomes and remain visible in the reports. Exact counts, source hashes, raw test results, baseline comparison and compiled-package checks are retained in `2026-10-01-b216-results.json` and `2026-10-01-b216-test-reports.zip`.

These checks execute SQF behavior and inspect the built package, but do not render RTMs or reproduce live multiplayer inside Arma. Exact animation smoothness, fridge hinge/sound timing and rendered ACE menus still need an in-game check. Linux release verification uses `--no-bin --no-archive`; the Windows helper performs normal `hemtt release` with asset binarization. Restart clients and server with the same complete B216 build.
