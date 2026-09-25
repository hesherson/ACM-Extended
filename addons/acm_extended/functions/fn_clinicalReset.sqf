/* Called before/after the existing physical teardown. Never deletes medic inventory. B57 hard-reset callers also scrub cosmetic injury evidence. */
params ["_patient", ["_phase", "finish"], ["_preserveJunctional", false]];
if (isNull _patient || {!local _patient}) exitWith {};
if (_phase == "begin") exitWith {
    [_patient] call ACME_fnc_headElevHoldClear;
    _patient setVariable ["ACME_headElev_manualUnsupported", false, true];
    [_patient] call ACME_fnc_aajtDownedStop;
    private _aajtPain = _patient getVariable ["ACME_AAJT_painPFH", -1];
    if (_aajtPain >= 0) then {[_aajtPain] call CBA_fnc_removePerFrameHandler;};
    _patient setVariable ["ACME_AAJT_painPFH", -1, false];
    // Keep custody of reusable equipment. A full heal is not an inventory deletion/refund.
    _patient setVariable ["ACME_resetVentCustody", [
        _patient getVariable ["ACME_vent_onPatient", false],
        _patient getVariable ["ACME_vent_operator", objNull],
        (([] call ACME_fnc_ventDeviceFields) select {!isNil {_patient getVariable _x}}) apply {[_x, _patient getVariable _x]}
    ], false];
    _patient setVariable ["ACME_clinicalEpoch", ([_patient] call ACME_fnc_clinicalEpoch) + 1, true];
    private _nativePtxPFH = _patient getVariable ["ACM_breathing_Pneumothorax_PFH", -1];
    if (_nativePtxPFH isEqualType 0 && {_nativePtxPFH >= 0}) then {[_nativePtxPFH] call CBA_fnc_removePerFrameHandler;};
    [_patient, [["pneumothoraxPFH", -1]], false] call ACM_breathing_fnc_setRuntimeState;
    private _nativeCardiacPFH = _patient getVariable ["ACM_circulation_CardiacArrest_PFH", -1];
    private _nativeReversiblePFH = _patient getVariable ["ACM_circulation_ReversibleCardiacArrest_PFH", -1];
    {if (_x isEqualType 0 && {_x >= 0}) then {[_x] call CBA_fnc_removePerFrameHandler;};} forEach [_nativeCardiacPFH, _nativeReversiblePFH];
    [_patient, [["cardiacArrestPFH", -1], ["reversibleCardiacArrestPFH", -1]], false] call ACM_circulation_fnc_setRuntimeState;
    private _nativeVomitPFH = _patient getVariable ["ACM_airway_AirwayObstructionVomit_PFH", -1];
    if (_nativeVomitPFH isEqualType 0 && {_nativeVomitPFH >= 0}) then {[_nativeVomitPFH] call CBA_fnc_removePerFrameHandler;};
    [_patient, [["vomitPFH", -1]], false] call ACM_airway_fnc_setAirwayState;
    {private _h = _patient getVariable [_x, -1]; if (_h isEqualType 0 && {_h >= 0}) then {[_h] call CBA_fnc_removePerFrameHandler;}; _patient setVariable [_x, -1, false];} forEach ["ACME_juncPFH", "ACME_thora_drainPFH"];
    _patient setVariable ["ACME_juncWorker", [], false];
    _patient setVariable ["ACME_nativeVomitWorker", [], false];
    _patient setVariable ["ACME_alt_ptxSample", nil, false];
    _patient setVariable ["ACME_nativeVomitActive", false, true];
    _patient setVariable ["ACME_JuncBleedActive", false, false];
    _patient setVariable ["ACME_junctionalBleedLPS", 0, false];
    _patient setVariable ["ACME_nativeRequestedRhythm", nil, false];
    _patient setVariable ["ACME_nrb_drawPending", [], true];
    _patient setVariable ["ACME_nrb_session", "", true];
    _patient setVariable ["ACME_nrb_o2Pending", 0, true];
    {private _k = toLowerANSI _x; if ((_k find "acme_clock_") == 0 || {(_k find "acme_clamprate_") == 0}) then {_patient setVariable [_x, nil, false];};} forEach allVariables _patient;
    {missionNamespace setVariable [_x, (missionNamespace getVariable [_x, []]) - [_patient]];} forEach ["ACME_clinical_activePatients", "ACME_infusion_activePatients", "ACME_circ_activePatients", "ACME_tbi_activePatients", "ACME_cs_activePatients", "ACME_nrb_activePatients", "ACME_hpmk_activePatients", "ACME_autoBP_patients"];
};
// Physical equipment is detached, not converted into inventory by a medical full heal.
if ((_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient) then {
    [_patient, [["bvmProvider", objNull], ["bvmConnectedOxygen", false]], true] call ACM_breathing_fnc_setRuntimeState;
};
// Compatibility support for an explicit preservation caller remains here, but B57 hard-reset paths always pass false.
private _junctionalEvidence = [];
if (_preserveJunctional && {!alive _patient}) then {
    _junctionalEvidence = [
        "ACME_AAJT_inguinal", "ACME_AAJT_inguinalSide", "ACME_AAJT_zone3", "ACME_AAJT_axillaleft", "ACME_AAJT_axillaright",
        "ACME_AAJT_inguinalAt", "ACME_AAJT_zone3At", "ACME_AAJT_axillaleftAt", "ACME_AAJT_axillarightAt", "ACME_AAJT_legs"
    ];
    {
        private _part = _x;
        {
            _junctionalEvidence pushBack format [_x, _part];
        } forEach ["ACME_Junc_%1", "ACME_Junc_At_%1", "ACME_Junc_PackedAt_%1", "ACME_Junc_XStatAt_%1", "ACME_Junc_XStatRebled_%1"];
    } forEach ["leftarm", "rightarm", "leftleg", "rightleg"];
};
{
    _x params ["_name", "", "_reset"];
    if (_reset && {!(_name in _junctionalEvidence)} && {!(_name in [
        "ACME_nrb_on", "ACME_nrb_hasO2", "ACME_nrb_delivering",
        "ACME_hpmk_state", "ACME_hpmk_on",
        "ACME_obtunded", "ACME_obtunded_manual", "ACME_obtunded_posture",
        "ACME_blastLung_State", "ACME_blastLung_ARDS",
        "ACME_blastLung_exposures", "ACME_blastLung_Onset", "ACME_blastLung_Time",
        "ACME_rhythmNativeHoldKind", "ACME_rhythmNativeHoldRhythm",
        "ACME_rhythmNativeHighHRFloorUntil", "ACME_rhythmNativeShockGraceUntil",
        "ACME_coldBloodHungAt", "ACME_tempFlagHoldUntil",
        "ACME_hypo_temp",
        "ACME_requiresEvac",
        "ACME_vent_shunt",
        "ACME_roc_postROSCGraceUntil", "ACME_roc_awakeDwell", "ACME_roc_awakeResistAdd", "ACME_hrDrive_roc",
        "ACME_roc_awarenessEvent", "ACME_roc_awarenessAt", "ACME_roc_awarenessSeconds",
        "ACME_roc_awakeParalysis", "ACME_roc_apnea",
        "ACME_medicationToxicityFired",
        "ACME_ETT_Inserted", "ACME_ETT_CuffInflated", "ACME_ETT_Secured", "ACME_ETT_Unsecured",
        "ACME_roc_paralyzed", "ACME_ca_caCl2Given"
    ])} && {!isNil {_patient getVariable _name}}) then {_patient setVariable [_name, nil, true];};
} forEach (call ACME_fnc_clinicalFields);

// B106: never leave the derived XStat impairment/surgery flags or forceWalk state detached from the device state.
private _preservedAnyXStat = _preserveJunctional && {!alive _patient} && {(["leftarm", "rightarm", "leftleg", "rightleg"] findIf {
    toLowerANSI (_patient getVariable [format ["ACME_Junc_%1", _x], ""]) isEqualTo "xstat"
}) >= 0};
private _preservedLegXStat = _preserveJunctional && {!alive _patient} && {(["leftleg", "rightleg"] findIf {
    toLowerANSI (_patient getVariable [format ["ACME_Junc_%1", _x], ""]) isEqualTo "xstat"
}) >= 0};
_patient setVariable ["ACME_XStat_needsSurgery", _preservedAnyXStat, true];
_patient setVariable ["ACME_XStat_impaired", _preservedLegXStat, true];
_patient forceWalk _preservedLegXStat;

// Phase 67: the reset half of persistence uses the same owners as live mutation and restore.
[_patient, "", true, false] call ACME_fnc_hpmkStateCommit;
[_patient, false, false, "", -1, true] call ACME_fnc_obtundedStateCommit;
[_patient, 0, true, false, true] call ACME_fnc_blastLungStateCommit;
[_patient, "CLEAR", "CLEAR", "CLEAR", true] call ACME_fnc_blastLungEpisodeCommit;
[_patient, objNull, objNull, true, false, true] call ACME_fnc_blastLungArdsCommit;
[_patient, "", -1, true, false] call ACME_fnc_rhythmNativeHoldCommit;
[_patient, 0, true, false, true] call ACME_fnc_rhythmNativeHighHRFloorCommit;
[_patient, 0, true, true] call ACME_fnc_rhythmNativeShockGraceCommit;
[_patient, objNull, objNull, objNull, objNull, true, true] call ACME_fnc_bloodThermalStateCommit;
[_patient, 37, true, false, true] call ACME_fnc_hypothermiaTemperatureCommit;
[_patient, false, true, false, true] call ACME_fnc_evacuationRequirementCommit;
[_patient, 0, true, false] call ACME_fnc_ventShuntCommit;
[_patient, "CLEAR", "CLEAR", "CLEAR", "CLEAR", true, false] call ACME_fnc_rocStressStateCommit;
[_patient, "CLEAR", "CLEAR", "CLEAR", true, false] call ACME_fnc_rocAwarenessStateCommit;
[_patient, false, true, false, true] call ACME_fnc_rocAwakeParalysisCommit;
[_patient, false, true, false, true] call ACME_fnc_rocApneaCommit;
[_patient, "clear", "", -1, createHashMap, true] call ACME_fnc_medicationToxicityFiredCommit;
[_patient, false, false, false, true, false] call ACME_fnc_nrbStateCommit;
[_patient, false, false, false, false, true, false] call ACME_fnc_ettAirwayStateCommit;
[_patient, false, true, false] call ACME_fnc_rocParalysisCommit;
[_patient, 0, "clear", true, false] call ACME_fnc_calciumCreditCommit;
{_patient setVariable [_x, false, true];} forEach ["ACME_vent_connected", "ACME_vent_driving", "ACME_CS_heldSealed"];
{_patient setVariable [_x, 0, true];} forEach ["ACME_resp_neuralRR", "ACME_resp_deliveredRR", "ACME_rhythm_painContribution"];
_patient setVariable ["ACME_yFlushJobs", createHashMap, true];
_patient setVariable ["ACME_bagMoves", createHashMap, true];
[_patient, []] call ACME_fnc_detachedBagsCommit;
[_patient, []] call ACME_fnc_infusionMedicationStateCommit;
[_patient, createHashMap] call ACME_fnc_circStateCommit;
[_patient, createHashMap] call ACME_fnc_tbiStateCommit;
[_patient, "ml", 0, false] call ACME_fnc_thoraOutputStateCommit;
[_patient, "perHour", 0, false] call ACME_fnc_thoraOutputStateCommit;
[_patient, "hist", [], false] call ACME_fnc_thoraOutputStateCommit;
_patient setVariable ["ACME_clinicalLastOwner", -1, false];

private _custody = _patient getVariable ["ACME_resetVentCustody", [false, objNull]];
if (_custody select 0) then {
    _patient setVariable ["ACME_vent_onPatient", true, true];
    _patient setVariable ["ACME_vent_operator", _custody select 1, true];
    {_patient setVariable [_x select 0, _x select 1, true];} forEach (_custody param [2, []]);
};
_patient setVariable ["ACME_resetVentCustody", nil, false];
_patient setVariable ["ACME_nativeWorkerOwner", nil, false];
