
disableSerialization;
params [["_closing", displayNull]];
private _active = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (!isNull _closing && {_closing isNotEqualTo _active}) exitWith {};
if (isNull _active) exitWith {};
private _session = +(_active getVariable ["ACME_IV_Session", []]);
private _return = +(_active getVariable ["ACME_IV_ReturnMenu", []]);
private _ecgPat = uiNamespace getVariable ["ACME_IV_Patient", objNull];
if (!isNull _ecgPat) then {[_ecgPat, "ui:iv:" + str clientOwner, false] call ACME_fnc_ecgJostleRequest;};
// this fires first, before anything in this function can run or fail. the order against the keydown probes is the
// whole answer: a close landing at the same instant ACE's cursormenu is created means creating a second child
// display of 46 destroyed the first, and display mode is structurally impossible.

// the iv mini-game teardown. stop the tick and drop the ctrlcreate'd sprites, the dot, catheter, stain and mark
// sprites, so a re-open rebuilds cleanly. the persistent marks live on the patient, so they survive and re-render
// on re-open.
// save the unfinished work before the teardown clears it. a band still on the arm or a catheter still in it
// comes back on the next open.
[] call ACME_fnc_ivMinigameSaveState;
[] call ACME_fnc_ivMinigameResetView;
["clear"] call ACME_fnc_ivMinigamePrepView;

private _pfh = uiNamespace getVariable ["ACME_IV_PFH", -1];
if (_pfh isEqualType 0 && {_pfh >= 0}) then { [_pfh] call CBA_fnc_removePerFrameHandler; };
uiNamespace setVariable ["ACME_IV_PFH", -1];

{ if (!isNull _x) then { ctrlDelete _x; }; } forEach (uiNamespace getVariable ["ACME_IV_MarkCtrls", []]);
uiNamespace setVariable ["ACME_IV_MarkCtrls", []];
uiNamespace setVariable ["ACME_IV_BruiseFades", []];

{
    private _c = uiNamespace getVariable [_x, controlNull];
    if (!isNull _c) then { ctrlDelete _c; };
    uiNamespace setVariable [_x, controlNull];
} forEach ["ACME_IV_DotCtrl", "ACME_IV_PipCtrl", "ACME_IV_CathCtrl", "ACME_IV_CathGhost", "ACME_IV_CleanCtrl", "ACME_IV_HeldCursorCtrl"];

// the antiseptic scrub trail is a LIST of controls rather than a single one, so it does not fit the loop above.
{ private _pc = _x param [0, controlNull]; if (!isNull _pc) then { ctrlDelete _pc; }; } forEach (uiNamespace getVariable ["ACME_IV_PrepCtrls", []]);
uiNamespace setVariable ["ACME_IV_PrepCtrls", []];
uiNamespace setVariable ["ACME_IV_PrepPts", []];
uiNamespace setVariable ["ACME_IV_PrepTotal", 0];
uiNamespace setVariable ["ACME_IV_PrepSum", [0, 0]];
uiNamespace setVariable ["ACME_IV_PrepLast", []];
uiNamespace setVariable ["ACME_IV_PrepCells", createHashMap];
// the prep bruise is one control that grows with the wiped area. it is deleted with the dabs, because it belongs
// to the scrub that made it.
private _pb = uiNamespace getVariable ["ACME_IV_PrepBruise", controlNull];
if (!isNull _pb) then { ctrlDelete _pb; };
uiNamespace setVariable ["ACME_IV_PrepBruise", controlNull];

// drop the cba middle button handler, or it keeps firing for the rest of the mission.
private _mbId = uiNamespace getVariable ["ACME_IV_MBDisplayHandler", -1];
if (_mbId isEqualType 0 && {_mbId >= 0}) then {
    ["MouseButtonDown", _mbId] call CBA_fnc_removeDisplayHandler;
};
uiNamespace setVariable ["ACME_IV_MBDisplayHandler", -1];
private _mbUpId = uiNamespace getVariable ["ACME_IV_MBUpDisplayHandler", -1];
if (_mbUpId isEqualType 0 && {_mbUpId >= 0}) then {
    ["MouseButtonUp", _mbUpId] call CBA_fnc_removeDisplayHandler;
};
uiNamespace setVariable ["ACME_IV_MBUpDisplayHandler", -1];
uiNamespace setVariable ["ACME_IV_MBHandler", {}];
uiNamespace setVariable ["ACME_IV_MBUpHandler", {}];
uiNamespace setVariable ["ACME_IV_ScrollHandler", {}];

uiNamespace setVariable ["ACME_IV_DLG", displayNull];
uiNamespace setVariable ["ACME_IV_Held", "none"];
uiNamespace setVariable ["ACME_IV_BandOn", false];
uiNamespace setVariable ["ACME_IV_InsSite", ""];
uiNamespace setVariable ["ACME_IV_Stage", "ready"];
uiNamespace setVariable ["ACME_IV_Dragging", false];
uiNamespace setVariable ["ACME_IV_PullIdx", -1];  // any pull in progress is abandoned here.

// the darkness shade belongs to the display that is closing. drop the handle, or the next open inherits a dead
// control and never draws the shade again, a bug that would only show up at night, days later.
uiNamespace setVariable ["ACME_IV_Shade", controlNull];

// drop the captured resting layout. if it survived the close, the next open would shake from stale positions.
uiNamespace setVariable ["ACME_IV_ShakeBase", []];
uiNamespace setVariable ["ACME_IV_ShakeBase_off", [0, 0]];  // a stale offset would corrupt the rest positions of the next open.

// the darkness panels die with the dialog, so clear the handles and the z-order count and the next open rebuilds
// cleanly.
uiNamespace setVariable ["ACME_IV_Shade", []];
uiNamespace setVariable ["ACME_IV_Shade_n", -1];

// the flashlights self-action is gated on this. left set, ACE would offer it forever.
uiNamespace setVariable ["ACME_minigame_open", false];

// Restore ACE's menu PFH if the underlying medical menu survived the procedure. If it did not, openMenu will
// install its normal PFH when the captured page is restored below.
call ACM_GUI_fnc_resumeMedicalMenuPFH;

// The same return applies after complete placement, partial work, or Escape.
// Flashlight rebuilding preserves the captured page without opening it underneath.
if (count _return == 3 && {count _session == 3} && {[_session] call ACME_fnc_ivUiValid}) then {
    (_return + [_session]) call ACME_fnc_reopenMedicalMenu;
};
