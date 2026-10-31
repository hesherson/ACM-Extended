/* B45 stethoscope-only continuous action controller.
 *
 * The scope dialog owns its own lifetime. A provider pose ending is NOT a treatment cancellation: B44 coupled
 * those two states, so the panel disappeared with "Stopped using stethoscope" whenever the held pose retired
 * before the bell was picked up. Normal exit is Escape, and every normal dialog close routes back to the
 * previous medical menu. H is consumed while the scope is open so it cannot silently replace the minigame.
 */
params ["_args", "_onStart", "_onCancel", "_perFrame", ["_allowProne", false], ["_dialogID", -1]];
_args params ["_medic", "_patient", "_bodyPart", ["_extraArgs", []]];

if (isNull _medic || {isNull _patient} || {!local _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]} || {ACM_core_ContinuousAction_Active}) exitWith {false};

// B127 shares the same generation as ACM_core_fnc_beginContinuousAction. The old stethoscope PFH used only the
// global Active flag, so an interrupted scope could survive long enough to see a later maneuver set Active=true and
// then close/cancel that newer maneuver. Each scope now owns one immutable generation.
private _epoch = (missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", 0]) + 1;
private _providerTreatmentEpoch = _medic getVariable ["ACME_providerTreatmentEpoch", 0];
[_medic, [["epoch", _epoch]], false] call ACM_core_fnc_setContinuousActionState;

// Match the core continuous-action ownership contract. Provider reconciliation treats an active controller
// without a matching session/heartbeat as stale; the stethoscope used to omit both and was therefore torn down
// about a second after opening even though its dialog was healthy.
[_medic, [["session", [_patient, _epoch]], ["lastSeen", CBA_missionTime]], true] call ACM_core_fnc_setContinuousActionState;

private _isDialog = (_dialogID != -1);
[_medic, [["isDialog", _isDialog], ["active", true], ["shouldReopen", false]], false] call ACM_core_fnc_setContinuousActionState;
ace_medical_gui_pendingReopen = false;

// Remove generic continuous-action key handlers left by an interrupted older generation. The stethoscope dialog
// uses its own display handler when possible, but the non-dialog fallback shares the global ESC slot.
private _oldOpenID = missionNamespace getVariable ["ACM_core_ContinuousAction_OpenMedicalMenu_ID", -1];
if (!(_oldOpenID isEqualTo -1) && {!(_oldOpenID isEqualTo "")}) then {[_oldOpenID, "keydown"] call CBA_fnc_removeKeyHandler;};
private _oldEscapeID = missionNamespace getVariable ["ACM_core_ContinuousAction_Cancel_EscapeID", -1];
if (!(_oldEscapeID isEqualTo -1) && {!(_oldEscapeID isEqualTo "")}) then {[_oldEscapeID, "keydown"] call CBA_fnc_removeKeyHandler;};
[_medic, [["openMedicalMenuID", -1], ["cancelEscapeID", -1]], false] call ACM_core_fnc_setContinuousActionState;

if (dialog) then {closeDialog 0;};

private _notInVehicle = isNull objectParent _medic;

// The stethoscope is a long provider pose. Weapon state is owned by treatmentPoseStart/medicAnimationPrep; do not
// use selectWeapon "" here, because a sidearm can remain visibly attached after its logical selection is cleared.

// Install recovery/cancellation before opening the UI: a throwing OnStart must not strand its patient state.
private _scopeDisplay = displayNull;
private _poseEpoch = -1;
private _dialogKeyEH = -1;
private _keyID = -1;
private _worker = {
    params ["_args", "_idPFH"];
    _args params ["_medic", "_patient", "_bodyPart", "_extraArgs", "_notInVehicle", "_poseEpoch", "_perFrame", "_onCancel", "_dialogID", "_dialogKeyEH", "_scopeDisplay", "_keyID", "_isDialog", "_epoch", "_startupComplete", ["_providerTreatmentEpoch", -1]];

    // A newer continuous action owns the globals now. Remove only this scope's PFH/input hook and its token-safe pose;
    // never execute the old cancellation/reopen path against the new owner.
    if ((missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1]) != _epoch) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if (_isDialog) then {
            if (!isNull _scopeDisplay && {_dialogKeyEH >= 0}) then {_scopeDisplay displayRemoveEventHandler ["KeyDown", _dialogKeyEH];};
        } else {
            if (!(_keyID isEqualTo -1) && {!(_keyID isEqualTo "")}) then {[_keyID, "keydown"] call CBA_fnc_removeKeyHandler;};
        };
        if (_poseEpoch >= 0) then {[_medic, "stethoscope", _poseEpoch, true] call ACME_fnc_treatmentPoseStop;};
    };

    private _controller = missionNamespace getVariable ["ACM_core_ContinuousAction_Controller", []];
    if ((_controller param [2, -2]) != _epoch) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    private _patientCondition = isNull _patient;
    private _medicCondition = isNull _medic || {!local _medic} || {!(alive _medic)} || {_medic getVariable ["ACE_isUnconscious", false]};
    private _vehicleCondition = (objectParent _medic isNotEqualTo objectParent _patient);
    private _enteredVehicle = _notInVehicle && {!isNull objectParent _medic};
    private _distanceCondition = (!isNull _patient) && {(_patient distance2D _medic > ace_medical_gui_maxDistance)};

    private _dialogCondition = dialog;
    if (_isDialog) then {
        _dialogCondition = isNull (findDisplay _dialogID);
    };

    // DO NOT include treatmentPoseEpisode here. Bell pickup/drag state and animation retirement cannot close the
    // scope. Only an explicit close/ESC or a genuinely invalid treatment context ends the action.
    if (!_startupComplete || _patientCondition || _medicCondition || _enteredVehicle || !ACM_core_ContinuousAction_Active || _dialogCondition
        || {(!_notInVehicle && _vehicleCondition) || {(_notInVehicle && _distanceCondition)}}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;

        if (_isDialog) then {
            private _d = findDisplay _dialogID;
            if (!isNull _d && {_dialogKeyEH >= 0}) then {_d displayRemoveEventHandler ["KeyDown", _dialogKeyEH];};
        } else {
            if (!(_keyID isEqualTo -1) && {!(_keyID isEqualTo "")}) then {[_keyID, "keydown"] call CBA_fnc_removeKeyHandler;};
            if ((missionNamespace getVariable ["ACM_core_ContinuousAction_Cancel_EscapeID", -1]) == _keyID) then {
                [_medic, [["cancelEscapeID", -1]], false] call ACM_core_fnc_setContinuousActionState;
            };
        };

        // A dialog that was closed normally (ESC or UI teardown while the treatment context is still valid)
        // returns to the medical menu. Do not try to reopen for a dead/unconscious/remote medic.
        private _returnToMenu = (ACM_core_ContinuousAction_ShouldReopen || {_dialogCondition})
            && {!_patientCondition} && {!_medicCondition};

        [_medic, [["active", false], ["isDialog", false], ["pfh", -1], ["controller", []]], false] call ACM_core_fnc_setContinuousActionState;
        if ((_medic getVariable ["ACM_core_ContinuousAction_Session", []]) isEqualTo [_patient, _epoch]) then {
            [_medic, [["session", []]], true] call ACM_core_fnc_setContinuousActionState;
        };
        // A live display's Unload owns the appropriate normal-vs-carrier exit. Do not retire its
        // pose first in handoff mode, which leaves a no-carrier provider with no exit to execute.
        if (_poseEpoch >= 0 && {isNull _scopeDisplay}) then {[_medic, "stethoscope", _poseEpoch, false] call ACME_fnc_treatmentPoseStop;};
        [_medic, _patient, _bodyPart, _extraArgs, _notInVehicle] call _onCancel;

        // A carrier preflight paused DP under UseStethoscope, not the generic
        // ACM_ContinuousAction name. Retire that pause even if no display survived.
        [_medic, _patient, _epoch, _providerTreatmentEpoch] call ACME_fnc_stethoscopePressureRelease;
        ["ace_treatmentFailed", [_medic, _patient, _bodyPart, "ACM_ContinuousAction", "", "", false]] call CBA_fnc_localEvent;

        if (_returnToMenu && {(missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1]) == _epoch}
            && {!ACM_core_ContinuousAction_Active}) then {
            ["ACM_core_openMedicalMenu", _patient] call CBA_fnc_localEvent;
        };
    };

    _args call _perFrame;

    // A failed scope callback must not keep an orphaned controller looking healthy.
    if (ACM_core_ContinuousAction_Active
        && {(missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1]) == _epoch}
        && {CBA_missionTime - (_medic getVariable ["ACM_core_ContinuousAction_LastSeen", -100]) >= 2}) then {
        [_medic, [["lastSeen", CBA_missionTime]], true] call ACM_core_fnc_setContinuousActionState;
    };

};
private _workerArgs = [_medic, _patient, _bodyPart, _extraArgs, _notInVehicle, _poseEpoch, _perFrame, _onCancel, _dialogID, _dialogKeyEH, _scopeDisplay, _keyID, _isDialog, _epoch, false, _providerTreatmentEpoch];
private _pfh = [_worker, 0, _workerArgs] call CBA_fnc_addPerFrameHandler;
[_medic, [["pfh", _pfh], ["controller", [_medic, _patient, _epoch, _worker, _workerArgs, _pfh]]], false] call ACM_core_fnc_setContinuousActionState;

