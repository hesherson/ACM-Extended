#include "..\script_component.hpp"
/*
 * Author: Blue
 * Begin continuous action
 *
 * Arguments:
 * 0: Arguments <ARRAY>
 *   0: Medic <OBJECT>
 *   1: Patient <OBJECT>
 *   2: Body Part <STRING>
 * 1: On Start <CODE>
 * 2: On Cancel <CODE>
 * 3: Per Frame Code <CODE>
 * 4: Allowed Prone <BOOL>
 * 5: Dialog ID <NUMBER>
 * 6: Suppress provider animation <BOOL>
 * 7: Reopen medical menu when this action ends <BOOL>
 *
 * Return Value:
 * Started <BOOL>
 *
 * Example:
 * [[player, cursorTarget, "Head"], {}, {}, {}] call ACM_core_fnc_beginContinuousAction;
 *
 * Public: No
 */

params [
    "_args", "_onStart", "_onCancel", "_perFrame",
    ["_allowProne", false],
    ["_dialogID", -1],
    ["_suppressProviderAnim", false, [false]],
    ["_reopenOnEnd", false, [false]]
];
_args params ["_medic", "_patient", "_bodyPart", ["_extraArgs", []]];

// A stale shared gate used to make every later continuous action silently no-op. A live generation publishes a
// provider session immediately and refreshes LastSeen at least every two seconds, so a missing session or >4 s
// heartbeat gap is definitive stale state on this client. Recover before the normal exclusivity guard; valid BVM,
// CPR, stethoscope, Narc Box and manual Semi-Fowler sessions remain exclusive exactly as before.
if (!isNull _medic && {local _medic} && {GVAR(ContinuousAction_Active)}) then {
    private _staleSession = _medic getVariable [QGVAR(ContinuousAction_Session), []];
    private _staleSeen = _medic getVariable [QGVAR(ContinuousAction_LastSeen), -1e6];
    if ((count _staleSession) < 2 || {(CBA_missionTime - _staleSeen) > 4}) then {
        GVAR(ContinuousAction_Active) = false;
        _medic setVariable [QGVAR(ContinuousAction_Session), [], true];
        GVAR(ContinuousAction_PFH) = -1;
    };
};

if (isNull _medic || {isNull _patient} || {!local _medic} || {!alive _medic}
    || {IS_UNCONSCIOUS(_medic)} || {GVAR(ContinuousAction_Active)}) exitWith {false};

// Bind only a session started by the local controlled unit. AI/local scripted
// providers retain their existing behavior when the player changes units.
private _playerBound = hasInterface && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player};

// B127: every continuous action gets a generation. The old implementation used only the shared Active boolean, so
// a delayed stance callback or PFH from action A could wake back up after action B set Active=true and then animate,
// cancel, close or reopen the newer action. Generation checks make every delayed callback belong to one episode.
private _epoch = (missionNamespace getVariable [QGVAR(ContinuousAction_Epoch), 0]) + 1;
GVAR(ContinuousAction_Epoch) = _epoch;
_medic setVariable [QGVAR(ContinuousAction_Session), [_patient, _epoch], true];
_medic setVariable [QGVAR(ContinuousAction_LastSeen), CBA_missionTime, true];
private _isDialog = (_dialogID != -1);
GVAR(ContinuousAction_IsDialog) = _isDialog;
GVAR(ContinuousAction_Active) = true;
// This accepted maneuver is patient-specific care, so its reopened medical menu
// may retain ACM's animated crouch. Merely opening a menu never enables it.
_medic setVariable ["ACME_menuPoseAfterTreatment", _patient];
if (!isNil "ACME_fnc_menuPoseStop") then {[_medic, true] call ACME_fnc_menuPoseStop;};
GVAR(ContinuousAction_ShouldReopen) = _reopenOnEnd;

ACEGVAR(medical_gui,pendingReopen) = false; // Prevent medical menu from reopening

