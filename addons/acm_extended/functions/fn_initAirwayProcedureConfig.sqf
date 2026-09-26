/*
 * Phase 22 subsystem initialization: Airway/head-position, RSI, chest-seal hardcore, ETT and rocuronium interaction tunables.
 *
 * Behavior-preserving extraction from ACME_fnc_postInit. Runtime event/PFH ownership
 * remains outside this helper and the call stays at the original initialization point.
 */

// ACM's own repositioning animations, matched loosely because they appear with suffixes and variants.
// the recovery position cancels head elevation. the rest only suspend it and it returns afterward.
ACME_headElev_acmCancelAnims = ["acm_recoveryposition"];
ACME_headElev_acmYieldAnims  = ["acm_genericcontinuous", "acm_pronecontinuous", "acm_lyingstate", "acm_cpr", "acm_cpr_stop"];

// fentanyl as RSI pretreatment.
// laryngoscopy is a noxious stimulus. the sympathetic response to it drives ICP up in a head injury, and
// fentanyl given early enough blunts that. both numbers below matter, and the second is the one people get
// wrong: 3 minutes to peak, so a dose pushed as the blade goes in has done almost nothing.
ACME_laryngo_icpSurge = missionNamespace getVariable ["ACME_laryngo_icpSurge", 4]; // B11 transient game calibration; no provider announcement
ACME_fent_minBluntMcg   = 50;  // an analgesic dose. below this, no blunting at all
ACME_fent_fullBluntMcg  = 200;  // roughly 2 to 3 mcg/kg, the pretreatment dose
ACME_fent_peakSec       = 180;  // 3 minutes to peak effect
ACME_fent_durationSec   = 1800;  // useful blunting gone by 30 minutes

// hardcore systems that model something real.
// chest seal: the vent clogs and a medic has to burp it. circulation: a pressor on an empty tank raises the
// number and starves the tissue. transfusion: the lethal triad as a loop rather than three separate bad
// numbers. ventilator: the machine delivers exactly what it is told, including a tidal volume that injures the
// lung.
// THE BURP GESTURE. the wheel over an applied seal lifts the corner, holds it open, and lays it back down. the
// three run off one timestamp and the art plays forwards then in reverse.
// the length of the chest seal one-shot, MEASURED. ffprobe reports sound/chest_seal_sfx.ogg at 2.171088 s.
// fn_chestSealSnd refuses to start a second copy inside that window, so a fast scroll cannot stack the clip on
// top of itself. it guards the AUDIO only: a refused sound never refuses the notch, so the peel still advances.
// re-cutting the audio means changing this one number.
ACME_cs_sealSndLen = 2.171;

// THE BURP HAS NO TIMING KNOBS. it moves one frame per scroll notch and holds wherever the medic stops, so
// there is nothing to tune. ACME_cs_burpPeelSec, ACME_cs_burpCloseSec, ACME_cs_burpOpenSec and
// ACME_cs_burpAutoCloseSec are all retired.

ACME_hcCirc_safeDeficit = 0.15;  // a pressor on a nearly full tank is fine
ACME_hcCirc_debtRate    = 0.9;  // tissue debt per second at full deficit
ACME_hcCirc_debtMax     = 100;

ACME_hcTx_coldDropPerMin = 0.22;  // degrees c per minute at 100 percent cold blood
ACME_hcTx_freeUnits      = 1;  // units before citrate starts binding calcium
ACME_hcTx_caDropPerUnit  = 0.06;

ACME_hcVent_safeMlKg  = 8;  // lung protective is 6 to 8 ml/kg
ACME_hcVent_viliRate  = 0.5;
ACME_hcVent_viliSatMax = 14;

ACME_vent_mvSensorDelaySec = 2.0;  // B20: M.V. shows --.-- for at least this long while the live flow estimate settles.

