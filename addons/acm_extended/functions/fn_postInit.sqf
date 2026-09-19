// Phase 37: fork version/network bootstrap, chest-seal/vent custody and owner initialization.
call ACME_fnc_initForkStartupRuntime;
// Phase 37: debug-menu PFH plus EachFrame fallback registration.
call ACME_fnc_registerDebugWatchdogRuntime;
// B114: rebindable two-page debug navigation.
call ACME_fnc_registerDebugPageKeybindRuntime;

// Medical-menu rendering is owned at compile time by addons/gui.
call ACME_fnc_initMedicationRegistry;

call ACME_fnc_initTrainingCasualty;

// Spawn-severity ownership now lives in ACM_mission_fnc_generatePatient.

call ACME_fnc_initInfusionConfig;

call ACME_fnc_initThoracostomyConfig;

// Phase 37: chest-tube/body bruising overlays and bilateral chest-tube injury-list presentation.
call ACME_fnc_registerThoracicMenuPresentationRuntime;

// Surgical-casualty evacuation eligibility now lives in ACM_evacuation_fnc_canConvert.

// Phase 37: premixed-bag owner refresh and provider menu-pose lifecycle on medical-menu open.
call ACME_fnc_registerMedicalMenuOpenRuntime;

// left-aligned medical menu

// there is no live overlay compositor. the renderer override above creates real left-aligned action button
// controls when the accessibility option is on.

// narc box. this resets the plunger to a fresh syringe after each draw.
// ACM's draw dialog leaves the plunger down and drawnamount above 0 after a draw, which grays out the
// medication list until the medic pushes the plunger back to zero by hand. the mod resets it so the next drug
// draws at once. it tags the button type on each press. after preparefinish runs, if the press was a draw,
// type 0 and not a push or inject, and the draw dialog is still open, it snaps the plunger handle and the
// visual barrel back to the top limit of the size and zeroes drawnamount. the med list re-enables on the next
// pfh tick. a push or inject calls preparefinish with a type above 0, so the mod skips it. the infusion prep
// path rewires the button to injectIntoBag, which never calls preparefinish, so that path cannot trip it.
// overrides/fn_updateCirculationState.sqf merges native eligibility and Extended arrest gates.
// It publishes one result. Compare the native conditions again when the ACM dependency changes.

// Syringe draw/prepare behavior is owned directly by addons/circulation.

// Phase 38: clinical injury-list relabels, access-site logging and universal AED-vitals presentation.
call ACME_fnc_registerClinicalMenuPresentationRuntime;

// Phase 38: vesicant/extravasation configuration, medication-effect integration and recovery tick.
call ACME_fnc_initVesicantRuntime;

// y-saline clamp. ACE compiles ace_medical_status_fnc_getBloodVolumeChange as final. it cannot be overridden,
// because the engine logs "Attempt to override final function" and keeps the ACM and ACE stock version. the
// stock drainer therefore always runs and would drain our clamped y reserve. instead the mod pins the reserve
// each frame. fn_ysalinepin holds every ACME_SalineY bag at full volume and reverses the small patient-side
// fluid that the stock drainer pushes from it. the reserve then sits clamped with zero net drip until a flush
// line lowers the pin. this runs server-side and gates itself on IV_Bags_Active.
call ACME_fnc_ySalinePin;

// getIVFlowRate, the slower 18g flow, is a compile-time CfgFunctions override in
// class ACME_overwrite_circulation. ACM compiles getIVFlowRate final, so the old runtime reassignment here did
// nothing. there is nothing to install at runtime.

// getbloodpressure and bpoffset are abandoned. ACM compiles getbloodpressure final. the hr fix works because
// it drives a variable that ACM reads, but bp changes only if you replace the function, and that fails. the
// engine rejects the runtime wrapper with "Attempt to override final function", and it rejects a compile-time
// CfgFunctions override for any function ACM finalizes. this was confirmed in game, where bp stayed equal to
// natbp. the bpoffset is therefore unreachable. pressor and push-dose bp now come from cardiac output through
// the hr drive, which is the only lever that works. bpnative stays as the offset-free native source for the
// natbp debug field and the shock and acidosis baselines. with no offset in play it equals ACM's live bp.

