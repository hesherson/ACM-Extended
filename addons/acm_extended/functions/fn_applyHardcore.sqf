// resolve the effective hardcore setting per system and apply the difficulty knobs of that system.
// it is safe to call repeatedly. this used to be a straight-line block in fn_postInit, which meant two things.
// 1. toggling any hardcore box mid-mission did nothing at all, because the block only ran once at postinit.
// 2. nothing ever restored the baseline, so even a restart and untick left no way back within a session.
// it also contained a multiplicative override, the chest seal exit factor times 1.15, which would have compounded
// every time it ran. all three are fixed here: the baselines are snapshotted once, every knob is written from
// the baseline rather than from its current value, and a system whose hardcore box is off is actively restored.
// call it with no arguments. it is called at postinit and from the CBA change handler of every hardcore
// setting.

// CBA can dispatch settings before the defaults in fn_postInit.sqf are ready.
// Post-init sets this gate and applies the final resolved settings once all baselines exist.
if (!(missionNamespace getVariable ["ACME_hcReady", false])) exitWith {false};

// snapshot the baselines exactly once.
if (isNil "ACME_hcBase_captured") then {
    ACME_hcBase_junctionalBleedNorm      = ACME_junctionalBleedNorm;
    ACME_hcBase_junctionalDPControl      = ACME_junctionalDPControl;
    ACME_hcBase_junctionalGauzeControl   = ACME_junctionalGauzeControl;
    ACME_hcBase_junctionalGauzeDPControl = ACME_junctionalGauzeDPControl;
    ACME_hcBase_junctionalChanceVelocity = ACME_junctionalChanceVelocity;
    ACME_hcBase_junctionalChanceAvulsion = ACME_junctionalChanceAvulsion;
    ACME_hcBase_tbi_compBudgetSeconds    = ACME_tbi_compBudgetSeconds;
    ACME_hcBase_rhythm_torsadesChancePerTick      = ACME_rhythm_torsadesChancePerTick;
    ACME_hcBase_rhythm_torsadesChanceSevere       = ACME_rhythm_torsadesChanceSevere;
    ACME_hcBase_rhythm_torsadesRefractorySec      = ACME_rhythm_torsadesRefractorySec;
    ACME_hcBase_rhythm_defibTorsadesRefractorySec = ACME_rhythm_defibTorsadesRefractorySec;
    ACME_hcBase_nrb_flowLPM   = ACME_nrb_flowLPM;
    ACME_hcBase_CS_exitFactor = ACME_CS_exitFactor;
    ACME_hcBase_DP_treatTimeMult = ACME_DP_treatTimeMult;
    ACME_hcBase_DP_limbBleedMult = ACME_DP_limbBleedMult;
    // the newer systems.
    ACME_hcBase_vesicant_severeFloorStage = missionNamespace getVariable ["ACME_vesicant_severeFloorStage", 2];
    ACME_hcBase_vesicant_recoverPerMin    = missionNamespace getVariable ["ACME_vesicant_recoverPerMin", 0.5];
    ACME_hcBase_blastLung_ardsEnterSev    = missionNamespace getVariable ["ACME_blastLung_ardsEnterSev", 0.85];
    ACME_hcBase_blastLung_ardsEnterSecs   = missionNamespace getVariable ["ACME_blastLung_ardsEnterSecs", 60];
    ACME_hcBase_hypo_selfRewarmPerMin     = missionNamespace getVariable ["ACME_hypo_selfRewarmPerMin", 0.15];
    ACME_hcBase_hypo_selfRecoverFloorC    = missionNamespace getVariable ["ACME_hypo_selfRecoverFloorC", 30];
    ACME_hcBase_altitude_ptxGrowRate      = missionNamespace getVariable ["ACME_altitude_ptxGrowRate", 0.06];
    ACME_hcBase_flightG_maxResistDrop     = missionNamespace getVariable ["ACME_flightG_maxResistDrop", 28];
    ACME_hcBase_captured = true;
};

