// CBA settings. they are exposed in addon options under the "ACM Extended:" listings, covering systems,
// circulation, infusion and iv, neuro and TBI, debug, and accessibility.
// this holds the debug toggle and the most useful live-tunable knobs for testing the TBI loop.

// the master debug gate. it defaults to off, and every debug menu action, HUD and feature is hidden unless it is
// on.
// the duplicate setting ACME_debug_enabled is registered in XEH_preInit.sqf. it is kept out here so CBA does not
// overwrite saved values.

[
    "ACME_tbi_debugHud",
    "CHECKBOX",
    ["TBI debug HUD", "Show a live TBI / CPP readout overlay (top-left) for the nearest tracked patient. Requires 'Enable debug features'."],
    ["ACM Extended: Debug", "Options"],
    false,
    2,
    {}
] call CBA_fnc_addSetting;

// the duplicate setting ACME_tbi_applyVitals is registered in XEH_preInit.sqf. it is kept out here so CBA does
// not overwrite saved values.

// the duplicate setting ACME_tbi_cppTarget is registered in XEH_preInit.sqf. it is kept out here so CBA does not
// overwrite saved values.

// the duplicate setting ACME_tbi_volumeAdequateFloor is registered in XEH_preInit.sqf. it is kept out here so
// CBA does not overwrite saved values.

// the duplicate setting ACME_tbi_herniationICP is registered in XEH_preInit.sqf. it is kept out here so CBA does
// not overwrite saved values.

// the blood spoilage master toggle. on, the default, means the cold chain spoils warm blood as normal. off means
// blood never turns into spoiled blood, so the cooler, the coolant and the thaw still tick and the final spoil
// step is skipped. it is for servers and sessions that do not want to manage the cold chain.
[
    "ACME_bloodSpoilEnabled",
    "CHECKBOX",
    ["Blood spoilage", "When ON, warm/out-of-date blood spoils into Spoiled Blood (the normal cold-chain). Turn OFF to disable all blood spoilage."],
    ["ACM Extended: Systems", "Blood"],
    true,
    1,
    {}
] call CBA_fnc_addSetting;

[
    "ACME_flushReqEnabled",
    "CHECKBOX",
    ["Require saline flush after push", "When ON, selected Narc Box IV/IO pushes require a saline flush before taking effect."],
    ["ACM Extended: Circulation", "Medications"],
    true,
    1,
    {}
] call CBA_fnc_addSetting;

// cold-blood transfusion hypothermia.
// unwarmed, cooler-stored, [cooled] blood pulls the core temperature of the patient down as it transfuses, which
// feeds the lethal triad, unless a medic runs it through the LifeWarmer quantum, which flips it to warming.
[
    "ACME_coldBloodHypothermia",
    "CHECKBOX",
    ["Cold blood causes hypothermia", "When ON, unwarmed (cold/[Cooled]) blood drops the patient's core temperature during transfusion. Use the LifeWarmer to negate it. Turn OFF to make all blood temperature-neutral."],
    ["ACM Extended: Systems", "Blood"],
    true,
    1,
    {}
] call CBA_fnc_addSetting;

[
    "ACME_cooler_tempDropPerLiter",
    "SLIDER",
    ["Cold blood cooling (C per liter)", "How many degrees C of core temperature one liter of unwarmed cold blood removes as it transfuses. Higher = harsher transfusion hypothermia."],
    ["ACM Extended: Systems", "Blood"],
    [0, 4, 1.1, 2],
    1,
    {}
] call CBA_fnc_addSetting;

// temperature-dependent blood flow rate.
// cold, cooler-stored blood is viscous and runs slower, warmed blood runs slightly faster, and normal
// room-temperature blood is unaffected, at a multiplier of 1. it encourages running cold units through the
// warmer.
[
    "ACME_coldBlood_flowMult",
    "SLIDER",
    ["Cold blood flow rate (x)", "Flow-rate multiplier for unwarmed COLD ([Cooled]) blood. Below 1 = slower (more viscous). Set to 1 to remove the cold flow penalty."],
    ["ACM Extended: Systems", "Blood"],
    [0.2, 1, 0.65, 2],
    1,
    {}
] call CBA_fnc_addSetting;

