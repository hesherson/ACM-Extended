/* Release only the completed scope's pressure pause. Do not stop/restart DP, release
 * its patient-owner claim, or assert a pose over the remaining carrier restoration.
 * Both controller fallback and display Unload may call this; duplicates are harmless. */
params [
    ["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]],
    ["_scopeEpoch", -1, [0]], ["_treatmentEpoch", -1, [0]]
];
if (isNull _medic || {!local _medic} || {isNull _patient}
    || {_scopeEpoch < 0} || {_treatmentEpoch < 0}
    || {(missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -2]) != _scopeEpoch}
    || {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}
    || {(_medic getVariable ["ACME_providerTreatmentEpoch", -2]) != _treatmentEpoch}
    || {!(_medic getVariable ["ACME_DP_Active", false])}
    || {!((_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient)}) exitWith {false};
private _pauseClass = _medic getVariable ["ACME_DP_PauseTreatmentClass", ""];
if (_pauseClass != "usestethoscope") exitWith {false};
_medic setVariable ["ACME_DP_Paused", false, false];
_medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
_medic setVariable ["ACME_DP_TreatmentBusy", false, false];
_medic setVariable ["ACME_DP_InPose", false, false];
_medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
_medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
// directPressureTick still yields to the actual head/carrier/body controller;
// directPressurePose applies the existing two-second quiet delay once it is free.
true
