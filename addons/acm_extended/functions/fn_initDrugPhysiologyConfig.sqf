/*
 * Phase 20 subsystem initialization: Infusion PK, toxicity, antiarrhythmic and osmotherapy tunables.
 *
 * This is a behavior-preserving extraction from ACME_fnc_postInit. Keep runtime
 * event/PFH ownership in postInit or the owning subsystem; this helper only establishes
 * startup state and tunables in the same order as before.
 */

// infusion drug kinetic envelopes for the custom effects in this addon. ACM's own medicationlocal still
// handles the normal medication record, onset and effect curve. these govern the custom MAP and rhythm effects
// that do not exist in ACM.
ACME_infusion_pressorOnsetSec = 45;  // norepi and epi MAP support ramps in rather than appearing at once.
ACME_infusion_pressorOffsetSec = 120;  // pressor support decays after the line is stopped or removed, rather than dropping to zero.
ACME_rhythm_magTerminateEffect = 0.35;  // magnesium effect needed to terminate active torsades. a drip can achieve it.
ACME_rhythm_magSuppressEffect = 0.25;  // magnesium effect needed to suppress recurrence

// lidocaine, a class ib antiarrhythmic.
// this reads the same lidocaine value ACM does, through getcardiacmedicationeffects. at or above
// lidotherapeuticeffect a therapeutic dose counts as on board and the long washout clock restarts. while it is
// effective, lidocaine terminates vt-with-pulse and suppresses its recurrence, and it raises the conversion
// odds when a medic defibrillates vf or pulseless vt. at full effect the shock gives a deterministic ROSC.
ACME_rhythm_lidoTherapeuticEffect = 0.6;  // the ACM lidocaine cardiac-effect level that counts as a therapeutic dose on board.
ACME_rhythm_lidoFullSec    = 1800;  // holds full antiarrhythmic effect at least this long (30 min)
ACME_rhythm_lidoWashoutSec = 5400;  // ramps linearly to zero by here (1.5 h)
ACME_rhythm_lidoDefibBaseChance = 0.2;  // vf/pVT shock conversion floor while lidocaine is on board
ACME_rhythm_lidoDefibBoost      = 0.8;  // + effectiveness*boost -> 1.0 (deterministic) at full effect

// lidocaine serum-level pk accumulator. this is phase 1 of the toxicity model: accumulate and display.
// it tracks a real serum level in mcg/ml, so the toxicity arc has something past therapeutic to read. the ACM
// lidocaine effect saturates at 1.0 and cannot represent an overdose. there are two knobs.
// plateau: the steady level in mcg/ml is drip mg/min divided by clearancelmin. at 0.625, a 2 mg/min drip
// settles near 3.2, which is therapeutic. 4 gives about 6.4 and 8 gives about 12.8, the seizure band. lower
// clearance raises the plateau.
// speed: the half-life is compressed on purpose, about 5.5 min against about 100 min in life, so a too-fast
// drip or an impaired clearance reaches the toxic band inside a scenario instead of across many hours.
// impaired clearance, from active shock perfusion or a beta-blocker on board, multiplies clearance down. that
// raises the plateau and lengthens the effective half-life. nothing reads the level yet. this phase is
// calibration only.
ACME_lido_clearanceLmin = 0.40;  // l/min. the plateau in mcg/ml is drip mg/min divided by this. it was lowered from 0.625 so a dilute bedside-mixed bag run wide open reaches toxicity, which makes careless technique punishing.
ACME_lido_halfLifeSec   = 330;  // about a 5.5 min compressed elimination half-life. real lidocaine runs about 100 min. it is halved for faster onset and washout.
ACME_lido_shockClearFrac = 0.6;  // active shock multiplies clearance by this, because hepatic clearance is perfusion-limited.
ACME_lido_betaClearFrac  = 0.7;  // esmolol (beta-blocker) on board multiplies clearance by this

