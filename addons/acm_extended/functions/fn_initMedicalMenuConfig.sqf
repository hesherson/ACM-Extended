/*
 * Phase 22 subsystem initialization: Medical-menu grouping and dropdown presentation configuration.
 *
 * Behavior-preserving extraction from ACME_fnc_postInit. Runtime event/PFH ownership
 * remains outside this helper and the call stays at the original initialization point.
 */

// MENU item state gate. see fn_ventitemgate. the manual colors every menu item with a rule. gray means not
// while ventilating, yellow means confirm first, and red means both plus a technician code.
// nested medical MENU groups.
// the airway category had grown to about 35 actions across ACM's airway module, ACM's breathing module and our
// own, which is more than anyone can scan under pressure. these tables add one level of nesting beneath the
// existing category tabs.
// The collector retains action class IDs and stable bucket keys for the changed routes.
// Display-name lists remain a compatibility fallback for the existing groups.
// Format: [key, label, category, exact fallback names, visibility code, color].
// Group visibility is anatomy-only presentation. It prevents a stale cached dropdown from surviving a body-part
// change (including death transitions) without touching any treatment row, condition, statement or callback.
// Head: Airway, Breathing, Capnography. Body: Chest, Positioning. Medication route groups were already head-only.
ACME_menuGroups = [
    // airway
    ["adjuncts", "Airway", "airway", [
        "Check Airway", "Perform Head Turning", "Perform Head Tilt-Chin Lift",
        "Use Suction Bag", "Use ACCUVAC", "Drain Fluid (ACCUVAC)", "Drain Fluid (Suction Bag)",
        "Insert OPA", "Insert NPA", "Insert i-gel",
        "Remove OPA", "Remove NPA", "Remove i-gel",
        "Intubate (Orotracheal)", "Remove Endotracheal Tube",
        "Establish Surgical Airway", "Stitch Airway Incision"
    ], {ace_medical_gui_selectedBodyPart == 0}, [0.53, 0.53, 0.95, 1]],
    ["ventilation", "Breathing", "airway", [
        "Check Breathing",
        "Use BVM", "Use BVM with Oxygen", "Use BVM with Oxygen (Vehicle)", "Use BVM with Oxygen (Portable)",
        "Apply Non-Rebreather Mask", "Remove Non-Rebreather Mask"
    ], {ace_medical_gui_selectedBodyPart == 0}, [0.19, 0.65, 0.57, 1]],
    ["chest", "Chest", "airway", [
        "Apply Chest Seal", "Perform Needle-Chest-Decompression", "Perform NCD (NAR SPEAR)",
        "Perform Thoracostomy", "Perform Thoracostomy (Kit)", "Adjust Thoracostomy", "Insert Chest Tube",
        "Drain Fluid (ACCUVAC)", "Drain Fluid (Suction Bag)", "Re-Seal Chest Tube",
        "Close Thoracostomy Incision", "Close Incision (Suture)", "Suture Chest Tube"
    ], {ace_medical_gui_selectedBodyPart == 1}, [0.58, 0.24, 0.92, 1]],
    ["position", "Positioning", "airway", [
        "Establish Recovery Position", "Cancel Recovery Position"
    ], {ace_medical_gui_selectedBodyPart == 1}, [0.60, 0.88, 0.64, 1]],
    ["capno", "Capnography", "airway", [
        "Attach EMMA to My BVM", "Remove EMMA from My BVM",
        "Attach EMMA to their i-gel", "Remove EMMA from their i-gel",
        "Attach EMMA to ETT", "Remove EMMA from ETT"
    ], {ace_medical_gui_selectedBodyPart == 0}, [0.95, 0.53, 0.74, 1]],

    // Medication route labels are selected live by fn_updateActions.
    // The class-based collector supplies membership; no clinical behavior is changed.
    ["route_po", "By Mouth", "medication", [], {ace_medical_gui_selectedBodyPart == 0}, [0.60, 0.88, 0.64, 1]],
    ["route_in", "Inhaled", "medication", [], {ace_medical_gui_selectedBodyPart == 0}, [0.19, 0.65, 0.57, 1]],
    ["route_buc", "Buccal", "medication", [], {ace_medical_gui_selectedBodyPart == 0}, [0.95, 0.53, 0.74, 1]],

    // advanced.
    // the AED stays in advanced exactly where it is, in its own group.
    ["aed", "AED", "advanced", [
        "Apply AED Pads", "Remove AED Pads", "View AED Monitor", "Analyze Rhythm",
        "Charge AED", "Administer Shock", "Cancel Charge",
        "Measure Blood Pressure (AED)", "Auto Blood Pressure (AED)",
        "Connect AED Pulse Oximeter", "Disconnect AED Pulse Oximeter",
        "Connect AED Pressure Cuff", "Disconnect AED Pressure Cuff",
        "Connect AED Capnograph", "Disconnect AED Capnograph"
    ], {true}, [0.85, 0.40, 0.18, 1]],
    // debug is hidden outright unless the setting is on. no empty submenu is shown. with the setting
    // off the group header does not render at all, so a normal session never sees it.
    ["debug", "Debug", "advanced", [
        "Inflict Junctional Wound [TEST]",
        "Induce/Clear Peri-Arrest Shock",
        "Induce/Clear Over-Resuscitation (debug)",
        "Induce/Clear Obtunded Back (debug)",
        "Induce/Clear Obtunded Prone (debug)",
        "Obtunded BACK pose only (debug)",
        "Force Shake (debug)",
        "Visual FX: Hypoxia cycle (debug)",
        "Visual FX: Hypotension / shock cycle (debug)",
        "Visual FX: Hypercapnia cycle (debug)",
        "Visual FX: Ketamine / dissociation cycle (debug)",
        "Visual FX: Near-syncope cycle (debug)",
        "Visual FX: Clear debug overrides",
        "Step Hypothermia: mild/mod/severe/clear (debug)",
        "Rhythm: AFib-RVR on/off (debug)",
        "Rhythm: Atrial Fibrillation (controlled) on/off (debug)",
        "Rhythm: Atrial Tachycardia on/off (debug)",
        "Rhythm: Torsades / polymorphic VT on/off (debug)",
        "Rhythm: SVT on/off (debug)",
        "Respirations: Cheyne-Stokes on/off (debug)",
        "Induce Seizure (debug)"
    ], {[] call ACME_fnc_debugEnabled}, [0.92, 0.80, 0.24, 1]]
];
// Examination membership and display order share one class-based definition.
ACME_menuGroups append (([] call ACME_fnc_menuExamineGroups) apply {
    _x params ["_key", "_label", "", "_color"];
    [_key, _label, "examine", [], {true}, _color]
});
// ACME_menuNestEnabled and acme_menushowdebug are CBA settings now, under addon options, ACM extended,
// accessibility. do not assign them here. an assignment would stamp over the player's choice on every mission
// start, which is the sort of bug that looks like the setting not saving.
// dropdown presentation. groups expand in place rather than replacing the list, so nobody has to walk into a
// sub-page and back out to compare two options. the marker shows the state and the indent shows membership.
ACME_menuMarkClosed  = "[ + ]  ";
ACME_menuMarkOpen    = "[ - ]  ";
ACME_menuChildIndent = "        ";
// Cream is the default on both open and closed headers. The existing optional
// per-section palette remains a separate accessibility preference.
ACME_menuHeaderColorDefault = [1, 0.96, 0.84, 1];
ACME_menuRowColorDefault = [1, 1, 1, 1];
ACME_menuRowColorAlternate = [1, 1, 1, 1];
