# ACM Extended patch notes

## 1.2.4.1 — B272 (vented thoracostomy seals / PTX resolution)

- Chest seals over completed finger thoracostomies now retain a bounded vented outlet and can be applied while the internal leak is still healing. They protect the selected surgical tract without declaring unrelated penetrating wounds covered.
- A functioning covered finger can earn the same controlled recovery interval as an open finger or chest tube. Seal placement, burping, peeling and repeat finger sweeps preserve injury identity and earned recovery; continuing leaks can still overwhelm an obstructed or insufficient outlet.
- Once the leak settles, all communicating wounds are covered and pressure is controlled, remaining air and its residual floor gradually clear. The new residual-air clearance setting defaults to 600 seconds per normalized air unit; open finger and tube drainage accelerate clearance.
- Historical covered-finger records are interpreted as vented dressings. Ordinary wound sealing no longer silently closes a surgical incision; actual surgical closure keeps its owner readiness gate.
- Owner-authoritative inventory receipts, seal request retries, clinical epochs and pressure-scaled retained-blood drainage remain intact. No continuous blood drainage is added to finger dressings.
- Stable version remains **1.2.4.1**, network protocol **1**. B272 is a draft development candidate pending automated and native multiplayer acceptance.

## 1.2.4.1 — B264 (manual carrier / modded gear integrity)

- Manual **Remove Plate Carrier** now initiates the original patient-owner Grab/Hold/Remove/Release transaction without waiting for a separate medic4/provider animation acknowledgement, which could consume the entire eight-second deadline under a slow or heavily modded server.
- Successful removal commits through a single idempotent lease-checked patient-owner worker. A locality-transfer owner can finish the same verified removal; old callbacks cannot duplicate medical activity or replace a later episode.
- The removal timeout now has a 20-second bounded failure path, retaining identity across owner handoffs. An unsuccessful removal explicitly reports failure instead of falsely logging `Plate carrier automatically returned (remove-timeout)` when the vest never left the patient. Failed real returns preserve custody records for retry.
- Hang Bag removes only the temporary primary/launcher weapons via `removeWeapon` and restores the original classes, attachments and partially loaded magazines via `addWeapon`/`addWeaponItem` without `setUnitLoadout`. Restoration validates each saved slot and retains unmatched records if a third-party weapon mod refuses them.
- The pre-B218 legacy carrier-restoration fallback now re-equips only the saved vest and its contents, never rebuilding the casualty's full uniform/loadout. Live carrier inventory/supply custody remains authoritative and unchanged.
- Reviewed unmerged equipment compatibility submissions PRs #42 and #43; integrated an audited variant of their no-full-loadout-reset approach. Unrelated unmerged medical-item mass/weight PRs are **not** implicitly applied.
- Added B264 regression coverage and dedicated-server acceptance checks for mixed player/AI ownership, the provider-queue timeout, exact ammo and magazine restoration, live vest contents, and uniform hidden selections (boots, gloves, camouflage, sleeves). Public version remains **1.2.4.1**; B264 is a candidate pending strict CI, HEMTT and live multiplayer acceptance.

## 1.2.4.1 — B263 (multiplayer modal procedure resilience)

- Chest Seal and Thoracostomy now retire BOTH ACE's native medical-menu PFH and ACME's generation-bound independent renderer **before** closing the old menu, preventing the stale ACE closeDialog call from destroying their new panel.
- Chest-seal patient-owner enrollment retries only missing identical idempotent tokens, up to four times; a 30-second hard deadline or unexpected owner change yields full token-scoped cleanup and a visible retry reason. No clinical chest edits or supply debits are replayed.
- Patient-owner closure retains a bounded short-lived session tombstone so an out-of-order delayed Begin cannot resurrect a cancelled workspace and re-remove carrier gear. Deleted casualties are guarded before membership lookups.
- Thoracostomy pre-open abort, timeout and failed panel creation now use the complete close path; late callbacks are lease-scoped and stale panel onUnload is display-identity guarded. Heavy modpack preparation is given up to 20 seconds before clean abort.
- Cached/legacy ACM `ApplyChestSeal` and `PerformThoracostomy` requests normalize to ACME's canonical permission/supply-checked launchers, and the obsolete AI presenter no longer tries to animate these modal-only actions.
- Modal eligibility, context and distance refusals produce a diagnostic; runtime compatibility check detects replacement of the ACE treatment bridge by another addon. This does not forcibly overwrite other mods.
- Added B263 regression coverage and a multiplayer modpack acceptance matrix. Stable public version stays **1.2.4.1**; B263 remains a **candidate** until strict CI, HEMTT and dedicated multiplayer acceptance pass.

## 1.2.4.1 — B262 (NRB kit oxygen / empty-cylinder compatibility)

- Non-rebreather oxygen-source selection now accepts an ACM oxygen tank packed inside an Enhanced First Aid Kits (EFAK) kit, as long as EFAK's actual draw-charge API is loaded. The usual medic/patient donor order remains authoritative.
- Loose cylinders with zero reserve no longer block an otherwise available EFAK cylinder (or cause the native reserve debit to select an empty magazine ahead of a charged magazine).
- Added executable donor-selection regressions and reserve/source contract checks. This includes no-EFAK behavior, depleted tanks, a medic's kit vs a patient's cylinder, and correct donor-bound debit.
- Ported the compatibility approach reported in community PR #32 without merging that PR into main. Public version remains 1.2.4.1, B262 candidate pending CI and dedicated-server/EFAK verification.

## 1.2.4.1 — B261 (transfusion UI refresh / CI parity)

- Restored the historical B34 ventilation-test identifier without discarding the revised advanced-ventilation assertions; fixes B260's sole known strict regression-parity blocker (an accidentally renamed test).
- Transfuse Fluids: the Adjust Infusion button now receives its own reserved row below the ordinary fluid list, so the action control cannot overlap live bag rows.
- Active medicated-bag labels now show the authoritative remaining mL of the physical hung bag, rather than an out-of-date infusion-entry amount.
- Infusion-list rebuild identity excludes the changing volume suffix; remaining mL and tooltip update in place while retaining the selected row and avoiding list flicker.
- Added executable geometry/signature regressions, live-volume source contracts, and a focused multiplayer verification checklist.
- Public version remains 1.2.4.1. B261 is a candidate until strict CI, HEMTT and dedicated-server acceptance pass.


## 1.2.4.1 — B260 (B259 regression stabilization)

