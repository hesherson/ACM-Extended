// this appends our bags to ACM's fluid candidate list. our xeh_postinit runs after ACM's because of
// requiredaddons, so the arrays exist. the isnil guard is a safeguard.
if (!isNil "ACM_circulation_Fluids_Array" && {!isNil "ACM_circulation_Fluids_Array_Data"}) then {
    private _items = ["ACME_EsmololBag", "ACME_HTSBag", "ACME_MagnesiumBag", "ACME_MannitolBag", "ACME_PlasmaLyteBag", "ACME_PlasmaLyteBag_500", "ACME_PlasmaLyteBag_250", "ACME_PlasmaLyteBag_100", "ACME_SalineBag_50", "ACME_SalineBag_100"];
    private _data  = ["EsmololIV_250", "HTSIV_250", "MagnesiumIV_50", "MannitolIV_500", "PlasmaLyteIV_1000", "PlasmaLyteIV_500", "PlasmaLyteIV_250", "PlasmaLyteIV_100", "SalineIV_50", "SalineIV_100"];
    {
        private _item = _x;
        private _fluidData = _data select _forEachIndex;
        private _index = ACM_circulation_Fluids_Array find _item;
        if (_index < 0) then {
            ACM_circulation_Fluids_Array pushBack _item;
            ACM_circulation_Fluids_Array_Data pushBack _fluidData;
        } else {
            // Keep the two parallel ACM arrays paired even if another addon rebuilt or partially modified them.
            while {count ACM_circulation_Fluids_Array_Data <= _index} do { ACM_circulation_Fluids_Array_Data pushBack ""; };
            ACM_circulation_Fluids_Array_Data set [_index, _fluidData];
        };
    } forEach _items;
};

ACME_infusion_bodyParts = ["head", "body", "leftarm", "rightarm", "leftleg", "rightleg"];
ACME_infusion_dropSets = [10, 15, 20, 60];
// default drop set in gtt/ml for a new infusion before the medic picks one. this had no definition before, so
// registerBagMedication, handleinfusions, the register, give and format prepared calls, and adjustDripRate all
// resolved to nil. the ml/s math then broke and delivered nothing. 20 gtt/ml matches the fallback that the
// clamp dialog already used.
ACME_infusion_defaultDropSet = 20;
ACME_infusion_minDropsPerMinute = 0;
ACME_infusion_defaultClampPosition = 1;
// wheel geometry, relative to the clamp art rect. 0 is the top edge and 1 is the bottom.
ACME_infusion_clampTravelTop = 0.186;  // wheel center at 0% open (calibrated to reference renders)
ACME_infusion_clampTravelBottom = 0.849;  // wheel center at 100% open (calibrated to reference renders)
ACME_infusion_clampWheelXRatio = 0.49;  // wheel center x across the art
ACME_infusion_clampWheelHeightRatio = 0.247;  // wheel height as fraction of art height
// where the art sits inside its paa canvas, as [x, y, w, h]. the textures carry 2048x2048 padding. set both to
// [0,0,1,1] if you reconvert the art to fill the full power-of-two canvas.
ACME_infusion_clampBGContent = [0.3525, 0.0, 0.2949, 1.0];
ACME_infusion_clampWheelContent = [0.4336, 0.7120, 0.1328, 0.2720];
ACME_infusion_clampCommitInterval = 0.25;  // network commit throttle while dragging
// roller clamp tick sfx. one tick plays per percent of change. the pitch rises toward 0 percent, fully shut,
// up to pitchmax. the volume falls toward volmin as the clamp closes.
ACME_infusion_clampSfxFile = "\acm_extended\sound\roller_clamp_sfx.ogg";
ACME_infusion_clampSfxPitchMax = 1.5;
ACME_infusion_clampSfxVolMin = 0.65;
ACME_infusion_clampSfxSlowThreshold = 0.12;  // ticks spaced wider than this count as fine control, which steps every percent.
ACME_infusion_clampSfxMinInterval = 0.06;  // hard cap between ticks while fast-sliding

ACME_infusion_defaultDurationSeconds = createHashMapFromArray [
    ["Epinephrine", 7200],
    ["Norepinephrine", 7200],
    ["Amiodarone", 600],
    ["Lidocaine", 1200],
    ["Ketamine", 900],
    ["TXA", 600],
    ["HTS3", 1800],
    ["Esmolol", 1800],
    ["Fentanyl", 600],
    ["Morphine", 900],
    ["Midazolam", 1200],
    ["Propofol", 1800],
    ["Ondansetron", 300],
    ["CalciumChloride", 300],
    ["CalciumGluconate", 600],
    ["Ceftriaxone", 1800]
];

