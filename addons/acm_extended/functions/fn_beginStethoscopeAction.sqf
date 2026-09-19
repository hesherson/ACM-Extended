/* B45 stethoscope-only continuous action controller.
 *
 * The scope dialog owns its own lifetime. A provider pose ending is NOT a treatment cancellation: B44 coupled
 * those two states, so the panel disappeared with "Stopped using stethoscope" whenever the held pose retired
 * before the bell was picked up. Normal exit is Escape, and every normal dialog close routes back to the
 * previous medical menu. H is consumed while the scope is open so it cannot silently replace the minigame.
 */
params ["_args", "_onStart", "_onCancel", "_perFrame", ["_allowProne", false], ["_dialogID", -1]];
_args params ["_medic", "_patient", "_bodyPart", ["_extraArgs", []]];

if (ACM_core_ContinuousAction_Active) exitWith {};

// B127 shares the same generation as ACM_core_fnc_beginContinuousAction. The old stethoscope PFH used only the
// global Active flag, so an interrupted scope could survive long enough to see a later maneuver set Active=true and
// then close/cancel that newer maneuver. Each scope now owns one immutable generation.
private _epoch = (missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", 0]) + 1;
missionNamespace setVariable ["ACM_core_ContinuousAction_Epoch", _epoch];
private _isDialog = (_dialogID != -1);
ACM_core_ContinuousAction_IsDialog = _isDialog;
ACM_core_ContinuousAction_Active = true;
ACM_core_ContinuousAction_ShouldReopen = false;
ace_medical_gui_pendingReopen = false;

// Remove generic continuous-action key handlers left by an interrupted older generation. The stethoscope dialog
// uses its own display handler when possible, but the non-dialog fallback shares the global ESC slot.
private _oldOpenID = missionNamespace getVariable ["ACM_core_ContinuousAction_OpenMedicalMenu_ID", -1];
if (!(_oldOpenID isEqualTo -1) && {!(_oldOpenID isEqualTo "")}) then {[_oldOpenID, "keydown"] call CBA_fnc_removeKeyHandler;};
private _oldEscapeID = missionNamespace getVariable ["ACM_core_ContinuousAction_Cancel_EscapeID", -1];
if (!(_oldEscapeID isEqualTo -1) && {!(_oldEscapeID isEqualTo "")}) then {[_oldEscapeID, "keydown"] call CBA_fnc_removeKeyHandler;};
missionNamespace setVariable ["ACM_core_ContinuousAction_OpenMedicalMenu_ID", -1];
missionNamespace setVariable ["ACM_core_ContinuousAction_Cancel_EscapeID", -1];

if (dialog) then {closeDialog 0;};

private _notInVehicle = isNull objectParent _medic;

// The stethoscope is a long frozen provider pose. Clear a stale logical rifle selection exactly once before pose
// ownership begins; never issue per-frame put-away/select requests while the camera is attached to this maneuver.
if (local _medic && {currentWeapon _medic != ""}) then {_medic selectWeapon "";};

// One animation owner is enough, but its lifetime is deliberately independent from the dialog lifetime.
private _poseEpoch = [_medic, "stethoscope"] call ACME_fnc_treatmentPoseStart;
_args call _onStart;

private _dialogKeyEH = -1;
private _scopeDisplay = displayNull;
private _keyID = -1;
if (_isDialog) then {
    _scopeDisplay = findDisplay _dialogID;
    if (!isNull _scopeDisplay) then {
        _scopeDisplay setVariable ["ACME_continuousEpoch", _epoch];
        _dialogKeyEH = _scopeDisplay displayAddEventHandler ["KeyDown", {
            params ["_display", "_key"];
            private _epoch = _display getVariable ["ACME_continuousEpoch", -1];
            if ((missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -2]) != _epoch) exitWith {false};
            // DIK_ESCAPE. Consume the native close and let the controller run one clean cancellation/reopen path.
            if (_key == 0x01) exitWith {
                ACM_core_ContinuousAction_ShouldReopen = true;
                ACM_core_ContinuousAction_Active = false;
                true
            };
            // DIK_H. The medical-menu hotkey must not replace a live stethoscope minigame.
            if (_key == 0x23) exitWith {true};
            false
        }];
    };
} else {
    private _keyCode = compile format [
        "if ((missionNamespace getVariable ['ACM_core_ContinuousAction_Epoch', -1]) == %1) then {missionNamespace setVariable ['ACM_core_ContinuousAction_ShouldReopen', true]; missionNamespace setVariable ['ACM_core_ContinuousAction_Active', false];}; false",
        _epoch
    ];
    _keyID = [0x01, [false, false, false], _keyCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;
    ACM_core_ContinuousAction_Cancel_EscapeID = _keyID;
};

private _pfh = [{
    params ["_args", "_idPFH"];
    _args params ["_medic", "_patient", "_bodyPart", "_extraArgs", "_notInVehicle", "_poseEpoch", "_perFrame", "_onCancel", "_dialogID", "_dialogKeyEH", "_scopeDisplay", "_keyID", "_isDialog", "_epoch"];

    // A newer continuous action owns the globals now. Remove only this scope's PFH/input hook and its token-safe pose;
    // never execute the old cancellation/reopen path against the new owner.
    if ((missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1]) != _epoch) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if (_isDialog) then {
            if (!isNull _scopeDisplay && {_dialogKeyEH >= 0}) then {_scopeDisplay displayRemoveEventHandler ["KeyDown", _dialogKeyEH];};
        } else {
            if (!(_keyID isEqualTo -1) && {!(_keyID isEqualTo "")}) then {[_keyID, "keydown"] call CBA_fnc_removeKeyHandler;};
        };
        [_medic, "stethoscope", _poseEpoch] call ACME_fnc_treatmentPoseStop;
    };

    private _patientCondition = isNull _patient;
    private _medicCondition = isNull _medic || {!local _medic} || {!(alive _medic)} || {_medic getVariable ["ACE_isUnconscious", false]} || {_medic isNotEqualTo ACE_player};
    private _vehicleCondition = (objectParent _medic isNotEqualTo objectParent _patient);
    private _enteredVehicle = _notInVehicle && {!isNull objectParent _medic};
    private _distanceCondition = (!isNull _patient) && {(_patient distance2D _medic > ace_medical_gui_maxDistance)};

    private _dialogCondition = dialog;
    if (_isDialog) then {
        _dialogCondition = isNull (findDisplay _dialogID);
    };

    // DO NOT include treatmentPoseEpisode here. Bell pickup/drag state and animation retirement cannot close the
    // scope. Only an explicit close/ESC or a genuinely invalid treatment context ends the action.
    if (_patientCondition || _medicCondition || _enteredVehicle || !ACM_core_ContinuousAction_Active || _dialogCondition
        || {(!_notInVehicle && _vehicleCondition) || {(_notInVehicle && _distanceCondition)}}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;

        if (_isDialog) then {
            private _d = findDisplay _dialogID;
            if (!isNull _d && {_dialogKeyEH >= 0}) then {_d displayRemoveEventHandler ["KeyDown", _dialogKeyEH];};
        } else {
            if (!(_keyID isEqualTo -1) && {!(_keyID isEqualTo "")}) then {[_keyID, "keydown"] call CBA_fnc_removeKeyHandler;};
            if ((missionNamespace getVariable ["ACM_core_ContinuousAction_Cancel_EscapeID", -1]) == _keyID) then {
                missionNamespace setVariable ["ACM_core_ContinuousAction_Cancel_EscapeID", -1];
            };
        };

        // A dialog that was closed normally (ESC or UI teardown while the treatment context is still valid)
        // returns to the medical menu. Do not try to reopen for a dead/unconscious/remote medic.
        private _returnToMenu = (ACM_core_ContinuousAction_ShouldReopen || {_dialogCondition})
            && {!_patientCondition} && {!_medicCondition};

        ACM_core_ContinuousAction_Active = false;
        [_medic, "stethoscope", _poseEpoch] call ACME_fnc_treatmentPoseStop;
        [_medic, _patient, _bodyPart, _extraArgs, _notInVehicle] call _onCancel;

        ["ace_treatmentFailed", [_medic, _patient, _bodyPart, "ACM_ContinuousAction", "", "", false]] call CBA_fnc_localEvent;

        if (_returnToMenu) then {
            ["ACM_core_openMedicalMenu", _patient] call CBA_fnc_localEvent;
        };
    };

    _args call _perFrame;
}, 0, [_medic, _patient, _bodyPart, _extraArgs, _notInVehicle, _poseEpoch, _perFrame, _onCancel, _dialogID, _dialogKeyEH, _scopeDisplay, _keyID, _isDialog, _epoch]] call CBA_fnc_addPerFrameHandler;

missionNamespace setVariable ["ACM_core_ContinuousAction_PFH", _pfh];
