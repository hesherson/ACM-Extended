// the CBA addon options registration, at preinit.
// the rule: every setting name below must match the missionnamespace variable the runtime code reads, because the
// functions use missionnamespace getvariable [name, def] with the same default. CBA writes the value of the user
// into missionnamespace under the setting name, so matching names means zero glue code.
// the rule: fn_postInit.sqf must never assign these variables. postinit runs after preinit, so any assignment
// there silently stomps the choice of the user. that was an early bug: six settings registered here, all
// overwritten.

// multiple top-level addon options listings, so the settings are not dumped into one giant category.
private _cSys  = "ACM Extended: Systems";  // the control panel: the per-system enable and hardcore.
private _cIV   = "ACM Extended: Infusion & IV";  // the infusion flow, roller clamp, iv line and hang bag.
private _cCirc = "ACM Extended: Circulation";  // shock, push-dose, ICH, auto bp and access.
private _cTBI  = "ACM Extended: Neuro & TBI";  // the TBI model tuning.
private _cTrau = "ACM Extended: Trauma";  // the chest seal, junctional, direct pressure, NRB and obtundation.
private _cDbg  = "ACM Extended: Debug";  // the debug overlay.
private _cVent = "ACM Extended: Ventilator";
private _cAir  = "ACM Extended: Airway";


// Keep ACME's patient-state dump next to ACE's own pause-menu diagnostics. This is intentionally client-only.
if (hasInterface) then {
    [["ACME DEBUG TO CLIPBOARD", "Copies the current ACME/ACM patient state, physiology, and raw medical variables to the clipboard and RPT."], "ACME_MainMenuHelperDumpDebug"] call CBA_fnc_addPauseMenuOption;
};

