/* B175 one-shot provider gesture for instantaneous minigame actions.
 * Never interrupts an unrelated ACME-owned finite treatment pose. NAR SPEAR is the deliberate exception:
 * it may hand off from the chest-seal workspace, own one bounded ncdSeat episode, then return to that workspace.
 * _duration is the maximum owned window; <=0 lets the helper use a safe native-duration fallback.
 */
params [
    ["_medic", objNull, [objNull]],
    ["_mode", "", [""]],
    ["_duration", -1, [0]],
    ["_patient", objNull, [objNull]]
];
if (isNull _medic || {!local _medic} || {!alive _medic} || {_mode == ""}) exitWith {false};

private _existing = _medic getVariable ["ACME_treatmentPoseState", []];
private _resumeChestWorkspace = false;
private _blockedByExistingPose = false;
if !(_existing isEqualTo []) then {
    private _existingMode = _existing param [1, ""];
    private _existingEpoch = _existing param [0, -1];
    if (_mode == "ncdSeat"
        && {_existingMode == "chestSealWorkspace"}
        && {!isNull _patient}
        && {(uiNamespace getVariable ["ACME_CS_Patient", objNull]) isEqualTo _patient}
        && {(uiNamespace getVariable ["ACME_CS_Medic", objNull]) isEqualTo _medic}) then {
        _resumeChestWorkspace = true;
        [_medic, _existingMode, _existingEpoch, true] call ACME_fnc_treatmentPoseStop;
    } else {
        _blockedByExistingPose = true;
    };
};
if (_blockedByExistingPose) exitWith {false};

private _window = if (_duration > 0) then {_duration} else {3};
// If this starts outside an already-held workspace, account for the normal provider stand/prone -> kneel entry.
private _entry = if (_resumeChestWorkspace) then {0} else {
    switch (stance _medic) do {case "STAND": {0.65}; case "PRONE": {1.116}; default {0};};
};

private _epoch = [_medic, _mode, _window, _patient] call ACME_fnc_treatmentPoseStart;
if !(_epoch isEqualType 0 && {_epoch >= 0}) exitWith {
    if (_resumeChestWorkspace
        && {!isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])}
        && {(uiNamespace getVariable ["ACME_CS_Medic", objNull]) isEqualTo _medic}
        && {(uiNamespace getVariable ["ACME_CS_Patient", objNull]) isEqualTo _patient}) then {
        [_medic, _patient] call ACME_fnc_chestSealProviderHoldStart;
    };
    false
};

[{
    params ["_m","_p","_mode","_epoch","_resume"];
    if (isNull _m || {!local _m}) exitWith {};
    private _state = _m getVariable ["ACME_treatmentPoseState", []];
    if ((_state param [0,-2]) != _epoch || {(_state param [1,""]) != _mode}) exitWith {};

    [_m,_mode,_epoch,_resume] call ACME_fnc_treatmentPoseStop;

    if (_resume
        && {!isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])}
        && {(uiNamespace getVariable ["ACME_CS_Medic", objNull]) isEqualTo _m}
        && {(uiNamespace getVariable ["ACME_CS_Patient", objNull]) isEqualTo _p}) then {
        private _holdEpoch = [_m, _p] call ACME_fnc_chestSealProviderHoldStart;
        _m setVariable ["ACME_CS_providerHoldEpoch", _holdEpoch, false];
        uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch", _holdEpoch];
    };
}, [_medic,_patient,_mode,_epoch,_resumeChestWorkspace], _window + _entry] call CBA_fnc_waitAndExecute;

true
