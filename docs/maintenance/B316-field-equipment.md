# B316 field equipment and Tempus

Version 1.2.4.1, network protocol 9. Use one complete B316 build on the server, clients and headless clients.

## Medical menu and placement

- **Medical menu → Advanced** has Tempus Pro and LS setup and screen actions beside the LifePak actions. Pro exposes ECG and temperature on the torso, SpO₂ and NIBP on the right arm, and EtCO₂ on the head. LS exposes ECG monitoring leads and defibrillator pads on the torso. The Pro measures blood pressure when the cuff is attached and the monitor is powered. The LS continues to use its own defibrillation and pacing controls.
- World sensor actions and medical-menu actions make the same checked requests. Leaving the menu open and clicking twice does not toggle a completed attachment back off.
- Default patient-side spots are retained. Deployed monitors, ACCUVAC, connected Ventway and blood coolers face the person placing the equipment. **Rotate towards me** is also available for those props, field mounts when empty, and dropped HPMKs. A mounted monitor or a device that someone is carrying must first be released. A Ventway retains its heading when its oxygen prop changes. Packed or naturally dropped inventory items still use the engine's holder behavior.
- ACCUVAC uses the original upright MLOD in all ten LODs. The keypad supplies its facing axis. The ACE equipment submenu separates Use, Pick Up and Rotate.
- Tempus patient leads and USB use the same black ACE hose class as Megacode Kelly. The client worker limits itself to 16 ropes and retires their local helpers when the connection or device goes away. Check hose anchoring, rendering and local creation in Arma.
- Both transfusion tubing diagrams are defined below the action popover in the native dialog's fixed draw order.

## Training computer

Routine adds ocular irritation and superficial burns. Priority adds right and bilateral structural eye injuries, partial-thickness burns, and localized and systemic infection. Immediate adds extensive full-thickness burns, facial burns with inhalation injury, and sepsis. These use the existing single and bulk spawners and respect the enabled injury systems. The injuries are constructed before the exercise is handed to the trainee.

## Tempus waveform and controls

The native LifePak generator now accepts a local sample context for Tempus. It returns de-duplicated R-wave positions and beat phase with the sample block. The consumer schedules contiguous short blocks with the next beat reserved across block and HR changes. The browser keeps a stable session clock, rejects overlapping or replayed packets, and clears previous traces and LS sync timers on an actual patient/power change. Independent limb and precordial projections use the same beat phase, with separate P, QRS and T gains. They are simulations of ECG leads. The Pro has a full 12-lead display and the LS can display its pads trace and limb leads I–III. LS sync markers only come from eligible organized beats and remain subject to the native pad and charge checks.

The Pro's NIBP request is handled through the operating monitor screen and cuff state. The LS sends changed screen settings back to the equipment instead of continuously postponing its save. Existing device display layouts and their hardware overlays remain in use.

## Native acceptance

1. Open **Bag Actions** and **Infusion Actions** on both a Y set and a piggyback pair. Check every menu edge and verify the exposed tubing remains visible.
2. Set down each device from multiple headings and rotate it from a second client. Verify ACCUVAC feet, ACE action layout, raised-floor seating, and a Ventway oxygen swap. Reconnect to verify heading and cables.
3. Start a Tempus case from the medical menu, exercise connections and NIBP, then change HR at mid-sweep and test sinus, AF, VT, VF, asystole and CPR across the ECG sources. Exercise 12-lead capture, sync arming/markers, shock, pacing, metronome, lead/speed/gain and pair controls. Test power cycling and patient replacement during a sweep. Verify no obsolete trace or sync event crosses that boundary.
4. Spawn each new case solo and through the bulk menu. Check the native symptoms and treatment paths.

Automated checks cannot certify Arma control hit areas, in-game model fit, PhysX ropes, or replication timing. The Linux integration candidate retains MLOD assets. The Windows installer uses normal HEMTT release.
