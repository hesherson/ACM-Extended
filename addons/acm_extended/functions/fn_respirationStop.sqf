/* B213 retire only the captured observation, then return its provider and UI ownership exactly once. */
disableSerialization;
params [["_complete", false], ["_reopen", false], ["_epoch", -1], ["_handoff", false], ["_releaseDP", true]];
private _session = uiNamespace getVariable ["ACME_RespirationSession", []];
if (_session isEqualTo [] || {_epoch >= 0 && {(_session select 0) != _epoch}}) exitWith {};
_session params ["_currentEpoch", "_medic", "_patient", "_poseEpoch", "_pfh", "_watch", "", "", "", "_main", "_keyEH"];
uiNamespace setVariable ["ACME_RespirationSession", []];
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
if (!isNull _main && {_keyEH >= 0}) then {_main displayRemoveEventHandler ["KeyDown", _keyEH];};
private _watchControl = _session param [13, controlNull];
if (!isNull _watchControl) then {ctrlDelete _watchControl;};
"ACME_Respiration" cutText ["", "PLAIN", 0, false];
if (_poseEpoch >= 0) then {[_medic, "pulse", _poseEpoch, _handoff] call ACME_fnc_treatmentPoseStop;};

// A successor treatment already owns TreatmentBusy. Only a real finish/cancel hands it back to DP.
if (_releaseDP && {!isNull _medic} && {local _medic}
    && {_medic getVariable ["ACME_DP_Active", false]}
    && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}) then {
    _medic setVariable ["ACME_DP_TreatmentBusy", false, false];
    _medic setVariable ["ACME_DP_InPose", false, false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
};
private _validProvider = !isNull _medic && {local _medic} && {alive _medic}
    && {_medic isEqualTo ACE_player} && {!(_medic getVariable ["ACE_isUnconscious", false])};
// Never report a partial or canceled observation as a completed measurement.
if (_complete && {_validProvider} && {count _watch >= 5}
    && {(_watch select 1) - (_watch select 0) >= 15}) then {
    private _count = _watch select 3;
    private _estimate = round (_count * 60 / 15);
    [format ["Respirations: %1~ /min (%2 breaths in 15 seconds)", _estimate, _count], 5, _medic] call ace_common_fnc_displayTextStructured;
    private _resultArgs = [[_medic, false, true] call ace_common_fnc_getName, _estimate, _count];
    [_patient, "activity", "%1 measured respirations @ %2 RR/min~ (%3 breaths in 15 seconds)", _resultArgs] call ace_medical_treatment_fnc_addToLog;
    [_patient, "quick_view", "%1 measured respirations @ %2 RR/min~ (%3 breaths in 15 seconds)", _resultArgs] call ace_medical_treatment_fnc_addToLog;
};
if (_reopen && {_validProvider} && {!isNull _patient}
    && {(uiNamespace getVariable ["ACME_RespirationEpoch", -1]) == _currentEpoch}) then {
    [_patient, "examine"] call ACME_fnc_reopenMedicalMenu;
};