// the stethoscope overrides for over-resuscitation crackles install at compile time through CfgFunctions, in
// class ACME_overwrite_breathing in config.cpp. ACM compiles its own breathing functions final, so the old
// runtime reassignment here did nothing and ACM's originals ran with no crackle handling. there is nothing to
// install at runtime.

// getup, blocked while obtunded, is a compile-time CfgFunctions override in class ACME_overwrite_core. ACM
// compiles getup final, so the old runtime reassignment here did nothing. there is nothing to install at
// runtime.

// over-resuscitation pulmonary edema degrades breathing effectiveness, the gas exchange, through the
// getBreathingState override in overrides/fn_getBreathingState.sqf at compile time. it works the same way a
// pneumothorax or a hemothorax does. ACM's own oxygen sim then carries SpO2 down on its own curve. the old
// artificial SpO2 cap wrapper is gone, because a floor on SpO2 was the wrong model and did not match the other
// thoracic insults. updateLungState still sets the auscultation crackles.

// updateHeartRate consumes a separate ACME rhythm target and retains native physiological adjustments.
// A validated perfusing atrial rhythm keeps its identity above 220 bpm; the native critical-vitals
// watchdog remains active for actual deterioration. No per-frame HR clamp or ECG-only correction is used.
// a check breathing on a patient with irregular respirations, cheyne-stokes, reports "irregular rate and depth"
// instead of the single-sample normal, shallow or rapid line, which would mislead mid-pattern.
// the Cheyne-Stokes wrapper that used to live here is gone. it is folded into the real override at
// overrides/fn_checkBreathingLocal.sqf, which had to exist anyway so the clinical breathing strings could be
// resolved before ACM sends the hint through CBA_fnc_targetEvent.

// the medics manage their own stance. there is no auto-crouch and no auto weapon-lowering in the medical menu.

// Phase 39: ROSC timestamp safety, post-arrest stress reset, gasp and Biot respiration start.
call ACME_fnc_registerRoscBreathingRuntime;

// Heart rate is registered at compile time in CfgFunctions.
// updateRespirationRate sole writer. ACM's updateRespirationRate eases the live rr toward its own
// oxygen-derived target on every vitals tick. the TBI also wrote the live rr directly each tick, with a
// per-frame random jitter on top, so the two fought and the rate kept resetting rapidly. the TBI now publishes
// a desired rr in ACME_rrDrive_tbi, and this eases the live rate toward it as the sole writer. ACM's easing
// never runs for a TBI-driven patient and the rate swings smoothly.
// as a safeguard the TBI also sets ACM_core_TargetVitals_RespirationRate to the same value. if this wrap is
// bypassed, ACM's own easing converges to the same place, smooth and with slightly less apnea depth. the
// one-shot log confirms whether the wrap runs.
// the drive releases, at -1, on standdown and in cardiac arrest, where ACM owns rr for apnea and agonal
// breathing.
// NA3: one compile-time respiratory endpoint replaces both former layers.

// NA3: edema tachypnea is composed in the authoritative respiration function; no target-writing PFH.


// Phase 39: roller-clamp mouse capture, wheel presentation and throttled position commits.
call ACME_fnc_registerClampDragRuntime;

// Phase 39: TBI/CPP runtime patient registries.
call ACME_fnc_initTbiCoreState;

// Phase 20: Circulation, acid-base, hypothermia and custom-rhythm tunables.
call ACME_fnc_initCirculationConfig;
call ACME_fnc_initVisualEffectsConfig;
if (hasInterface) then {
    // Local medication receipt is authoritative for the five-minute analgesic ketamine perception window. Any new
    // IV/IM/esketamine dose refreshes the window without changing ACM/ACE pharmacokinetics.
    ["ace_medical_treatment_medicationLocal", {
        params ["_patient", "_bodyPart", "_medication", "_dose", "_injection"];
        if (isNull _patient || {_patient != player} || {!(_medication isEqualType "")}) exitWith {};
        if ((toLowerANSI _medication) in ["ketamine","ketamine_iv","esketamine"]) then {
            uiNamespace setVariable ["ACME_VFX_KetLastDoseAt",diag_tickTime];
        };
    }] call CBA_fnc_addEventHandler;
    [{call ACME_fnc_visualFxTick}, (missionNamespace getVariable ["ACME_visualFx_updateSec",0.12]), []] call CBA_fnc_addPerFrameHandler;
};