- Preserved exact measured push-dose epinephrine selector/debit semantics for extended-duration specialty syringes, rather than migrating them to the generic slow-push worker. Long normal calcium/other vascular pushes retain B259's incremental, acknowledged delivery; IM and short/default pushes remain unchanged.
- When unsupported high-rate SIMV ventilation overlaps actual chest compressions, propagate its reduced gas-exchange fraction into the current respiratory-acidosis deficit calculation as well as PaCO2 clearance.
- Updated the historical ventilation test from the retired Simple-only policy to require both Simple and advanced machine-owned ventilation to use their measured delivery, while hand BVM retains its fallback.
- Fixed the B259 executed batch-cadence test harness for SQF-VM's unimplemented HashMap getOrDefault primitive without weakening the one-second normal / five-second Hardcore expectations.
- Fixed a legacy HPMK inventory test's string-actor mock for B258's physical patient CPR gate. Native module ownership and dedicated-server acceptance remain required.
- Public version stays 1.2.4.1; B260 is a candidate until CI and multiplayer acceptance pass.


## 1.2.4.1 — B259 (live slow pushes / high-rate SIMV)

- Normal-mode vascular syringe pushes with a selected duration longer than three seconds now use the existing provider-owned incremental/acknowledged plunger transaction, shared with Hardcore but with its own 1-second physiological batch cadence. Partial dosing enters circulation during the push, retains exact syringe inventory mass, supports Stop Push, and validates provider/line locality on every tick. Default/short 1–3-second actions and IM use their previous normal choreography.
- High-rate SIMV now discounts useful alveolar gas exchange when expiratory time is too short for the modeled lung emptying time. Measured exhaled minute-volume remains separate from effective alveolar ventilation.
- During CPR with a connected advanced ventilator, the acid-base model no longer substitutes a 75% hand-bagging floor for poor actual machine ventilation. Non-CPR modes at extreme rates lose additional effective gas transport due to compression/ventilator interference; IMV VC (CPR) is not penalized this way.
- Retained oxygen-carrying blood and metabolic acidosis are unchanged by these corrections: ventilator settings alone must not directly restore circulation or neurologic consciousness.
- Repaired B258 historical HPMK mocks with native CPR-provider reads, and corrected native circulation test paths in B257 regression coverage. New executed and structural B259 regressions added.
- Public version stays 1.2.4.1. B259 is a dedicated-server candidate pending full CI and multiplayer physiology testing.


## 1.2.4.1 — B258 (community-reported clinical bugs)

- Pleural suction now requires an actual in-situ chest tube at both menu admission and the patient-owner fluid mutation. Explicit Extended left/right tube state overrides stale native ACM aggregates, while genuine legacy native-only tubes remain supported.
- Pulling the last chest tube synchronizes ACM's aggregate thoracostomy state, retires the removed side's definitive pleural outlet, and rechecks residual PTX and ongoing leak. Removing one of two tubes preserves the other.
- Needle decompression retains a higher residual PTX floor than an open finger-thoracostomy or functioning tube, including when a traumatic wound is chest-sealed.
- A removed carrier's temporary model and cargo are retired when the patient is deleted, but not simply on death.
- HPMK preparation/wrapping is refused during any active or paused CPR reservation, with inventory refund on a rejected preparation callback.
- An awake patient with an ETT or bloody/vomitus-obstructed airway can use Check Airway; an awake obstructed patient can access suction.
- Pupil examination displays a temporary arrest-related nonreactive finding even without permanent TBI.
- A new, configurable native-blood compartment threshold prevents ROSC based solely on plasma/crystalloid preload immediately after severe exsanguination; deeper extended-time red-cell accounting still requires multiplayer physiology validation.
- Added nine regression checks for these field reports. The separately reported transfusion-menu bar overlap/animation requires a reproducible screenshot and UI-specific repair; bag list and volume sync are already present in source and should not be replaced speculatively.
- Public version remains 1.2.4.1. B258 is a candidate pending CI and dedicated-server testing.


## 1.2.4.1 — B257 (final planned code audit)

- Fixed B256's SQF-VM handoff-distance fixture (the game uses a real object distance; the VM uses a controlled scalar). The actual BVM → CPR admission/range logic is unchanged.
- The CPR AnimDone event now verifies its live provider locality and recorded generation before reasserting compressions; a stale callback retires only its matching handler rather than overwriting another owner's animation.
- The provider Local event immediately retires its own machine-local CPR AnimDone handler on both ownership edges, closing the gap before the CPR controller's next frame.
- Added regression tests for valid/invalid CPR AnimDone re-entry and the owner Local retirement contract.
- Added a 13-case dedicated-server multiplayer acceptance matrix. B257 remains a 1.2.4.1 release candidate until full CI and live multiplayer sign-off.


## 1.2.4.1 — B256

- CPR now binds its local per-frame episode to the provider-locality generation. A rapid away/back transfer cancels the old session without starting new compressions or a BVM swap.
- BVM → CPR's 0.1-second delayed transition now checks the captured locality generation as well as the continuous-action epoch, preventing stale CPR launches following owner transfers.
- B255 cleanup was moved to run after shared native patient-owner worker retirement, keeping locality event preflight and existing B209/B249/PTX contracts intact.
- Corrected the B255 SQF-VM fixture extraction comment header and added six handoff/ownership tests.
- Public version remains 1.2.4.1, candidate build B256.


## 1.2.4.1 — B255

- On both provider-locality edges, retire the exact Direct Pressure claim and cancel any pending ACK token, including rapid away/back changes that prevent the original worker from running.
- Departing machines dispose of their own pressure input/PFH handles. The incoming owner retires inherited provider pressure state without clearing a replacement token.
- Patient-owner invalid claim cleanup immediately clears matching torso/limb markers and recalculates external limb blood loss.
- Normal stops and dedicated-server disconnect/death cleanup now replicate the body-part reset, preventing stale site labels.
- Added SQF-VM/source regression coverage. Public version remains 1.2.4.1, candidate build B255.


## 1.2.4.1 — B254

- BVM provider tracking now remembers the owning machine and detects ownership migration with a server-side 1 Hz worker over **tracked BVM sessions only**. Old session tokens are released atomically; paused BVM still has no heartbeat expiry.
- The same worker retires finished/cancelled session records after the existing 3-second out-of-order network grace so abandoned registry entries no longer accumulate.
- Added execution regressions for owner transfer, replacement-session safety, normal retirement and non-expiring paused BVM.
- Fixed the SQF-VM-only B253 regression failure by adapting the unsupported finite check for the numeric timer fixture.
- Public version remains 1.2.4.1; B254 / NA8-B254-1.2.4.1-candidate.


## 1.2.4.1 — B253

- Reconciler now compares a recorded continuous-action worker's original provider-locality generation with the current provider generation. A stopped worker can therefore release stale BVM/head-tilt/other continuous reservations after a rapid away/back transfer without waiting for its six-second heartbeat expiry (existing one-second invalid-state debounce retained).
- Legacy continuous controllers with no locality-generation field retain their heartbeat recovery fallback.
- Repaired the B72 historical stance regression contract to recognize B251's new locality parameter rather than demanding retired callback signatures. New SQF-VM checks cover new, healthy and legacy controller ownership.
- Public version remains 1.2.4.1, B253 candidate.


