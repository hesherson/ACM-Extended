/* B246: one bounded owner discovery pass for idle-capable physiology and maintenance registries.
 * Active registries run at their original clinical cadence; this 1 Hz pass is only a
 * missed-transition/locality safety net. Healthy units are read-only and never published from here.
 * Circulation, coagulation and infusion no longer perform their own broad owner scans.
 */
params [["_units", [], [[]]]];
private _fullAudit = _units isEqualTo [];
if (_fullAudit) then {
    _units = missionNamespace getVariable ["ACME_clinical_ownedUnits", []];
} else {
    _units = _units select {!isNull _x && {local _x} && {alive _x}};
};
private _now = CBA_missionTime;
private _preox = if (_fullAudit) then {[]} else {(missionNamespace getVariable ["ACME_preox_activePatients", []]) - _units};
private _aspiration = if (_fullAudit) then {[]} else {(missionNamespace getVariable ["ACME_aspiration_activePatients", []]) - _units};
private _shock = if (_fullAudit) then {[]} else {(missionNamespace getVariable ["ACME_shock_activePatients", []]) - _units};
private _rhythmThreshold = if (_fullAudit) then {[]} else {(missionNamespace getVariable ["ACME_rhythmThreshold_activePatients", []]) - _units};
// These three hot workers own their own retirement. Preserve an already enrolled local patient
// through the discovery pass so a direct treatment/event enrollment cannot be erased before its first tick.
private _circPatients = if (_fullAudit) then {
    (missionNamespace getVariable ["ACME_circ_activePatients", []]) select {!isNull _x && {local _x} && {alive _x}}
} else {(missionNamespace getVariable ["ACME_circ_activePatients", []]) - _units};
private _coag = if (_fullAudit) then {
    (missionNamespace getVariable ["ACME_coag_activePatients", []]) select {!isNull _x && {local _x} && {alive _x}}
} else {(missionNamespace getVariable ["ACME_coag_activePatients", []]) - _units};
private _infusion = if (_fullAudit) then {
    (missionNamespace getVariable ["ACME_infusion_activePatients", []]) select {!isNull _x && {local _x} && {alive _x}}
} else {(missionNamespace getVariable ["ACME_infusion_activePatients", []]) - _units};
private _autoSVT = missionNamespace getVariable ["ACME_rhythmAutoSVTFromRateEnabled", false];
private _svtHR = missionNamespace getVariable ["ACME_rhythmCustomSVTHR", missionNamespace getVariable ["ACME_rhythmCriticalSVTHR", 190]];
private _acmHighHR = missionNamespace getVariable ["ACME_rhythmACMFatalHighHR", 220];
{
    private _u = _x;
    if (isNull _u || {!local _u} || {!alive _u}) then {continue};

    // Preoxygenation: displaced reserve, active respiratory support, or a state
    // capable of consuming/limiting reserve.
    private _reserve = (_u getVariable ["ACME_preox_reserve",0.30]) max 0 min 1;
    private _rr = _u getVariable ["ACME_resp_neuralRR", (_u getVariable ["ACM_breathing_RespirationRate",16])];
    private _support = alive (_u getVariable ["ACM_breathing_BVM_Medic",objNull])
        || {_u getVariable ["ACME_vent_onPatient",false]}
        || {_u getVariable ["ACME_nrb_on",false]};
    private _preoxPhys = (_rr <= 2)
        || {_u getVariable ["ACE_isUnconscious",false]}
        || {_u getVariable ["ace_medical_inCardiacArrest",false]}
        || {(_u getVariable ["ace_medical_spo2",97]) < 94}
        || {(_u getVariable ["ACME_blastLung_State",0]) > 0}
        || {(_u getVariable ["ACME_aspiration_load",0]) > 0.001}
        || {(_u getVariable ["ACME_alt_pRatio",1]) < 0.999};
    if (abs (_reserve - 0.30) > 0.001 || {_support} || {_preoxPhys}) then {
        _preox pushBack _u;
    };

    // Aspiration: a fresh emesis edge, retained lung burden, or one final
    // replicated/local drive that still needs neutralization.
    private _load = (_u getVariable ["ACME_aspiration_load",0]) max 0;
    private _edema = (_u getVariable ["ACME_aspiration_edema",0]) max 0;
    private _event = _u getVariable ["ACME_laryngo_emesis", []];
    private _vomitState = _u getVariable ["ACM_airway_AirwayObstructionVomit_State",0];
    private _eventKey = if (_event isEqualType [] && {count _event >= 3}) then {
        format ["%1:%2:%3:%4", _event param [0,""], _event param [1,0], _event param [2,0], _vomitState]
    } else {
        format ["native:%1",_vomitState]
    };
    private _freshAspiration = (_eventKey != (_u getVariable ["ACME_aspiration_lastEmesisKey",""]))
        && {_vomitState > 0 || {count _event >= 3}};
    private _aspResidue = (_u getVariable ["ACME_aspiration_injury",0]) > 0.0005
        || {(_u getVariable ["ACME_aspiration_SpO2Penalty",0]) > 0.001}
        || {abs (_u getVariable ["ACME_aspiration_RRDrive",0]) > 0.001}
        || {(_u getVariable ["ACME_aspiration_shunt",0]) > 0.0001}
        || {_u getVariable ["ACME_aspiration_edemaActive",false]}
        || {abs (_u getVariable ["ACME_aspiration_lastRRAdj",0]) > 0.001};
    if (_freshAspiration || {_load > 0.0005} || {_edema > 0.0005} || {_aspResidue}) then {
        _aspiration pushBack _u;
    };

    // Shock: forced phenotype, hemodynamic/chest trigger, hypovolemia, or a
    // prior drive that needs one neutralization pass.
    private _priorShock = (toLowerANSI (_u getVariable ["ACME_shock_phenotype","none"])) != "none"
        || {abs (_u getVariable ["ACME_shock_severity",0]) > 0.001}
        || {abs (_u getVariable ["ACME_shock_resistDelta",0]) > 0.01}
        || {abs (_u getVariable ["ACME_shock_hrAdj",0]) > 0.01}
        || {_u getVariable ["ACME_shock_warm",false]}
        || {_u getVariable ["ACME_shock_ownsCirc",false]};
    private _forced = _u getVariable ["ACME_shock_forced", []];
    private _forcedLive = _forced isEqualType [] && {count _forced >= 2}
        && {(_forced param [2,-1]) < 0 || {_now <= (_forced param [2,-1])}};
    private _circState = _u getVariable ["ACME_circ_State", createHashMap];
    private _circShock = _circState isEqualType createHashMap && {_circState getOrDefault ["shockActive",false]};
    if (_priorShock || {_forcedLive}
        || {_u getVariable ["ACM_breathing_TensionPneumothorax_State", false]}
        || {(_u getVariable ["ACM_breathing_Hemothorax_Fluid",0]) >= 0.75}
        || {_circShock}
        || {(_u getVariable ["ACM_circulation_Blood_Volume",6]) < 5.1}) then {
        _shock pushBack _u;
    };


    // Circulation missed-transition discovery. This exactly replaces the former
    // one-second owner scan inside the 4 Hz circulation worker.
    private _circArrest = _u getVariable ["ace_medical_inCardiacArrest", false];
    private _circUncon = _u getVariable ["ACE_isUnconscious", false];
    private _circRR = _u getVariable ["ACM_breathing_RespirationRate", 18];
    private _rrTarget = _u getVariable ["ACM_core_TargetVitals_RespirationRate", 16];
    if (_rrTarget <= 6) then {_rrTarget = 16;};
    private _circStateNeeds = (_circState getOrDefault ["shockActive", false])
        || {abs (_circState getOrDefault ["shockDrop", 0]) > 0.01}
        || {abs (_circState getOrDefault ["pressorSupport", 0]) > 0.01}
        || {abs (_circState getOrDefault ["pushDoseSupport", 0]) > 0.01}
        || {(_circState getOrDefault ["ichRisk", 0]) > 0.001}
        || {(_circState getOrDefault ["ionizedCa", 1.15]) < 0.999}
        || {(_circState getOrDefault ["temp", 37]) < 35.99}
        || {(_circState getOrDefault ["salineAcidosis", 0]) > 0.001}
        || {(_circState getOrDefault ["totalAcidosis", 0]) > 0.001}
        || {(_circState getOrDefault ["paCO2", 40]) > 40.1}
        || {(_circState getOrDefault ["respiratoryAcidosisDeficit", 0]) > 0.001}
        || {(_circState getOrDefault ["hyperSpike", 0]) > 0.001};
    private _needsCirc = _circArrest
        || {_u getVariable ["ACME_vent_connected", false]}
        || {_u getVariable ["ACME_ETT_Inserted", false]}
        || {_u getVariable ["ACME_nrb_on", false]}
        || {(_u getVariable ["ACME_blastLung_State", 0]) > 0}
        || {count (_u getVariable ["ace_medical_medications", []]) > 0}
        || {count (_u getVariable ["ACME_yFlushJobs", createHashMap]) > 0}
        || {_circUncon}
        || {_circStateNeeds}
        || {_u getVariable ["ACME_tbi_HasTBI", false]}
        || {_circRR < (_rrTarget * 0.85)}
        || {(_u getVariable ["ACME_circ_salineGivenMl", 0]) > 0}
        || {(_u getVariable ["ACM_circulation_Saline_Volume", 0]) > 0}
        || {(_u getVariable ["ACME_lido_serumLevel", 0]) > 0.05}
        || {(_u getVariable ["ACME_lido_seizureState", ""]) != ""}
        || {count (_u getVariable ["ACM_circulation_IV_Bags", createHashMap]) > 0};
    if (_needsCirc) then {_circPatients pushBackUnique _u;};

    // Coagulation missed-transition discovery. Expensive base reconstruction is
    // skipped for healthy units unless an input can actually move the lethal-triad base.
    private _platelets = (_u getVariable ["ACM_circulation_Platelet_Count", 3]) max 0;
    private _saline = (_u getVariable ["ACM_circulation_Saline_Volume", 0]) max 0;
    private _plasmaVol = (_u getVariable ["ACM_circulation_Plasma_Volume", 0]) max 0;
    private _givenMl = (_u getVariable ["ACME_circ_salineGivenMl", 0]) max 0;
    private _hasTXA = ((_u getVariable ["ace_medical_medications", []]) findIf {(_x param [0, ""]) == "TXA_IV"}) >= 0;
    private _coagTemp = _u getVariable ["ACME_hypo_temp", 37];
    private _coagAcid = _circState getOrDefault ["acidosis", 0];
    private _transfused = _u getVariable ["ACM_circulation_TransfusedBlood_Volume", 0];
    private _baseSuspect = _coagTemp < (missionNamespace getVariable ["ACME_hypo_coagStartTemp", 35])
        || {_coagAcid > (missionNamespace getVariable ["ACME_acidosis_coagThreshold", 0.3])}
        || {_transfused > (missionNamespace getVariable ["ACME_ca_citrateThreshold", 1.0])};
    private _baseNeeds = _baseSuspect && {(([_u] call ACME_fnc_coagulationBase) select 0) > 1};
    private _hadCoagEffect = (_u getVariable ["ACME_ca_coagMult", 1]) != 1
        || {(_u getVariable ["ACME_ca_coagBaseMult", 1]) != 1}
        || {(_u getVariable ["ACME_coag_clotStrength", 1]) != 1}
        || {(_u getVariable ["ACME_coag_dilutionSeverity", 0]) != 0}
        || {(_u getVariable ["ACME_coag_extraMult", 1]) != 1};
    if (_baseNeeds || {_platelets < 3} || {_saline > 0} || {_plasmaVol > 0} || {_givenMl > 0} || {_hasTXA} || {_hadCoagEffect}) then {
        _coag pushBackUnique _u;
    };

    // Medicated-infusion discovery is a safety net only. Normal bag registration
    // enrolls immediately; the active worker retires after its final empty-state commit.
    if (count (_u getVariable ["ACME_infusion_BagMedications", []]) > 0
        || {_u getVariable ["ACME_infusion_HasBagMedications", false]}) then {
        _infusion pushBackUnique _u;
    };


    // Rhythm-threshold observer: only custom/legacy cleanup, explicit lidocaine
    // conversion, or an actually eligible auto-SVT episode needs the 2 Hz worker.
    // Native ACM critical rhythms remain entirely native when no ACME overlay exists.
    private _rhythmActive = _u getVariable ["ACME_rhythm_active",0];
    private _nativeRhythm = _u getVariable ["ACM_circulation_Cardiac_RhythmState",0];
    private _arrest = _u getVariable ["ace_medical_inCardiacArrest",false];
    private _thresholdPending = (_u getVariable ["ACME_rhythmThresholdKind",""]) != ""
        || {!isNil {_u getVariable "ACME_rhythmThresholdStart"}}
        || {(_u getVariable ["ACME_rhythmThresholdForced",""]) != ""};
    private _legacyHold = (_u getVariable ["ACME_rhythmNativeHoldKind",""]) != ""
        || {(_u getVariable ["ACME_rhythmNativeHoldRhythm",-1]) != -1}
        || {(_u getVariable ["ACME_rhythmNativeHighHRFloorUntil",0]) > 0};
    private _lidoCandidate = _nativeRhythm == 4 && {!_arrest}
        && {count (_u getVariable ["ace_medical_medications",[]]) > 0};
    private _hr = _u getVariable ["ace_medical_heartRate",0];
    private _autoCandidate = _autoSVT && {!_arrest} && {_rhythmActive == 0}
        && {_nativeRhythm in [0,5]} && {_hr >= _svtHR} && {_hr <= _acmHighHR};
    if (_rhythmActive >= 100 || {_thresholdPending} || {_legacyHold} || {_lidoCandidate} || {_autoCandidate}) then {
        _rhythmThreshold pushBack _u;
    };
} forEach _units;

ACME_preox_activePatients = _preox;
ACME_aspiration_activePatients = _aspiration;
ACME_shock_activePatients = _shock;
ACME_rhythmThreshold_activePatients = _rhythmThreshold;
ACME_circ_activePatients = _circPatients;
ACME_coag_activePatients = _coag;
ACME_infusion_activePatients = _infusion;
