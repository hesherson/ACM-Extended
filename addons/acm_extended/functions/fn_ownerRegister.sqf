/* Rebuild machine-local scheduler membership from replicated treatment state.
   No patient physiology is cleared on ownership loss. PFH IDs never travel. */
params ["_patient"];
if (isNull _patient || {!local _patient} || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {};

[_patient] call ACME_fnc_transientStateReconcile;

// Migrate old bilateral inguinal AAJT saves exactly once. The physical AAJT-S has one wedge, so an old
// ACME_AAJT_legs=[leftleg,rightleg] state must become one deterministic side instead of silently retaining
// bilateral control. Prefer the only recorded leg, then the only leg with junctional evidence, otherwise left.
if ((_patient getVariable ["ACME_AAJT_inguinal", false]) && {(_patient getVariable ["ACME_AAJT_inguinalSide", ""]) == ""}) then {
    private _legacy = (_patient getVariable ["ACME_AAJT_legs", []]) select {_x in ["leftleg", "rightleg"]};
    private _side = if ((count _legacy) == 1) then {_legacy select 0} else {
        private _leftHas = (_patient getVariable ["ACME_Junc_leftleg", ""]) != "";
        private _rightHas = (_patient getVariable ["ACME_Junc_rightleg", ""]) != "";
        if (_leftHas != _rightHas) then {if (_leftHas) then {"leftleg"} else {"rightleg"}} else {"leftleg"}
    };
    [_patient, "inguinal", [true, _patient getVariable ["ACME_AAJT_inguinalAt", nil], _side]] call ACME_fnc_aajtStateCommit;
};

private _headState = (_patient getVariable ["ACME_headElevated", false])
    || {_patient getVariable ["ACME_headElev_vestRemoved", false]}
    || {(_patient getVariable ["ACME_headElev_propVest", ""]) != ""};
if (!alive _patient) exitWith {
    [_patient] call ACME_fnc_deadPhysiologyFreeze;
    if (_headState) then {[_patient] call ACME_fnc_headElevDeathRelease;};
};
// Rebuild coagulation immediately on treatment enrollment and ownership recovery.
[[_patient]] call ACME_fnc_coagulationTick;

// Same-object recovery/debug resurrection must be able to arm a future death freeze again.
_patient setVariable ["ACME_deadPhysiologyFrozenLocal", false, false];
if (_patient getVariable ["ACME_headElevated", false]) then {[_patient] call ACME_fnc_headElevWatch;};
{
    _x params ["_listName", "_flag"];
    if (_patient getVariable [_flag, false]) then {
        private _list = missionNamespace getVariable [_listName, []];
        _list pushBackUnique _patient;
        missionNamespace setVariable [_listName, _list];
    };
} forEach [
    ["ACME_nrb_activePatients", "ACME_nrb_on"],
    ["ACME_hpmk_activePatients", "ACME_hpmk_on"],
    ["ACME_tbi_activePatients", "ACME_tbi_HasTBI"],
    ["ACME_cs_activePatients", "ACME_cs_active"],
    ["ACME_autoBP_patients", "ACME_autoBP_Active"]
];
// Start elapsed clocks on THIS owner; migration must not grant a default whole-tick bolus.
if (_patient getVariable ["ACME_nrb_on", false] && {isNil {_patient getVariable "ACME_nrb_lastTickLocal"}}) then {
    _patient setVariable ["ACME_nrb_lastTickLocal", CBA_missionTime, false];
};
if (_patient getVariable ["ACME_hpmk_on", false] && {isNil {_patient getVariable "ACME_hpmk_lastTickLocal"}}) then {
    _patient setVariable ["ACME_hpmk_lastTickLocal", CBA_missionTime, false];
};
if ((_patient getVariable ["ACME_thora_tube_left", false]) || {_patient getVariable ["ACME_thora_tube_right", false]}) then {
    [_patient] call ACME_fnc_thoraPassiveDrain;
};

// A stable or isolated chest injury still needs the shared progression controller.
// Adopting an existing injury must never replay native injury creation on migration.
private _hasPtx = (_patient getVariable ["ACM_breathing_Pneumothorax_State", 0]) > 0
    || {_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]}
    || {_patient getVariable ["ACM_breathing_ChestInjury_State", false]}
    || {count (_patient getVariable ["ACME_ptx_state", []]) > 0};