// delivery class override. when the medic infuses these drugs, the mod delivers the medication as another
// classname so the record shows the intended one. ceftriaxone remains Ceftriaxone_IV, which credits ACM's evac
// antibiotic gate and carries the ertapenem effect. calcium gluconate has its own iv class, and
// ACME_infusion_calciumCaCl2Equivalent handles its calcium credit.
ACME_infusion_deliveryClassOverride = createHashMapFromArray [
    ["Ceftriaxone", "Ceftriaxone_IV"]
];

// flush-required push meds. a push of one of these through iv or io from the narc box parks the dose in the
// line with no effect. the "Flush IV Line (Saline)" action, ACME_FlushLine into fn_salineflush "flushLine",
// then delivers it. this mirrors the bedside rule that adenosine, amiodarone, calcium and push-dose epi need a
// saline flush behind the push. the ACME_flushReqEnabled CBA option toggles the mechanic. edit this list to
// change the set.
ACME_flushReqMeds = ["Adenosine", "Amiodarone", "CalciumGluconate", "CalciumChloride", "Epinephrine"];

// premixed bags arrive with a drug already loaded. the infusion tracker reads this to know what each one
// carries. the format is bag classname into [medication, totaldosemg, volumeml].
// esmolol is 2500 mg in 250 ml, which gives 10 mg/ml for rate control in AFib-RVR and atrial tach.
// HTS is 3 percent in 250 ml for osmotherapy. its mg value is nominal because volume drives the effect.
ACME_infusion_PremixedBags = createHashMapFromArray [
    ["ACME_EsmololBag", ["Esmolol", 2500, 250]]
];

ACME_infusion_minPulseDose = createHashMapFromArray [
    ["Epinephrine", 0.01],
    ["Norepinephrine", 0.01],
    ["Amiodarone", 1],
    ["Lidocaine", 1],
    ["Ketamine", 1],
    ["TXA", 10],
    ["Fentanyl", 0.005],
    ["Morphine", 0.5],
    ["Midazolam", 0.5],
    ["Ondansetron", 0.5],
    ["CalciumChloride", 50],
    ["CalciumGluconate", 50],
    ["Ceftriaxone", 50],
    ["Magnesium", 25],
    ["Propofol", 5]
];

// therapeutic dose registry for every medication this addon can deliver as an infusion. these are gameplay and
// ACM effect targets, not a real protocol. the infusion tracker, the debug HUD and the custom systems all read
// this table, so every bag has one definition of enough drug delivered.
ACME_infusion_therapeuticDoseMg = createHashMapFromArray [
    ["Amiodarone", 150],
    ["Epinephrine", 1],
    ["Norepinephrine", 4],
    ["Lidocaine", 100],
    ["Ketamine", 50],
    ["TXA", 1000],
    ["Fentanyl", 0.1],
    ["Morphine", 10],
    ["Midazolam", 5],
    ["Ondansetron", 4],
    ["CalciumChloride", 1000],
    ["CalciumGluconate", 3000],
    ["Ceftriaxone", 1000],
    ["Esmolol", 2500],
    ["Magnesium", 2000],
    ["HTS3", 7500],
    ["Mannitol", 100000],
    ["Propofol", 100]
];

// calcium credit equivalence for the citrate and hypocalcemia model. the circ loop stores everything as grams
// of calcium chloride equivalent credit, because the lethal triad model already uses that variable. the mod
// treats 3 g of calcium gluconate as about 1 g of CaCl2 equivalent.
ACME_infusion_calciumCaCl2Equivalent = createHashMapFromArray [
    ["CalciumChloride", 1],
    ["CalciumChloride_IV", 1],
    ["CalciumGluconate", 0.333333],
    ["CalciumGluconate_IV", 0.333333]
];

ACME_infusion_pulseInterval = 3;
// cap on how many ACM medication adjustment entries one infused drug can hold at once. ACM sums the uncapped
// CO2 sensitivity and breathing effectiveness penalty of each entry. without this cap, an opioid or sedative
// drip stacks entries until it forces apnea at any dose. 4 gives a sustained, safe effect. raise it for a
// stronger drip.
ACME_infusion_maxMedEntries = 4;
ACME_infusion_maxDeltaSeconds = 10;
ACME_infusion_activePatients = [];
