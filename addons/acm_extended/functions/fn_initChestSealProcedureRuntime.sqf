// chest-seal mini-game tunables. all of them are in getMousePosition space, where x is a fraction of screen
// width and y a fraction of height.
// these shape the rake, find and place feel. the hole spawns at random inside chestregion, and a dot or seal
// counts as on the hole by aspect-corrected distance. expect to tune chestregion and the radii in game once the
// chest image position is on screen, the same as the iv-pose and syringe-dialog coordinate passes.
// the chest-seal mini-game is drag-to-find holes. it is wound-driven, flips front to back, and is 32:9 safe.
ACME_CS_rollTime = 1.85 / (missionNamespace getVariable ["ACME_choreographyAnimSpeed", 1.50]);
ACME_rollProviderDuration = 2.2;
// B54 provider pose freeze rules. Seconds on the native RTM timeline, measured on the owner's clock from the frame
// the requested state is first reported. A mode with no entry plays at native speed until its action ends it.
// ACME_poseStopAfterHold is how long the frozen frame is held before the controller starts the exit blend itself;
// modes without an entry stay frozen until their own action or minigame ends the episode.
ACME_poseHoldAt = createHashMapFromArray [
    ["roll", 2.2],         // Patient Flip and every ACM/ACME front-back roll: AinvPknlMstpSnonWnonDnon_medic4 to 2.2 s.
    ["chestAccess", 2.2],  // Carrier lift/removal/restoration: same medic4 frame, held until the casualty is back down.
    ["inspect", 2.2],      // Inspect Chest: the same medic4 motion, frozen at 2.2 s until the inspection ends.
    ["pulse", 0.421],      // Check Pulse: same ACME_StethoscopeWork hold as auscultation.
    ["stethoscope", 0.421] // Auscultation: ACME_StethoscopeWork to the authored 0.421 s sample.
];
ACME_poseStopAfterHold = createHashMapFromArray [
    ["roll", 0.25]         // Hold the 2.2 s frame briefly, then blend back to the unarmed crouch.
];
// B57 medical-menu provider stance. Opening the menu uses only empty hands plus the normal BI transition into
// crouch. No medic-over-patient state is held, which keeps root motion and the player's head/camera free.
ACME_menuPoseEnabled = true;
// B56 upright patients: candidate standing medicUp states per pose mode, used only when the patient is standing
// or crouching, conscious and on foot, and only if the state exists on this machine (fn_poseUprightState). Names
// follow the BI pattern of the kneeling states; correct any entry here without a build.
ACME_poseUprightStates = createHashMapFromArray [
    ["torsoBandage", "AinvPercMstpSnonWrflDnon_medicUp4"],
    ["headBandageLeft", "AinvPercMstpSnonWrflDnon_medicUp0"],
    ["headBandageRight", "AinvPercMstpSnonWrflDnon_medicUp2"],
    ["directPressureAction", "AinvPercMstpSnonWrflDnon_medicUp5"],
    ["chestSeal", "AinvPercMstpSnonWnonDnon_medicUp3"],
    ["ncdSeat", "AinvPercMstpSnonWrflDnon_medicUp1"],
    ["pulse", "AinvPercMstpSnonWrflDnon_medicUp1"],
    ["inspect", "AinvPercMstpSnonWnonDnon_medicUp4"],
    ["response", "AinvPercMstpSnonWrflDnon_medicUp3"],
    ["airway", "AinvPercMstpSnonWrflDnon_medicUp4"]
];
// the searchable thorax band, as a fraction of the body rect [x,y,w,h]. it sits above the diaphragm and over
// the lung fields, not the abdomen. nudge it if holes land off the chest on your body image.
ACME_CS_thoraxZoneFrac = [0.395, 0.205, 0.21, 0.18];
// hole centers are generated inside this inner ellipse, [centerx, centery, radiusx, radiusy]. the ellipse is
// inset far enough that a full chest-seal sprite, at 5 percent of the body, stays on the thorax.
ACME_CS_holeField = [0.5, 0.29, 0.08, 0.06];
// wound placement bias, from plate-carrier physics. the ceramic plate covers the center of the chest and stops
// most rounds, so wounds must not cluster there. a round that gets through passes under the plate, at the
// bottom of the field, which is the most common case, or clips the top-left or top-right corners beside it.
// holes are pushed toward the field edge, away from the plated center, and kept spaced so seals cannot stack on
// one another.
ACME_CS_zoneBottomWeight = 0.55;  // share of wounds below the plate, at the bottom of the blue area. this is the majority.
ACME_CS_zoneTopWeight    = 0.45;  // share split across the two upper corners, top-left and top-right, where a round missed the plate.
ACME_CS_edgeBias         = 0.60;  // minimum radial fraction, 0 to 1. wounds hug the rim, which leaves the plated center clear.
ACME_CS_minHoleSep       = 0.052;  // B69: seal-safe per-axis center clearance; seal art is ~0.05 x 0.05 body UV.
// do not invent routine holes for an uninjured chest. a single compatibility hole is created only when ACM
// already reports an active pneumo or hemo and the original wound record is unavailable. an example is a state
// injected by zeus, or a casualty created before this extension began to track ACM chest-injury events.
ACME_CS_minHoles = 0;
// the set of wounds. this holds which ACE wound types are penetrating, and can punch a through-and-through
// chest hole, and the chance each one also blows an exit wound out the back. an entry hole goes on the front
// and an exit on the back, so not every entry has an exit. it is read off this table, and you can add or adjust
// types freely.
ACME_CS_woundTable = createHashMapFromArray [
    ["VelocityWound", [true, 0.55]],  // gsw / high-velocity fragment: penetrating, frequently exits
    ["PunctureWound", [true, 0.20]],  // stab / spike: penetrating, sometimes exits
    ["Avulsion",      [false, 0]],  // tissue torn away. open but not a sealed pneumothorax tract
    ["Laceration",    [false, 0]],
    ["Cut",           [false, 0]],
    ["Crush",         [false, 0]],
    ["Contusion",     [false, 0]],
    ["Abrasion",      [false, 0]],
    ["ThermalBurn",   [false, 0]]
];
// penetrating chest wounds come from ACM's own chestinjury_chances map. ACM uses the same eligible-wound set
// before it rolls whether the resulting chest injury becomes a pneumothorax or a hemothorax. every qualifying
// chest wound creates a front entry hole. the exit chance is severity-scaled from ACM's own chance curve.
ACME_CS_exitFactor   = 0.6;
// chest-seal rake geometry and sensitivity.
// the find radius is measured against the visible hole size on purpose. keep it tight, so the rake has to pass
// directly over the wound instead of sweeping the whole chest from the center.
ACME_CS_findRadius   = 0.0075;
ACME_CS_applyRadius  = 0.062;
ACME_CS_dragMaxSpeed = 0.30;
ACME_CS_dragBaseRate = 0.55;
ACME_CS_dragGainRate = 1.05;
ACME_CS_dragMaxRate  = 1.30;
ACME_CS_dragLagDenom = 0.36;
ACME_CS_toolColumnYOffset = 0.065;
ACME_CS_fingerColorDecay = 0.28;
// preserve the later anatomical limit without a change to the wound extraction and generation path.
ACME_CS_maxHolesPerSide = 4;
ACME_CS_applySfxCooldown = 2.2;

// restore the original tracking hook. hole generation still reconciles directly from ACE's torso open-wound
// map whenever the dialog opens, which was the working compatibility path.
["ACM_breathing_handleChestInjury", {_this call ACME_fnc_chestSealTrackWound}] call CBA_fnc_addEventHandler;