## 1.2.4.1 — B252

- Continuous-treatment workers now bind to the provider's locality generation. Rapid away/back transfers cancel stale controllers and release their clinical reservation and global action gate instead of letting old PFHs continue.
- Delayed crouch-entry animations and deferred animation-speed resets verify the original provider locality generation, so old callbacks cannot overwrite the returning/new owner's pose.
- Repaired B250 SQF-VM test incompatibility with the unimplemented finite primitive; added collision-restoration assertions and five B252 regression checks.
- Public version remains 1.2.4.1; B252 / NA8-B252-1.2.4.1-candidate.


## 1.2.4.1 — B251

- Delayed treatment-pose exits now capture and verify the provider's locality generation. The 0.12 s crouch correction, subsequent timed stance release, and both 0.35 s / 4.25 s handoff callbacks cannot change a provider after an away/back locality transition, even when the old treatment-pose epoch is unchanged.
- Active, matching-owner callbacks retain their existing movement timing and cleanup behavior.
- Added executed SQF-VM regression coverage for stale and valid callbacks. Public version stays 1.2.4.1; runtime marker B251 / NA8-B251-1.2.4.1-candidate.


## 1.2.4.1 — B250

- Expired patient-animation leases now use the token-checked owner-authoritative release helper instead of directly deleting only the lock. This restores animation speed and collision state when the patient owner reconciles a missed expiry.
- Orphan speed tokens from malformed legacy leases are released only when no newer animation lease exists; natural expiry remains non-retiring.
- Added SQF-VM and source regressions for expired, active, and malformed lease cleanup. Public version remains 1.2.4.1; candidate build B250.



## 1.2.4.1 — B249

- Explicitly release the patient breathing-sound per-frame handler on both locality-transition edges, preventing stale machine-local handles after dedicated-server/HC ownership changes.
- Preserve the clinical breath-pattern state; only the local worker handle is retired and may be recreated by the new owner.
- Added audio-locality regression coverage; release candidate B249, public version 1.2.4.1.


## 1.2.4.1 — B248

- Disabling Cheyne–Stokes now releases its active respiratory-rate drive on the owning machine instead of leaving an obsolete override pinned.
- Cheyne–Stokes breath audio stops when the feature is disabled, while patient enrollment is preserved for later re-enable.
- Added toggle lifecycle tests; version remains 1.2.4.1, B248 candidate.


## 1.2.4.1 — B247

- Cheyne–Stokes: unchanged rounded respiration rates no longer invoke the network publication helper at 10 Hz; actual RR changes still publish immediately.
- Delayed post-ROSC Biot gasp audio now verifies patient locality, preventing a departed owner from emitting an extra sound after migration.
- Added regression contracts. Public version stays 1.2.4.1, runtime build B247 (release candidate).



## 1.2.4.1 — B246

Updated 7 October 2026.

- Consolidated circulation, coagulation, medicated-infusion, preoxygenation, aspiration, shock, and rhythm-threshold missed-transition discovery into one 1 Hz owner-registry pass. The hot 4-5 Hz clinical workers no longer rescan every server-owned unit.
- Preserved the previous circulation fallback's one-second worst-case discovery latency while removing the duplicate 1 s / 2 s / 2 s broad scans.
- Fixed medicated-infusion lifecycle retirement: after the final tracked bag disappears or completes, the owner publishes the final empty structured state and removes the patient from the 4 Hz infusion registry, preventing an indefinite post-treatment 1 Hz state heartbeat.
- Gated chest-seal server maintenance when there are no live sessions and no pending edit outcomes, removing its otherwise permanent one-second `allPlayers` scan on healthy idle servers.
- Added regression coverage that keeps healthy owned units out of every consolidated active registry, preserves direct treatment enrollments until their first worker tick, and rejects reintroduction of independent owner scans.
- Public version remains 1.2.4.1; runtime marker is B246 / NA8-B246-1.2.4.1-candidate.

## 1.2.4.1 — B243

- IV component click capture widened to 1.8% while preserving the 5.2% attraction field and 0.4% hard-seat.
- Field IV second-catheter placement keeps both 14g and 16g selections and supports direct gauge switching.
- Extension/line geometry seats 20 authored pixels deeper into the catheter hub with aligned downstream targets.
- Historical import-time regression modules are being converted to named current-behavior checks so collection can complete.
- Public version remains 1.2.4.1; runtime marker is B243 / NA8-B243-1.2.4.1-candidate.


## 1.2.4.1 — B207

Updated 30 September 2026.

- Direct Pressure and Hang Bag now share bounded owner-side claim validation and cancellation history. Duplicate replies, cancelled requests arriving late, reordered renewals and old releases cannot reapply or replace a newer action.
- Direct Pressure acceptance expires with its owner-granted reservation. Patient-side marker and clot updates carry the exact claim token so delayed work cannot overwrite or credit a replacement hold.
- Fixed Hang Bag episode collisions during rapid restart and long mission uptime. Renewal sequence numbers prevent replayed requests from extending a lease or reapplying flow.
- Continuous-action recovery tracks the actual provider and generation and runs the original cancellation worker. A second local medic cannot replace a live controller; failed startup and interrupted callbacks release the matching session once.
- Direct Pressure's medical-menu bridge reports queued requests correctly. Its accepted-claim path owns the one-shot treatment sound, removing the remaining global sound broadcast from the core override.
- Manual plate-carrier checks use an active patient registry with a 30-second recovery scan. Ventilator alarm discovery runs twice per second while retaining the existing 20 Hz beep scheduler and checking nearby vehicle occupants.
- Added per-PBO build/protocol stamps and bounded server/client/headless-client verification. Mixed or unverified installations produce diagnostics without kicking players or disabling treatment.
- Added opt-in, bounded local network diagnostics and a dedicated-server validation runbook. Strengthened CI to reject new failures, new skips, missing tests and incomplete runs while reporting the historical failing baseline separately.
- Public version remains 1.2.4.1; runtime marker is B207 / NA7-B207-1.2.4.1-stable. Live dedicated-server validation remains required before broad rollout.

## 1.2.4.1 — B206

Updated 30 September 2026.

