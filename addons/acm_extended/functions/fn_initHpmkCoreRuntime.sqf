/*
 * Phase 24 subsystem ownership: HPMK rewarming, LifeWarmer coupling and core thermal tick registration.
 *
 * Extracted intact from ACME_fnc_postInit and invoked at the original point so startup
 * sequencing and CBA registration order are preserved.
 */

// NAR HPMK, the hypothermia warming blanket.
ACME_hpmk_activePatients  = [];  // patients currently wrapped
ACME_hpmk_warmRatePerMin  = 0.6;  // passive rewarming rate (deg c / min) for a stable patient
ACME_hpmk_minMAP          = 60;  // MAP floor below which passive rewarming can't work
ACME_hpmk_exposedWarmFactor = 0.80;  // while the HPMK chest is exposed for care, rewarming runs at 80 percent, because the broken seal over the chest and left arm loses heat.
// LifeWarmer quantum, an inline blood warmer.
// when a medic sets up a blood line with the warmer, flagged on the patient at bag-hang time, every liter of
// blood that transfuses adds this many degrees c toward 37. a 500 ml unit adds about 0.4 c and a 4-unit massive
// transfusion about 1.6 c, which offsets the lethal-triad cooling of cold product.
ACME_warmer_tempPerLiter  = 0.8;
// this rewarms wrapped, perfusing patients slowly toward normothermic, and prunes the dead and removed.
[{call ACME_fnc_hpmkTick}, 5, []] call CBA_fnc_addPerFrameHandler;
// Visual class for an HPMK that has been dropped after a wrapped casualty becomes mobile. Wrapped patients never
// receive a world object; the dropped representation uses a collision-free network anchor plus client simpleObject.
// Resolve at initialization when all vehicle configs are loaded.
ACME_hpmk_blanketClass = ["Land_EmergencyBlanket_02_discarded_F","ACME_HPMK_Open"] select
    (isClass (configFile >> "CfgVehicles" >> "ACME_HPMK_Open"));