// Phase 20: Obtundation, impaired-consciousness and recovery/input-lock tunables.
call ACME_fnc_initConsciousnessConfig;

// Phase 21: Calcium/citrate, fluid-overload edema and circulation resuscitation tunables.
call ACME_fnc_initResuscitationConfig;

// Phase 20: IV/EJ procedure presentation, prep and catheter-flow tunables.
call ACME_fnc_initIVProcedureConfig;

// Phase 39: base ICP, secondary-insult and vasodilatory/CO2 TBI progression constants.
call ACME_fnc_initTbiCoreConfig;

// Phase 20: Head-elevation, patient posture and unconscious-positioning tunables.
call ACME_fnc_initPatientPositioningConfig;

// Phase 20: Megacode Kelly training-manikin presentation and timing tunables.
call ACME_fnc_initMegacodeConfig;

// Phase 21: TBI vital coupling, recovery, autoregulation, ventilation and herniation progression tunables.
call ACME_fnc_initTbiProgressionConfig;

// Phase 20: Infusion PK, toxicity, antiarrhythmic and osmotherapy tunables.
call ACME_fnc_initDrugPhysiologyConfig;

// Phase 23: TBI/CPP and Cheyne-Stokes runtime tick registration.
call ACME_fnc_registerTbiRuntime;

// Phase 22: IO, thoracostomy and chest-seal procedural pain/logging tunables.
call ACME_fnc_initProcedurePainConfig;

// Phase 39: IO placement pain, fracture direct-pressure pain, infusion pulse bridge and head-positioned breath audio.
call ACME_fnc_registerProcedureIntegrationRuntime;

// Phase 22: Blast-lung pacing, treatment ladder and ARDS progression tunables.
call ACME_fnc_initBlastLungConfig;

// Phase 23: Blast-lung wound intake event registration.
call ACME_fnc_registerBlastLungRuntime;

// Phase 23: Circulation, saline-acidosis and automatic-BP runtime ticks.
call ACME_fnc_registerCirculationRuntime;

// Phase 23: Ventilator server sound-source lifecycle, local alarm cadence and audio/logbook events.
call ACME_fnc_registerVentilatorAudioRuntime;

// Phase 23: Non-rebreather oxygen configuration and runtime tick registration.
call ACME_fnc_initNrbRuntime;

// Phase 24: Hang Bag/pressure-infuser presentation, line geometry and treatment-pose synchronization.
call ACME_fnc_initHangBagRuntime;

// Phase 24: HPMK rewarming, LifeWarmer coupling and core thermal tick registration.
call ACME_fnc_initHpmkCoreRuntime;

// darkness occlusion. it uses ACE's own lighting model, getlightingat, so any light source counts
// automatically: a flashlight, a chemlight, ir, vehicle headlights, a burning wreck and the laryngoscope blade
// lamp.
// the ventilator and the EMMA are not shaded on purpose. they have backlit screens, and a backlit screen is
// readable in the dark. that is what backlighting is for. the patient around them is another matter.
// Phase 22: Vehicle-motion minigame shake and flight-chill tunables.
call ACME_fnc_initFlightMotionConfig;

// Phase 22: Ventilator trigger, dyssynchrony, alarms, circuit, sedation and boot-audio tunables.
call ACME_fnc_initVentilatorClinicalConfig;

// Phase 22: Medical-menu grouping and dropdown presentation configuration.
call ACME_fnc_initMedicalMenuConfig;

// Phase 22: Ventilator battery, brightness, panel geometry and alarm-volume tunables.
call ACME_fnc_initVentilatorUiPowerConfig;