// lidocaine toxicity, phase 2: the shared generalized seizure. at or above seizurethreshold an unconscious
// patient seizes. The visible convulsion is the same 1.35x GestureSpasm3-6 sequence used by TBI and severe ACM
// nerve-agent seizures. the physiologic tell is apnea, because the dedicated seizure
// rr channel drives rr to seizureapnearr, which crashes SpO2 through ACM's native oxygen model. a sympathetic
// tachycardia runs with it. the arc is active, then postictal, then resolve. it recurs while the patient stays
// toxic and untreated, which is status epilepticus. midazolam on board, at a count of seizuremidazolamsupp or
// more, aborts the active seizure to postictal and suppresses a re-trigger.
ACME_lido_seizureThreshold      = 12;  // mcg/ml at/above which a seizure starts
ACME_lido_seizureClearThreshold = 10;  // must fall below this or the seizures recur. the hysteresis gives status epilepticus.
ACME_lido_seizureMaxSec         = 120;  // HARD cap: 2 minutes seizing straight, then a forced cooldown
ACME_lido_seizureCooldownSec    = 30;  // forced postictal cooldown after an episode, with depressed breathing and no seizing.
ACME_lido_seizureApneaRR        = 0;  // active-seizure rr. a generalized seizure is apneic, because tensed muscles cannot breathe.
ACME_lido_seizurePostictalRR    = 9;  // depressed rr during the postictal cooldown phase
ACME_lido_seizureHRBoost        = 35;  // + bpm sympathetic tachycardia during the active seizure

// dose-graded refractory benzo control. the midazolam needed to terminate and suppress is the base plus
// refractory times the level above the seizure threshold. higher toxicity is more refractory, so the benzo can
// be overwhelmed and the seizure breaks through as the benzo washes out or the level climbs. that is the
// pressure toward stopping the drip and giving lipid.
ACME_lido_benzoClassnames        = ["Midazolam", "Midazolam_IV"];  // classnames a benzo can be recorded under. the narc box appends _IV for an iv push. add others here.
ACME_lido_seizureBenzoBase       = 1;  // midazolam administrations, as an effective count, that control a seizure right at the threshold.
ACME_lido_seizureBenzoRefractory = 0.1;  // extra administrations needed per mcg/ml above the seizure threshold.

// Shared seizure control. These are internal physiology tunables, not separate medication exceptions.
// Midazolam preserves the old 1-effective-count baseline. Propofol reaches baseline control at roughly
// induction-scale native effect. Ketamine receives no control credit at low analgesic exposure and ramps
// into anticonvulsant effect as anesthetic exposure is reached.
ACME_seizure_driveBase = 1.0;
ACME_seizure_driveTBI = 1.0;
ACME_seizure_driveSarin = 1.0;
ACME_seizure_driveDebug = 1.0;
ACME_seizure_midazolamControlWeight = 1.0;
ACME_seizure_propofolControlWeight = 1.0;
ACME_seizure_ketamineControlFloor = 0.30;
ACME_seizure_ketamineControlWeight = 1.0;
ACME_seizure_ketamineExtraWeight = 0.35;
ACME_seizure_controlHysteresis = 0.10;
ACME_seizure_controlCap = 4.0;

// seizure body motion. BI GestureSpasm3-6 are played as ACME-only gesture aliases at 1.35x and chained on
// GestureDone, so each spasm completes before the next one begins. The old setDir tremor, random yaw jitter,
// burst/pause oscillator, repeated ragdoll flops and seizure camera shake are retired.
ACME_seizure_motionEnabled = 1;  // legacy mission-level master toggle retained for compatibility
ACME_seizure_settleDur     = 1.5;  // let the one-time onset collapse settle before the first gesture

// Legacy visual tuning names are retained as inert compatibility values so old missions/settings do not error.
// fn_seizureMotion no longer reads any of them.
ACME_seizure_jerkHz         = 11;
ACME_seizure_yawAmp         = 1.2;
ACME_seizure_yawChaos       = 0.75;
ACME_seizure_burstMin       = 1;
ACME_seizure_burstMax       = 2;
ACME_seizure_pauseMin       = 1;
ACME_seizure_pauseMax       = 2.5;
ACME_seizure_ragdollChance  = 0.7;
ACME_seizure_ragdollDur     = 1.2;
ACME_seizure_camShake       = 1;

// ACM Sarin/nerve-agent seizure activity now enters the same seizure state machine instead of using intermittent
// local camera shake. 10 is ACM's original onset for the Midazolam-suppressible seizure/shake effect; the separate
// airway-spasm/critical band still begins at buildup 60.
ACME_sarin_seizureThreshold = 10;

// TBI pre-herniation seizures. this is the per-tick chance to start a seizure while the brain sits in the
// pre-herniation decompensation stage, with cushing engaged and no herniation yet. a high value gives a
// variable onset that is near certain to fire and to recur while the stage holds, so a decompensating brain
// seizes before it herniates.
ACME_tbi_seizureChancePerTick = 0.3;

