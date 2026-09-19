disableSerialization;
params [["_closing", displayNull]];
// A late unload from an older panel cannot release the current workspace or its input loop.
if (_this isNotEqualTo [] && {_closing isNotEqualTo (uiNamespace getVariable ["ACME_CS_DLG", displayNull])}) exitWith {};
// Cancel a pending provider-entry wait before any patient-session restoration.
uiNamespace setVariable ["ACME_CS_FlipPendingToken",""];
private _flipMedic = uiNamespace getVariable ["ACME_CS_Medic",objNull];
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
private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
if (!isNull _patient) then {[_patient, "ui:chest:" + str clientOwner, false] call ACME_fnc_ecgJostleRequest;};
// NA2: no clinical writes on unload. Pending actions resolve independently of this display.

// Restore the casualty through the same owner-local procedure transaction that prepared them. It returns them to
// the side they had before the minigame, gives the carrier back, then resumes an existing Semi-Fowler placement.
private _sessionToken = uiNamespace getVariable ["ACME_CS_SessionToken", ""];
if (!isNull _patient && {_sessionToken != ""}) then {
    [_patient, "chestSealPatientEnd", [_patient, _sessionToken]] call ACME_fnc_ownerDispatch;
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
