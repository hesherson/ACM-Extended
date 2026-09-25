disableSerialization;
params [["_closing", displayNull]];
// A late unload from an older panel cannot release the current workspace or its input loop.
if (_this isNotEqualTo [] && {_closing isNotEqualTo (uiNamespace getVariable ["ACME_CS_DLG", displayNull])}) exitWith {};
private _entryPFH = uiNamespace getVariable ["ACME_CS_EntryPFH", -1];
private _entryProvider = uiNamespace getVariable ["ACME_CS_EntryProvider", []];
if (_entryPFH >= 0) then {[_entryPFH] call CBA_fnc_removePerFrameHandler;};
uiNamespace setVariable ["ACME_CS_EntryPFH", -1];
{
    if (!(_x isEqualTo -1) && {!(_x isEqualTo "")}) then {[_x, "keydown"] call CBA_fnc_removeKeyHandler;};
} forEach (uiNamespace getVariable ["ACME_CS_EntryKeys", []]);
uiNamespace setVariable ["ACME_CS_EntryKeys", []];
uiNamespace setVariable ["ACME_CS_EntryCancelToken", ""];
uiNamespace setVariable ["ACME_CS_EntryProvider", []];
[false, uiNamespace getVariable ["ACME_CS_Medic", objNull], uiNamespace getVariable ["ACME_CS_Patient", objNull],
    uiNamespace getVariable ["ACME_CS_SessionToken", ""]] call ACME_fnc_chestAccessPreparing;
// Cancel a live Flip immediately. Closing the minigame is an explicit abort, not a request to let the provider
// finish medic4. Remove the flip PFH now, invalidate its token, and hard-cancel only this chest-seal roll owner.
private _flipPFH = uiNamespace getVariable ["ACME_CS_FlipPFH",-1];
if (_flipPFH isEqualType 0 && {_flipPFH >= 0}) then {[_flipPFH] call CBA_fnc_removePerFrameHandler;};
uiNamespace setVariable ["ACME_CS_FlipPFH",-1];
uiNamespace setVariable ["ACME_CS_FlipPendingToken",""];
private _flipMedic = uiNamespace getVariable ["ACME_CS_Medic",objNull];
private _closingPatient = uiNamespace getVariable ["ACME_CS_Patient",objNull];

if (!isNull _flipMedic && {local _flipMedic}) then {
    [_flipMedic,"chestSealFlip"] call ACME_fnc_rollProviderCancel;

    // Whatever chest presentation owns the provider now (workspace, seal-placement medic3, or a still-frozen
    // chestAccess medic4) is a handoff into ONE clean exit. Do not run its ordinary crouch exit first.
    private _pose = _flipMedic getVariable ["ACME_treatmentPoseState",[]];
    private _poseMode = _pose param [1,""];
    private _poseEpoch = _pose param [0,-1];
    private _ownsChestPose = _poseMode in ["chestSealWorkspace","chestSeal","chestAccess"];
    if (_entryPFH >= 0) then {
        private _provider = _flipMedic getVariable ["ACME_chestAccessProvider", []];
        _ownsChestPose = _poseMode == "chestAccess"
            && {!(_entryProvider isEqualTo [])}
            && {(_provider param [0, objNull]) isEqualTo _closingPatient}
            && {(_provider param [1, -2]) == _poseEpoch}
            && {(_entryProvider select 0) == _poseEpoch}
            && {(_entryProvider select 1) == (_provider param [2, ""])};
    };
    if (_poseEpoch >= 0 && {_ownsChestPose}) then {
        [_flipMedic,_poseMode,_poseEpoch,true] call ACME_fnc_treatmentPoseStop;
    };

    _flipMedic setVariable ["ACME_CS_providerHoldEpoch",-1,false];

    // User-requested close theatre: the exact Semi-Fowler Putdown pair, then normal unarmed crouch.
    if (_ownsChestPose
        && {alive _flipMedic}
        && {!(_flipMedic getVariable ["ACE_isUnconscious",false])}
        && {isNull objectParent _flipMedic}
        && {!(_flipMedic getVariable ["ACME_headElev_seqActive",false])}) then {
        [_flipMedic,"lower"] call ACME_fnc_headElevMedicSeq;
    };
};
uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch",-1];
if (!isNull _flipMedic && {local _flipMedic}
    && {(_flipMedic getVariable ["ACME_DP_PauseTreatmentClass",""]) == "chestsealflip"}) then {
    _flipMedic setVariable ["ACME_DP_Paused",false];
    _flipMedic setVariable ["ACME_DP_PauseTreatmentClass",""];
    _flipMedic setVariable ["ACME_DP_TreatmentBusy",false];
    _flipMedic setVariable ["ACME_DP_IdleStart",CBA_missionTime];
};
// this fires first, before anything in this function can run or fail. the order against the keydown probes is the
// whole answer: a close landing at the same instant ACE's cursormenu is created means creating a second child
// display of 46 destroyed the first, and display mode is structurally impossible.

// onunload: persist the final hole state to the patient, so re-opening shows exactly what was left, then drop the
// pfh and clear the runtime state. the ctrlcreate'd dots, holes, seals and cursor-seal die with the dialog.
private _patient = _closingPatient;
if (!isNull _patient) then {[_patient, "ui:chest:" + str clientOwner, false] call ACME_fnc_ecgJostleRequest;};
// NA2: no clinical writes on unload. Pending actions resolve independently of this display.

// Restore through the same owner-local procedure transaction that prepared them. Teardown ALWAYS normalizes
// anterior-up / lying on the back, gives the carrier back, then resumes Semi-Fowler only from that supine base.
private _sessionToken = uiNamespace getVariable ["ACME_CS_SessionToken", ""];
if (!isNull _patient && {_sessionToken != ""}) then {
    [_patient, "chestSealPatientEnd", [_patient, _sessionToken, _flipMedic]] call ACME_fnc_ownerDispatch;
};
uiNamespace setVariable ["ACME_CS_SessionToken", ""];