- Fixed Direct Pressure failing to start on dedicated servers: provider requests now carry the originating client's ID, and acknowledgements target the provider object. Pending reservations remain protected on player and headless-client casualty owners.
- Fixed the same client ownership mismatch in Hang Bag claims and seizure gesture validation.
- Fixed HPMK preparation/removal callbacks interpreting ACE treatment arguments as internal transaction flags.
- Fixed facility and evacuation modules parsing numeric position coordinates as strings.
- Includes the B205 network snapshot, infusion queue, procedural handoff and cleanup fixes. Public version remains 1.2.4.1; runtime marker is B206 / NA6-B206-1.2.4.1-stable.

## 1.2.4

Updated 27 September 2026.

### Stable release identity

- Public and debug version is 1.2.4.
- HEMTT package version is 1.2.4.0.
- Stable runtime identity uses internal build B190 with no RC or hotfix suffix in the debug menu.
- CPR now treats an HPMK in the `exposed` state as genuine chest access and normalizes the action to the Body selection before both menu eligibility and treatment execution. Fully wrapped HPMKs still block chest CPR.
- IO fluid syncope is now one-shot per physical IO-line generation. Eligibility is decided only by the casualty's consciousness when the first admitted fluid enters that IO; an IO that first flowed while the casualty was unconscious can never make them pass out later after they wake.
- A conscious casualty can experience at most one short IO fluid syncope event on that IO generation. ACE's timed unconscious transition is used with stable-vitals forced wake, so the event is transient rather than a repeatedly re-armed knockout.
- Medication pushes through an IO no longer use the fluid-pressure syncope path or force raw pain to maximum. They use only a moderate IO medication-pain floor, allowing analgesics pushed through the IO to behave as medication rather than repeatedly recreating fluid syncope.
- Fixed the remaining first-open Narc Box Seconds to Push over focus race. Deferred Draw-page tag controls are no longer created after Body Map takes ownership, and hidden medication/list refreshes are suspended while the duration editor owns keyboard focus.
- A manually removed plate carrier can now be borrowed directly as the Semi-Fowler support when no backpack is present. The same saved vest and world prop are reused, so no duplicate carrier is spawned and manual custody remains authoritative.
- Semi-Fowler now resumes automatically after manual carrier-removal choreography if it had been temporarily flattened for the removal. The casualty replays the normal patient lift/hold sequence, and the provider replays the normal supported Semi-Fowler lift.
- The chest-access carrier watchdog no longer pulls a manually borrowed Semi-Fowler support prop back to the ground park while the patient is elevated.
- Lowering/canceling Semi-Fowler returns a borrowed manual carrier to its parked manual-custody position instead of re-wearing it. The carrier still remains off until Replace Plate Carrier or an automatic wake/transport return.
- Wake, Get Up, drag/carry, vehicle loading, or independent movement while Semi-Fowler is borrowing the manual carrier now retires Semi-Fowler first and then force-restores the carrier to the casualty.
- Manual plate-carrier eligibility now uses explicit HEMTT-safe alive/awake checks instead of the previously ambiguous compound expression.
- i-gel and ETT removal continue to sever Ventway clinical state and initiate ventilator custody return before the airway state is cleared.
- Removing an i-gel or extubating an ETT now immediately stops patient-side Ventway ventilation and starts a full custody return of the mounted ventilator to the airway-removing medic.
- ETT extubation no longer clears only the connected/driving flags; airway loss uses the same complete Ventway patient/custody teardown path for both ETT and i-gel removal.
- Ventway's patient-as-BVM gas-exchange sentinel no longer counts as AED motion. Analyze can complete while the Ventway is ventilating in CPR mode, while real chest compressions and a real BVM provider still register as motion exactly as before.
- Fixed a manual plate-carrier completion callback argument mismatch that unpacked the provider object into the lease slot. The resulting string-vs-object comparison threw every scheduler pass and stranded the provider animation.
- Fixed manual plate-carrier medical log entries to pass ACE a string message instead of an array, eliminating the repeated `isLocalized: Type Array, expected String` medical-log errors.
- Manual Plate Carrier eligibility now uses valid SQF lazy-evaluation syntax for the medic-awake guard, fixing the HEMTT `SPE2` parse failure in `fn_manualPlateCarrierCanToggle.sqf`.
- Transient-state reconciliation now treats IV band presence as a boolean existence problem end-to-end. Malformed replicated band flags are type-normalized before logical use, and the old numeric `findIf >= 0` path that could throw `Type Bool, expected Number` has been removed.
- Native treatment animation handling now canonicalizes non-string/blank animation config to an empty string and completely skips animation-duration lookup when no native provider animation exists. ACME-owned Chest Seal, Inspect Chest, Thoracostomy, IV minigame and similar modal actions no longer emit empty-animation duration warnings.
- Structured item descriptions now XML-escape ampersands. The HPMK description no longer produces repeated `Unknown entity: Management Kit. Reusable warming blanket` log spam, and the AAJT-S description was corrected at the same boundary.
- Remove/Replace Plate Carrier is now a global medical-menu control pinned above every category instead of living only under Advanced.
- Manual carrier removal now uses the same chest-access medic4 provider choreography, patient lift/release animation and fixed above-head carrier prop as automatic chest access.
- Manual removal is represented by a persistent chest-access lease. Later CPR/BVM, Chest Seal and other chest procedures reuse the already-open chest and skip the carrier-removal choreography instead of creating a second custody system.
- A manually removed carrier is automatically and forcefully returned if the casualty wakes, starts Get Up, is dragged/carried, enters a vehicle, is externally moved away from the removal point, or another system restores a vest.
- Manual carrier leases do not expire with provider lifetime or the ordinary 15-minute temporary chest-access stale-lease cleanup; another medic can still explicitly replace the carrier while the casualty remains down.
- LifePak stock button hitboxes have been restored to ACM's native AED pixel grid. The separately tuned SYNC button/LED remains on the 1.05x rendered-background mapping; applying that mapping to the stock controls was what shifted them downward.
- Provider animation speed now has an explicit ownership contract. Native treatment, treatment-pose and Semi-Fowler rate leases retire without leaving getAnimSpeedCoef above 1, preventing a completed medical action from making that player run/sprint abnormally fast.
- Remove/Replace Plate Carrier uses the shared animated chest-access custody path: provider medic4 theatre, patient lift/release, and the parked carrier above the casualty. It is pinned above every medical-menu category and automatically returns on wake, Get Up, movement or transport.
- Deferred provider gestures now capture the treatment patient explicitly in the next-frame callback arguments. This removes the HEMTT undefined-`_patient` warning and prevents the gesture from depending on an out-of-scope local variable.
- Applied bandages are now mechanically stable: platelet count, coagulopathy and ACE wound-reopen probability no longer schedule a dressing to fail or move a bandaged wound back to open state.
- Clot popping now acts only on unsecured clotted wounds. One event can affect only one selected clot and can reopen at most 0.15 of one wound by default, hard-capped at 0.25.
- The dilutional clot-pop roll is now genuinely rare: 0.1% base chance per 60-second evaluation, 0.3% hard ceiling after severity scaling, with a shared 10-minute casualty cooldown.
- ACM native unstable-clot reopening now uses the same single partial-pop function and the same cooldown instead of independently scheduling multiple full-wound reopens.
- TXA detection in native clot stability now reads the actual TXA medication count instead of an always-positive multiplier.
- LifePak/AED physical buttons now use the exact same 1.05x background transform as the rendered device artwork, eliminating invisible hitbox drift at 1680x1050 and other nonstandard aspect ratios. Analyze, Charge, NIBP, Speed Dial/Cancel and Shock all resolve the actual monitor operator rather than the legacy casualty sentinel.
- The Narc Box Seconds to Push over editor now owns an explicit focus lease from mouse-down through KillFocus. Carousel, stock-list and 25 Hz UI refreshes cannot move, hide, disable or rewrite the edit while typing, and the lease is cleared on dialog teardown.
- Get Up is mutually exclusive with ACE carry ownership. An attached/carried casualty cannot clear lying state or force a new animation underneath the carry transaction, and the Get Up prompt retires while carry ownership is active.
- Same-vehicle medical care is clinically allowed while provider/patient animation remains suppressed. Generic progress bars, chest-access preparation, Chest Seal and Thoracostomy now treat a shared vehicle as a valid interaction context rather than failing because the animation cannot run.
- Penetrating chest-hole state is authoritatively capped at six front and six back. New impacts cannot bypass the cap, and existing over-cap casualties are migrated down to the first six records per side.
- Accepted medical-menu treatments now start native treatment/progress immediately on the click frame. Provider weapon/stance preparation is presentation-only and can no longer hold a clinical button for 0.5–3 seconds before anything happens.
- Suture Chest Tube no longer inherits the Thoracostomy launcher's one-second treatment delay; it uses a 0.001 s ACE treatment window so the state commit is effectively immediate while retaining the normal treatment callback path.
- Intentionally timed transfusion assembly buttons repaint their active state on the click frame before their assembly timer begins. Existing deferred menu transitions already close the current UI or start the native move flow first.
- Conscious patients retain ownership of their own body animation during native treatment. A conscious prone casualty may use the normal downed-target provider animation, but ACME/ACM no longer starts an `animationPatient` state on that conscious casualty.
- Conscious casualties who are independently standing or crouched retain their worn plate carrier during chest-access interventions; if they wake and return to either stance while a carrier is already parked, it is restored immediately.
- Chest Seal, NAR SPEAR, Thoracostomy and shared chest-access preparation recognize locally controlled NPC/Zeus medics through ACE's player-control predicate rather than requiring the provider object to equal the cached ACE_player object.
- Conscious independently standing or crouched casualties use provider-only ambulatory treatment presentation instead of downed-casualty poses. Explicit treatments select validated vanilla `AinvPknl...medicUp0-5` empty-hands states and fall back safely if a state is unavailable.
- Conscious prone casualties deliberately return to the normal downed-target provider animation family, but ACME does not take over or settle the patient's animation while that casualty remains independently conscious.
- Standing/crouched auscultation uses the existing Semi-Fowler Putdown reach, freezes the frame already on screen without seeking backward into the RTM, then resumes directly through the authored Putdown return animation on close.
- Ambulatory `medicUp` animations are now strict one-shot gestures: no hold recovery, no watchdog replay, no repeated seek, and no independent Chest Seal reassert loop. Chest Seal and NAR SPEAR no longer replay the ambulatory workspace animation after their one-shot gesture ends.
- The debug overlay is now pinned to the absolute left safe edge and uses one height-based reference geometry across aspect ratios. Its panel width, typography and spacing scale uniformly instead of widening on ultrawide displays.
- Debug rows dynamically expand their value columns before rendering, then the entire overlay receives one common width/height fit. Normal values no longer word-wrap, and the body control is hard-bounded to the panel bottom so 1680x1050 and other short safe areas cannot clip the final sections.
- Launcher metadata now identifies the package as ACM Extended rather than the development fork.
- The current stable thoracostomy preparation lifecycle and its providerless menu handoff are included in this release.