// Phase 22: PPV preload, iatrogenic NCD, oxygen delivery and permissive-hypotension tunables.
call ACME_fnc_initPerfusionConfig;

// Phase 22: Ventilator technician, sound-overlap, barotrauma, sedation, zeroing and cough tunables.
call ACME_fnc_initVentilatorRuntimeConfig;

// Phase 22: Flight-noise, altitude-datum and G-loading physiology tunables.
call ACME_fnc_initFlightPhysiologyConfig;

// Phase 22: Airway/head-position, RSI, chest-seal hardcore, ETT and rocuronium interaction tunables.
call ACME_fnc_initAirwayProcedureConfig;

// Phase 22: Narc Box body-map sizing, access and IM presentation tunables.
call ACME_fnc_initNarcBoxConfig;

// Phase 47: shared network publication tolerance.
call ACME_fnc_initNetworkSyncConfig;

// Phase 24: ACRE2 obtunded speech-pulse configuration and delayed language registration.
call ACME_fnc_initAcreBabbleRuntime;

// Phase 24: Intubation geometry plus procedure darkness, adaptation and cyanosis presentation tunables.
call ACME_fnc_initProcedureEnvironmentConfig;

// Phase 24: HPMK blanket reconciliation, pickup interaction and client visual runtime.
call ACME_fnc_registerHpmkVisualRuntime;

// Phase 25: Chest-seal collaborative cursor/tool presence events.
call ACME_fnc_registerChestSealPresenceRuntime;

// Phase 25: Legacy HPMK network-blanket cleanup during patient transport.
call ACME_fnc_registerHpmkTransportCleanupRuntime;

// Phase 25: Hypothermia injury-cooling, recovery tunables and thermal tick registration.
call ACME_fnc_initHypothermiaRuntime;

// Phase 25: Base medical-body overlays for HPMK, NRB and junctional wounds plus junctional GUI reconciliation.
call ACME_fnc_registerMedicalBodyBaseRuntime;

// Phase 26: full-heal, death reset, IV hub seeding and owner-side Y-saline lifecycle hooks.
call ACME_fnc_registerClinicalLifecycleRuntime;

// Phase 25: Blood-fridge/cooler storage, cold-chain, clot-pop and loadout-change runtime.
call ACME_fnc_initBloodStorageRuntime;

// Phase 26: head/EJ/ETT body presentation, unsecured-tube migration, head-TBI triggers and iatrogenic pneumothorax.
call ACME_fnc_initHeadAirwayRuntime;

// Phase 27: blast-overpressure projectile/unit event ownership plus the coupled single-player blood-type lock.
call ACME_fnc_initBlastOverpressureRuntime;

// Phase 28: junctional hemorrhage, packing and XStat rebleed configuration.
call ACME_fnc_initJunctionalConfig;

// Phase 28: chest-seal minigame geometry/provider-pose configuration and wound tracking registration.
call ACME_fnc_initChestSealProcedureRuntime;

// Phase 28: junctional/thoracostomy/AAJT/seizure/skin/cyanosis injury-list presentation hooks.
call ACME_fnc_registerInjuryPresentationRuntime;

// Phase 29: catecholamine, hypothermia, esmolol, amiodarone and torsades rhythm-trigger configuration.
call ACME_fnc_initRhythmTriggerConfig;

// Phase 29: edema crackle threshold plus direct-pressure pain/wake/provider-pose configuration.
call ACME_fnc_initPressureAndAuscultationConfig;

// Phase 29: custom-rhythm pain, obtundation, pressure offsets and ACM rhythm-proxy configuration.
call ACME_fnc_initRhythmHemodynamicsConfig;

// Phase 30: minigame display policy plus late ventilator alarm/power/control defaults.
call ACME_fnc_initMinigameVentDefaults;

// Phase 30: unsynchronized organized-rhythm shock safety configuration.
call ACME_fnc_initCardioversionSafetyConfig;

// Phase 30: delayed ACM/ACE fork compatibility verification.
call ACME_fnc_registerCompatibilityCheck;