[
    "ACME_warmedBlood_flowMult",
    "SLIDER",
    ["Warmed blood flow rate (x)", "Flow-rate multiplier for WARMED blood. Above 1 = slightly faster. Set to 1 for no warmed-flow bonus."],
    ["ACM Extended: Systems", "Blood"],
    [1, 2, 1.1, 2],
    1,
    {}
] call CBA_fnc_addSetting;

// hold-bag weapon handling.
// while holding an iv bag up, the back-slung weapons of the medic are removed and restored afterward, so they
// cannot clip the ground in the crouch and loop collision audio with some weapon mods. turn it off to stow the
// weapon on the back instead, with no removal, which avoids any weapon-loss risk on a hard disconnect
// mid-hold.
[
    "ACME_hang_removeWeapon",
    "CHECKBOX",
    ["Stow weapons off-body while holding bag", "ON: remove back weapons during the hold (restored when it ends) to stop the ground-collision audio loop. OFF: keep the weapon on the back."],
    ["ACM Extended: Infusion & IV", "Hold Bag"],
    true,
    1,
    {}
] call CBA_fnc_addSetting;


// accessibility: the global colorblind-safe cue palette.
// it applies to the procedural colored cues across the ACM extended minigames and HUD overlays.
[
    "ACME_a11y_colorblindMode",
    "LIST",
    ["Colorblind mode", "Recolors ACM Extended procedural cues into palettes that remain distinguishable for common color-vision deficiencies. Applies to IV palpation, chest-seal fingers, BVM/EMMA/AED cues, and other colored runtime overlays."],
    ["ACM Extended: Accessibility", "Options"],
    [
        ["normal", "deuteranomaly", "deuteranopia", "protanomaly", "protanopia", "tritanomaly", "tritanopia", "achromatopsia"],
        ["Off / normal", "Deuteranomaly", "Deuteranopia", "Protanomaly", "Protanopia", "Tritanomaly", "Tritanopia", "Achromatopsia / monochrome"],
        0
    ],
    2,
    {
        missionNamespace setVariable ["ACME_a11y_colorblindMode", _this, false];
        // force color-built displays to rebuild immediately. per-frame cues recolor on their next tick.
        if (!isNil "BIS_fnc_rscLayer") then {
            private _emmaLayer = "ACME_EMMA" call BIS_fnc_rscLayer;
            _emmaLayer cutText ["", "PLAIN"];
            uiNamespace setVariable ["ACME_EMMA_DLG", displayNull];
            private _bvmLayer = "ACME_BVMVent" call BIS_fnc_rscLayer;
            _bvmLayer cutText ["", "PLAIN"];
            uiNamespace setVariable ["ACME_BVMVent_DLG", displayNull];
        };
        if (!isNil "ACME_fnc_chestSealRender") then { [] call ACME_fnc_chestSealRender; };
        if (!isNil "ACME_fnc_ivMinigameRenderMarks") then { [] call ACME_fnc_ivMinigameRenderMarks; };
    }
] call CBA_fnc_addSetting;

// accessibility: the BVM ventilation visual cue.
// the blue circle pulses from the same instant ACM plays the BVM squeeze sound.
[
    "ACME_a11y_bvmVentCircle",
    "CHECKBOX",
    ["BVM ventilation visual cue", "Show a blue inflating circle when the BVM ventilation sound plays. Client-side per player."],
    ["ACM Extended: Accessibility", "Options"],
    true,
    2,
    {}
] call CBA_fnc_addSetting;

// the inflate window. the default matches the length of ACM bvm_squeeze.wav.
[
    "ACME_a11y_bvmVentInflateSec",
    "SLIDER",
    ["BVM cue: inflate time (s)", "How long the circle takes to inflate from default size to peak."],
    ["ACM Extended: Accessibility", "Options"],
    [0.3, 3, 1.23, 2],
    2,
    {}
] call CBA_fnc_addSetting;

