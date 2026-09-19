# ACM Extended patch notes

## 1.2.2 cumulative update

Updated 19 September 2026. Version 1.2.2 incorporates the complete 1.2.1-rc1 patch series and aligns the release metadata. Consolidates all subsequent patches from 18–19 September, through [8fd12c0](https://github.com/hesherson/ACM-Extended/commit/8fd12c016f17504b05781925f095d75f0fbe9424). The [covered commit range](https://github.com/hesherson/ACM-Extended/compare/f2b6c482123aff1a60234e4d2b737e44de33767c...8fd12c016f17504b05781925f095d75f0fbe9424) includes 132 commits. The release check corrections below are also included.

These notes describe the combined current behavior. Later corrections take precedence over intermediate implementations in the individual patch records.

### Build, debug and settings

- Fixed two drag handle condition errors that could interrupt attachment and release checks.
- Fixed a missing UI scaling definition when changing syringe size in the Narc Box.
- Fixed the duplicate ACE_Actions declaration and invalid inheritance that stopped HEMTT with L-C03/L-C04. Drag handle actions now share the existing patient action tree, preserving Get Up and release actions.
- Updated the public/runtime version and debug overlay to 1.2.2. HEMTT and native addon metadata now use 1.2.2.0.
- Separated shared gameplay settings from client preferences. Gameplay rules remain globally controlled; presentation, accessibility, interface and debug preferences are controlled by each client and cannot be overridden by the server or mission.

### Medication pushes and IV tray

- Reworked the Seconds to Push field with an explicitly editable control and click focus. Carousel shortcuts and click areas now leave the field available for typing.
- Moved the gray recommended time onto a separate label so it cannot replace entered digits. Correcting an invalid duration now updates the Push button while typing. The duration row still follows the Push button layout.
- A blank seconds field defaults to a push lasting 3 seconds in both normal and Hardcore medication modes. Gray suggested times are guidance; entering a duration selects that duration, within 1–300 seconds.
- Restored continuous syringe plunger movement during Hardcore pushes, following the actual remaining medication volume.
- Corrected the IV tray catheter fan's visual anchoring.

### Transfusions and access selection

- Removed the separate Hardcore Transfusion setting. Bag preparation, Y lines, flushing, infusion and access site management are now the standard workflow.
- Removed the 250 mL saline bag minimum. Y lines still require compatible saline and retain the configured flush volume rule.
- Retained the standard calcium/citrate and hypothermic coagulation values. Old exported Hardcore Transfusion values no longer select an alternate model.
- Fixed IV/IO access selection so clicking a site updates the selected access, top left name, artwork and bag lists together.
- Added the normal button sound to access site clicks and removed the top left IV/IO toggle. The inventory source switch remains available.

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

### Drag handle and patient positioning

- Added hip interactions and a medical Drag/Carry row for attaching and releasing the drag handle, with eligibility checked again by the patient owner.
- Replaced the drawn thin line with a native rope using ACE fast roping helper endpoints. ACE fast roping is now an explicit addon dependency.
- Changed dragging to use native ragdoll forces and removed the reset to a prone animation that snapped unconscious patients into a new position.
- Stopped unconscious pose and training manikin handlers from pinning an actively dragged casualty. Settled bodies are awakened for physics impulses, with consistent force scaling across frame rates.
- Added bounded startup grace for brief tether stretches. Sustained overextension, teleports and conflicting procedures still release the handle.
- Retained weight, fatigue and movement limits. The drag speed cap cannot accelerate a provider who is already slowed or overwrite a zero movement coefficient.
- Hardened cleanup for release, wake/full heal, deleted patients, vehicle entry and ownership changes. Delayed start/stop acknowledgements are tied to the current session; restoration of head elevation waits for transport or conflicting procedures to finish.
- Semi-Fowler's is unavailable for standing or crouching patients, including when an old lying flag remains. Eligibility is checked in the menu and again before positioning.

### Finger thoracostomy and chest seals

- Added removal and burping of a seal over a finger thoracostomy tract. After removing the seal, the existing tract can be swept again without consuming another kit, then used for a chest tube.
- In Adjust Thoracostomy, put down the held tool. Right click the surgical seal to remove it; scroll five notches to lift and burp a corner, and reverse the wheel to lay it flat. Select the finger and click the open tract to repeat the sweep.
- Traumatic and surgical chest seal burps share a cooldown of 10 seconds per patient, including between providers. Rejected repeats do not repeat the treatment, activity log entry or animation. The lifted corner can still be laid flat during cooldown.
- Accepted burps request the corresponding chest seal treatment animation on the provider.
- Chest seal Flip waits for the actual provider roll animation before physically rolling the patient. Entry transitions no longer trigger the flip; closing, cancelling or timing out the panel cancels a pending roll.
- Aftercare acts on the selected side and preserves unrelated seals and a chest tube on the opposite side.
- Current gameplay behavior: an open finger tract vents air, while sealing it can allow pressure to recur if an internal leak remains. No penalty is added for time spent open, and the tract does not close spontaneously. Continuous passive blood drainage belongs to chest tubes; inadequate preparation can flag the incision for infection.

### Auscultation controls, sound and posterior view

- The bell opens at the cursor and is 19% larger. Hold left mouse to listen and move it with drag resistance; it shrinks by 12% while pressed. Releasing lifts it and stops contact sound.
- Left lung, right lung and cardiac sounds mix continuously as the bell moves, without restarting their phase at each listening point.
- Reduced all 21 stethoscope sound variants by another 6 dB, including cardiac, normal, shallow, dull and crackling sounds.
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

The supplied Windows release log confirms successful packaging of 14 PBOs for 1.2.2.0, with 28 UI scaling warnings and five drag condition warnings. Both causes are now corrected. HEMTT 1.21.0 strict checks passed across 16 addon configs, 1,591 SQF files and 12 stringtables with no code diagnostics, and all 16 focused tests passed. Rebuild the release package after pulling these corrections. Confirmation in Arma remains necessary for seizure startup and speed, ragdoll dragging, chest animations, transfusion selection, audible auscultation mixing and PEA transitions, including patients owned by another machine.

The version update changes release metadata and documentation; the cumulative gameplay changes are listed above.

The medication duration followup passed 36 focused checks on this branch, including strict HEMTT diagnostics, complete config compilation and SQF execution of the duration readers and input filtering. Mouse focus and actual keyboard entry still require verification in Arma. See the detailed input patch record below.

### Detailed patch records

- [Transfusion and thoracostomy](docs/patch-notes/2026-09-19-transfusion-thoracostomy.md)
- [Patient motion and ketamine](docs/patch-notes/2026-09-19-patient-motion.md)
- [Chest interactions, drag rope and held auscultation](docs/patch-notes/2026-09-19-chest-interactions.md)
- [Final seizure speed correction, posterior auscultation and clinical descriptors](docs/patch-notes/2026-09-19-auscultation-seizures.md)
- [PEA morphology](docs/patch-notes/2026-09-19-pea-morphology.md)
- [Release check corrections](docs/patch-notes/2026-09-19-release-warnings.md)
- [Medication push duration input](docs/patch-notes/2026-09-19-push-duration-input.md)
- [Discord posts and patch index](docs/patch-notes/README.md)