## 1.2.3

Updated 24 September 2026.

### Player-facing hotfix

- IV tray catheter stacks are centered on the visible catheter artwork, fan upward only, use lighter overlap opacity, and keep the extra-stock `+` badge inside the tray tile.
- Tibial IO flow is now occluded by a tourniquet on that leg and by Zone 3 AAJT-S/REBOA occlusion.
- Narc Box syringe carousel hover no longer forces repeated full-opacity repaints, and typed push-duration seconds remain stable while editing and across syringe selection changes.
- Medication cannot be pushed through an IV/IO line that still contains a non-empty Blood, FreshBlood, or FBTK bag. The blood bag must be empty or removed; blood on a different access does not block the selected line.
- Medic-role providers retain thoracostomy access but no longer receive a chest-tube tray option. Doctor-role providers retain thoracostomy plus chest-tube access.
- Check Breathing / Inspect Chest no longer enter a redundant ACME roll-only `Preparing...` stage when native ACM already owns the patient roll.
- Leaving interaction range during `Preparing...` now permanently cancels that preparation generation; it cannot later launch when range changes again.
- `Preparing...` is now text-only with no black background panel.
- Patient-spawner casualties now receive their plate carrier inside the initial spawn/loadout transaction, before unconsciousness or injuries are applied.
- Semi-Fowler can now be initiated with no backpack or plate carrier as a true provider-held continuous maneuver. The provider freezes in the authored Putdown support pose and releasing/moving/leaving range or losing the maneuver lays the casualty back down.
- Unsupported/manual Semi-Fowler never auto-resumes after the provider yields; it must be initiated again.
- Supported Semi-Fowler remains compatible with BVM. CPR permanently cancels Semi-Fowler and direct BVM -> CPR swaps perform one authored lay-flat before compressions while keeping the chest-access lease alive.

### Wake posture

- Successful on-foot clinical wakes now pre-arm ACM's treatment/lying contract before ACE clears unconsciousness, so the casualty wakes into `ACM_LyingState` instead of immediately exiting to a normal prone/get-up animation.
- `Get Up` remains a separate patient action after consciousness returns. Vehicle wake behavior is unchanged.

### Consciousness and wake stimuli