// Open the clinical UI before presentation takes animation ownership. A provider animation failure must never
// consume the auscultation click. fnc_useStethoscope creates/initializes the display synchronously in _onStart.
_args call _onStart;

_scopeDisplay = if (_isDialog) then {findDisplay _dialogID} else {displayNull};
_workerArgs set [10, _scopeDisplay];
if (_isDialog && {isNull _scopeDisplay}) exitWith {
    // Reuse normal cancellation, including the action's reservation/clinical cleanup.
    [_medic, [["active", false]], false] call ACM_core_fnc_setContinuousActionState;
    [_workerArgs, _pfh] call _worker;
    false
};

// The provider pose is presentation only and starts after the minigame exists.
_poseEpoch = [_medic, "stethoscope", -1, _patient] call ACME_fnc_treatmentPoseStart;
_workerArgs set [5, _poseEpoch];

if (_isDialog) then {
    if (!isNull _scopeDisplay) then {
        // The display owns the exact continuous-action and treatment-pose generations that created it.
        // Its Unload EH can therefore release only this scope, even if the normal controller PFH is interrupted.
        _scopeDisplay setVariable ["ACME_continuousEpoch", _epoch];
        _scopeDisplay setVariable ["ACME_stethMedic", _medic];
        _scopeDisplay setVariable ["ACME_stethPoseEpoch", _poseEpoch];
        _scopeDisplay setVariable ["ACME_stethProviderTreatmentEpoch", _providerTreatmentEpoch];

        _dialogKeyEH = _scopeDisplay displayAddEventHandler ["KeyDown", {
            params ["_display", "_key"];
            private _epoch = _display getVariable ["ACME_continuousEpoch", -1];
            if ((missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -2]) != _epoch) exitWith {false};
            // DIK_ESCAPE. Consume the native close and let the controller run one clean cancellation/reopen path.
            if (_key == 0x01) exitWith {
                [_display getVariable ["ACME_stethMedic", objNull], [["shouldReopen", true], ["active", false]], false] call ACM_core_fnc_setContinuousActionState;
                true
            };
            // DIK_H. The medical-menu hotkey must not replace a live stethoscope minigame.
            if (_key == 0x23) exitWith {true};
            false
        }];
    };
} else {
    private _keyCode = compile format [
        "if ((missionNamespace getVariable ['ACM_core_ContinuousAction_Epoch', -1]) == %1) then {[objNull, [['shouldReopen', true], ['active', false]], false] call ACM_core_fnc_setContinuousActionState;}; false",
        _epoch
    ];
    _keyID = [0x01, [false, false, false], _keyCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;
    [_medic, [["cancelEscapeID", _keyID]], false] call ACM_core_fnc_setContinuousActionState;
};

_workerArgs set [9, _dialogKeyEH];
_workerArgs set [10, _scopeDisplay];
_workerArgs set [11, _keyID];
// Failed initialization must take the normal cancellation branch on its next worker invocation.
_workerArgs set [14, true];
true