// Clear any key handler left behind by an interrupted older generation before installing this one's handler. The
// PFH also removes its own id, but doing this synchronously prevents one stale ESC/H handler from touching the new
// action during the one-frame handoff.
private _oldOpenID = missionNamespace getVariable [QGVAR(ContinuousAction_OpenMedicalMenu_ID), -1];
if (!(_oldOpenID isEqualTo -1) && {!(_oldOpenID isEqualTo "")}) then {[_oldOpenID, "keydown"] call CBA_fnc_removeKeyHandler;};
private _oldEscapeID = missionNamespace getVariable [QGVAR(ContinuousAction_Cancel_EscapeID), -1];
if (!(_oldEscapeID isEqualTo -1) && {!(_oldEscapeID isEqualTo "")}) then {[_oldEscapeID, "keydown"] call CBA_fnc_removeKeyHandler;};
GVAR(ContinuousAction_OpenMedicalMenu_ID) = -1;
GVAR(ContinuousAction_Cancel_EscapeID) = -1;

// Non-dialog continuous actions (BVM, head tilt, etc.) are commonly started FROM ACE's medical/progress
// dialog. On a listen server closeDialog 0 is not guaranteed to make "dialog" false before the next PFH frame.
// Give only that startup handoff a bounded grace so the source dialog cannot immediately cancel the action.
private _dialogStartupUntil = diag_tickTime + 0.75;
if (dialog) then {
    closeDialog 0;
};