- Fixed a CBA state-machine calling-convention regression introduced by the September 22 wake refactor. CBA invokes transition conditions with the casualty object directly, while the new wake gate expected an argument array; this could abort every normal wake transition.
- `ACM_core_fnc_canWake` now accepts both CBA's direct casualty-object call and normal array-style calls.
- The `ace_medical_WakeUp` observer now accepts the actual direct-object event payload instead of running `params` on an object.
- Ammonia inhalant, Slap Awake, Shake Awake, spontaneous wake and fracture-pressure stimulation now reach the same functioning canonical wake path again.
- Fracture-pressure stimulation now calls `ACM_core_fnc_requestWake` directly instead of manually publishing a parallel WakeUp event.
- Sedation, paralysis, active seizure, cardiac arrest and other explicit forced-unconscious blockers remain authoritative; the fix restores eligible waking rather than bypassing those gates.

### CPR / BVM chest access

- The chest-access preflight is now a single-click state: the medical menu closes immediately, a top-center **Preparing...** banner appears, and repeated CPR/BVM clicks cannot enqueue duplicate carrier animations.
- Escape/F0 during Preparing cancels that exact generation, releases only its chest-access lease, clears the banner and reopens the medical menu.
- Direct Pressure now yields before carrier/head/intervention animation ownership and remains animation-passive for the full native CPR/BVM lifetime instead of resuming when the short launcher treatment ends.
- Direct Pressure episodes now persist across CPR/BVM: its PFH, input ownership and target remain intact while the clinical marker/provider pose yield, then resume only after CPR, BVM and their bounded transfer window are all clear.
- Semi-Fowler suspension is lower priority than active intervention patient animation/physics and will not re-elevate during CPR, BVM or the CPR/BVM transfer window.
- CPR/BVM use one stable maneuver-family chest-access lease across repeated middle-mouse swaps. Provider-local and patient-owner transfer windows both prevent carrier restoration in the gap.
- Carrier restoration now has its own accelerated patient choreography: 0.75 s lift + 0.02 s hold + 0.88 s lower, with a token-scoped 1.60x patient animation speed and guaranteed reset to 1.0.
- A new chest intervention clicked during the short carrier-return animation queues behind that restore instead of waiting until the 12-second fail-open timeout.
- CPR and all BVM variants now use the same plate-carrier chest-access preflight.
- Plate-carrier custody remains active while either CPR or BVM is active, including repeated middle-mouse swaps between the two interventions.
- CPR -> BVM and BVM -> CPR handoffs use a bounded provider-local transfer token so the carrier cannot be restored during the transition gap. If the replacement maneuver fails to start, normal restoration resumes automatically.
- Patient-owner restoration also refuses to put the carrier back while live CPR or BVM is present, providing a second guard against stale provider cleanup.
- Carrier-off choreography now uses dedicated faster chest-access timing: 0.70 s lift, 0.04 s top hold and 0.78 s lower. These values do not change Semi-Fowler/head-elevation timing.
- Removed the extra synthetic settle delay after carrier removal/lowering. The queued intervention may launch on the first readiness frame, before the medic4 provider pose reaches its 2.2 s frozen hold.

### Version identity

- Public/debug version advanced to 1.2.3.
- HEMTT package version advanced to 1.2.3.0.
- Stable 1.2.3 runtime identity uses internal build B152 with no RC suffix in the debug menu.

## 1.2.2 cumulative update

