# B282: critical reliability in modded servers

Stable version **1.2.4.1**, build **B282**, network protocol **1**.
Baseline: B281, `fe24f129def97b5968912a54723bdeae2801ffcf`.

This pass follows critical clinical work through delayed events, low frame rates,
ownership changes, competing providers, transport, respawn and equipment changes.
The supplied `375th_20261004` preset contains 69 mods. The review uses the supplied
ACM, ACE and Animate sources, actual aircraft-helper implementation from Ride
Where You Look, and the public contracts of collision and equipment mods.
It does not certify that all 69 mods have been run together in native Arma.

## Demonstrated failures and corrections

| Failure | Corrected behavior |
| --- | --- |
| Mainstem effects, ventilator injury and pressor debt integrated rendering-frame duration inside a slower clinical worker. | Independent owner-local elapsed clocks produce the same progression for equal elapsed clinical time; stalls are bounded and duplicate callbacks add no progress. |
| Needle leak charged inactive drainage/off intervals and old-owner time after reactivation. | Only active elapsed time accumulates; ownership and inactive transitions discard backlog while retaining the five-second output cadence. |
| Medical flags arriving after ownership registration could permanently miss workers and registries. | A bounded 1 Hz predicate repairs missing live workers, without enrolling or publishing for healthy patients. |
| NRB/CPAP oxygen gains and preoxygenation could bypass or use stale altitude exposure. | Gas delivery and current pressure are shared with native altitude oxygenation; no fixed gain ceiling, cached pressure floor or returning-owner saturation jump. |
| The same emesis could be aspirated again after ownership changes or suction, and its respiration adjustment could be added twice. | An atomic episode/burden tuple follows ownership and save/restore. Aspiration contributes through the respiratory compositor rather than modifying the native target repeatedly. |
| Attached/nested aircraft seat helpers lost their aircraft context and could eject unconscious occupants. | A bounded native seating/attachment/cargo ancestry resolver identifies the live aircraft. External seats still need actual enclosure before cabin pressure applies. |
| Containment checked patient drag/carry flags that supplied ACE does not set. | Exact ACE provider–patient claims hand control over before physical attachment, including Animate's accelerated carry path. |
| Delayed aircraft snapshots could retire containment despite movement exactly matching ACME's applied velocity. | The local lease accepts a bounded prediction from its own previous velocity and simulation time, retaining floor validation and the 1.5 m displacement tolerance. |
| Stale CPR/BVM reservations and releases could overlap or erase another provider. | Patient-owner admission grants and immutable tokens serialize each channel independently; old grants cannot change a replacement session. |
| CPR pause, rapid replacement, or patient ownership transfer could lose the clinical worker while animation continued. | Exact worker identity supports pause, replacement and current-owner adoption; old callbacks cannot retire a replacement worker. |
| Delayed hand-BVM actions could overwrite mechanical ventilation or credit retired breaths. | Delivered breaths and oxygen changes validate the current grant, patient eligibility and manual channel. Mechanical ventilation keeps its patient sentinel. |
| Shocks could fail between seats that normal medical access considered reachable. | The shock transaction uses the shared medical proximity contract. |
| Separate attached seat helpers could prevent nearby CPR/BVM in the same aircraft. | Clinical admission and native controllers share a contact predicate: actual shared aircraft ancestry plus real reach for separate helpers or walking occupants. Native same-vehicle seating retains ACE's contract. |
| A delayed respawn callback could full-heal injuries or treatment acquired after spawning. | Fresh-body initialization is an owner transaction with completion, epoch, age and clinical-activity fences. Preserved lives receive no outside posture reset. |
| Delayed syringe ACKs after controlled-unit switching could strand known unsent/rejected volume. | Settlement-only recovery restores exact known volume and returns one original token without restarting flow or touching another provider. An uncertain syringe blocks its own identity rather than other funded syringes. |
| A lost ventilator-battery ACK could strand the reserved spare and block later exchange. | Immutable requests retry independently of the panel; the owner replays recorded decisions without exchanging again. Physical settlement remains bound to the original donor and charge source. |
| A returned depleted battery could overwrite the charge of another fresh spare on the same donor. | Charge belongs to the physical returned item, with inherited battery variants surviving inventory transfers and separate transactions. Fresh base batteries remain fully charged. |
| A replacement vest could trigger repeated carrier-return broadcasts and diagnostics. | Unchanged failures retry at a bounded cadence, publish only transitions and preserve both parked cargo and the newly worn vest. Equipment/generation changes trigger immediate retry. |

No aircraft or equipment classname whitelist is added. Explicit oxygen/cabin
capabilities remain necessary: a cosmetic mask is not an oxygen supply, and an
aircraft name does not establish pressurization. The floor lease preserves ACE
and native unconsciousness.

## Evidence requirements

Each correction has production-SQF execution cases with declared engine
boundaries. Delayed grants, cancellation overtaking admission, repeated and
out-of-order ACKs, provider and patient locality changes, old callbacks, long
stalls, live gas changes, external teleports and unrelated replacement equipment
are exercised. Semantic mutations must fail. Every B281 case identity remains
required; tests are not dropped or exempted to obtain a green result.