// accessibility: the optional left-aligned medical menu.
// it left-aligns the treatment menu labels. it is client-side per player.
[
    "ACME_a11y_menuLeftAlign",
    "CHECKBOX",
    ["Left-align medical menu", "Left-align treatment menu button labels. Client-side per player."],
    ["ACM Extended: Accessibility", "Options"],
    false,
    2,
    {
        private _disp = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
        if (isNull _disp) exitWith {};
        if (isNil "ace_medical_gui_fnc_updateActions") exitWith {};
        // The renderer selects the new button class without clearing open groups.
        [_disp] call ace_medical_gui_fnc_updateActions;
    }
] call CBA_fnc_addSetting;

// Grouped menus use left-aligned headers and children. The independent alignment
// checkbox still controls the flat layout; neither setting overwrites the other.
[
    "ACME_menuNestEnabled",
    "CHECKBOX",
    ["Group medical menu into dropdowns", "Groups treatments into expandable Airway, Breathing, Chest, Positioning, Capnography, AED and Debug sections. Head medications use PO/IN/BUC or By Mouth/Inhaled/Buccal, according to Clinical Descriptors. Groups use left alignment; turning this off restores a flat menu and your alignment choice. Client-side per player."],
    ["ACM Extended: Accessibility", "Options"],
    true,
    2,
    {
        private _disp = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
        if (!isNull _disp && {!isNil "ace_medical_gui_fnc_updateActions"}) then {
            // The renderer resets groups only if the setting value actually changed.
            [_disp] call ace_medical_gui_fnc_updateActions;
        };
    }
] call CBA_fnc_addSetting;

// ventilator: the battery model, on or off.
// the electrical clock is the point of the battery. a ventilated casualty becomes a reason to move, and reaching
// a vehicle becomes an objective rather than a ride home. not every mission wants that pressure, so it can be
// switched off wholesale. with it off the battery is pinned full and flagged as externally powered, which means
// the icon, the readouts and the LOW and CRITICAL alarms all resolve to fine without any of them needing to
// know the setting exists. it is mission-side, so a server decides it for everyone.
[
    "ACME_vent_batteryEnabled",
    "CHECKBOX",
    ["Ventilator battery drains", "ON (default): the Ventway Sparrow runs on its battery, drains faster at high PEEP, rate and pressure, raises LOW BATTERY at 25% and BATTERY CRITICAL at 10%, and stops at 0% leaving you to bag. Vehicle power halts the drain and recharges it. OFF: the machine simply runs, no charge management and no battery alarms."],
    ["ACM Extended: Airway", "Ventilator"],
    true,
    1,
    {}
] call CBA_fnc_addSetting;

// accessibility: colored group headers.
[
    "ACME_menuColorHeaders",
    "CHECKBOX",
    ["Use separate colors for medical menu sections", "OFF (default): all dropdown headings use cream text. ON: each section uses its own color. Open headings keep their brightness. Regular action rows use uniform white text. Requires grouped menus for headings. Personal display preference."],
    ["ACM Extended: Accessibility", "Options"],
    false,
    2,
    {}
] call CBA_fnc_addSetting;

// color-vision correction strength for the comprehensive client-local mode registered above.
[
    "ACME_a11y_colorblindStrength",
    "SLIDER",
    ["Colorblind correction strength", "How far to push the correction. Full strength is not always the most readable result, particularly for mild deficiency, so this can be dialled back. No effect when the mode above is Off."],
    ["ACM Extended: Accessibility", "Options"],
    [0, 1, 1, 2],
    2,
    { missionNamespace setVariable ["ACME_a11y_colorblindStrength", _this, false]; }
] call CBA_fnc_addSetting;

