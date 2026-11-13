/*
 * Phase 21 subsystem initialization: Calcium/citrate, fluid-overload edema and circulation resuscitation tunables.
 *
 * Behavior-preserving extraction from ACME_fnc_postInit. Values and ordering inside
 * this domain are intentionally unchanged.
 */

// calcium and citrate. a massive transfusion causes hypocalcemia, a lethal-triad leg.
ACME_ca_citrateThreshold = 2.0;  // existing standard baseline, formerly set by applyHardcore
ACME_ca_citratePerLiter = 0.22;  // ionized-ca deficit per l over threshold (normalized)
ACME_ca_creditPerGram = 0.12;  // ionized-ca restored per 1 g CaCl2 pushed
ACME_ca_floor = 0.45;  // lowest normalized ionized ca (1.0 = normal)
ACME_ca_mapDropPerUnit = 40;  // mmhg MAP drop at zero ionized ca (contractility)
ACME_ca_coagMaxMult = 1.4;  // bleed-rate multiplier at the ionized-ca floor
ACME_ca_gramsPerDose = 1;  // CaCl2 grams per push action
// over-resuscitation pulmonary edema
ACME_edema_threshold = 0.2;  // accumulated Overload_Volume above which the crackles are audible, with the dead-band.
                                       // model. the overload starts to build past 200 ml of excess, so the crackles trail true over-resus.
ACME_edema_fullSpan = 1.6;  // overload above the threshold for full crackle and edema severity, 0.2 plus 1.6. the plateau is 1.5 l.
                                       // at about 81 percent severity, so even a maxed over-resus reads as heavy but not absolute edema.
// fluid-overload accrual control. the total-excess model runs dead-band, then a reasonable rise, then a
// plateau, and it always tapers.
ACME_edema_deadband = 0.2;  // ml over capacity as grace before any edema accrues. 0.2 l is 200 ml. you can top a
                                       // patient off, or replace lost volume freely. only true over-resuscitation past this point counts.
ACME_edema_accrueScale = 1.0;  // gain from the over-fill rate into edema. 1.0 raises overload about 1 to 1 with how far past the
                                       // dead-band you push, so a slow drip builds slowly and a pressure bag builds fast. lower is gentler.
ACME_edema_overloadCap = 1.5;  // hard cap and plateau on accumulated Overload_Volume. over-filling climbs toward this and stops.
                                       // was effectively unbounded, because ACM integrated the raw over-capacity each tick to 4.0 and above.
ACME_edema_taperPerSec = 0.01;  // the instant fluid is not pushed past the dead-band, overload always tapers at this
                                       // rate, which clears 1.5 to 0 in about 2.5 min, even while the patient is still over capacity. raise it to
ACME_edema_breathPenaltyMax = 0.35;  // max gas-exchange, or breathing-effectiveness, loss at the overload cap. it applies multiplicatively in getBreathingState, exactly like a hemothorax.
ACME_edema_spo2Floor = 85;  // legacy. the old direct SpO2 cap floor. edema works through breathing effectiveness now, so nothing uses it. it is kept so any external reference still resolves.
ACME_edema_tachypneaMax = 32;  // rr target at full edema (drives fast crackles)
ACME_edema_debugInduceVolume = 1.8;  // the Overload_Volume the debug toggle pins. it was bumped to 1.8 to still hit full severity.
// Push-dose washout uses the server medication policy. The response magnitude is a circulation setting.
ACME_circ_pushDoseMAPcap = 35;  // ceiling on stacked push-dose support
ACME_circ_pushDoseBolusMcg = 10;  // mcg per push (1 ml of 1:100,000)
// push-dose epi chronotropy. a bolus raises hr, and bp follows through the cardiac output. it ties to the live
// dose, so a 10 mcg push gives plus 20 bpm at peak and decays with the bolus. it is skipped in shock, because
// the shock arc already folds it in.
ACME_circ_pushDoseChronoBpmPerMcg = 2.0;  // bpm of hr boost per mcg of push-dose epi on board
ACME_circ_pushDoseChronoMaxBpm = 55;  // cap on the push-dose hr boost (stacked boluses)
// vasopressor bp through real resistance, for norepi and the non-epi share of any pressor. bpoffset is dead,
// because getbloodpressure is final. a vasoconstrictor therefore raises bp by raising SVR, which ACM reads as
// bp = co * r. this value is the resistance units added per mmhg of pressor MAP support. ACM's baroreflex damps
// it at a normal MAP and lets it land when the patient is hypotensive, so the net bp rise near normal is
// smaller than this suggests. tune to taste.
ACME_pressor_resistPerMmHg = 2.0;
// ICH. an epi-driven MAP overshoot above the threshold bleeds, and it is worse on a TBI brain.
// ACME_circ_ichMAPThreshold moved to CBA, under circulation.
ACME_circ_ichSeverityPerSec = 0.01;  // ICH accrual rate at 20 mmhg over
// distal-peripheral drip and pressor hypertensive surge, on the mid limb and lower limb.
ACME_circ_hyperSpikeHalfLife = 25;  // s, brief surge decay
ACME_circ_hyperSpikeMAP = 55;  // transient MAP surge from erratic distal catecholamine delivery.
ACME_circ_distalDripHazardPerMin = 0.2;  // plain medicated drip, distal limb
ACME_circ_distalPressorHazardPerMin = 0.6;  // distal pressor, higher surge risk