// lidocaine toxicity, phase 3: cardiac toxicity, with bradycardia, hypotension and bradyasystolic arrest.
// above the cardiac threshold the conduction fails. the seizure tachycardia gives way to progressive
// bradycardia, as hr drives from the baseline toward cardiacbradyfloor and scales across cardiacthreshold to
// arrestthreshold. the slow rate plus a layered vasodilation, cardiacresistdrop as a negative peripheral
// resistance, drive the hypotension. caught early it reverses with the level, once the medic stops the drip or
// gives lipid. at or above arrestthreshold it tips into asystole, a real arrest that needs CPR and ROSC plus
// removal of the cause. the bradycardia also stands in for high-grade av block, because the slow rate is the
// hemodynamic tell. a widened QRS morphology on the ecg is a later refinement.
ACME_lido_cardiacThreshold = 15;  // mcg/ml at/above which cardiac toxicity begins
ACME_lido_arrestThreshold  = 25;  // mcg/ml at/above which it tips into bradyasystolic arrest
ACME_lido_cardiacBradyFloor = 30;  // the hr in bpm that the bradycardia drives toward at the arrest threshold.
ACME_lido_cardiacResistDrop = 45;  // max vasodilation, as a peripheral-resistance drop, at the arrest threshold.
ACME_rhythm_magRefractorySec = 20;  // brief refractory after magnesium terminates torsades
ACME_rhythm_esmololControlEffect = 0.35;  // esmolol effect needed to rate-control AFib-RVR, or to terminate SVT and atrial tach.
// esmolol sinus-rate beta-blockade. this addon owns it, and config zeroes ACM's esmolol hr adjustment because
// it misfired for a continuous infusion. on a sinus patient with no custom rhythm, esmolol slows the resting
// rate toward the target hr times sinusfactor as the bounded effect develops. it has a floor, so it never
// bradys hard, and it never raises the rate.
ACME_esmolol_sinusOnsetEff = 0.08;  // esmolol effect at which the sinus slowing begins to engage
ACME_esmolol_sinusFullEff  = 0.6;  // esmolol effect at which the slowing reaches full depth
ACME_esmolol_sinusFactor   = 0.78;  // resting-hr multiplier at full effect. 0.78 gives a sinus rate about 22 percent slower.
ACME_esmolol_sinusFloorHR  = 55;  // hard floor. therapeutic sinus esmolol never drives hr below this.
// esmolol serum estimate and overdose. the serum in mcg/ml is the eased drip in mg/min divided by clearance.
// it is the readout in the debug panel and the trigger for overdose. below serumtherapeuticlow it is
// subtherapeutic. between low and high it is the therapeutic rate-control window. above high the beta-blockade
// turns toxic, with a high-grade av block, where hr drives below the normal floor toward overdosefloorhr, plus
// hypotension from a peripheral-resistance drop of up to overdoseresistdrop. the overdose deepens linearly
// from serumtherapeutichigh up to serumoverdosemax.
ACME_esmolol_clearanceLmin        = 3.5;  // serum scale. the serum in mcg/ml is drip mg/min divided by this. it is a game value, not real pk.
ACME_esmolol_serumTherapeuticLow  = 0.5;  // below this: subtherapeutic
ACME_esmolol_serumTherapeuticHigh = 2.0;  // above this: overdose begins (heavy block)
ACME_esmolol_serumOverdoseMax     = 5.0;  // the serum at which the overdose effects reach full depth. the dial maxes near 5.7.
ACME_esmolol_overdoseFloorHR      = 35;  // the hr that the overdose bradycardia, an av block, drives toward at full overdose.
ACME_esmolol_overdoseResistDrop   = 45;  // max peripheral-resistance drop, which is the hypotension, at full overdose.
// fast-infusion consequences for amiodarone and magnesium, the push-slow drugs. each scales off its eased
// drip rate in mg/min. a sane drip does nothing and a wide-open clamp turns dangerous. fastonsetmgmin is where
// the penalty begins and fastmaxmgmin is where it is full. amiodarone vasodilates and gives hypotension only.
// magnesium suppresses the node, driving bradycardia toward bradyfloorhr, and drops the pressure through
// resistance. calcium is absent here, because the elemental overdose model below owns its fast-push cascade,
// covering rate and serum into vasodilation, bradycardia, arrhythmia and arrest. onsetsec and offsetsec ease
// the rate so it tracks the clamp with no flicker.
ACME_infusionTox_onsetSec   = 15;
ACME_infusionTox_offsetSec  = 35;
ACME_infusionTox_bradyFloorHR = 50;  // hr the magnesium fast-push bradycardia drives toward at full
ACME_amio_fastOnsetMgMin = 25;   ACME_amio_fastMaxMgMin = 90;   ACME_amio_fastResistDrop = 35;  // amiodarone hypotension. the standard 150 mg across 10 min, or 15 mg/min, stays clear.
// the elemental overdose model below owns the calcium fast-push, not a salt-rate fast fraction.
ACME_mag_fastOnsetMgMin  = 800;  ACME_mag_fastMaxMgMin  = 2500; ACME_mag_fastResistDrop  = 22;  // magnesium: therapeutic ~200-400 mg/min is well clear

