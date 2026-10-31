/* B213: real successor work owns the hands immediately; a menu alone does not. */
params ["_medic", ["_patient", objNull]];
(_medic getVariable ["ACME_DP_TreatmentBusy", false])
    || {_medic getVariable ["ACME_DP_Paused", false]}
    || {_medic getVariable ["ACME_treatmentPreflightActive", false]}
    || {(_medic getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []}
    || {(_medic getVariable ["ACME_nativeTreatmentRate", []]) isNotEqualTo []}
    || {_medic getVariable ["ACME_chestAccessPreflightActive", false]}
    || {(_medic getVariable ["ACME_chestAccessProvider", []]) isNotEqualTo []}
    || {_medic getVariable ["ACME_headElev_seqActive", false]}
    || {_medic getVariable ["ACME_rollProviderActive", false]}
    || {_medic getVariable ["ACM_circulation_isPerformingCPR", false]}
    || {_medic getVariable ["ACM_breathing_isUsingBVM", false]}
    || {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}
    || {!isNull _patient && {[_patient] call ACM_core_fnc_cprActive}}
    || {!isNull _patient && {[_patient] call ACM_core_fnc_bvmActive}}
    // Only ACE's own final bookkeeping receives the short entry grace. A new real controller never does.
    || {CBA_missionTime >= (_medic getVariable ["ACME_DP_PoseGraceUntil", 0])
        && {(_medic getVariable ["ace_medical_treatment_endInAnim", ""]) != ""}}