private _epochVar = QGVAR(ContinuousAction_Epoch);
private _activeVar = QGVAR(ContinuousAction_Active);
private _reopenVar = QGVAR(ContinuousAction_ShouldReopen);
private _keyID = -1;
if (_isDialog) then {
    // Embed the generation in the handler itself. If removal is ever missed, an old H handler becomes a no-op rather
    // than changing the reopen state of a later action.
    private _keyCode = compile format [
        "if ((missionNamespace getVariable ['%1', -1]) == %2) then {missionNamespace setVariable ['%3', true];}; false",
        _epochVar, _epoch, _reopenVar
    ];
    _keyID = [0x23, [false, false, false], _keyCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;
    GVAR(ContinuousAction_OpenMedicalMenu_ID) = _keyID;
} else {
    private _keyCode = compile format [
        "if ((missionNamespace getVariable ['%1', -1]) == %2) then {missionNamespace setVariable ['%3', false];}; false",
        _epochVar, _epoch, _activeVar
    ];
    _keyID = [0x01, [false, false, false], _keyCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;
    GVAR(ContinuousAction_Cancel_EscapeID) = _keyID;
};

// A finite assessment can still own a zero-speed hold when the next maneuver starts.
// Retire that owner before this action takes over, including its observer/JIP freeze.
if (!isNil "ACME_fnc_treatmentPoseStop") then {[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;};
private _choreographyRate = if (isNil "ACME_fnc_choreographyRate") then {1.5} else {call ACME_fnc_choreographyRate};
if (!_suppressProviderAnim) then {
    _medic setAnimSpeedCoef _choreographyRate;
    [QACEGVAR(common,setAnimSpeedCoef), [_medic, _choreographyRate]] call CBA_fnc_globalEvent;
};

private _notInVehicle = isNull objectParent _medic;

private _medicStance = stance _medic;
private _isProne = (_medicStance == "PRONE") && _allowProne;

if (_notInVehicle && {!_suppressProviderAnim}) then {
    switch (stance _medic) do {
        case "STAND": {
            [_medic, "AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 1] call ACEFUNC(common,doAnimation); // 0.650

            [{
                params ["_medic", "_epoch", "_playerBound"];
                if (GVAR(ContinuousAction_Active) && {GVAR(ContinuousAction_Epoch) == _epoch}
                    && {local _medic} && {alive _medic} && {isNull objectParent _medic}
                    && {!_playerBound || {_medic isEqualTo ACE_player}}) then {
                    [_medic, "ACM_GenericContinuous", 1] call ACEFUNC(common,doAnimation);
                };
            }, [_medic, _epoch, _playerBound], 0.65 / _choreographyRate] call CBA_fnc_waitAndExecute;
        };
        case "PRONE": {
            if (_allowProne) then {
                [_medic, "ACM_ProneContinuous", 1] call ACEFUNC(common,doAnimation);
            } else {
                [_medic, "AmovPpneMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 1] call ACEFUNC(common,doAnimation); // 1.116

                [{
                    params ["_medic", "_epoch", "_playerBound"];
                    if (GVAR(ContinuousAction_Active) && {GVAR(ContinuousAction_Epoch) == _epoch}
                    && {local _medic} && {alive _medic} && {isNull objectParent _medic}
                    && {!_playerBound || {_medic isEqualTo ACE_player}}) then {
                            [_medic, "ACM_GenericContinuous", 1] call ACEFUNC(common,doAnimation);
                    };
                }, [_medic, _epoch, _playerBound], 1.116 / _choreographyRate] call CBA_fnc_waitAndExecute;
            };
        };
        case "CROUCH": {
            [_medic, "ACM_GenericContinuous", 1] call ACEFUNC(common,doAnimation);
        };
        default {};
    };
};

if (currentWeapon _medic != "") then {
    [_medic] call ACEFUNC(weaponselect,putWeaponAway);
};

private _pfh = [{
    params ["_args", "_idPFH"];
    _args params ["_medic", "_patient", "_bodyPart", "_extraArgs", "_notInVehicle", "_isProne", "_perFrame", "_onCancel", "_dialogID", "_epoch", "_keyID", "_isDialog", "_dialogStartupUntil", "_playerBound", "_suppressProviderAnim", "_reopenOnEnd"];

    // Superseded action. Retire only this PFH and its own key id. Never run the old cancellation/reopen path against
    // the newer generation.
    if ((missionNamespace getVariable [QGVAR(ContinuousAction_Epoch), -1]) != _epoch) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if (!(_keyID isEqualTo -1) && {!(_keyID isEqualTo "")}) then {[_keyID, "keydown"] call CBA_fnc_removeKeyHandler;};
    };

    private _patientCondition = (isNull _patient);
    private _identityChanged = _playerBound && {!(_medic isEqualTo ACE_player)};
    private _medicCondition = (isNull _medic || {!local _medic} || {!(alive _medic)} || {IS_UNCONSCIOUS(_medic)});
    private _vehicleCondition = (objectParent _medic isNotEqualTo objectParent _patient);
    private _enteredVehicle = _notInVehicle && {!isNull objectParent _medic};
    private _distanceCondition = (!isNull _patient) && {(_patient distance2D _medic) > ACEGVAR(medical_gui,maxDistance)};

    private _dialogCondition = false;
    if (_isDialog) then {
        _dialogCondition = isNull (findDisplay _dialogID);
    } else {
        // The source ACE dialog may still report live for a few frames on locally hosted/listen-server clients.
        // During this bounded startup window the continuous maneuver owns the interface: suppress stale reopen state
        // and keep asking the old dialog to close. After the window expires, any new dialog again cancels normally.
        if (diag_tickTime < _dialogStartupUntil && {GVAR(ContinuousAction_Active)}) then {
            ACEGVAR(medical_gui,pendingReopen) = false;
            // Preserve this episode's explicit end behavior. B166 reset this to false every frame, which meant
            // non-dialog hands-on actions could never return to the medical menu even when they opted in.
            GVAR(ContinuousAction_ShouldReopen) = _reopenOnEnd;
            if (dialog) then {closeDialog 0;};
        } else {
            // If the provider explicitly reopened the medical menu, the menu-open handler may already have set
            // Active=false. In that case never close the new display as though it were the stale source progress
            // dialog; cleanup below will retire the hold while leaving this menu intact.
            _dialogCondition = dialog;
        };
    };

    if (_patientCondition || _medicCondition || _identityChanged || _enteredVehicle || !GVAR(ContinuousAction_Active) || _dialogCondition || {(!_notInVehicle && _vehicleCondition) || {(_notInVehicle && _distanceCondition)}}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;

        // Release the shared ownership state before touching CBA handler cleanup. CBA currently returns string key-handler
        // ids, and a cleanup failure must never leave the global continuous-action gate latched (which would make the
        // Narc Box play its SFX but refuse to open any later continuous-action dialog).
        if (_isDialog) then {
            if (GVAR(ContinuousAction_OpenMedicalMenu_ID) == _keyID) then {GVAR(ContinuousAction_OpenMedicalMenu_ID) = -1;};
        } else {
            if (GVAR(ContinuousAction_Cancel_EscapeID) == _keyID) then {GVAR(ContinuousAction_Cancel_EscapeID) = -1;};
        };
        if ((missionNamespace getVariable [QGVAR(ContinuousAction_PFH), -1]) == _idPFH) then {
            GVAR(ContinuousAction_PFH) = -1;
        };
        // The generation check above guarantees this cleanup still owns the global gate.
        GVAR(ContinuousAction_Active) = false;
        if ((_medic getVariable [QGVAR(ContinuousAction_Session), []]) isEqualTo [_patient, _epoch]) then {
            _medic setVariable [QGVAR(ContinuousAction_Session), [], true];
        };

        if (!(_keyID isEqualTo -1) && {!(_keyID isEqualTo "")}) then {[_keyID, "keydown"] call CBA_fnc_removeKeyHandler;};

        [_medic, _patient, _bodyPart, _extraArgs, _notInVehicle] call _onCancel;

        if (_notInVehicle && {!_medicCondition} && {isNull objectParent _medic} && {!_suppressProviderAnim}
            && {GVAR(ContinuousAction_Epoch) == _epoch} && {!GVAR(ContinuousAction_Active)}) then {
            private _rate = if (isNil "ACME_fnc_choreographyRate") then {1.5} else {call ACME_fnc_choreographyRate};
            _medic setAnimSpeedCoef _rate;
            [QACEGVAR(common,setAnimSpeedCoef), [_medic, _rate]] call CBA_fnc_globalEvent;
            _medic setUnitPos "AUTO";
            private _animation = ["AmovPknlMstpSnonWnonDnon", "AmovPpneMstpSnonWnonDnon"] select _isProne;
            [_medic, _animation, 1] call ACEFUNC(common,doAnimation);
            [{
                params ["_medic", "_epoch", "_poseEpoch"];
                if (isNull _medic || {!local _medic}) exitWith {};
                if (GVAR(ContinuousAction_Epoch) != _epoch || {GVAR(ContinuousAction_Active)}) exitWith {};
                if ((_medic getVariable ["ACME_treatmentPoseEpoch", -1]) != _poseEpoch) exitWith {};
                if (!isNil "ACME_fnc_providerStanceOwned" && {[_medic] call ACME_fnc_providerStanceOwned}) exitWith {};
                _medic setAnimSpeedCoef 1;
                [QACEGVAR(common,setAnimSpeedCoef), [_medic, 1]] call CBA_fnc_globalEvent;
            }, [_medic, _epoch, _medic getVariable ["ACME_treatmentPoseEpoch", -1]], 0.85 / _rate] call CBA_fnc_waitAndExecute;
        } else {
            if (!_suppressProviderAnim && {local _medic} && {GVAR(ContinuousAction_Epoch) == _epoch}
                && {!GVAR(ContinuousAction_Active)}) then {
                _medic setAnimSpeedCoef 1;
                [QACEGVAR(common,setAnimSpeedCoef), [_medic, 1]] call CBA_fnc_globalEvent;
            };
        };

        ["ace_treatmentFailed", [_medic, _patient, _bodyPart, "ACM_ContinuousAction", "", "", false]] call CBA_fnc_localEvent;

        if (GVAR(ContinuousAction_ShouldReopen) && {!isNull _patient} && {!_medicCondition} && {!_identityChanged}) then {
            disableSerialization;
            private _medicalMenu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
            private _medicalTarget = missionNamespace getVariable ["ace_medical_gui_target", objNull];
            // Opening the medical menu is itself a valid way to leave a hands-on hold. Do not destroy/recreate an
            // already-live menu just to satisfy the reopen contract.
            if (isNull _medicalMenu || {_medicalTarget isNotEqualTo _patient}) then {
                [QGVAR(openMedicalMenu), _patient] call CBA_fnc_localEvent;
            };
        };
    };

    _args call _perFrame;

    // Publish the liveness heartbeat only after this generation's per-frame body completed successfully. If an
    // action-specific callback throws, the heartbeat now ages out and the B166/B167 stale-gate recovery can clear
    // the orphan instead of considering a broken PFH healthy forever.
    if (GVAR(ContinuousAction_Active)
        && {GVAR(ContinuousAction_Epoch) == _epoch}
        && {CBA_missionTime - (_medic getVariable [QGVAR(ContinuousAction_LastSeen), -100]) >= 2}) then {
        _medic setVariable [QGVAR(ContinuousAction_LastSeen), CBA_missionTime, true];
    };
}, 0, [_medic, _patient, _bodyPart, _extraArgs, _notInVehicle, _isProne, _perFrame, _onCancel, _dialogID, _epoch, _keyID, _isDialog, _dialogStartupUntil, _playerBound, _suppressProviderAnim, _reopenOnEnd]] call CBA_fnc_addPerFrameHandler;

GVAR(ContinuousAction_PFH) = _pfh;
_args call _onStart;
true
