// drugs that can infuse into a line, either a saline carrier or a running blood line. the list holds calcium
// chloride, calcium gluconate, TXA, ceftriaxone and other antibiotics, ketamine, fentanyl, morphine,
// midazolam, epinephrine, norepinephrine and ondansetron. amiodarone and lidocaine stay because both are
// valid drips.
// B48: ACM_MEDICATION_VIALS is a preprocessor macro, not a literal runtime variable. In ACM's
// script_macros.hpp it expands to ACM_circulation_MedicationVialList. Read and repair that real registry.
// The literal missionNamespace key "ACM_MEDICATION_VIALS" used by B45-B47 was never consumed by ACM.
private _acmVials = +(missionNamespace getVariable ["ACM_circulation_MedicationVialList", []]);
if (_acmVials isEqualTo []) then {
    _acmVials = ("getNumber (_x >> 'ACM_isVial') > 0" configClasses (configFile >> "CfgWeapons")) apply {configName _x};
};
// Hide the deprecated cardiac-epi alias from presentation while preserving compatibility in the stock counter.
_acmVials = _acmVials - ["ACM_Vial_EpinephrineCardiac"];
_acmVials pushBackUnique "ACME_Vial_EpinephrineCardiac";
[[["medicationVialList", +_acmVials]]] call ACM_circulation_fnc_setLocalUiState;
missionNamespace setVariable ["ACME_medicationVialRegistryFull", +_acmVials];
// Propofol remains available in the Narc Box for syringe boluses. Its emulsion
// bottle is spiked directly; it is not one of the medications mixed into saline.
ACME_infusion_allowedMedications = ["Amiodarone", "Epinephrine", "Norepinephrine", "Lidocaine", "Ketamine", "TXA", "Fentanyl", "Morphine", "Midazolam", "Ondansetron", "CalciumChloride", "CalciumGluconate", "Ceftriaxone"];
ACME_syringe_pushSecPerMl = 1.0;  // modeled manual IV push duration per mL for rate-sensitive adverse effects.
ACME_syringe_pushMinSec = 1.5;
ACME_syringe_pushMaxSec = 10;
ACME_syringe_imDeliverySec = 3;
// "Saline" is the standard crystalloid carrier. "Esmolol" and "HTS" are premixed transfusable bags. they ride
// ACM's fluid system as their own type. fn_syncpremixedbags attaches their drug and also pushes the exact type
// string that ACE's ivbag produces, so this list tolerates case at runtime.
// magnesium and mannitol are absent on purpose. they are standalone premixed add-bag bags, not something you
// prepare an infusion into. handleinfusions still delivers their drug and osmo because it accepts any type in
// ACME_infusion_premixedByType.
ACME_infusion_allowedBagTypes = ["Saline"];  // only a normal saline bag can receive an injected medication, into any remaining volume. premixed bags are serviced separately through ACME_infusion_premixedByType.
// crystalloid carrier fluids that can hold a mixed drug. the 250, 500 and 1000 ml bags register as type
// "PlasmaLyte" and the 50 and 100 ml bags as "Saline". both must count as carriers. if they do not, a prepared
// PlasmaLyte bag never matches its new bag in findNewestBagContext and stays a plain fluid in the menu.
ACME_infusion_carrierTypes = ["Saline", "PlasmaLyte"];
// y-line flush cadence. a y blood line needs a flush only after this many units or this much volume in ml of
// blood. a real line does not need a saline flush until the second unit.
ACME_YFlushAfterUnits  = 2;
ACME_YFlushAfterVolume = 1000;
// a flush drains this much saline in ml across this many seconds. the flow is gradual and then stops.
ACME_YFlushVolume  = 50;
ACME_YFlushSeconds = 5;
// diagnostic. this logs [ACME-ysaline] lines to the .rpt for the y reserve clamp. the master debug switch
// gates it.
// hypertonic saline bags run through the roller clamp path for osmotherapy. a flag stops the mod from treating
// them as volume-resuscitation crystalloid.
ACME_infusion_hypertonicBagTypes = ["HTS3"];
// agents whose delivered volume drives osmotherapy and an ICP drop instead of an ACM medication pulse.
// handleinfusions routes these to fn_tbiapplyosmotherapy.
ACME_infusion_osmoticAgents = ["HTS3", "Mannitol"];
ACME_infusion_pressorMedications = ["Epinephrine", "Norepinephrine"];
ACME_infusion_allowedVials = ACME_infusion_allowedMedications apply {[_x] call ACME_fnc_vialClass};
// B73: a displayed 0.01 mL vial remnant is below useful draw resolution and may be discarded. This also cleans
// old ledgers stranded by plunger endpoint rounding so the next deliberately selected vial is not blocked by 0.01 mL.
ACME_vialDiscardResidualMl = 0.0105;
// Local tally cache. Accepted component records own the mixture; there is no push-count limit.
// Injecting commits inventory and cannot be undone by closing preparation.
ACME_infusion_bagTally = [];
ACME_infusion_syringeExtraDrawItems = [];  // extra non-infusion items for the syringe draw list. mannitol is a hung bag now, not a push.

// premixed drug bags: esmolol, HTS and magnesium. these hang in ACM's native add bag panel beside saline,
// plasma and blood. each pairs a carryable bag item in CfgWeapons with an iv fluid class in
// ace_medical_treatment >> iv, defined in config.cpp, that gives its type and volume. ACM transfuses the volume
// and fn_syncpremixedbags attaches the drug.
// ACM models esmolol, HTS and calcium as vials and syringe pushes, not bags. config.cpp supplies the data
// strings and bag items that make the bags work.
ACME_bag_useDistinctType = true;

// active bag fluid type in lower case maps to [medication, totaldosemg]. the mod attaches this when the bag
// goes active. the key is lower case for case tolerance. magnesium 2 g in 50 ml enters ACM's medication curve
// and stops torsades only after it reaches therapeutic effect. the HTS mg value is nominal because volume
// drives osmotherapy.
ACME_infusion_premixedByType = createHashMapFromArray [
    ["esmolol",   ["Esmolol", 2500]],
    ["hts",       ["HTS3", 7500]],
    ["magnesium", ["Magnesium", 2000]],
    ["mannitol",  ["Mannitol", 100000]]
];