Updated 19 September 2026. Version 1.2.2 incorporates the complete 1.2.1-rc1 patch series and aligns the release metadata. Consolidates all subsequent patches from 18–19 September, through [8fd12c0](https://github.com/hesherson/ACM-Extended/commit/8fd12c016f17504b05781925f095d75f0fbe9424). The [covered commit range](https://github.com/hesherson/ACM-Extended/compare/f2b6c482123aff1a60234e4d2b737e44de33767c...8fd12c016f17504b05781925f095d75f0fbe9424) includes 132 commits. The release check corrections and removal of the experimental drag handle are also included.

Build public releases from `main`. The experimental drag handle remains on `dev` only.

These notes describe the combined current behavior. Later corrections take precedence over intermediate implementations in the individual patch records.

### Build, debug and settings

- Removed Attach Drag Handle and Release Drag Handle from release packages, including releases built from dev. Experimental actions are available only in dev or launch builds from the dev branch.

- Fixed a missing UI scaling definition when changing syringe size in the Narc Box.
- Fixed the duplicate ACE_Actions declaration and invalid inheritance that stopped HEMTT with L-C03/L-C04. Patient actions use the existing action tree, preserving Get Up.
- Updated the public/runtime version and debug overlay to 1.2.2. HEMTT and native addon metadata now use 1.2.2.0.
- Separated shared gameplay settings from client preferences. Gameplay rules remain globally controlled; presentation, accessibility, interface and debug preferences are controlled by each client and cannot be overridden by the server or mission.

### Medication pushes and IV tray

- Reworked the Seconds to Push field with an explicitly editable control and click focus. Carousel shortcuts and click areas now leave the field available for typing.
- Moved the gray recommended time onto a separate label so it cannot replace entered digits. Correcting an invalid duration now updates the Push button while typing. The duration row still follows the Push button layout.
- A blank seconds field defaults to a push lasting 3 seconds in both normal and Hardcore medication modes. Gray suggested times are guidance; entering a duration selects that duration, within 1–300 seconds.
- Restored continuous syringe plunger movement during Hardcore pushes, following the actual remaining medication volume.
- Corrected the IV tray catheter fan's visual anchoring.

### Transfusions and access selection

- Fixed held IV bag and custom line visibility for other players, including players joining during a hold. Observer props follow the existing lowering and cleanup lifecycle. Corrected a remaining client ownership check that rejected observer visuals after the initial patch.
- Removed the separate Hardcore Transfusion setting. Bag preparation, Y lines, flushing, infusion and access site management are now the standard workflow.
- Removed the 250 mL saline bag minimum. Y lines still require compatible saline and retain the configured flush volume rule.
- Retained the standard calcium/citrate and hypothermic coagulation values. Old exported Hardcore Transfusion values no longer select an alternate model.
- Fixed IV/IO access selection so clicking a site updates the selected access, top left name, artwork and bag lists together.
- Added the normal button sound to access site clicks and removed the top left IV/IO toggle. The inventory source switch remains available.

### Shared menus and provider cleanup

- Carry Assist now handles left click and Escape directly as well as through CBA. Cancellation removes both input paths and releases the patient, and the shared holding animations include native crouch and prone exits. Stale callbacks cannot cancel a later action.
- Chest seal and ventilator menu entry no longer waits for a provider stance or holster animation. Each provider has one pending menu request and one display update loop.
- Fixed duplicate chest menu updates bypassing finger drag resistance. Reopening cannot inherit an old panel's drag state, and a late unload cannot close a newer panel.
- Chest workspace restoration waits for the last viewer and cannot restore gear or positioning over a new session. Server cleanup releases viewers lost through death, respawn or disconnect.
- Dead patients no longer trigger the ventilator recovery warning or disable its controls solely because they died. Connected devices remain available to multiple viewers and for manual recovery.
- Fixed Head Tilt–Chin Lift, Carry Assist, Feel Pulse and stethoscope startup or cleanup aborting on string key handler IDs. Manual holds have a server watchdog for abandoned providers and preserve another provider's replacement session.
- Patient death preserves treatment evidence and attached equipment. Provider death or replacement clears the affected local action and UI without opening menus on the replacement player.

### CPR and BVM on servers

- Restored ACM BVM control flow and removed the added heartbeat, server expiry worker and per-frame replicated session check. Native breath timing, oxygen use, pause/resume and CPR compatibility are retained.
- In 1.2.2, starting BVM fully released that provider's Direct Pressure. In 1.2.3 RC3 this is superseded: CPR/BVM now temporarily yield the same-provider pressure episode and allow it to resume after the maneuver family ends.
- Prevented new pressure on any body region during an active maneuver. Stale pressure callbacks and earlier queued menu/stance callbacks cannot cancel BVM or replace its controls.
- Fixed CPR cancellation leaving the provider in the compression animation. Cancellation disables animation re-entry and releases the patient before removing input handlers, then plays the existing exit animation and queues a normal movable crouch. CPR loop states now include native exit connections, and stale assessment holds are retired before a new maneuver starts.
- Pausing CPR disables the compression loop before changing pose. Repeated starts, respawn, disconnect and abandoned CPR sessions now receive session cleanup without stopping another provider's BVM.
- Corrected boolean status comparisons that interrupted CPR and BVM updates, including BVM oxygen status.
- Fixed string input handler IDs interrupting BVM startup or cleanup and leaving providers stuck or patients permanently reserved.
- Release the captured BVM session on cancellation or respawn, with server cleanup for provider death and disconnect. Pausing ventilation still reserves the patient, and old cleanup cannot cancel a newer session.

### Field Blood Transfusion Kit

- Blood collection now requires IV access. IO collection is disabled with an IV required message and is rejected before consuming the kit.
- Corrected collected volume yield and recognition of a full bag.
- Collection respects bag capacity and available donor blood, with consistent volume accounting. Existing fresh blood metadata and multiplayer transfer are retained.

### PEA and the AED monitor

- Default PEA now uses a narrow tracing resembling sinus rhythm, with P, QRS and T components, including obstructive PEA without severe uncovered transfusion burden.
- The existing wide complex PEA tracing is reserved for a severe transfusion burden not covered by calcium. ACME uses its current transfusion/calcium model as a gameplay proxy for this appearance; it does not simulate a measured potassium level.
- At an 80 BPM resting baseline, more than 2 L of uncovered burden selects the wide tracing. Calcium coverage can narrow it while another unresolved cause keeps the patient in PEA.
- The monitor detects this morphology change while open and when reopened, preserving electrical beat timing. Both forms remain pulseless and nonshockable; arrest entry and ROSC rules are unchanged.

### Seizures and the patient spawner

- Added Head > Debug > Induce Seizure for living patients who are not in cardiac arrest. It requires the provider's debug setting and runs on the patient owner without the normal treatment stance/weapon preparation.
- Unified seizure presentation around the shared seizure state machine, including Sarin while preserving ACM's original Sarin onset threshold.
- Reworked startup so a settled unconscious or spawned training patient can begin convulsing without needing CPR or a manual roll first. The driver starts the gesture directly and preserves a downed patient's supine, prone or elevated hold during the animation handoff.
- Corrected seizure speed to 1.05 times each native clip's speed. The previous shared speed value made the clips much too fast. Spasm3–6 now last approximately 4.0, 4.1, 4.6 and 7.4 seconds.
- Published seizure state before collapse, prevented patients from waking spontaneously during active seizures, and stopped generic pose settling or manikin pose maintenance from cancelling the episode.
- Seizures yield to CPR, active rolls, vehicles and drag/carry. Repeating the debug action can recover an interrupted visual driver without repeating the collapse.
- Full heal, episode replacement and stop clear the seizure gesture and invalidate delayed callbacks, preventing an old episode from restarting.

### Patient positioning

- Release builds omit the experimental drag handle regardless of branch. It remains available in dev or launch builds from dev. Standard ACE dragging and carrying remain available.
- Semi-Fowler's is unavailable for standing or crouching patients, including when an old lying flag remains. Eligibility is checked in the menu and again before positioning.

### Finger thoracostomy and chest seals

- Added removal and burping of a seal over a finger thoracostomy tract. After removing the seal, the existing tract can be swept again without consuming another kit, then used for a chest tube.
- In Adjust Thoracostomy, put down the held tool. Right click the surgical seal to remove it; scroll five notches to lift and burp a corner, and reverse the wheel to lay it flat. Select the finger and click the open tract to repeat the sweep.
- Traumatic and surgical chest seal burping has no timer or cooldown. Each completed five-notch peel triggers one treatment, activity log entry and animation request. Scroll again to start another peel immediately, or reverse the wheel to lay the corner flat.
- Accepted burps request the corresponding chest seal treatment animation on the provider. Scrolling a fully lifted corner immediately starts another peel cycle without moving off the seal. Both seal types remain usable on a corpse without restarting physiology.
- Chest seal Flip waits for the actual provider roll animation before physically rolling the patient. Entry transitions no longer trigger the flip; closing, cancelling or timing out the panel cancels a pending roll.
- Aftercare acts on the selected side and preserves unrelated seals and a chest tube on the opposite side.
- Current gameplay behavior: an open finger tract vents air, while sealing it can allow pressure to recur if an internal leak remains. No penalty is added for time spent open, and the tract does not close spontaneously. Continuous passive blood drainage belongs to chest tubes; inadequate preparation can flag the incision for infection.

### Auscultation controls, sound and posterior view

- Fixed remote observers seeing Feel Pulse and Auscultate Chest continue animating after the provider reached the frozen pose. The followup corrects the same client ownership check used by bag visuals.
- The bell opens at the cursor and is 19% larger. Hold left mouse to listen and move it with drag resistance; it shrinks by 12% while pressed. Releasing lifts it and stops contact sound.
- Left lung, right lung and cardiac sounds mix continuously as the bell moves, without restarting their phase at each listening point.
- Restored all 21 stethoscope sounds to their original levels. Outside audio now drops to 10% while listening, with chest sounds kept separate from that reduction.
- Added a Front/Back view button using the existing body textures at matching scale. Anatomical left/right mapping follows the selected view. Switching views lifts the bell and changes the diagram without physically rolling the patient.
- Added basal crackles on the affected lung when hemothorax fluid exceeds 0.3 L, increasing to full contribution at 1.1 L. Draining fluid reduces the finding; findings in the upper zones and opposite lung remain.
- Hemothorax listening uses ACM's pooled pleural fluid and finding for the affected lung, rather than introducing separate left/right fluid volumes.
- Lung sounds fade out at the diaphragm. Below it, the front view retains only a narrow centerline cardiac field, fading sideways and downward; lower lateral areas are silent. The back view uses lung fields without anterior cardiac listening points.
- Closing or replacing the scope panel removes its sound objects and restores hearing attenuation; release and focus loss clear held contact.

### Visual effects, descriptors and icons

- Reduced ketamine water distortion amplitudes by another 25% across dose and debug tiers, preserving wave timing, easing, blur and chromatic response.
- Clinical descriptor mode now uses Severe Ecchymosis for extensive bruising in chest inspection and injury list rows.
- Dress Junctional Wound now uses the same medical menu icon as Pressure Bandage.

### Validation status

The initial ACE action config correction passed its focused config check and the existing 20 RC1, drag and seizure checks at that point. Subsequent patches received source or numerical checks covering registration, class duplication, UI selection, animation ownership, sound mixing, waveform samples and handling of stale callbacks.

The earlier supplied Windows release log confirmed successful packaging of 14 PBOs for 1.2.2.0. The missing UI scaling definition has been corrected, and the experimental drag handle has now been removed from the public release. The current release source passed all 31 focused tests, including HEMTT 1.21.0 strict checks with no code diagnostics, complete addon config compilation, release transport boundaries, seizure behavior contracts and chest interaction contracts.

Pull `main` and rebuild the release package to include the removal. This new package has not been built on Windows or tested in Arma here. Confirmation in Arma remains necessary for normal ACE dragging and carrying, seizure startup and speed, chest animations, transfusion selection, audible auscultation mixing and PEA transitions, including patients owned by another machine.

The version update changes release metadata and documentation; the cumulative gameplay changes are listed above.

The medication duration followup passed 25 focused checks on this branch, including strict HEMTT diagnostics, complete config compilation and SQF execution of the duration readers and input filtering. Mouse focus and actual keyboard entry still require verification in Arma. See the detailed input patch record below.

The release build followup produced 14 PBOs from each branch with HEMTT 1.21.0 using `--no-bin --no-sign --no-archive`. Inspection of the packaged binary config, GUI renderer and startup script confirmed that every drag handle action and startup call is absent. The separate development build retains its actions. Main passed 9 checks with its development-only check skipped; dev passed all 21 checks. Full Windows asset binarization and in-game verification remain outstanding.

The provider hold followup passed 18 checks on each branch, including SQF execution of observer recovery and packet ordering, strict HEMTT diagnostics and full addon config compilation. Two-client Arma verification remains outstanding.

The server bag and BVM followup passed 33 checks on each branch, with one optional development package check skipped. Both branches built 14 PBOs with HEMTT 1.21.0 using `--no-bin --no-sign --no-archive`; targeted package inspection confirmed the new runtime is included. Dedicated server gameplay remains unverified. Update the server and every client, then restart the mission.

The bag visibility and CPR stop followup passed 72 focused checks on each branch, with one optional development package check skipped. Both produced 14 release PBOs. Revised client/server tests reproduce the earlier failures and verify the corrected paths. Actual multiplayer rendering and animation still need verification.

The seal burping and Carry Assist followup passed 124 focused checks on each branch, with one optional development package check skipped. Both built 14 release PBOs without binarization, signing or archiving. The new tests reproduce the previous seal latch failure and execute the actual Carry Assist cancel callbacks. Arma multiplayer input and animation still need verification.

The removal of the burping timer passed 25 focused checks on each branch, including immediate repeat peels, strict HEMTT diagnostics and config compilation.

The BVM startup followup passed 95 focused checks on each branch, including complete startup, pause/resume, cancellation, CPR, Carry Assist, shared menus, strict HEMTT diagnostics and config compilation. Both branches built 14 release PBOs using `hemtt release --no-bin --no-sign --no-archive`. Windows asset binarization, signing and live multiplayer playback were not tested here.

The native BVM restoration passed 108 focused checks on each branch, including repeated Direct Pressure to BVM transitions, native breath delivery, pause/resume, cancellation, rejected starts, provider lifecycle cleanup, CPR, Carry Assist, shared menus, strict HEMTT diagnostics and config compilation. Both branches built 14 release PBOs with `hemtt release --no-bin --no-sign --no-archive`. Windows asset binarization, signing and live Arma multiplayer behavior were not tested here.

The stethoscope audio correction passed 37 focused checks on each branch, including chest interaction contracts, treatment cleanup, strict HEMTT diagnostics and complete config compilation. All 21 diagnostic gains were compared with the original source and match exactly. Both branches built 14 release PBOs without binarization, signing or archiving. In-game listening remains unverified.

### Detailed patch records

- [Stethoscope audio correction](docs/patch-notes/2026-09-20-stethoscope-audio.md)
- [Restore ACM BVM flow](docs/patch-notes/2026-09-20-bvm-native-flow.md)
- [BVM startup cancellation](docs/patch-notes/2026-09-20-bvm-startup.md)
- [Chest seal burping without a timer](docs/patch-notes/2026-09-20-burp-no-timer.md)
- [Repeat seal burping and Carry Assist release](docs/patch-notes/2026-09-19-burp-carry-release.md)
- [Shared menus and death cleanup](docs/patch-notes/2026-09-19-shared-menus-death-cleanup.md)
- [Bag visibility and CPR stop followup](docs/patch-notes/2026-09-19-bag-visibility-cpr-stop.md)
- [Server bag visibility and BVM recovery](docs/patch-notes/2026-09-19-server-bag-bvm.md)
- [Provider hold synchronization](docs/patch-notes/2026-09-19-provider-hold-observers.md)
- [Release build drag handle exclusion](docs/patch-notes/2026-09-19-release-drag-build-gate.md)

- [Transfusion and thoracostomy](docs/patch-notes/2026-09-19-transfusion-thoracostomy.md)
- [Patient motion and ketamine](docs/patch-notes/2026-09-19-patient-motion.md)
- [Chest interactions, drag rope and held auscultation](docs/patch-notes/2026-09-19-chest-interactions.md)
- [Final seizure speed correction, posterior auscultation and clinical descriptors](docs/patch-notes/2026-09-19-auscultation-seizures.md)
- [PEA morphology](docs/patch-notes/2026-09-19-pea-morphology.md)
- [Release check corrections](docs/patch-notes/2026-09-19-release-warnings.md)
- [Release drag handle removal](docs/patch-notes/2026-09-19-release-drag-removal.md)
- [Medication push duration input](docs/patch-notes/2026-09-19-push-duration-input.md)
- [Discord posts and patch index](docs/patch-notes/README.md)
