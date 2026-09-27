/*
 * Death is a physiology stop, not a treatment/evidence reset.
 * Preserve wounds, IV/IO access, airway devices, chest seals/holes, thoracostomy/chest tubes, AAJT-S/XStat,
 * HPMK/NRB/ventilator custody and every other patient intervention. Only owner-local workers/runtime ledgers are
 * stopped so corpses do not keep consuming scheduler/network budget.
 */
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {};

// The begin half invalidates delayed work, removes native/custom PFHs and active-list membership, but does not clear
// clinical/intervention fields. Do not run the finish half: finish is the full-heal/respawn reset path.
[_patient, "begin", true] call ACME_fnc_clinicalReset;
[_patient] call ACME_fnc_deadPhysiologyFreeze;
_patient setVariable ["ACME_resetVentCustody", nil, false];

// Stop presentation-only seizure motion. Do not tear down an actively held direct-pressure action here: direct
// pressure is intentionally still usable on a corpse, and silently releasing it on death would disclose the state.
if (!isNil "ACME_fnc_seizureMotion") then {[_patient, false] call ACME_fnc_seizureMotion;};

// A corpse does not need respiratory/physiology enrollment. Device custody and visible intervention fields stay.
{
    private _list = missionNamespace getVariable [_x, []];
    if (_list isEqualType []) then {missionNamespace setVariable [_x, _list - [_patient]];};
} forEach [
    "ACME_nrb_activePatients", "ACME_hpmk_activePatients", "ACME_tbi_activePatients", "ACME_cs_activePatients",
    "ACME_coag_activePatients", "ACME_autoBP_patients", "ACME_clinical_activePatients", "ACME_infusion_activePatients", "ACME_circ_activePatients"
];