private _settings = [
    ["ACME_ptx_stableSec", "SLIDER",
        ["Pneumothorax stability interval", "Seconds of controlled air accumulation before the internal model records stability. Does not display a provider notification."],
        [_cTrau, "Pneumothorax"], [0, 300, 60, 0], 1, {}],
    ["ACME_ptx_leakSettleSec", "SLIDER",
        ["Pneumothorax leak settling time", "Simulation time scale for internal air leaks to settle. Larger values prolong leakage. Open chest wounds and actual drainage remain consequential."],
        [_cTrau, "Pneumothorax"], [120, 1800, 600, 0], 1, {}],
    ["ACME_vent_simpleMode", "CHECKBOX",
        ["Simple Ventilator Mode", "Use the selected breathing rate with automatic supporting settings. Lung and airway problems, circulation, power and circuit failures still affect the patient. Advanced settings are retained for when this mode is disabled."],
        [_cVent, "Mode"], false, 1, {}],
    // systems: enable and disable, plus hardcore.
    // hardcore descriptors. it uses precise anatomical and clinical wording in the assessment text instead of
    // plain-language terms, and appends findings, such as chest-seal counts and NCD laterality, that a trained
    // provider would note.
    ["ACME_hc_descriptors", "CHECKBOX",
        ["[HARDCORE] Clinical Descriptors", "Report findings the way a clinician would, not in generic game terms. Anatomical IV and IO site names (Basilic, AC Fossa, Cephalic, Great Saphenous, Popliteal, Dorsal Arch, External Jugular, Humeral Head, Tibial Tuberosity, Sternal FAST1) instead of Upper/Middle/Lower. Precise wound terminology: Axillary and Inguinal rather than junctional. Chest seal counts and Unilateral or Bilateral NCD on chest inspection. Personal wording preference. Cannot be forced by the mission or server. Takes effect on the next assessment; existing log entries retain their recorded wording."],
        [_cSys, "Hardcore"], false, 2, {}],
    // the per-system enable. off means that system is fully inert.
    // Core physiological workers remain active. Procedure access controls below gate new starts.
    // the ventilator, BVM, oxygen delivery, capnography, paralytics, IV placement anatomy, cardiac rhythms,
    // shock and push-dose, NRB oxygen, automatic blood pressure, the syringe kit and HPMK rewarming were all
    // switchable here as whole systems and are not any more. Each worker is load bearing: another system calls into it, an
    // action in the medical menu depends on it, or a casualty already carrying its state is left with no way to
    // resolve that state once it is switched off. a mission that turns one off does not get a simpler mod, it
    // gets a broken one, and the report that follows costs more than the setting was ever worth.
    // every read site takes a default of true, so removing the setting leaves the system permanently on. that
    // was checked at every call site before these were removed. New procedure switches below do not disable
    // these workers or strand existing equipment; runtime actions enforce the separate access policy.
    // what is left in this list is genuinely optional: a mission can run without it and nothing else notices.
    ["ACME_sys_junc",      "CHECKBOX", ["Junctional Wounds", "Junctional hemorrhage + Combat-Gauze/pressure chain. OFF: junctional wounds are neither inflicted nor bled. Takes effect immediately."], [_cSys, "Systems"], true, 1, {}],
    ["ACME_sys_dp",        "CHECKBOX", ["Direct Pressure", "Hold-pressure hemorrhage control. OFF: direct pressure cannot be started, and any hold in progress is released. Takes effect immediately."], [_cSys, "Systems"], true, 1, {}],
    ["ACME_sys_chestSeal", "CHECKBOX", ["Chest Seal Mini-game", "Drag-to-find seal placement. Off = ACM's instant seal. OFF: the mini-game cannot be opened and seals are handled without it. Takes effect immediately."], [_cSys, "Systems"], true, 1, {}],
    ["ACME_sys_hang",      "CHECKBOX", ["Hang Bag", "Raise an IV/blood bag for gravity-assisted flow. OFF: the bag cannot be raised, and a bag being held is lowered. Takes effect immediately."], [_cSys, "Systems"], true, 1, {}],
    ["ACME_sys_tbi",       "CHECKBOX", ["TBI model", "ICP / herniation / osmotherapy. OFF: no TBI or ICP is tracked or applied. Takes effect immediately."], [_cSys, "Systems"], true, 1, {}],
    // the per-system hardcore: harsher pathology with less margin.
    ["ACME_hc_junc",     "CHECKBOX", ["[HARDCORE] Junctional Wounds", "Faster, heavier bleed; pressure controls less. Takes effect immediately."], [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_dp",       "CHECKBOX", ["[HARDCORE] Direct Pressure", "Longer hold to clot; less control while held. Takes effect immediately."], [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_chestSeal","CHECKBOX", ["[HARDCORE] Chest Seal Mini-game", "More holes, smaller find radius, exits more likely. Takes effect immediately; seals already placed keep their current hole count."], [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_hpmk",     "CHECKBOX", ["[HARDCORE] Rewarming", "Slower rewarming; hypothermia bites harder. Takes effect immediately."], [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_tbi",      "CHECKBOX", ["[HARDCORE] TBI", "Shorter compensation, faster herniation, tighter osmo ceiling. Takes effect immediately; a casualty already carrying a TBI keeps the severity they were given."], [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_circ",     "CHECKBOX", ["[HARDCORE] Shock", "Lower shock floor, shorter push-dose, more distal surges. Takes effect immediately."], [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_medications", "CHECKBOX", ["[HARDCORE] Medications", "Enable rate-sensitive IV/IO syringe pushes, resumable one-handed pushes, and rapid-administration consequences. Closing or reopening medical menus does not interrupt an active push."], [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],


    // These existing modes had no individual setting before the master switch was removed.
    ["ACME_hc_rhythm", "CHECKBOX",
        ["[HARDCORE] Cardiac Rhythms", "During cardiac arrest, require Extended's reversible-cause conditions for ROSC. Native circulation checks still apply. Takes effect immediately."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_nrb", "CHECKBOX",
        ["[HARDCORE] NRB Oxygen", "Allow mask placement without an oxygen-source warning. A mask without supplied oxygen provides no oxygen support. Sets the existing hardcore oxygen demand to 25 L/min. Takes effect immediately."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_blastLung", "CHECKBOX",
        ["[HARDCORE] Blast Lung / ARDS", "Use the existing lower severity threshold and shorter exposure time for progression to ARDS. Requires the blast-lung system to be enabled. Takes effect immediately."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_vent", "CHECKBOX",
        ["[HARDCORE] Ventilation", "Enable the existing ventilator-induced lung-injury model for excessive tidal volumes. Disabling this stops additional injury from this mode; it does not heal injury already present. Takes effect immediately."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_burns", "CHECKBOX",
        ["[HARDCORE] Major Burns", "Major burns can leave a residual field-unresolved systemic burden after the acute capillary-leak and heat-loss phase. The casualty can be stabilized but requires evacuation/definitive care. OFF: systemic burn physiology is game-reversible; burn wounds and infection risk still remain."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_infection", "CHECKBOX",
        ["[HARDCORE] Infection / Sepsis", "Prolonged septic shock can leave residual organ dysfunction and an evacuation requirement even after antibiotics control the infection. OFF: infection and sepsis can fully regress in the field on the game-compressed timeline."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_ophthalmology", "CHECKBOX",
        ["[HARDCORE] Ocular Trauma", "Structural ocular trauma becomes a stabilization-and-evacuation problem. Eye shields protect the injury but do not field-heal it. OFF: structural ocular injury recovers on a game-compressed timeline; dust and irritant injury remain eyewash-reversible in either mode."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],

    // infusion, which is global because it affects the flow math.
    [
        "ACME_infusion_defaultDropSet", "LIST",
        ["Default drop set (gtt/mL)", "Drip chamber used when a bag has no explicit drop set. 10/15 = macro, 20 = standard, 60 = micro."],
        [_cIV, "Flow & drip"],
        [[10, 15, 20, 60], ["10", "15", "20", "60 (micro)"], 2], 1, {}
    ],
    [
        "ACME_infusion_maxDropsPerMinute", "SLIDER",
        ["Max drip rate (gtt/min)", "Flow at a fully open roller clamp. Drip rates snap to 5 gtt/min increments below this."],
        [_cIV, "Flow & drip"],
        [60, 300, 120, 0], 1, {}
    ],
    [
        "ACME_infusion_clampCurve", "SLIDER",
        ["Clamp response curve", "Exponent mapping wheel position to flow. Higher = finer control near closed, steeper near open. 1 = linear."],
        [_cIV, "Flow & drip"],
        [1, 4, 2, 1], 1, {}
    ],

    // IV mini-game settings are explicitly split by authority. Pure presentation/accessibility choices are
    // CBA local-only (2), so a server can never overwrite them. Anything that changes the actual procedural
    // success threshold or shared vein geometry is global-only (1), so every provider sees the same gameplay
    // rules even when the mission maker never configured CBA overrides.
    [
        "ACME_iv_uiScaleV3", "SLIDER",
        ["IV panel: panel size", "1.0 is now the former 1.10 panel size. Minimum preserves the previous absolute minimum; maximum remains 50% larger than the new default. Use Up/Down arrows to pan an enlarged limb. Targets and placed items scale together; tray controls remain on screen. Takes effect the next time the panel opens."],
        [_cIV, "Mini-game panel"],
        [0.6486486486, 1.5, 1, 2], 2, {}
    ],
    [
        "ACME_iv_trayIconBias", "SLIDER",
        ["IV panel: tray icon height", "Moves the catheter toward the top (0) or bottom (1) of its tray box. Position is bounded to keep the full upward stock fan inside the box."],
        [_cIV, "Mini-game panel"],
        [0, 1, 0.66, 2], 2, {}
    ],
    [
        "ACME_iv_bruiseMaxAlpha", "SLIDER",
        ["IV panel: bruise maximum opacity", "A miss bruise never gets more opaque than this. At full opacity it reads as a solid blob stuck on the skin and buries the puncture hole drawn on top of it."],
        [_cIV, "Mini-game panel"],
        [0.2, 1, 0.9, 2], 2, {}
    ],
    [
        "ACME_iv_bruiseBoost14", "SLIDER",
        ["IV panel: 14g bruise size", "Widens the 14g bruise before it is clamped to fit the limb. The stock radii sit close enough together that a narrow site flattened all three gauges to the same visible size."],
        [_cIV, "Mini-game panel"],
        [1, 2.5, 1.45, 2], 2, {}
    ],
    [
        "ACME_iv_prepMarksToClean", "SLIDER",
        ["IV panel: scrub coverage to prep", "How many scrub marks the alcohol pad must lay before the site counts as prepped. A mark is only laid once the cursor has MOVED, so this cannot be satisfied by holding still."],
        [_cIV, "Mini-game panel"],
        [4, 40, 16, 0], 1, {}
    ],

    // palpation. how the fingertip reports what is under it, and how the veins of the antecubital fossa are
    // arranged for a given casualty.
    [
        "ACME_iv_palpModel", "LIST",
        ["IV panel: palpation feel", "How the palpating finger reports a vein. Classic is the old proximity ramp, kept for comparison. Ridge gives a small green core with a hard taper. Pulse breathes at the casualty's own heart rate, deeper on a better vein. Edge brightens at the walls of the vessel and softens dead center."],
        [_cIV, "Palpation"],
        [[0, 1, 2, 3], ["Classic (old behavior)", "Ridge", "Pulse", "Edge"], 1], 2, {}
    ],
    [
        "ACME_iv_phenotypeForce", "LIST",
        ["Venous phenotype (singleplayer only)", "Forces the antecubital vein arrangement for testing. Auto derives it from the Steam UID in multiplayer, exactly as ACM derives blood type, so a player's veins are the same every session. IGNORED in multiplayer, where the UID is the authority."],
        [_cIV, "Palpation"],
        [[0, 1, 2, 3, 4], ["Auto (UID)", "N pattern", "M pattern", "No communicator", "One side dominant"], 0], 2, {}
    ],
    [
        "ACME_iv_dotSize", "SLIDER",
        ["IV panel: palpation dot size", "Base size of the palpating fingertip. The palpation models shrink it further as it closes, so a bigger base makes the four modes easier to tell apart."],
        [_cIV, "Palpation"],
        [0.010, 0.045, 0.024, 3], 2, {}
    ],
    [
        "ACME_iv_prepDabAlpha", "SLIDER",
        ["Alcohol redness opacity", "Uniform redness strength across prepared skin. Wipe speed and repeated passes do not create random dark patches."],
        [_cIV, "Palpation"],
        [0.01, 0.20, 0.085, 3], 2, {}
    ],
    [
        "ACME_iv_prepDabSize", "SLIDER",
        ["Alcohol pad footprint", "Width of the smooth-edged, consistent prep footprint as a fraction of the limb canvas."],
        [_cIV, "Palpation"],
        [0.015, 0.080, 0.032, 3], 2, {}
    ],
    [
        "ACME_iv_prepHoldSec", "SLIDER",
        ["IV panel: antiseptic hold time", "Seconds the scrub marks stay at full strength before they begin to fade."],
        [_cIV, "Palpation"],
        [5, 180, 45, 0], 2, {}
    ],
    [
        "ACME_iv_prepFadeSec", "SLIDER",
        ["IV panel: antiseptic fade time", "Seconds the scrub marks take to fade away once the hold time has passed."],
        [_cIV, "Palpation"],
        [5, 180, 40, 0], 2, {}
    ],
    [
        "ACME_iv_fossaSpread", "SLIDER",
        ["IV panel: fossa vein spread", "How far apart the cephalic and basilic sit either side of the antecubital midline, in body fractions. Larger makes the three fossa veins easier to tell apart by feel."],
        [_cIV, "Palpation"],
        [0.015, 0.06, 0.03, 3], 1, {}
    ],

    // the roller clamp, which is client-side because it is pure ux.
    [
        "ACME_infusion_clampScrollStep", "SLIDER",
        ["Scroll step", "Clamp travel per mouse-wheel notch (fraction of full travel)."],
        [_cIV, "Roller clamp"],
        [0.01, 0.25, 0.10, 2], 2, {}
    ],
    [
        "ACME_infusion_clampScrollInvert", "CHECKBOX",
        ["Invert scroll direction", "Flip which way the wheel moves on scroll."],
        [_cIV, "Roller clamp"],
        false, 2, {}
    ],
    [
        "ACME_infusion_clampSfxEnabled", "CHECKBOX",
        ["Clamp sounds", "Play the roller-clamp tick while adjusting."],
        [_cIV, "Roller clamp"],
        true, 2, {}
    ],

    // auto bp, which is global.
    [
        "ACME_autoBP_interval", "SLIDER",
        ["Auto BP interval (s)", "Seconds between automatic AED cuff cycles while Auto BP is active."],
        [_cCirc, "Auto BP"],
        [60, 900, 120, 0], 1, {}
    ],

    // TBI tuning, which is global.
    [
        "ACME_tbi_applyVitals", "CHECKBOX",
        ["TBI affects vitals", "Let TBI write Cushing/terminal patterns onto ACM heart rate. Off = isolate the model."],
        [_cTBI, "Tuning"],
        true, 1, {}
    ],
    [
        "ACME_tbi_cppTarget", "SLIDER",
        ["CPP target floor (mmHg)", "CPP below which TBI severity worsens. Default 60 = the 60-70 target band is safe; below 60 accrues secondary injury."],
        [_cTBI, "Tuning"],
        [40, 100, 60, 0], 1, {}
    ],
    [
        "ACME_tbi_volumeAdequateFloor", "SLIDER",
        ["Volume-adequate floor (L)", "Blood volume at/above which a pressor does real work. Below this, blood comes first."],
        [_cTBI, "Tuning"],
        [3, 6, 5.1, 1], 1, {}
    ],
    [
        "ACME_tbi_cushingICP", "SLIDER",
        ["Cushing ICP (mmHg)", "ICP at which the Cushing reflex tell (hypertension + bradycardia) appears."],
        [_cTBI, "Tuning"],
        [15, 40, 25, 0], 1, {}
    ],
    [
        "ACME_tbi_herniationICP", "SLIDER",
        ["Herniation ICP (mmHg)", "ICP that arms the herniation cascade."],
        [_cTBI, "Tuning"],
        [15, 60, 30, 0], 1, {}
    ],
    [
        "ACME_tbi_herniationStageSeconds", "SLIDER",
        ["Herniation stage length (s)", "Seconds per herniation stage once the cascade is armed."],
        [_cTBI, "Tuning"],
        [60, 600, 240, 0], 1, {}
    ],
    [
        "ACME_tbi_hypoxiaThreshold", "SLIDER",
        ["Hypoxia threshold (SpO2 %)", "SpO2 below which hypoxic secondary insult accrues."],
        [_cTBI, "Tuning"],
        [80, 95, 90, 0], 1, {}
    ],
    [
        "ACME_tbi_pressorMAPcap", "SLIDER",
        ["Pressor MAP cap (mmHg)", "Maximum MAP a pressor infusion may add on top of native pressure."],
        [_cTBI, "Tuning"],
        [10, 40, 25, 0], 1, {}
    ],
    [
        "ACME_tbi_pressorMAPperMcgMin", "SLIDER",
        ["Pressor response (mmHg per mcg/min)", "MAP support per mcg/min of norepi/epi before the cap. Higher = more potent pressor."],
        [_cTBI, "Tuning"],
        [0.1, 2.0, 0.9, 1], 1, {}
    ],
    [
        "ACME_tbi_sodiumCeiling", "SLIDER",
        ["Sodium ceiling (mEq/L)", "Serum Na+ at/above which osmotherapy stops lowering ICP. Hard stop on 'osmo your way out'."],
        [_cTBI, "Tuning"],
        [150, 170, 160, 0], 1, {}
    ],

    [
        "ACME_infusion_dirtyEpiMargin", "SLIDER",
        ["Dirty epi margin (+/-)", "Per-tick delivered-dose jitter for improvised 1 mg/1 L epi drips. 0 = perfectly accurate."],
        [_cIV, "Flow & drip"],
        [0, 0.5, 0.25, 2], 1, {}
    ],

    // circulation, shock and push-dose epi, which are global.
    [
        "ACME_circ_shockFloorMAP", "SLIDER",
        ["Peri-arrest shock floor MAP", "MAP the patient is driven to at full shock severity. Below ACM's MAP<55 arrest line, so an unsupported patient crashes. Pressors/push-dose lift the effective MAP back up; fluids don't (fluid-refractory)."],
        [_cCirc, "Shock & pressors"],
        [25, 55, 38, 0], 1, {}
    ],
    [
        "ACME_circ_pushDoseMAPperMcg", "SLIDER",
        ["Push-dose response (mmHg per mcg)", "Transient MAP bump per mcg of push-dose epi pushed."],
        [_cCirc, "Shock & pressors"],
        [0.5, 3.0, 1.4, 1], 1, {}
    ],
    [
        "ACME_circ_pushDoseHalfLife", "SLIDER",
        ["Push-dose half-life (s)", "How fast push-dose epi support decays. Push-dose epi is gone in minutes by design."],
        [_cCirc, "Shock & pressors"],
        [30, 300, 120, 0], 1, {}
    ],
    [
        "ACME_circ_ichMAPThreshold", "SLIDER",
        ["ICH overshoot MAP (mmHg)", "MAP above which epi-driven overshoot accrues intracranial hemorrhage risk (worse on a TBI brain)."],
        [_cCirc, "Shock & pressors"],
        [110, 160, 130, 0], 1, {}
    ],
    [
        "ACME_circ_distalPressorHazardPerMin", "SLIDER",
        ["Distal pressor surge chance / min", "Per-minute chance a vasopressor running through a MID/LOWER arm or leg IV throws a severe hypertensive surge."],
        [_cCirc, "Shock & pressors"],
        [0, 1, 0.6, 2], 1, {}
    ],
    [
        "ACME_circ_hyperSpikeMAP", "SLIDER",
        ["Hypertensive surge size (mmHg)", "MAP spike from a distal-peripheral drip/pressor surge. Feeds ICH like any overshoot."],
        [_cCirc, "Shock & pressors"],
        [25, 90, 55, 0], 1, {}
    ],
    [
        "ACME_iv18gFlowFactor", "SLIDER",
        ["18G flow (fraction of 16G)", "18G is smaller-bore than 16G, so it flows slower. 0.55 ~ real-world ratio."],
        [_cCirc, "Shock & pressors"],
        [0.3, 1, 0.55, 2], 1, {}
    ],
    [
        "ACME_iv20gFlowFactor", "SLIDER",
        ["20G flow (fraction of 16G)", "20G is the smallest bore on the tray and the slowest line. 0.35 ~ real-world ratio."],
        [_cCirc, "Shock & pressors"],
        [0.2, 1, 0.35, 2], 1, {}
    ],

    // debug, which is client-side.
    [
        "ACME_debug_enabled", "CHECKBOX",
        ["Debug menu", "Show the transparent clinical, treatment and network diagnostics in one overlay."],
        [_cDbg, "Overlay"],
        false, 2, {
            missionNamespace setVariable ["ACME_debug_enabled", _this, false];
            uiNamespace setVariable ["ACME_debug_enabled", _this];
            ACME_debug_enabled = _this;
            if (!isNil "ACME_debug_registerWatchdog") then {call ACME_debug_registerWatchdog};
            if (!isNil "ACME_fnc_debugMenu") then {call ACME_fnc_debugMenu};
        }
    ],
    // OBTUNDATION, ALL OF IT, IN ONE PLACE AND IN THE ORDER YOU WOULD READ IT.
    // it used to be three settings in two top level categories and three subcategories, and none of them said the
    // other two existed. the master lived under ACM Extended: Systems while its two children lived here, one of
    // them alone in a subcategory of its own, and the five entry sliders that tune the automatic entry sat under
    // the heading for the posture and black screen extras instead.
    // nothing below changes a variable name, a default or a line of behaviour. it is the same three gates in the
    // same order they take effect, with the children named after the parent they depend on.
    //
    // THE THREE GATES ANSWER THREE DIFFERENT QUESTIONS.
    // 1. Obtundation. does the state exist in this mission at all. off means nothing enters it, nothing maintains
    //    it, and no black screen budget runs.
    // 2. Automatic entry from vitals. what is allowed to put a casualty into it. off leaves the whole system built
    //    and running, and only Zeus and the debug toggle can trigger it.
    // 8. Two-posture cascade and black-screen cap. how elaborate it is once a casualty is in it. off gives the
    //    simple back-stuck state with one posture and no time cap.
    [
        "ACME_sys_obtunded", "CHECKBOX",
        ["1. Obtundation [BETA]", "The master switch for everything below. A semi-conscious, awake-but-down state: the casualty is awake and cannot get up, rather than being unconscious. BETA and off by default, because it takes over posture, input and vision and touches more of the player experience than any other system in the addon. Try it on a small group before a full mission. OFF: nothing enters the state, nothing maintains it, and the black-screen cap does not run. A casualty already obtunded is released. Takes effect immediately."],
        [_cTrau, "2. Obtundation"],
        false, 1, { call ACME_fnc_obtundedMasterChanged; }
    ],
    [
        "ACME_obtunded_autoEnable", "CHECKBOX",
        ["2. Automatic entry from vitals", "Requires 1. Obtundation. Lets a casualty's own SpO2 and MAP put them into the state. OFF: the system still runs, and only a Zeus module or the debug toggle can trigger it. The five entry settings below tune this."],
        [_cTrau, "2. Obtundation"],
        true, 1, {}
    ],
    [
        "ACME_obtunded_dwellEnter", "SLIDER",
        ["3. Entry: seconds below threshold", "Requires 2. Automatic entry. How long a casualty must stay below the threshold before obtundation takes them. A brief dip does not count, and the clock resets the moment they climb back out. Set to 0 for the old instant behavior."],
        [_cTrau, "2. Obtundation"],
        [0, 60, 8, 0], 1, {}
    ],
    [
        "ACME_obtunded_hardSpO2", "SLIDER",
        ["4. Entry: immediate SpO2", "Requires 2. Automatic entry. Below this saturation it is immediate and the entry timer is skipped. This is the profound case, where waiting would be dishonest."],
        [_cTrau, "2. Obtundation"],
        [50, 90, 83, 0], 1, {}
    ],
    [
        "ACME_obtunded_hardMAP", "SLIDER",
        ["5. Entry: immediate MAP", "Requires 2. Automatic entry. Below this mean arterial pressure it is immediate and the entry timer is skipped."],
        [_cTrau, "2. Obtundation"],
        [40, 70, 59, 0], 1, {}
    ],
    [
        "ACME_obtunded_refractory", "SLIDER",
        ["6. Entry: grace after recovery", "Requires 2. Automatic entry. Seconds of protection after a casualty comes round on their own vitals. Inside this window only the immediate thresholds, or the longer dwell below, can put them back down. It stops the bounce where a medic fixes someone and they drop again before anyone can act."],
        [_cTrau, "2. Obtundation"],
        [0, 300, 45, 0], 1, {}
    ],
    [
        "ACME_obtunded_dwellReEnter", "SLIDER",
        ["7. Entry: seconds to re-enter", "Requires 2. Automatic entry. The longer dwell that applies inside the grace window above."],
        [_cTrau, "2. Obtundation"],
        [0, 120, 20, 0], 1, {}
    ],
    [
        "ACME_ko_systemEnable", "CHECKBOX",
        ["8. Two-posture cascade and black-screen cap", "Requires 1. Obtundation. Adds two things on top of the state: a second posture, where a better perfused casualty can slow-crawl prone instead of being stuck on their back, and a hard cap on how long a single black screen can last. OFF: one posture, stuck on the back, and no time cap, which is the original simple behaviour. The six settings below tune this."],
        [_cTrau, "2. Obtundation"],
        true, 1, {}
    ],
    [
        "ACME_obtunded_proneEnable", "CHECKBOX",
        ["9. Prone-crawl posture", "Requires 8. Two-posture cascade. Two awake-but-down states: prone and able to slow-crawl when better perfused, stuck on the back when worse. OFF: always stuck on the back."],
        [_cTrau, "2. Obtundation"],
        true, 1, {}
    ],
    [
        "ACME_obtunded_crawlSpeedCoef", "SLIDER",
        ["10. Crawl speed", "Requires 9. Prone-crawl posture. Movement speed while prone-crawling. 1 is a normal prone crawl and lower is a slower drag."],
        [_cTrau, "2. Obtundation"],
        [0.3, 1.0, 0.65, 2], 1, {}
    ],
    [
        "ACME_obtunded_backSpO2", "SLIDER",
        ["11. Prone or back split: SpO2", "Requires 9. Prone-crawl posture. At or above this saturation, and the MAP below, a casualty can prone-crawl. Below it they are stuck on their back."],
        [_cTrau, "2. Obtundation"],
        [80, 92, 86, 0], 1, {}
    ],
    [
        "ACME_obtunded_backMAP", "SLIDER",
        ["12. Prone or back split: MAP", "Requires 9. Prone-crawl posture. The MAP half of the prone-crawl versus stuck-on-back split."],
        [_cTrau, "2. Obtundation"],
        [50, 75, 62, 0], 1, {}
    ],
    [
        "ACME_ko_mercySeconds", "SLIDER",
        ["13. Black-screen cap (s)", "Requires 8. Two-posture cascade. A hard cap on one continuous true knockout, meaning a black screen. At the cap the casualty is stabilised just enough to drop into the awake-but-down state instead. Worst case is one black window rather than a void."],
        [_cTrau, "2. Obtundation"],
        [60, 600, 300, 0], 1, {}
    ],
    [
        "ACME_ko_mercyHoldSeconds", "SLIDER",
        ["14. Mercy hold (s)", "Requires 8. Two-posture cascade. After the black-screen cap, how long the casualty is held awake-but-down regardless of vitals before the normal rules resume."],
        [_cTrau, "2. Obtundation"],
        [10, 120, 45, 0], 1, {}
    ],
    [
        "ACME_ko_wakeFloorSpO2", "SLIDER",
        ["15. Wake-floor SpO2", "Requires 8. Two-posture cascade. The saturation the mercy backstop stabilises a casualty to, so consciousness sticks and ACE does not knock them straight back out. It sits above ACE's own knockout floor."],
        [_cTrau, "2. Obtundation"],
        [80, 92, 85, 0], 1, {}
    ],

    // SEIZURES. the convulsion animation only.
    // the physiology of a seizure is core gameplay and has no switch: the casualty still seizes, still loses
    // consciousness, and still carries every vital sign and consequence of it. this setting governs the BODY
    // MOTION and nothing else.
    // ACME uses BI's GestureSpasm3-6 as dedicated 1.35x seizure gestures. Each gesture finishes before the next
    // begins. The old heading tremor, random yaw jitter and repeated ragdoll-flop loop are no longer used.
    [
        "ACME_seizure_animEnabled", "CHECKBOX",
        ["Seizure body motion", "The convulsion ANIMATION only. ON: active seizures cycle BI GestureSpasm3-6 at 1.35x, allowing each spasm to finish before the next begins. OFF: a seizing casualty lies still, while loss of consciousness, apnea, vitals, postictal state and treatment remain unchanged. Takes effect immediately, including on a seizure already running."],
        [_cTrau, "3. Seizures"],
        true, 2, {}
    ],
    // newer systems: the full-off toggles.
    // each of these is read live at the top of the tick of that system, so unticking one stops it immediately and
    // completely, with no restart required.
    ["ACME_sys_vesicant", "CHECKBOX",
        ["Extravasation / vesicant injury", "Drug leaks into tissue from a compromised IV, with staged damage and the phentolamine / hyaluronidase antidotes. OFF: no extravasation injury is ever created or ticked. Takes effect immediately."],
        [_cSys, "Systems"], true, 1, {}],
    ["ACME_sys_blastLung", "CHECKBOX",
        ["[BETA] Blast lung / ARDS", "Primary blast injury to the lung, air hunger, and progression to ARDS. BETA: off by default, and driven by the blast overpressure model below. OFF: no blast lung is inflicted or progressed. Takes effect immediately."],
        [_cSys, "Systems"], false, 1, {}],
    ["ACME_sys_blastOverpressure", "CHECKBOX",
        ["[BETA] Blast overpressure", "One pressure calculation per explosion, shared by every consequence, so the hearing, brain and lung injuries all follow from the same wave instead of separate rolls. Models charge size, range, line of sight, body orientation and reflection inside rooms and vehicles, against the published injury thresholds. Repeated exposure accumulates and decays. BETA: off by default. It hooks every projectile in the mission to catch detonations, and its thresholds are real ones, so it fires rarely in the open and hard indoors. OFF: explosions cause no pressure injury at all. Takes effect immediately."],
        [_cSys, "Systems"], false, 1, {}],
    ["ACME_sys_hypothermia", "CHECKBOX",
        ["Hypothermia model", "Core temperature, the lethal triad coupling, and cold-blood cooling. OFF: temperature stops being tracked or applied. Takes effect immediately."],
        [_cSys, "Systems"], true, 1, {}],
    ["ACME_sys_bloodChain", "CHECKBOX",
        ["Blood cold chain", "Blood aging, the cooler and fridge, warmed/cold unit states and the flow penalty for cold blood. OFF: blood never ages or changes temperature state and coolers stop simulating. Takes effect immediately. Units already in a cold or warm state keep that state until used."],
        [_cSys, "Systems"], true, 1, {}],
    ["ACME_sys_permHypo", "CHECKBOX",
        ["Permissive hypotension", "Bleeding scales with the pressure driving it, so resuscitating an uncontrolled hemorrhage to a normal pressure costs blood and pops fresh clots. Also enables the hypotension secondary insult in TBI, where a LOW pressure is the harmful one. The two pull opposite ways on a casualty who has both. OFF: bleeding ignores blood pressure entirely and TBI takes no penalty for hypotension. Takes effect immediately."],
        [_cSys, "Systems"], true, 1, {}],
    ["ACME_sys_flight", "CHECKBOX",
        ["Flight physiology", "Altitude gas expansion and hypobaric hypoxia, G-loading, airframe chill and cabin noise. OFF: altitude and flight forces stop affecting casualties. Takes effect immediately."],
        [_cSys, "Systems"], true, 1, {}],

    // newer systems: hardcore.
    // it is the same philosophy as ACM's own hardcore boxes: the field cannot fully fix it, so the answer is
    // evacuation. all of these apply live now, with no mission restart, because unticking one restores the original
    // baseline.
    ["ACME_hc_vesicant", "CHECKBOX",
        ["[HARDCORE] Extravasation", "A leak leaves a lasting tissue floor from stage 1 rather than stage 2, and recovers far more slowly. The matched antidote and early recognition stop being optional. Applies immediately."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_hypothermia", "CHECKBOX",
        ["[HARDCORE] Hypothermia", "Passive self-rewarming is much weaker and active rewarming becomes mandatory below 32C instead of 30C. An HPMK stops being optional. Applies immediately."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],
    ["ACME_hc_flight", "CHECKBOX",
        ["[HARDCORE] Flight Physiology", "Trapped gas expands faster on the climb and G-loading bites a hypovolemic casualty harder. Applies immediately."],
        [_cSys, "Hardcore"], false, 1, { call ACME_fnc_applyHardcore; }],

    [
        "ACME_hang_useRope", "CHECKBOX",
        ["IV line: physical rope", "ON (default): the IV line is a real PhysX rope (the engine default rope, like ACE fastroping) that hangs between the bag and the patient, collides with terrain, and needs no model file. OFF: no IV line is drawn at all (there is no Draw3D fallback)."],
        [_cIV, "IV line"],
        true, 2, {}
    ]
];

{
    _x call CBA_fnc_addSetting;
} forEach _settings;

// Procedure access controls gate new starts while preserving existing aftercare.
["ACME_allowThoracostomy", "CHECKBOX", ["Allow Thoracostomy", "Allow new incisions and finger sweeps. Existing wounds remain accessible for sealing, drainage and closure. Required training uses ACM Breathing: Thoracostomy."], ["ACM Extended: Trauma", "Procedures"], true, 1, {}] call CBA_fnc_addSetting;

["ACME_allowChestTubes", "CHECKBOX", ["Allow Chest Tubes", "Allow new chest tubes. Existing tubes retain drainage, suturing and removal."], ["ACM Extended: Trauma", "Procedures"], true, 1, {}] call CBA_fnc_addSetting;

["ACME_thora_allowSurgicalKit", "CHECKBOX", ["Allow Surgical Kit use for Thoracostomy", "Accept a reusable ACE Surgical Kit for the thoracostomy minigame. A disposable Thoracostomy Kit is used first if available, and is consumed once per completed side."], ["ACM Extended: Trauma", "Procedures"], false, 1, {}] call CBA_fnc_addSetting;

["ACME_allowNCD", "CHECKBOX", ["Allow Needle Decompression", "Allow new NAR SPEAR placements, including in the chest-seal minigame. Existing decompressions and their consequences persist. Required training uses ACM Breathing: Needle Decompression."], ["ACM Extended: Trauma", "Procedures"], true, 1, {}] call CBA_fnc_addSetting;

["ACME_allowIntubation", "CHECKBOX", ["Allow Orotracheal Intubation", "Allow new tube passage. Existing tubes remain accessible for cuff management, suction and extubation."], ["ACM Extended: Airway", "Procedures"], true, 1, {}] call CBA_fnc_addSetting;

["ACME_allowVentilator", "CHECKBOX", ["Allow Ventilator Connections", "Allow a new ventilator connection. Existing devices keep running and can be adjusted or disconnected."], ["ACM Extended: Ventilator", "Procedures"], true, 1, {}] call CBA_fnc_addSetting;

["ACME_allowPushDoseAction", "CHECKBOX", ["Allow Push-Dose Epinephrine Action", "Show the dedicated measured push-dose action. Ordinary medication syringes and infusions remain available through their existing rules."], ["ACM Extended: Circulation", "Procedures"], true, 1, {}] call CBA_fnc_addSetting;

["ACME_allowHTSBolus", "CHECKBOX", ["Allow Osmotherapy Bolus Actions", "Allow the dedicated hypertonic saline bullet and mannitol bolus treatments. Ordinary medication and infusion handling retain their existing rules."], ["ACM Extended: Neuro & TBI", "Procedures"], true, 1, {}] call CBA_fnc_addSetting;

["ACME_skillChestTube", "LIST", ["Chest Tubes: Required Training", "Minimum ACE medical trait for placing or removing chest tubes."], ["ACM Extended: Trauma", "Required Training"], [[0, 1, 2], ["Everyone", "Medic", "Doctor"], 2], 1, {}] call CBA_fnc_addSetting;

["ACME_skillThoracostomySeal", "LIST", ["Seal Thoracostomy: Required Training", "Minimum ACE medical trait to cover an existing thoracostomy with a chest seal. This is independent of permission to place a tube or make a new incision."], ["ACM Extended: Trauma", "Required Training"], [[0, 1, 2], ["Everyone", "Medic", "Doctor"], 1], 1, {}] call CBA_fnc_addSetting;

["ACME_skillIntubation", "LIST", ["Orotracheal Intubation: Required Training", "Minimum ACE medical trait for intubation and existing endotracheal-tube care."], ["ACM Extended: Airway", "Required Training"], [[0, 1, 2], ["Everyone", "Medic", "Doctor"], 1], 1, {}] call CBA_fnc_addSetting;

["ACME_skillVentilator", "LIST", ["Ventilator: Required Training", "Minimum ACE medical trait for connecting and controlling a ventilator."], ["ACM Extended: Ventilator", "Required Training"], [[0, 1, 2], ["Everyone", "Medic", "Doctor"], 1], 1, {}] call CBA_fnc_addSetting;

["ACME_skillMedicationPreparation", "LIST", ["Patient Narc Box: Required Training", "Minimum ACE medical trait for the previously Medic-gated patient Draw Medication action. Self preparation and native ACM medication permissions retain their own rules."], ["ACM Extended: Infusion & IV", "Required Training"], [[0, 1, 2], ["Everyone", "Medic", "Doctor"], 1], 1, {}] call CBA_fnc_addSetting;

["ACME_skillMedicationBolus", "LIST", ["Dedicated Bolus Actions: Required Training", "Minimum ACE medical trait for dedicated push-dose epinephrine and osmotherapy bolus actions."], ["ACM Extended: Circulation", "Required Training"], [[0, 1, 2], ["Everyone", "Medic", "Doctor"], 1], 1, {}] call CBA_fnc_addSetting;




// the blood, medications, hold bag, TBI tuning, debug and accessibility settings live in this file as standalone
// "[...] call CBA_fnc_addSetting;" statements. it was never #included, so none of them registered, which is why
// accessibility never appeared in addon options. pull them in here so they all register on preinit.
#include "XEH_settings.hpp"
