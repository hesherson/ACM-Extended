/* Read-only 1 Hz recovery predicate for late replicated clinical state.
 * Local/init notifications can precede public treatment flags. A known owner
 * still needs enrollment when required local membership or a worker is absent.
 * Healthy units only perform bounded state reads: no geometry, clocks or writes.
 */
params ["_patient", ["_kind", "all", [""]]];
if (isNull _patient || {!local _patient} || {!alive _patient}
    || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {false};
private _cpr = _patient getVariable ["ACME_resus_cpr", []];
private _cprLive = _cpr isEqualType [] && {count _cpr == 11}
    && {(_cpr select 7) isEqualTo true} && {(_cpr select 9) isEqualType 0}
    && {finite (_cpr select 9)} && {(_cpr select 9) >= 0}
    && {(_cpr select 2) == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {(_cpr select 0) isEqualType objNull} && {!isNull (_cpr select 0)}
    && {(_patient getVariable ["ACM_circulation_CPR_session", []]) isEqualTo [_cpr select 0, _cpr select 5]}
    && {(_patient getVariable ["ace_medical_CPR_provider", objNull]) isEqualTo (_cpr select 0)};
private _cprHandle = _patient getVariable ["ACM_circulation_CPR_PFH", -1];
private _cprWorker = _patient getVariable ["ACME_cprClinicalWorker", []];
private _cprCurrent = _cprLive && {_cprHandle isEqualType 0} && {finite _cprHandle} && {_cprHandle >= 0}
    && {_cprWorker isEqualType []} && {count _cprWorker == 3}
    && {(_cprWorker select 0) == _cprHandle} && {(_cprWorker select 1) isEqualTo (_cpr select [0, 6])}
    && {(_cprWorker select 2) == (_patient getVariable ["ACME_providerLocalityEpoch", 0])};
private _cprNeeds = _cprLive && {!_cprCurrent};
if (_kind == "cpr") exitWith {_cprNeeds};
if (_cprNeeds) exitWith {true};
if ((_patient getVariable ["ACME_ownerRegisterSeen", -999]) != owner _patient) exitWith {true};
// Public provider escrow can also arrive after all bounded Local retries.
// One independent worker settles it even when no panel is open.
private _escrows = _patient getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
private _providerPending = _escrows isEqualType createHashMap && {(values _escrows findIf {
    private _live = false;
    if (_x isEqualType [] && {count _x == 3} && {(_x select 1) isEqualType 0} && {(_x select 1) < 3}) then {
        private _request = _x select 0;
        if (_request isEqualType [] && {count _request == 10}) then {
            private _target = _request select 0;
            _live = !isNull _target;
        };
    };
    _live
}) >= 0};
private _providerWorker = _patient getVariable ["ACME_vent_batterySwapWorker", []];
private _providerCurrent = _providerWorker isEqualType [] && {count _providerWorker == 3}
    && {(_providerWorker select 0) == clientOwner}
    && {(_providerWorker select 1) == (_patient getVariable ["ACME_providerLocalityEpoch", 0])}
    && {(_providerWorker select 2) isEqualType 0} && {finite (_providerWorker select 2)}
    && {(_providerWorker select 2) >= 0};
if (_providerPending && {!_providerCurrent}) exitWith {true};

private _missing = {
    params ["_name"];
    private _handle = _patient getVariable [_name, -1];
    !(_handle isEqualType 0) || {!finite _handle} || {_handle < 0}
};
private _registryMissing = {
    params ["_name"];
    !(_patient in (missionNamespace getVariable [_name, []]))
};

if (([
    ["ACME_nrb_activePatients", "ACME_nrb_on"],
    ["ACME_hpmk_activePatients", "ACME_hpmk_on"],
    ["ACME_tbi_activePatients", "ACME_tbi_HasTBI"],
    ["ACME_cs_activePatients", "ACME_cs_active"],
    ["ACME_autoBP_patients", "ACME_autoBP_Active"]
] findIf {
    (_patient getVariable [_x select 1, false]) isEqualTo true
        && {[_x select 0] call _registryMissing}
}) >= 0) exitWith {true};
if ((_patient getVariable ["ACME_rhythm_active", 0]) >= 100
    && {["ACME_rhythm_activePatients"] call _registryMissing}) exitWith {true};

// Only resume workers with explicit live evidence. Existing airway contents
// alone are not permission to start a new vomiting/collapse episode.
if (([
    ["ACME_nativeVomitActive", "ACM_airway_AirwayObstructionVomit_PFH"],
    ["ACME_nativeCollapseActive", "ACM_airway_AirwayCollapse_PFH"],
    ["ACME_nativeBloodObstructionActive", "ACM_airway_AirwayObstructionBlood_PFH"],
    ["ACME_nativeHemolysisActive", "ACM_circulation_HemolyticReaction_PFH"]
] findIf {
    (_patient getVariable [_x select 0, false]) isEqualTo true
        && {[_x select 1] call _missing}
}) >= 0) exitWith {true};

private _raw = _patient getVariable ["ACM_circulation_Cardiac_RhythmState", 0];
if (_patient getVariable ["ace_medical_inCardiacArrest", false]
    && {(_raw == 5 && {["ACM_circulation_ReversibleCardiacArrest_PFH"] call _missing})
        || {_raw in [2, 3, 4] && {["ACM_circulation_CardiacArrest_PFH"] call _missing}}}) exitWith {true};

if ((_patient getVariable ["ACME_thora_tube_left", false]
    || {_patient getVariable ["ACME_thora_tube_right", false]})
    && {["ACME_thora_drainPFH"] call _missing}) exitWith {true};
if (_patient getVariable ["ACME_headElevated", false]
    && {(["ACME_headElev_pfh"] call _missing) || {["ACME_headElev_killEH"] call _missing}}) exitWith {true};
if (_patient getVariable ["ACME_AAJT_zone3", false]
    && {["ACME_AAJT_downedPFH"] call _missing}) exitWith {true};
private _aajt = ([_patient getVariable ["ACME_AAJT_zone3", false],
    _patient getVariable ["ACME_AAJT_inguinal", false],
    _patient getVariable ["ACME_AAJT_axillaleft", false],
    _patient getVariable ["ACME_AAJT_axillaright", false]] findIf {_x isEqualTo true}) >= 0;
if (_aajt && {["ACME_AAJT_painPFH"] call _missing}) exitWith {true};
if ((["leftarm", "rightarm", "leftleg", "rightleg"] findIf {
    (_patient getVariable [format ["ACME_Junc_%1", _x], ""]) in ["open", "packed", "xstat"]
}) >= 0 && {["ACME_juncPFH"] call _missing}) exitWith {true};

// The general controller is independent of the circulation-only registry.
// Use ownerRegister's live indications, never map existence as an indication.
private _clinicalNeeds = if (["ACME_clinical_activePatients"] call _registryMissing) then {
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
        || {(_s getOrDefault ["hyperSpike", 0]) > 0.001};
    private _hasPtx = (_patient getVariable ["ACM_breathing_Pneumothorax_State", 0]) > 0
        || {_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]}
        || {_patient getVariable ["ACM_breathing_ChestInjury_State", false]}
        || {count (_patient getVariable ["ACME_ptx_state", []]) > 0};
    (_patient getVariable ["ace_medical_inCardiacArrest", false]
        || {_hasPtx} || {_patient getVariable ["ACE_isUnconscious", false]}
        || {_patient getVariable ["ACME_vent_connected", false]}
        || {_patient getVariable ["ACME_ETT_Inserted", false]}
        || {_patient getVariable ["ACME_nrb_on", false]}
        || {_patient getVariable ["ACME_tbi_HasTBI", false]}
        || {(_patient getVariable ["ACME_blastLung_State", 0]) > 0}
        || {_circNeeds}
        || {count (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) > 0}
        || {count (_patient getVariable ["ace_medical_medications", []]) > 0}
        || {count (_patient getVariable ["ACME_yFlushJobs", createHashMap]) > 0}
        || {count (_patient getVariable ["ACME_suctionSessions", []]) > 0}
        || {(_patient getVariable ["ACME_suctionExposure", 0]) > 0}
        || {(_patient getVariable ["ACME_o2Drain_suction", 0]) > 0}
        || {(_patient getVariable ["ACME_laryngo_irritationUntil", 0]) > CBA_missionTime})
} else {false};
_clinicalNeeds