// Phase 30: synchronized cardioversion eligibility, AFib irregularity and LifePak SYNC/QRS indicator configuration.
call ACME_fnc_initMonitorSyncConfig;

// Phase 31: obtundation/consciousness PFHs, wrapping audio and treatment-grace/debug-target lifecycle.
call ACME_fnc_registerConsciousnessRuntime;

// Phase 31: ordinary treatment provider-stance release after ACE completion/failure.
call ACME_fnc_registerProviderStanceReleaseRuntime;

// Phase 31: head-elevation drag/carry teardown and automatic ground-setdown restoration.
call ACME_fnc_registerHeadElevationTransportRuntime;

// ACME_DEV_ONLY_BEGIN
// Phase 31: hands-free PhysX casualty drag handle. This intentionally initializes after the head-elevation
// transport events because it reuses those same down/up handoffs for elevated casualties.
if (getNumber (configFile >> 'CfgPatches' >> 'ACM_Extended' >> 'acme_developmentBuild') == 1) then {call ACME_fnc_initDragHandleRuntime;};

// ACME_DEV_ONLY_END
// Phase 32: custom-rhythm tick, obtunded-apply event, per-life respawn scrub and post-ROSC rhythm release.
call ACME_fnc_registerRhythmLifecycleRuntime;

// Phase 32: premixed-bag synchronization and infusion-processing PFHs.
call ACME_fnc_registerInfusionProcessingRuntime;

// Phase 33: EMMA patient-contact routing, anti-flicker hold defaults and HUD tick registration.
call ACME_fnc_initEmmaRuntime;

// Phase 33: hearing-impaired BVM ventilation cue tick registration.
call ACME_fnc_registerBvmVentRuntime;

// Phase 33: AED beat-clock/QRS gating and safe waveform-switch defaults.
call ACME_fnc_initAedMonitorRuntime;

// Phase 33: native fatal-rate latch/recovery thresholds and rhythm-threshold PFH registration.
call ACME_fnc_initRhythmThresholdRuntime;

// Phase 33: transfusion-menu control and roller-clamp dialog refresh PFHs.
call ACME_fnc_registerTransfusionUiRuntime;

// Direct-pressure treatment-time scaling now lives in ace_common_fnc_progressBar at compile time.

// Phase 34: live hardcore-system readiness and difficulty application.
call ACME_fnc_initHardcoreRuntime;

// Phase 34: generic roll-to-back provider-theatre routing for ACE treatments.
call ACME_fnc_registerTreatmentRollRuntime;

// Phase 34: paired treatment-start/end ownership for head-elevation treatment suspension.
call ACME_fnc_registerHeadElevationTreatmentRuntime;

// B122: exact-class chest-access vest leases for backpack-supported patients.
call ACME_fnc_registerChestAccessVestRuntime;

// Phase 34: Megacode laptop control-panel and debug cable-tuner interaction registration.
call ACME_fnc_registerMegacodeInteractionRuntime;

// Phase 35: ventilator dial-press keybind and laryngoscopy dialog-input ownership notes.
call ACME_fnc_registerVentilatorKeybindRuntime;

// Phase 35: procedure display registry, ventilator flip binding, ACE flashlight-menu filtering/reopen and watchdog runtime.
call ACME_fnc_initMinigameInteractionRuntime;

// Runtime function replacement diagnostics are obsolete: there are no runtime function-pointer patches.

// NA3: clinical ownership, bindings and reset/persistence integration.
// NA3: clinical ownership, bindings and reset/persistence integration.
call ACME_fnc_clinicalInit;

// Compile the local texture index once, before a player opens a night procedure.
// B10 leaves procedure textures and native NV resources unchanged. No variant map is loaded.

// Phase 36: acknowledged medication-delivery receipt and retry runtime.
call ACME_fnc_registerMedicationDeliveryRuntime;

// Phase 36: ACE treatment-driven ECG motion-artifact lease lifecycle.
call ACME_fnc_registerEcgJostleRuntime;

// Phase 36: per-life Narc Box syringe/tag selection cleanup on player death/respawn.
call ACME_fnc_registerSyringeLifecycleRuntime;
