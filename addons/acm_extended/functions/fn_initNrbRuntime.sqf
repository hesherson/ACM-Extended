/*
 * Phase 23 runtime ownership: Non-rebreather oxygen configuration and runtime tick registration.
 *
 * Extracted intact from ACME_fnc_postInit. The helper is invoked synchronously at the
 * original registration point so CBA handler/PFH order is unchanged.
 */

// NRB oxygen tool, the non-rebreather mask.
ACME_nrb_activePatients = [];  // patients currently masked
ACME_nrb_spo2Floor      = 95;  // passive oxygen support target while the patient is breathing
ACME_nrb_spo2RatePerSec = 0.35;  // slow passive SpO2 max gain per second. it is breath-gated and not instant.
ACME_nrb_minRR          = 1;  // rr must be above this or the NRB gives no oxygen benefit
ACME_nrb_fullEffectRR   = 12;  // rr where passive mask support reaches full effect
ACME_nrb_minAirway      = 0.05;  // blocked airway = no useful oxygen uptake
ACME_nrb_minBreathing   = 0.05;  // no effective ventilation = no useful oxygen uptake
ACME_nrb_maxDistance    = 6;  // m the applying medic can move before the mask is yanked, in the AED style.
ACME_nrb_flowLPM        = 15;  // l/min the NRB draws from the medic's tank while flowing
ACME_nrb_tankCapacityL  = 425;  // ACME_OxygenTank_425 nominal cylinder size in l, from the ACM source.
ACME_nrb_tankUnits      = 283;  // reserve units in a full tank, the CfgMagazines count, from the ACM source.
// 425/283 is about 1.5 l per reserve unit. at 15 l/min that is 1 unit every 6 s, which matches ACM's BVM. the
// tank lasts about 28 min.
// this sustains the o2 flow while the mask is on and tidies up the looping sfx on death or removal.
[{call ACME_fnc_nrbTick}, 0.5, []] call CBA_fnc_addPerFrameHandler;
