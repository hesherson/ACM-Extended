/* Read-only indication shared by clinical enrollment, late-owner recovery and
 * post-maintenance retirement. Historical maps/receipts alone are not activity.
 * The caller retires only after the full maintenance pass has performed cleanup.
 */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {false};

if (_patient getVariable ["ace_medical_inCardiacArrest", false]
    || {_patient getVariable ["ACE_isUnconscious", false]}
    || {_patient getVariable ["ACME_vent_connected", false]}
    || {_patient getVariable ["ACME_vent_configured", false]}
    || {_patient getVariable ["ACME_vent_onPatient", false]}
    || {_patient getVariable ["ACME_ETT_Inserted", false]}
    || {_patient getVariable ["ACME_ETT_Obstructing", false]}
    || {_patient getVariable ["ACME_nrb_on", false]}
    || {_patient getVariable ["ACME_tbi_HasTBI", false]}
    || {_patient getVariable ["ACME_headElevated", false]}
    || {(_patient getVariable ["ACME_blastLung_State", 0]) > 0}
    || {(_patient getVariable ["ACM_burns_SystemicBurden", 0]) > 0.001}
    || {(_patient getVariable ["ACM_burns_AirwayInflammation", 0]) > 0.001}
    || {(_patient getVariable ["ACM_infection_Infection_Stage", 0]) > 0}
    || {_patient getVariable ["ACM_infection_Sepsis_Permanent", false]}
    || {count (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) > 0}
    || {count (_patient getVariable ["ACME_infusion_BagMedications", []]) > 0}
    || {count (_patient getVariable ["ace_medical_medications", []]) > 0}
    || {count (_patient getVariable ["ACME_medicationDriveQueue", []]) > 0}
    || {count (_patient getVariable ["ACME_yFlushJobs", createHashMap]) > 0}
    || {count (_patient getVariable ["ACME_suctionSessions", []]) > 0}
    || {(_patient getVariable ["ACME_suctionExposure", 0]) > 0}
    || {(_patient getVariable ["ACME_o2Drain_suction", 0]) > 0}
    || {(_patient getVariable ["ACME_laryngo_irritationUntil", 0]) > CBA_missionTime}) exitWith {true};

private _s = _patient getVariable ["ACME_circ_State", createHashMap];
if !(_s isEqualType createHashMap) then {_s = createHashMap;};
private _circNeeds = (_s getOrDefault ["shockActive", false])
    || {abs (_s getOrDefault ["shockDrop", 0]) > 0.01}
    || {abs (_s getOrDefault ["pressorSupport", 0]) > 0.01}
    || {abs (_s getOrDefault ["pushDoseSupport", 0]) > 0.01}
    || {(_s getOrDefault ["ichRisk", 0]) > 0.001}
    || {(_s getOrDefault ["ionizedCa", 1.15]) < 0.999}
    || {(_s getOrDefault ["temp", 37]) < 35.99}
    || {(_s getOrDefault ["salineAcidosis", 0]) > 0.001}
    || {(_patient getVariable ["ACME_circ_salineGivenMl", 0]) > 0}
    || {(_s getOrDefault ["totalAcidosis", 0]) > 0.001}
    || {(_s getOrDefault ["paCO2", 40]) > 40.1}
    || {(_s getOrDefault ["respiratoryAcidosisDeficit", 0]) > 0.001}
    || {(_s getOrDefault ["hyperSpike", 0]) > 0.001}
    || {(_s getOrDefault ["shockDwell", 0]) > 0}
    || {(_s getOrDefault ["hypoventDwell", 0]) > 0}
    || {(_patient getVariable ["ACME_plasmaLyteAcidCredit", 0]) > 0}
    || {(missionNamespace getVariable ["ACME_sys_do2", true]) && {
        (_s getOrDefault ["do2Deficit", false]) || {_s getOrDefault ["do2WasArrest", false]}
    }};
if (_circNeeds) exitWith {true};

// Keep actual drug washout and finite stress/debt, including a final admitted
// bolus after its native medication record or infusion has disappeared.
if ((["pressorDriveEffMgMin", "epiInfusionDriveEffMgMin", "epiLikeDriveEffMgMin",
    "esmololInfusionDriveEffMgMin", "amioRateEffMgMin", "caRateEffMgMin",
    "caElemEffMgMin", "magRateEffMgMin", "epiBolusReserve"] findIf {
    abs (_s getOrDefault [_x, 0]) > 0.00001
}) >= 0) exitWith {true};
if (_patient getVariable ["ACME_roc_paralyzed", false]
    || {_patient getVariable ["ACME_roc_apnea", false]}
    || {(_patient getVariable ["ACME_roc_awakeResistAdd", 0]) > 0.01}
    || {(_patient getVariable ["ACME_hc_pressorDebt", 0]) > 0.001}
    || {(_patient getVariable ["ACME_lido_seizureState", ""]) != ""}) exitWith {true};
if ((["ACME_ca_serumLevel", "ACME_amio_serumLevel", "ACME_lido_serumLevel",
    "ACME_esmolol_serumLevel", "ACME_ketRapidLoad", "ACME_hcMed_rapidPropofol",
    "ACME_hcMed_rapidMidazolam", "ACME_hcMed_rapidOpioid", "ACME_hcMed_rapidRocuronium"] findIf {
    (_patient getVariable [_x, 0]) > 0.0001
}) >= 0) exitWith {true};
private _pk = missionNamespace getVariable ["ACME_infusion_pk", createHashMap];
if (((keys _pk) findIf {(_patient getVariable [format ["ACME_serum_%1", _x], 0]) > 0.0001}) >= 0) exitWith {true};

// Repeated-needle leakage has its own progression even after native PTX clears.
if ((missionNamespace getVariable ["ACME_sys_ncdLeak", true])
    && {(_patient getVariable ["ACME_ncd_total", 0]) > (missionNamespace getVariable ["ACME_ncd_freeCount", 2])}
    && {(_patient getVariable ["ACM_breathing_Thoracostomy_State", 0]) < 2}) exitWith {true};

if ((_patient getVariable ["ACM_breathing_Pneumothorax_State", 0]) > 0
    || {_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]}) exitWith {true};
private _ptx = _patient getVariable ["ACME_ptx_state", []];
private _validPtx = _ptx isEqualType [] && {count _ptx == 9} && {(_ptx select 0) == 1}
    && {(_ptx findIf {!(_x isEqualType 0) || {!finite _x}}) < 0};
if (!_validPtx) exitWith {
    // Legacy/malformed episodes receive their existing adoption pass. A bare
    // chest-injury flag cannot pin a valid, fully resolved episode afterwards.
    (_patient getVariable ["ACM_breathing_ChestInjury_State", false]) || {_ptx isNotEqualTo []}
};
if ((_patient getVariable ["ACM_breathing_Pneumothorax_State", 0]) != (_ptx select 7)) exitWith {true};
if (([1, 2, 4, 8] findIf {(_ptx select _x) > 0.000001}) >= 0) exitWith {true};
// Serial, observation seconds, old native projection and cannula patency remain
// as history. Actual communicating wounds or bleeding seal outlets still work.
private _context = [_patient] call ACME_fnc_ptxContext;
((_ptx select 6) > 0 && {(_context select 0) > 0})
    || {(_context select 6) && {(_context select 3) > 0}}