// calcium serum level and overdose model, for chloride and gluconate.
// the serum tracks elemental calcium excess in mg/dl above baseline. each salt contributes elemental calcium at
// its own fraction. 1 g of CaCl2 10 percent is about 273 mg, or 13.6 meq, elemental. 1 g of ca-gluconate 10
// percent is about 93 mg, or 4.65 meq. gluconate is therefore about 3 times gentler at the same salt mg/min,
// which is why it is the gentle salt. this is a first-order accumulator like lidocaine, where the plateau is
// elementaldrive mg/min divided by clearance. a compressed half-life lets a fast push spike the level and a
// stopped drip clear it. the therapeutic band is narrow. a proper slow correction, 1 g of CaCl2 across about
// 10 min at about 27 mg elemental/min, settles near 0.45 mg/dl, well under the 1.0 mg/dl overdose onset. a fast
// push, 1 g in about 1 min at about 273 mg elemental/min, drives both the level and the rate term into the
// overdose zone.
ACME_ca_elementalFrac = createHashMapFromArray [["CalciumChloride", 0.273], ["CalciumGluconate", 0.093]];
ACME_ca_serumClearance   = 60;  // elemental mg/min per mg/dl of plateau. the serum in mg/dl is elementaldrive divided by this.
ACME_ca_serumHalfLifeSec = 120;  // compressed serum half-life (calcium redistributes fast)
ACME_ca_serumTherapeuticHigh = 1.0;  // mg/dl of excess. the overdose band begins here, and the therapeutic window below it is narrow.
ACME_ca_serumOverdoseArrest  = 4.0;  // mg/dl excess: full overdose (arrest-capable) at/above here
// rate term, in elemental mg/min. too fast bites before the serum accumulates, because a high concentration
// reaches the heart too quickly. onset is where the symptoms begin and max is where the rate term is full.
ACME_ca_rateOnsetElemMgMin = 100;  // ~1 g CaCl2 over ~2.7 min
ACME_ca_rateMaxElemMgMin   = 280;  // ~1 g CaCl2 in ~1 min (rapid push)
// the overdose symptoms scale with the combined severity, taking the worse of rate and serum.
ACME_ca_overdoseResistDrop = 45;  // SVR drop at full overdose. this is terminal vasoplegia and gives hypotension near arrest.
ACME_ca_overdoseConstrictBand = 0.6;  // the _caOd value, 0 to 1, where acute vasoconstriction peaks. vasoplegia takes over above it.
ACME_ca_overdoseConstrictAdd  = 40;  // peak SVR rise. this is acute-hypercalcemia hypertension, the calcium-push bp spike.
ACME_ca_overdoseArrestFloorHR = 18;  // the hr that the bradycardia drives toward at full overdose. below 40 it enters ACM's arrest path.
ACME_ca_overdoseArrhythmiaFrac = 0.55;  // the severity at which the picture is a brady arrhythmia, junctional or escape.
// hypocalcemia pressor gate. ionized ca, where 1 is normal, blunts both catecholamines equally, because the
// transduction needs calcium.
ACME_ca_pressorGateStart = 0.85;  // ionized ca at/above which pressors work fully
ACME_ca_pressorGateFull  = 0.6;  // ionized ca at/below which the gate is maximal
ACME_ca_pressorGateMin   = 0.5;  // pressor effectiveness multiplier at full hypocalcemia

// amiodarone serum level, for display and parity. the rate and cumulative terms already model the
// consequences.
// the drip consequences of amiodarone are the fast-infusion hypotension, acme_amio_fast* above, and the
// cumulative qt ceiling into torsades, acme_rhythm_amio*. this serum accumulator is the readable level for the
// debug panel and gives parity with the other drips. the standard load is 150 mg across 10 min, or 15 mg/min.
ACME_amio_serumClearance   = 6;  // mg/min per mg/l plateau (serum mg/l = drive / this)
ACME_amio_serumHalfLifeSec = 420;  // compressed
ACME_amio_serumTherapeuticLow  = 1.0;  // mg/l
ACME_amio_serumTherapeuticHigh = 2.5;  // mg/l (above = fast-infusion / accumulation territory)