// junctional wounds: the bleed rate and the appearance frequency.
// this is the bleed rate multiplier on the tuned per-part junctional arterial drain, whose baseline
// ACME_junctionalBleedNorm is 0.10 l/min per part in normal mode and 0.15 in Hardcore. 1.0 is the default balance. the change-callback writes the
// effective base variable the bleed pfh reads, so live changes take effect on the next tick with no
// rebleed.
[
    "ACME_junctionalBleedMult",
    "SLIDER",
    ["Junctional bleed rate", "Multiplier on the junctional arterial bleed rate (per open/packed junction). 1.0 = default. Higher bleeds out faster."],
    ["ACM Extended: Trauma", "1. Junctional"],
    [0.25, 3.0, 1.0, 2],
    1,
    {
        params ["_value"];
        private _base = if (missionNamespace getVariable ["ACME_hc_junc", false]) then {
            missionNamespace getVariable ["ACME_junctionalBleedHardcoreNorm", 0.15]
        } else {
            missionNamespace getVariable ["ACME_junctionalBleedBaseNorm", 0.10]
        };
        missionNamespace setVariable ["ACME_junctionalBleedNorm", _base * _value, false];
    }
] call CBA_fnc_addSetting;

// the appearance-frequency multiplier on both junctional spawn chances, where the velocity-wound baseline is
// 0.60 and the large-avulsion baseline is 0.15, rolled per incoming wound in fn_junctionalrollspawn. 1.0 is the
// default and 0 never spawns junctionals from wounds. it is clamped, so the effective chance never exceeds
// 1.0.
[
    "ACME_junctionalFreqMult",
    "SLIDER",
    ["Junctional appearance frequency", "Multiplier on the chance an incoming wound spawns a junctional bleed. 1.0 = default. 0 = junctionals never spawn from wounds."],
    ["ACM Extended: Trauma", "1. Junctional"],
    [0.0, 2.0, 1.0, 2],
    1,
    {
        params ["_value"];
        private _hardcore = missionNamespace getVariable ["ACME_hc_junc", false];
        private _velocityBase = [0.60, 0.85] select _hardcore;
        private _avulsionBase = [0.15, 0.30] select _hardcore;
        missionNamespace setVariable ["ACME_junctionalChanceVelocity", (_velocityBase * _value) min 1.0, false];
        missionNamespace setVariable ["ACME_junctionalChanceAvulsion", (_avulsionBase * _value) min 1.0, false];
    }
] call CBA_fnc_addSetting;