// what holds an et tube.
ACME_ETT_cuffResist   = 0.88;  // fraction of a scroll the inflated cuff eats. it creeps rather than slides.
ACME_ETT_cuffTearAt   = 14;  // clicks of hauling on an inflated cuff before the cords tear
ACME_ETT_deflateSec   = 3.2;  // held right click on the pilot balloon to let it down
// ACME_ETT_carinaPushes is gone. it used to be the number of deliberate pushes needed to force the tube past the
// carina, because the tube stopped dead at the seating depth. nothing stops it now: it goes as deep as it is fed
// and fn_ettmainstemtick supplies the consequence. see the note in fn_laryngoscroll.

// tunables that were only ever inline defaults.
// each of these was read with a fallback and never declared, so it worked and could not be changed.
ACME_pi_bleedHalfLifeSec   = 150;  // pressure cuff half-life, seconds
ACME_ettMainstemRate       = 0.55;  // saturation points per second lost to a one-lung tube
ACME_ettMainstemSatDrop    = 22;  // and the ceiling on that
ACME_ettMainstemCompliance = 0.55;  // compliance multiplier when one lung is doing the work
ACME_roc_paralysisThresh   = 0.55;  // rocuronium level counted as full paralysis
ACME_roc_awakeHRRate         = 0.35;  // bpm/s; stress is gradual rather than an immediate monitor spike.
ACME_roc_awakeHRMax          = 138;   // absolute HR-drive ceiling from awake paralysis alone.
ACME_roc_awakeResistMax      = 20;    // bounded SVR contribution from acute distress.
ACME_roc_awakeResistRate     = 0.30;  // SVR points/s while the perfusing patient remains aware/paralyzed.
ACME_roc_awakeResistClearRate = 1.2;  // SVR points/s after adequate sedation, arrest, or block release.
ACME_roc_postROSCStressDelay = 15;    // seconds after ROSC before acute awake-paralysis stress may build again.
// ACME_sed_adequateThresh is initialized once with the shared sedation settings above.
ACME_ettWakeGraceSec       = 5;  // seconds of bucking on a tube before they go back under
// B120 procedural airway reactivity.  Values are normalized game-effect thresholds, not clinical dose guidance.
ACME_laryngo_proceduralSedation = 0.75; // sedation load at/above this suppresses the persistent post-attempt irritation worker.
ACME_laryngo_irritationSec = 45;        // duration after an awake/under-sedated tube attempt.
ACME_laryngo_irritationPulseMin = 2.0;
ACME_laryngo_irritationPulseMax = 3.5;

// 1.3.0 adult vagal airway reflex. Routine adult laryngoscopy remains predominantly sympathetic.
// These are rare-event gameplay probabilities, not pediatric values and not clinical incidence claims.
ACME_laryngo_vagalPassChance       = missionNamespace getVariable ["ACME_laryngo_vagalPassChance",0.015];
ACME_laryngo_vagalManipChance      = missionNamespace getVariable ["ACME_laryngo_vagalManipChance",0.025];
ACME_laryngo_vagalHypoxiaAddMax    = missionNamespace getVariable ["ACME_laryngo_vagalHypoxiaAddMax",0.12];
ACME_laryngo_vagalRepeatAddPerTry  = missionNamespace getVariable ["ACME_laryngo_vagalRepeatAddPerTry",0.003];
ACME_laryngo_vagalRepeatAddMax     = missionNamespace getVariable ["ACME_laryngo_vagalRepeatAddMax",0.03];
ACME_laryngo_vagalDurationSec      = missionNamespace getVariable ["ACME_laryngo_vagalDurationSec",12];
ACME_laryngo_vagalBpmDrop          = missionNamespace getVariable ["ACME_laryngo_vagalBpmDrop",55];
ACME_laryngo_vagalMinTargetHR      = missionNamespace getVariable ["ACME_laryngo_vagalMinTargetHR",28];
ACME_laryngo_vagalResistDrop       = missionNamespace getVariable ["ACME_laryngo_vagalResistDrop",28];