// generalized serum tracking for every other infusion, for display and the therapeutic band.
// the drugs with a bespoke serum and effect model, lidocaine, esmolol, calcium and amiodarone, are handled
// above. every other infusible drug gets a first-order serum accumulator here, so the debug panel can show its
// level and therapeutic band. the table maps med to [clearancelmin, halflifesec, theraplow, theraphigh,
// unitlabel], where the plateau is drip mg/min divided by clearancelmin.
ACME_infusion_pk = createHashMapFromArray [
    ["Epinephrine",    [0.30, 120, 0.02, 0.20, "mcg/mL"]],
    ["Norepinephrine", [0.25, 90,  0.01, 0.10, "mcg/mL"]],
    ["Ketamine",       [1.20, 180, 0.50, 3.00, "mcg/mL"]],
    ["Fentanyl",       [0.80, 200, 0.001, 0.003, "mcg/mL"]],
    ["Morphine",       [1.50, 300, 0.01, 0.08, "mcg/mL"]],
    ["Midazolam",      [0.50, 600, 0.05, 0.25, "mcg/mL"]],
    ["Ondansetron",    [0.60, 240, 0.02, 0.15, "mcg/mL"]],
    ["TXA",            [0.20, 360, 5.00, 15.00, "mcg/mL"]],
    ["Ceftriaxone",    [0.15, 480, 20.0, 150.0, "mcg/mL"]],
    ["Magnesium",      [0.80, 1800, 2.00, 4.00, "mg/dL"]]
];
// epinephrine chronotropy. this addon owns it, and config zeroes ACM's epi hr adjustment because it
// accumulated for a continuous drip. hr rises with the epi-specific infusion drive in mg/min, the same eased
// value the pressor system uses, so a push and a drip both raise hr and an infusion cannot run away. it is
// skipped in shock, because the shock arc already includes pressor support. wide open, near 12 mcg/min or
// 0.012, lands close to full boost.
ACME_epi_chronoOnsetMgMin = 0.0005;  // epi drive (mg/min) at which the hr rise begins to engage
ACME_epi_chronoFullMgMin  = 0.015;  // epi drive (mg/min) at which the hr rise reaches full boost
ACME_epi_chronoBoostBpm   = 50;  // bpm added to the resting hr target at full epi drive
ACME_infusion_epiArrhythmiaOnsetSec = 60;  // the distal epi drip arrhythmia check is delayed, so there is no instant rhythm flip on hang.
// ideal norepinephrine drip recipe, for levophed. this is the most effective ICP treatment when CPP is the
// problem. 4 mg in 250 ml of saline gives 16 mcg/ml. start at 30 gtt/min on a 60 gtt/ml microdrip set, which is
// about 0.5 ml/min or about 8 mcg/min, near 0.05 to 0.1 mcg/kg/min by weight, then titrate to a MAP of 80 to 90
// and a CPP of 60 to 70. use a clean route only, an upper iv or an io. a mid or lower peripheral limb iv makes
// it behave like dirty peripheral epi, with a surge and ICH.
ACME_tbi_norepiDripMg = 4;  // mg of norepi in the bag
ACME_tbi_norepiDripVolMl = 250;  // ml carrier (saline)
ACME_tbi_norepiDripGtt = 30;  // gtt/min starting rate
ACME_tbi_norepiDoseLowMcgKgMin = 0.05;  // titration floor
ACME_tbi_norepiDoseHighMcgKgMin = 0.1;  // titration ceiling for the starting rate

// blood-before-pressor gate and pressor behavior.
ACME_tbi_pressorOnEmptyPenalty = 0;  // todo[ref] severity penalty for pressor-on-empty (0 = off)

// osmotherapy per agent: the ICP drop, the na+ rise and the reference dose.
// ACME_tbi_sodiumCeiling moved to the CBA addon options, under TBI tuning. do not assign it here.
ACME_tbi_baseSodium = 140;  // todo[ref] baseline na+
ACME_tbi_osmICPdrop_HTS3 = 8;  // todo[ref]
ACME_tbi_osmNaRise_HTS3 = 3;  // todo[ref]
ACME_tbi_osmRefDose_HTS3 = 250;  // todo[ref] ml
ACME_tbi_osmICPdrop_Mannitol = 8;  // todo[ref]
ACME_tbi_osmNaRise_Mannitol = 0;  // todo[ref] (mannitol: diuresis, watch hypotension)
ACME_tbi_osmRefDose_Mannitol = 500;  // ml. a full 500 ml bag delivers the calibrated ICP drop, which matches HTS at 250 ml.