if (_hasPtx) then {[_patient] call ACME_fnc_ptxEnsure;};

// NA3 one enrollment registry supplies independent medical maintenance.
private _needs = (_patient getVariable ["ace_medical_inCardiacArrest", false])
    || {_hasPtx}
    || {_patient getVariable ["ACE_isUnconscious", false]}
    || {_patient getVariable ["ACME_vent_connected", false]}
    || {_patient getVariable ["ACME_ETT_Inserted", false]}
    || {_patient getVariable ["ACME_nrb_on", false]}
    || {_patient getVariable ["ACME_tbi_HasTBI", false]}
    || {(_patient getVariable ["ACME_blastLung_State", 0]) > 0}
    || {count (_patient getVariable ["ACME_circ_State", createHashMap]) > 0}
    || {count (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) > 0}
    || {count (_patient getVariable ["ace_medical_medications", []]) > 0}
    || {count (_patient getVariable ["ACME_yFlushJobs", createHashMap]) > 0}
    || {count (_patient getVariable ["ACME_suctionSessions", []]) > 0}
    || {(_patient getVariable ["ACME_suctionExposure", 0]) > 0}
    || {(_patient getVariable ["ACME_o2Drain_suction", 0]) > 0}
    || {(_patient getVariable ["ACME_laryngo_irritationUntil", 0]) > CBA_missionTime};
private _registry = missionNamespace getVariable ["ACME_clinical_activePatients", []];
if (_needs) then {_registry pushBackUnique _patient;} else {_registry = _registry - [_patient];};
missionNamespace setVariable ["ACME_clinical_activePatients", _registry];
if (count (_patient getVariable ["ACME_infusion_BagMedications", []]) > 0) then {
    private _infusions = missionNamespace getVariable ["ACME_infusion_activePatients", []]; _infusions pushBackUnique _patient;
    missionNamespace setVariable ["ACME_infusion_activePatients", _infusions];
};
[_patient] call ACME_fnc_junctionalResume;
[_patient] call ACME_fnc_clinicalBagRecover;

// Continue only a native vomiting worker that was actually active on the old
// owner/loaded episode. Existing contents or a procedural miss never enroll one.
if (_patient getVariable ["ACME_nativeVomitActive", false]) then {
    [_patient] call ACM_airway_fnc_handleAirwayObstruction_Vomit;
};

// Resume only native physiology workers that were already running before ownership moved.
if (_patient getVariable ["ACME_nativeCollapseActive", false]) then {
    [_patient] call ACM_airway_fnc_handleAirwayCollapse;
};
if (_patient getVariable ["ACME_nativeBloodObstructionActive", false]) then {
    [_patient] call ACM_airway_fnc_handleAirwayObstruction_Blood;
};
if (_patient getVariable ["ACME_nativeHemolysisActive", false]) then {
    [_patient, true] call ACM_circulation_fnc_handleHemolyticReaction;
};

// Recovery is keyed by actual worker absence, not a once-per-owner attempt.
// Inspect the raw native rhythm; a presentation overlay must not select the worker.
if (_patient getVariable ["ace_medical_inCardiacArrest", false]) then {
    private _raw = _patient getVariable ["ACM_circulation_Cardiac_RhythmState", 0];
    if (_raw == 5) then {
        if (_patient getVariable ["ACM_circulation_ReversibleCardiacArrest_PFH", -1] < 0) then {
            [_patient, true] call ACM_circulation_fnc_handleReversibleCardiacArrest;
        };
    } else {
        if (_raw in [2,3,4] && {_patient getVariable ["ACM_circulation_CardiacArrest_PFH", -1] < 0}) then {
            [_patient, true] call ACM_circulation_fnc_handleCardiacArrest;
        };
    };
};
if (_patient getVariable ["ACME_AAJT_zone3", false]) then {[_patient] call ACME_fnc_aajtDownedTick;};
if ((_patient getVariable ["ACME_AAJT_zone3", false])
    || {_patient getVariable ["ACME_AAJT_inguinal", false]}
    || {_patient getVariable ["ACME_AAJT_axillaleft", false]}
    || {_patient getVariable ["ACME_AAJT_axillaright", false]}) then {[_patient] call ACME_fnc_aajtPainTick;};