private _pfh = uiNamespace getVariable ["ACME_CS_PFH", -1];
if (_pfh >= 0) then { [_pfh] call CBA_fnc_removePerFrameHandler; };
uiNamespace setVariable ["ACME_CS_PFH", -1];

// ACE's medical menu may still be open underneath us. we neutralized its per-frame handler on open, so it could
// not yank this dialog shut mid-procedure. but if we leave it dead, the buttons of the medical menu stop working
// and it stops updating once we close, so it is restored here and the menu is live again. if ACE's menu already
// closed, gvar is -1 and ACE re-adds its own pfh the next time it opens, so we only restore an open menu.
call ACM_GUI_fnc_resumeMedicalMenuPFH;
uiNamespace setVariable ["ACME_CS_Dragging", false];
uiNamespace setVariable ["ACME_CS_DragPt", []];
uiNamespace setVariable ["ACME_CS_DragLast", -1];
uiNamespace setVariable ["ACME_CS_FlipLockedUntil", 0];
uiNamespace setVariable ["ACME_CS_ApplyGestureUntil", 0];
uiNamespace setVariable ["ACME_CS_VirtualFlip", false];
uiNamespace setVariable ["ACME_CS_FingerGlow", []];
uiNamespace setVariable ["ACME_CS_Held", false];
uiNamespace setVariable ["ACME_CS_SpearHeld", false];
uiNamespace setVariable ["ACME_CS_Holes", []];
uiNamespace setVariable ["ACME_CS_Dots", []];
uiNamespace setVariable ["ACME_CS_WastedCtrls", []];
uiNamespace setVariable ["ACME_CS_CursorSeal", controlNull];
uiNamespace setVariable ["ACME_CS_CursorSpear", controlNull];
uiNamespace setVariable ["ACME_CS_NCDPlacedCtrls", []];
uiNamespace setVariable ["ACME_CS_DLG", displayNull];

// the live-presence teardown. the ghost controls belong to the display that is closing, so drop our references or
// the next open would inherit dead control handles. it also clears our own presence entry and forces the next send
// to fire immediately, so we do not linger as a frozen finger on the screens of the other medics.
{
    _x params ["_c", ""];
    if (!isNull _c) then { ctrlDelete _c; };
} forEach (uiNamespace getVariable ["ACME_CS_GhostPool", []]);
uiNamespace setVariable ["ACME_CS_GhostPool", []];
uiNamespace setVariable ["ACME_CS_presenceLastT", -1];
uiNamespace setVariable ["ACME_CS_presenceLastState", ["", ""]];
private _viewer = uiNamespace getVariable ["ACME_CS_presenceViewer", objNull];
if (isNull _viewer) then {_viewer = _flipMedic;};
if (!isNull _patient) then {
    private _targets = (uiNamespace getVariable ["ACME_CS_presenceTargets", []]) - [_viewer];
    ["ACME_CS_session", [_patient, _viewer, "leave", _sessionToken]] call CBA_fnc_serverEvent;
    if !(_targets isEqualTo []) then {
        ["ACME_CS_presenceLeave", [netId _patient, netId _viewer], _targets] call CBA_fnc_targetEvent;
    };
};
if (!isNull _viewer) then { _viewer setVariable ["ACME_CS_viewing", objNull, true]; };
uiNamespace setVariable ["ACME_CS_presenceViewer", objNull];
ACME_CS_presence = createHashMap;

// the darkness shade belongs to the display that is closing. drop the handle, or the next open inherits a dead
// control and never draws the shade again, a bug that would only show up at night, days later.
uiNamespace setVariable ["ACME_CS_Shade", controlNull];

// drop the captured resting layout. if it survived the close, the next open would shake from stale positions.
uiNamespace setVariable ["ACME_CS_ShakeBase", []];
uiNamespace setVariable ["ACME_CS_ShakeBase_off", [0, 0]];  // a stale offset would corrupt the rest positions of the next open.

// the darkness panels die with the dialog, so clear the handles and the z-order count, and the next open rebuilds
// cleanly.
uiNamespace setVariable ["ACME_CS_Shade", []];
uiNamespace setVariable ["ACME_CS_Shade_n", -1];

// the flashlights self-action is gated on this. left set, ACE would offer it forever.
uiNamespace setVariable ["ACME_minigame_open", false];

// drop back into the medical menu rather than exiting to the game. it is a no-op during the flashlight close and
// reopen.
if (!isNull _flipMedic && {alive _flipMedic} && {_flipMedic isEqualTo ACE_player}
    && {!(_flipMedic getVariable ["ACE_isUnconscious", false])}) then {
    [uiNamespace getVariable ["ACME_CS_Patient", objNull], "airway"] call ACME_fnc_reopenMedicalMenu;
};

// a burp in progress dies with the panel. the state is uiNamespace, so leaving it set would make the next panel
// open with a seal already drawn half lifted and a timestamp from the last casualty.
uiNamespace setVariable ["ACME_CS_BurpIdx", -1];
uiNamespace setVariable ["ACME_CS_BurpFired", false];
uiNamespace setVariable ["ACME_CS_BurpFrame", 0];
uiNamespace setVariable ["ACME_CS_BurpDir", 0];
uiNamespace setVariable ["ACME_CS_BurpSide", "right"];

uiNamespace setVariable ["ACME_CS_netSnapshot", []];
uiNamespace setVariable ["ACME_CS_presenceTargets", []];
uiNamespace setVariable ["ACME_CS_presencePacket", []];
