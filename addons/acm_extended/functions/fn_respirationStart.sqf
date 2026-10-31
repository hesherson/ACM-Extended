/* B213 Measure Respirations: the existing Feel Pulse provider sequence with a 15-second observation watch.
 * diag_tickTime drives both the watch and counting; accelerated mission day/night never shortens the sample.
 * A same-vehicle observation uses the full watch but leaves both occupants' seat animations alone.
 */
disableSerialization;
params ["_medic", "_patient"];
if (!hasInterface || {isNull _medic} || {isNull _patient} || {!local _medic}
    || {_medic isNotEqualTo ACE_player} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {false};
private _vehicle = objectParent _medic;
if (_vehicle isNotEqualTo objectParent _patient
    || {isNull _vehicle && {_medic distance2D _patient > ace_medical_gui_maxDistance}}) exitWith {false};

// Fully retire a replaced observation before it can touch the successor's display or pose.
[false, false, -1, true] call ACME_fnc_respirationStop;
private _epoch = (uiNamespace getVariable ["ACME_RespirationEpoch", 0]) + 1;
uiNamespace setVariable ["ACME_RespirationEpoch", _epoch];
ace_medical_gui_pendingReopen = false;
if (dialog) then {closeDialog 0;};
"ACME_Respiration" cutRsc ["ACME_Respiration_Display", "PLAIN", 0, false];
private _display = uiNamespace getVariable ["ACME_RespirationDisplay", displayNull];
if (isNull _display) exitWith {false};
(_display displayCtrl 71592) ctrlSetText ([_patient, false, true] call ace_common_fnc_getName);

// Like Feel Pulse, the short ACE setup is over while the active observation still owns the provider.
if ((_medic getVariable ["ACME_DP_Active", false])
    && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}) then {
    _medic setVariable ["ACME_DP_TreatmentBusy", true, false];
};
private _poseEpoch = if (isNull _vehicle) then {
    [_medic, "pulse", -1, _patient] call ACME_fnc_treatmentPoseStart
} else {-1};
private _watchControl = _display ctrlCreate ["RscWatch", 71596];
if (!isNull _watchControl) then {_watchControl ctrlShow true;};
// Epoch, provider, casualty, pose, PFH, watch state, last visual breath, creation time,
// captured vehicle, main display, Escape EH, final-cue deadline, native treatment generation.
// Watch stays empty throughout preparation.
private _session = [_epoch, _medic, _patient, _poseEpoch, -1, [], -1e9, diag_tickTime, _vehicle, displayNull, -1, -1,
    _medic getVariable ["ACME_providerTreatmentEpoch", 0], _watchControl];
uiNamespace setVariable ["ACME_RespirationSession", _session];
if (isNull _vehicle && {_poseEpoch < 0}) exitWith {
    [false, true, _epoch] call ACME_fnc_respirationStop;
    false
};

// The cutRsc has no dialog input focus. Consume Escape on the main display as Feel Pulse does.
private _main = findDisplay 46;
if (!isNull _main) then {
    _main setVariable ["ACME_RespirationKeyEpoch", _epoch];
    private _eh = _main displayAddEventHandler ["KeyDown", {
        params ["_display", "_key"];
        private _session = uiNamespace getVariable ["ACME_RespirationSession", []];
        if (_key != 1 || {_session isEqualTo []}
            || {(_session select 0) != (_display getVariable ["ACME_RespirationKeyEpoch", -1])}) exitWith {false};
        [false, true, _session select 0] call ACME_fnc_respirationStop;
        true
    }];
    _session set [9, _main];
    _session set [10, _eh];
};
private _pfh = [{_this call ACME_fnc_respirationTick;}, 0, [_epoch]] call CBA_fnc_addPerFrameHandler;
_session set [4, _pfh];
true