// Resolve only the individual settings. Old mission exports of ACME_hc_master are ignored.
ACME_hcEff_junc   = missionNamespace getVariable ["ACME_hc_junc", false];
ACME_hcEff_dp     = missionNamespace getVariable ["ACME_hc_dp", false];
ACME_hcEff_cs     = missionNamespace getVariable ["ACME_hc_chestSeal", false];
ACME_hcEff_hpmk   = missionNamespace getVariable ["ACME_hc_hpmk", false];
ACME_hcEff_tbi    = missionNamespace getVariable ["ACME_hc_tbi", false];
ACME_hcEff_rhythm = missionNamespace getVariable ["ACME_hc_rhythm", false];
ACME_hcEff_circ   = missionNamespace getVariable ["ACME_hc_circ", false];
ACME_hcEff_nrb    = missionNamespace getVariable ["ACME_hc_nrb", false];
ACME_hcEff_medications = missionNamespace getVariable ["ACME_hc_medications", false];
private _juncBleedMult = missionNamespace getVariable ["ACME_junctionalBleedMult", 1.0];
private _juncFreqMult  = missionNamespace getVariable ["ACME_junctionalFreqMult", 1.0];

// Transfusion uses the standard circulation/resuscitation defaults for every mission.
// Old exports of the retired transfusion setting do not alter physiology or bag access.
// Clinical wording reads ACME_hc_descriptors directly. It has no difficulty cache.
// Other Hardcore systems retain their effective values below.
ACME_hcEff_vesicant  = missionNamespace getVariable ["ACME_hc_vesicant", false];
ACME_hcEff_blastLung = missionNamespace getVariable ["ACME_hc_blastLung", false];
ACME_hcEff_hypo      = missionNamespace getVariable ["ACME_hc_hypothermia", false];
ACME_hcEff_flight    = missionNamespace getVariable ["ACME_hc_flight", false];
ACME_hcEff_vent     = missionNamespace getVariable ["ACME_hc_vent", false];
ACME_hcEff_burns    = missionNamespace getVariable ["ACME_hc_burns", false];
ACME_hcEff_infection = missionNamespace getVariable ["ACME_hc_infection", false];
ACME_hcEff_ophthalmology = missionNamespace getVariable ["ACME_hc_ophthalmology", false];

// apply, or restore the baseline.
if (ACME_hcEff_junc) then {
    ACME_junctionalBleedNorm      = (missionNamespace getVariable ["ACME_junctionalBleedHardcoreNorm", 0.15]) * _juncBleedMult;
    ACME_junctionalDPControl      = 0.30;  // B102: about 70 percent control, slightly stronger than the old 65 percent.
    ACME_junctionalGauzeControl   = 0.65;  // gauze alone controls only about 35 percent, so dp on top matters more.
    ACME_junctionalGauzeDPControl = 0.10;  // B102: gauze plus pressure controls about 90 percent; the wrap is still definitive.
    ACME_junctionalChanceVelocity = (0.85 * _juncFreqMult) min 1.0;
    ACME_junctionalChanceAvulsion = (0.30 * _juncFreqMult) min 1.0;
} else {
    ACME_junctionalBleedNorm      = (missionNamespace getVariable ["ACME_junctionalBleedBaseNorm", 0.10]) * _juncBleedMult;
    ACME_junctionalDPControl      = ACME_hcBase_junctionalDPControl;
    ACME_junctionalGauzeControl   = ACME_hcBase_junctionalGauzeControl;
    ACME_junctionalGauzeDPControl = ACME_hcBase_junctionalGauzeDPControl;
    ACME_junctionalChanceVelocity = (0.60 * _juncFreqMult) min 1.0;
    ACME_junctionalChanceAvulsion = (0.15 * _juncFreqMult) min 1.0;
};

// TBI. hardcore shortens the compensation budget and stays pfc-safe, so it never becomes instant.
ACME_tbi_compBudgetSeconds = if (ACME_hcEff_tbi) then { 480 } else { ACME_hcBase_tbi_compBudgetSeconds };

