# ACM Extended patch notes

## 1.2.3

Updated 24 September 2026.

### CPR / BVM chest access

- CPR and all BVM variants now use the same plate-carrier chest-access preflight.
- Plate-carrier custody remains active while either CPR or BVM is active, including repeated middle-mouse swaps between the two interventions.
- CPR -> BVM and BVM -> CPR handoffs use a bounded provider-local transfer token so the carrier cannot be restored during the transition gap. If the replacement maneuver fails to start, normal restoration resumes automatically.
- Patient-owner restoration also refuses to put the carrier back while live CPR or BVM is present, providing a second guard against stale provider cleanup.
- Carrier-off choreography now uses dedicated faster chest-access timing: 0.70 s lift, 0.04 s top hold and 0.78 s lower. These values do not change Semi-Fowler/head-elevation timing.
- Removed the extra synthetic settle delay after carrier removal/lowering. The queued intervention may launch on the first readiness frame, before the medic4 provider pose reaches its 2.2 s frozen hold.

### Version identity

- Public/debug version advanced to 1.2.3.
- HEMTT package version advanced to 1.2.3.0.
- Internal build batch advanced to B144 and the release-candidate debug revision reset to rc1.

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
- Starting BVM fully releases that provider's Direct Pressure, including its worker, keys and pressure marker. Rejected BVM starts preserve pressure. Start pressure again after finishing BVM.
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