// the blood type lock, for single player only.
// it is client-side. it forces the ACM blood type of every casualty to a chosen type instead of ACM's per-reload
// random roll, which in single player rerolls on every reload by design. mp already derives a stable type from
// the player UID, so this is pointless and disabled there.
// the index maps to ACM's blood type constants: 0 is off, 1 is o+, 2 is o-, 3 is a+, 4 is a-, 5 is b+, 6 is b-,
// 7 is ab+ and 8 is ab-. the option index minus 1 is the ACM constant.
[
    "ACME_bloodTypeLock",
    "LIST",
    ["Lock blood type (Single player ONLY!)", "SINGLE PLAYER ONLY. Forces every casualty to the chosen blood type instead of ACM's random per-reload roll, for repeatable testing. Has no effect in multiplayer (blood type is UID-stable there). Clientside."],
    ["ACM Extended: Systems", "Blood"],
    [
        [0, 1, 2, 3, 4, 5, 6, 7, 8],
        ["Off", "O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
        0
    ],
    2,
    {}
] call CBA_fnc_addSetting;

// blood fridge: the default stock and the regen interval.
// these are global and server-authoritative. they set the default load a blood fridge spawns with and how often
// it regenerates, used when a fridge is placed with no explicit per-placement overrides, because the eden
// attributes or the zeus popup override these per fridge. the counts are 500 ml units.
[
    "ACME_bf_defOPos", "SLIDER",
    ["Blood fridge: default O+ units", "Default number of 500 mL O-positive units a newly placed blood fridge spawns with (and regenerates to)."],
    ["ACM Extended: Blood Fridge", "Default stock"],
    [0, 40, 6, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_bf_defOPos", round _v, false]; }
] call CBA_fnc_addSetting;
[
    "ACME_bf_defONeg", "SLIDER",
    ["Blood fridge: default O- units", "Default number of 500 mL O-negative (universal donor) units a newly placed blood fridge spawns with."],
    ["ACM Extended: Blood Fridge", "Default stock"],
    [0, 40, 2, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_bf_defONeg", round _v, false]; }
] call CBA_fnc_addSetting;
[
    "ACME_bf_defOther", "SLIDER",
    ["Blood fridge: default units (each other type)", "Default number of 500 mL units of each remaining type (A+, A-, B+, B-, AB+, AB-) a newly placed fridge spawns with."],
    ["ACM Extended: Blood Fridge", "Default stock"],
    [0, 40, 0, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_bf_defOther", round _v, false]; }
] call CBA_fnc_addSetting;

// the regen interval, expressed in in-game hours and minutes. the fridge refills to its configured load once
// this much in-game time has elapsed since its last restock. the default is 24 in-game hours and 0 minutes,
// which is the classic daily behavior. the two sliders sum, and if both are 0 the fridge never
// regenerates.
[
    "ACME_bf_regenHours", "SLIDER",
    ["Blood fridge: regen interval (hours)", "In-game HOURS between blood fridge regenerations. Adds to the minutes setting. Default 24. Set hours and minutes both to 0 to disable regeneration."],
    ["ACM Extended: Blood Fridge", "Regeneration"],
    [0, 72, 24, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_bf_regenHours", round _v, false]; }
] call CBA_fnc_addSetting;
[
    "ACME_bf_regenMinutes", "SLIDER",
    ["Blood fridge: regen interval (minutes)", "In-game MINUTES between blood fridge regenerations, added to the hours setting. Default 0."],
    ["ACM Extended: Blood Fridge", "Regeneration"],
    [0, 59, 0, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_bf_regenMinutes", round _v, false]; }
] call CBA_fnc_addSetting;

// B14: IV legacy threshold retained; IM and nasal routes have distinct equivalent contributions.
// The shared hypnotic load is induction-normalized. Maintenance has hysteresis and all consumers
// read the same live setting; no startup write silently overrides a server's customization.
[
    "ACME_ket_induceThreshold", "SLIDER",
    ["Ketamine: induction threshold", "Legacy IV-equivalent ketamine load for AI induction. Default 7 equals approximately 1.75 mg/kg IV or 4.4 mg/kg IM at full modeled effect, without other sedatives. Game tuning, not a clinical dosing tool. Propofol and midazolam contribute through a shared normalized hypnosis model; small analgesic doses alone do not cause induction."],
    ["ACM Extended: Airway", "Ketamine sedation"],
    [2, 25, 7, 1],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_ket_induceThreshold", _v, false]; }
] call CBA_fnc_addSetting;
[
    "ACME_ket_maintainThreshold", "SLIDER",
    ["Ketamine: maintenance threshold", "Legacy-equivalent maintenance setting shared by ALL hypnotics. Divided by the induction setting to obtain the normalized maintenance threshold. Default 1.2 supports sustained manual infusions after induction. Below it, only drug-caused unconsciousness can resolve, and only with stable native vitals. Tube presence does not provide sedation."],
    ["ACM Extended: Airway", "Ketamine sedation"],
    [0.5, 20, 1.2, 1],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_ket_maintainThreshold", _v, false]; }
] call CBA_fnc_addSetting;

// rocuronium paralysis, the RSI paralytic. The native medication-count value already includes its onset envelope.
// Runtime/debug logic uses 0.5 as the normal block threshold; the old CBA default of 3 silently overwrote that on
// every mission and left even very large doses reported as sub-dose. This is a game-model tuning scale, not a
// clinical dosing recommendation.
[
    "ACME_roc_blockThreshold", "SLIDER",
    ["Rocuronium: paralysis threshold", "Effective modeled rocuronium level at/above which neuromuscular blockade is established. Default 0.5 matches the runtime/debug model. Game tuning only; not a clinical dosing tool."],
    ["ACM Extended: Airway", "Rocuronium paralysis"],
    [0.1, 3, 0.5, 1],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_roc_blockThreshold", _v, false]; }
] call CBA_fnc_addSetting;
[
    "ACME_roc_onsetSeconds", "SLIDER",
    ["Rocuronium: onset (seconds)", "Time from a paralyzing dose to full paralysis. Real rocuronium onset at an intubating dose is about 45-60 s."],
    ["ACM Extended: Airway", "Rocuronium paralysis"],
    [15, 120, 60, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_roc_onsetSeconds", _v, false]; }
] call CBA_fnc_addSetting;

// the ventilator scroll rate cap.
// this is the minimum time in seconds between accepted dial and scroll steps on the ventilator. higher gives a
// slower maximum scroll, and less dial-sound spam, and lower gives a faster one. scroll steps arriving sooner
// than this after the last one are ignored entirely. the default is 0.09 s, which is about 11 steps per
// second.
[
    "ACME_vent_scrollCooldown", "SLIDER",
    ["Ventilator: scroll rate cap (s)", "Minimum seconds between dial steps on the ventilator. Higher slows the max scroll speed and reduces dial-sound spam."],
    ["ACM Extended: Airway", "Ventilator"],
    [0.02, 0.30, 0.09, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_vent_scrollCooldown", _v, false]; }
] call CBA_fnc_addSetting;

// cabin motion, the minigame shake in a moving vehicle.
// every number in fn_motionshake is exposed. the defaults are the tuned values, so leaving these alone changes
// nothing. the two most worth touching by feel are the lull floor, which gives bigger openings, and the bump
// cooldown, which is how often rough air is allowed to ruin a stick you had lined up.

[
    "ACME_motion_enable", "CHECKBOX",
    ["Enable cabin motion", "Minigames shake in a moving vehicle. Off = perfectly steady everywhere."],
    ["ACM Extended: Cabin Motion", "Cabin motion"],
    [true],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_enable", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_maxSpeed", "SLIDER",
    ["Full-shake airspeed (km/h)", "Airspeed at which the vibration reaches full strength. MH-60 cruises 260-280 km/h."],
    ["ACM Extended: Cabin Motion", "Cabin motion"],
    [120, 320, 260, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_maxSpeed", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_vibAmplitude", "SLIDER",
    ["Vibration strength", "The airframe humming. Small and fast. Felt, not seen."],
    ["ACM Extended: Cabin Motion", "Vibration"],
    [0, 0.03, 0.007, 3],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_vibAmplitude", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_vibTau", "SLIDER",
    ["Vibration ramp (s)", "Seconds for the vibration to settle to a new level. Nothing snaps."],
    ["ACM Extended: Cabin Motion", "Vibration"],
    [0.1, 4, 1.1, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_vibTau", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_taperSpeed", "SLIDER",
    ["Taper below (km/h)", "Below this airspeed the buzz falls away. Landing should feel like landing."],
    ["ACM Extended: Cabin Motion", "Vibration"],
    [0, 200, 100, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_taperSpeed", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_rotorIdle", "SLIDER",
    ["Rotors-idling hum", "Rotors turning on the deck: a gentle hum, not silence, not a cruise."],
    ["ACM Extended: Cabin Motion", "Vibration"],
    [0, 0.6, 0.12, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_rotorIdle", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_manAmplitude", "SLIDER",
    ["Bank strength", "The airframe banking. Large and slow. This is where the severity lives."],
    ["ACM Extended: Cabin Motion", "Banking"],
    [0, 0.2, 0.055, 3],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_manAmplitude", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_manTau", "SLIDER",
    ["Bank ramp (s)", "Seconds for a bank to ramp in and ramp back out. No instant on/off."],
    ["ACM Extended: Cabin Motion", "Banking"],
    [0.1, 4, 0.75, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_manTau", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_envMin", "SLIDER",
    ["Lull floor (the opening)", "In a lull the cabin settles to this fraction of full strength, giving you a WINDOW to commit. Lower = bigger openings."],
    ["ACM Extended: Cabin Motion", "Openings"],
    [0.05, 1, 0.3, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_envMin", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_envRateA", "SLIDER",
    ["Swell rate A (Hz)", "First envelope oscillator. Incommensurate with B so the pattern never repeats."],
    ["ACM Extended: Cabin Motion", "Openings"],
    [0.03, 0.8, 0.17, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_envRateA", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_envRateB", "SLIDER",
    ["Swell rate B (Hz)", "Second envelope oscillator."],
    ["ACM Extended: Cabin Motion", "Openings"],
    [0.03, 0.8, 0.29, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_envRateB", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_bumpAmp", "SLIDER",
    ["Bump strength", "A discrete jolt of rough air. Sharp attack, fast decay."],
    ["ACM Extended: Cabin Motion", "Bumps"],
    [0, 0.1, 0.022, 3],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_bumpAmp", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_bumpDur", "SLIDER",
    ["Bump duration (s)", "How long one jolt lasts. Short. It is a hit, not a wallow."],
    ["ACM Extended: Cabin Motion", "Bumps"],
    [0.05, 1, 0.2, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_bumpDur", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_burstMax", "SLIDER",
    ["Max bumps per burst", "Rough air hits you up to this many times in quick succession."],
    ["ACM Extended: Cabin Motion", "Bumps"],
    [1, 6, 3, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_burstMax", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_burstGapMin", "SLIDER",
    ["Gap within a burst, min (s)", "Spacing between hits inside one burst."],
    ["ACM Extended: Cabin Motion", "Bumps"],
    [0.05, 1, 0.13, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_burstGapMin", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_burstGapMax", "SLIDER",
    ["Gap within a burst, max (s)", "Spacing between hits inside one burst."],
    ["ACM Extended: Cabin Motion", "Bumps"],
    [0.05, 1.5, 0.34, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_burstGapMax", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_bumpCooldownMin", "SLIDER",
    ["Cooldown after a burst, min (s)", "The calm after rough air. This is what PROTECTS the window: if a bump could land at any instant there would be no safe moment to commit."],
    ["ACM Extended: Cabin Motion", "Bumps"],
    [0.5, 30, 4, 1],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_bumpCooldownMin", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_motion_bumpCooldownMax", "SLIDER",
    ["Cooldown after a burst, max (s)", "The calm after rough air."],
    ["ACM Extended: Cabin Motion", "Bumps"],
    [1, 60, 14, 1],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_motion_bumpCooldownMax", _v, false]; }
] call CBA_fnc_addSetting;

// Local presentation preferences. These do not change patient state or treatment rates.
[
    "ACME_motion_interpolate", "CHECKBOX",
    ["Smooth vehicle shake", "Smooths the shared motion offset before artwork and hit targets move. Helps readability at low FPS. Does not generate frames."],
    ["ACM Extended: Cabin Motion", "Accessibility"],
    true, 2, {}
] call CBA_fnc_addSetting;
[
    "ACME_motion_interpolationTime", "SLIDER",
    ["Vehicle shake smoothing (s)", "Longer values soften rapid vibration more. Lower values follow the original movement more closely."],
    ["ACM Extended: Cabin Motion", "Accessibility"],
    [0.02, 0.4, 0.12, 2], 2, {}
] call CBA_fnc_addSetting;
[
    "ACME_minigameNV_focusBlur", "SLIDER",
    ["NV scene focus blur", "Adds a small local scene blur while goggles are on in a procedure. Zero disables it. Native NV masks, colors, grain and gain are left alone. This does not blur 2D dialog text or art."],
    ["ACM Extended: Cabin Motion", "Accessibility"],
    [0, 1, 0.35, 2], 2, {}
] call CBA_fnc_addSetting;

// minigame darkness.
// it ports ACE's map light. the beam is not a light, it is a shade with a hole in it, because arma has no blend
// modes and you cannot paint light onto black to reveal what is under it.

[
    "ACME_darkness_enable", "CHECKBOX",
    ["Enable minigame darkness", "Minigames go dark at night. You need a light source to work."],
    ["ACM Extended: Cabin Motion", "Darkness"],
    [true],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_darkness_enable", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_darkness_maxAlpha", "SLIDER",
    ["Darkness intensity", "How black it gets with no light. 1.0 = fully black. Anything less and a bright body image is still readable."],
    ["ACM Extended: Cabin Motion", "Darkness"],
    [0.5, 1, 1.0, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_darkness_maxAlpha", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_darkness_cabinRelief", "SLIDER",
    ["Closed-cabin relief", "A buttoned-up vehicle gets a hint of instrument glow. 1.0 = none at all. A doorless bird always gets none."],
    ["ACM Extended: Cabin Motion", "Darkness"],
    [0.5, 1, 0.97, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_darkness_cabinRelief", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_darkness_beamScale", "SLIDER",
    ["Torch beam width", "Divided by each flashlight's own size value, exactly as ACE does it, so a Maglite throws a wider pool than a weapon light."],
    ["ACM Extended: Cabin Motion", "Darkness"],
    [0.5, 4, 1.55, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_darkness_beamScale", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_darkness_boost", "SLIDER",
    ["Darkness boost", "Multiplies ACE's own darkness before clamping. ACE tops out near 0.86 at a moonlit ambient because the map only needs to be hard to read. Raise this until the body image is genuinely invisible without a torch."],
    ["ACM Extended: Cabin Motion", "Darkness"],
    [1.0, 3.0, 1.25, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_darkness_boost", _v, false]; }
] call CBA_fnc_addSetting;


[
    "ACME_darkness_adaptRelief", "SLIDER",
    ["Dark adaptation relief", "How much fully dark-adapted eyes lift the shade. Not enough to work by: enough to make out a limb. This is the ONLY thing that is ever less than black at night, and using a torch takes it away. Set to 0 to disable dark adaptation entirely."],
    ["ACM Extended: Cabin Motion", "Darkness"],
    [0, 0.35, 0.11, 2],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_darkness_adaptRelief", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_darkness_constrictTau", "SLIDER",
    ["Pupil constriction (s)", "Seconds for your pupils to shut when the light comes on. Fast."],
    ["ACM Extended: Cabin Motion", "Darkness"],
    [0.2, 8, 1.6, 1],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_darkness_constrictTau", _v, false]; }
] call CBA_fnc_addSetting;

[
    "ACME_darkness_dilateTau", "SLIDER",
    ["Dark recovery (s)", "Seconds for your night vision to come back after the light goes off. SLOW. The asymmetry is the point: switching the torch off does not hand you your night vision back."],
    ["ACM Extended: Cabin Motion", "Darkness"],
    [1, 60, 16, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_darkness_dilateTau", _v, false]; }
] call CBA_fnc_addSetting;

// intubation, the laryngoscopy attempt.
// this is the seconds a single laryngoscopy attempt can run before it is abandoned as no view. the apnea clock
// latches on when the blade first enters the mouth and runs until the tube passes or the attempt fails.
// standard teaching is a thirty second cap per look, and higher is more forgiving.
[
    "ACME_laryngo_attemptLimit", "SLIDER",
    ["Intubation: attempt time limit (s)", "Seconds a single laryngoscopy attempt may run before it is abandoned as no view. The clock runs from blade insertion until the tube passes."],
    ["ACM Extended: Airway", "Intubation"],
    [10, 90, 30, 0],
    1,
    { params ["_v"]; missionNamespace setVariable ["ACME_laryngo_attemptLimit", _v, false]; }
] call CBA_fnc_addSetting;