The final published candidate requires the 15 original CLI gates, complete case
collection and full CI on the exact source/merge tree, fresh strict HEMTT, signed
PBO/config/source and asset checks, exactly 32 producer files and both native
release ZIPs. Source, producer, ZIP and evidence hashes are rechecked after all
audits. SQFC checks establish output presence and producer provenance, not a
separate proof of the compiled instruction stream's semantics. Final counts and
the exact published source/CI link are recorded in the draft PR.

## Remaining boundaries

Native PhysX ragdoll behavior and actual dedicated-server event delivery require
in-game acceptance. Root tracking tests cannot certify every aircraft model or
an external script that replaces collision, position, animation or medical state.
Mixed ACME builds remain unsupported: older clients can still execute their old
direct writers. Server, all clients and headless clients must use this entire build.

Syringe recovery in this patch covers stopped transactions on the original
still-local provider. Genuine provider ownership migration or an accepted syringe
claim whose local continuation disappears still requires a server-authoritative
delivery journal. Such uncertain custody stays held; it is not refunded on a
timeout or guessed from a stale row. Other funded syringes remain available.
Battery decisions likewise retain unresolved custody rather than guessing a
refund when bounded evidence cannot establish the outcome.
Physical battery settlement has one immutable server grant. If ownership
changes before its physical effect is confirmed, that grant is not reassigned;
the uncertain original cell stays held while other funded cells remain usable.
Returned battery charge is rounded down to a whole percent, losing less than
one percentage point. Hidden charge variants inherit the original battery's
mass and appearance. The advanced ACE action still accepts fresh base batteries;
the ACME hatch accepts charge variants. Old saves storing a partial charge only
on the donor cannot identify which identical base item held that charge; legacy
base items are interpreted as fresh 100% cells.

ACM's real vomiting producers emit an explicit episode receipt. Bare writes by
another script to native vomit/grace fields retain their native airway effects
but cannot identify a new aspiration episode across reordered clearing packets.
Those fields alone therefore do not fabricate another lung injury. When known
aspiration mirrors arrive before their authority tuple, reserve/oxygen target
changes wait for the tuple; ventilation and paid gas delivery continue.

## Native acceptance

1. Use the complete matching build on the dedicated server, clients and HC. Test
   normal performance, sustained low server FPS and a delayed client, retaining
   RPTs and the actual build manifest from every participant.
2. Treat a previously untouched casualty; transfer its ownership before and
   during arrest, ventilation, oxygen delivery, infusion and airway/chest care.
   Verify clinical progress, device operation and access recover with late flags.
3. Race two providers for CPR/BVM, pause and resume across a clinical callback,
   swap provider control, wake/heal/re-arrest and load/unload the patient. Confirm
   one provider per channel and no animated-but-inactive resuscitation.
4. Repeat ground and HALO/aircraft unconsciousness at 10 km and above 11 km with
   walking interiors, native seats, attached FFV helpers and vehicle cargo. Test
   banks, carrier teleport, independent patient teleport and normal parachute exit.
   Confirm no floor penetration, obsolete following or forced ejection.
5. Change live oxygen supply and cabin pressure; compare cosmetic equipment,
   depleted supplies, real hand-BVM oxygen, metered NRB and measured ventilator gas.
   Descent and Flight physiology OFF must remove their altitude contribution.
6. Close/switch panels or providers during syringe/battery settlement. Race two
   remote providers for the last cell in shared patient/vehicle stock, change the device epoch, and replace a vest while its original
   cargo is parked. Confirm exact inventory/charge, no duplicated return and no
   repeated network or diagnostic churn after unchanged failures.

## References and deployment

- Supplied ACE public `fnc_isBeingDragged.sqf` and `fnc_isBeingCarried.sqf`.
- [Ride Where You Look source](https://github.com/ampersand38/ride-where-you-look),
  reviewed commit `61d6ad45fc229be67dc11f4b723dc98c5980d9af`.
- [Animate Rewrite](https://steamcommunity.com/sharedfiles/filedetails/?id=3283612524).
  Supplied ACE PBO SHA256:
  `ad36f3ad9bcf43d27839d84ca331a909163e90e03a4dcdb7aa9a1846e02caf05`.
- [Unconscious Collision Disabler](https://steamcommunity.com/sharedfiles/filedetails/?id=3450571478):
  its documented player/body collision removal preserves vehicle collisions.
  Its presence alone does not establish the aircraft-floor failure's cause.
- [Arma owner command](https://community.bistudio.com/wiki/owner): server owner
  validation is required for remote providers rather than assuming client lookup.

Close Arma and local servers. Fetch the exact published B282 commit into the
existing `F:\ACM-Extended` checkout and run `tools\Deploy-ACME-B282.ps1` with
execution-policy bypass. Confirm **1.2.4.1 / B282** in-game on every participant.
The PR remains draft until native acceptance is recorded.