// rhythm hardcore is no longer a difficulty multiplier. it used to raise the torsades frequency and shorten the
// refractory windows, which made arrests noisier without teaching anything. it gates ROSC on the reversible
// cause being fixed now, see overrides/fn_updateCirculationState.sqf, which turns a code into a differential.
// the torsades tunables are therefore left at their baseline in both states, so there is nothing to apply and
// nothing to restore.
ACME_rhythm_torsadesChancePerTick      = ACME_hcBase_rhythm_torsadesChancePerTick;
ACME_rhythm_torsadesChanceSevere       = ACME_hcBase_rhythm_torsadesChanceSevere;
ACME_rhythm_torsadesRefractorySec      = ACME_hcBase_rhythm_torsadesRefractorySec;
ACME_rhythm_defibTorsadesRefractorySec = ACME_hcBase_rhythm_defibTorsadesRefractorySec;

ACME_nrb_flowLPM      = if (ACME_hcEff_nrb) then { 25 } else { ACME_hcBase_nrb_flowLPM };
// written from the baseline, never from the current value. the old code multiplied in place, which would have
// compounded 1.15x on every re-apply.
ACME_CS_exitFactor    = if (ACME_hcEff_cs) then { ACME_hcBase_CS_exitFactor * 1.15 } else { ACME_hcBase_CS_exitFactor };
ACME_DP_treatTimeMult = if (ACME_hcEff_dp) then { 2.0 } else { ACME_hcBase_DP_treatTimeMult };
ACME_DP_limbBleedMult = if (ACME_hcEff_dp) then { missionNamespace getVariable ["ACME_DP_limbBleedMultHardcore", 0.80] } else { ACME_hcBase_DP_limbBleedMult };

// the newer systems, following ACM's hardcore philosophy that the field cannot fully fix it.
// extravasation: severe leaks leave a worse permanent floor and recover more slowly, so the matched antidote and
// early recognition carry real weight instead of being optional.
if (ACME_hcEff_vesicant) then {
    ACME_vesicant_severeFloorStage = 1;  // a stage-1 exposure already leaves a lasting floor. it was 2.
    ACME_vesicant_recoverPerMin    = 0.30;  // a slower spontaneous recovery. it was 0.5.
} else {
    ACME_vesicant_severeFloorStage = ACME_hcBase_vesicant_severeFloorStage;
    ACME_vesicant_recoverPerMin    = ACME_hcBase_vesicant_recoverPerMin;
};

// blast lung: ARDS is reached sooner and from a lower severity, so ineffective ventilation punishes faster.
if (ACME_hcEff_blastLung) then {
    ACME_blastLung_ardsEnterSev  = 0.70;  // it was 0.85.
    ACME_blastLung_ardsEnterSecs = 40;  // it was 60.
} else {
    ACME_blastLung_ardsEnterSev  = ACME_hcBase_blastLung_ardsEnterSev;
    ACME_blastLung_ardsEnterSecs = ACME_hcBase_blastLung_ardsEnterSecs;
};

// hypothermia: passive self-rewarming is much weaker and the mandatory active-rewarming floor is higher, so an
// HPMK stops being optional.
if (ACME_hcEff_hypo) then {
    ACME_hypo_selfRewarmPerMin  = 0.05;  // it was 0.15.
    ACME_hypo_selfRecoverFloorC = 32;  // active rewarming is mandatory below 32 c. it was 30.
} else {
    ACME_hypo_selfRewarmPerMin  = ACME_hcBase_hypo_selfRewarmPerMin;
    ACME_hypo_selfRecoverFloorC = ACME_hcBase_hypo_selfRecoverFloorC;
};

// flight: trapped gas expands faster on the climb and g-loading bites a hypovolemic casualty harder.
if (ACME_hcEff_flight) then {
    ACME_altitude_ptxGrowRate  = 0.10;  // it was 0.06.
    ACME_flightG_maxResistDrop = 40;  // it was 28.
} else {
    ACME_altitude_ptxGrowRate  = ACME_hcBase_altitude_ptxGrowRate;
    ACME_flightG_maxResistDrop = ACME_hcBase_flightG_maxResistDrop;
};

true
