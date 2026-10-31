
disableSerialization;
params [["_closing", displayNull], ["_pending", [], [[]]], ["_allowReturn", true, [true]]];
private _restore = {
    params ["_return", "_session", "_medic"];
    if (count _return == 3 && {count _session == 3} && {[_session] call ACME_fnc_ivUiValid}) then {
        (_return + [_session, _medic]) call ACME_fnc_reopenMedicalMenu;
    };
};
// A cancelled next-frame launch never reached init, so it has no display/PFH,
// controls or unfinished work to save. Release only its captured lease once.
if (_pending isNotEqualTo []) exitWith {
    if (count _pending != 8 || {_pending isNotEqualTo (uiNamespace getVariable ["ACME_IV_PendingLaunch", []])}) exitWith {};
    uiNamespace setVariable ["ACME_IV_PendingLaunch", []];
    _pending params ["_session", "_medic", "_return", "_medicalEpoch", "_lastOpened", "_displays", "_returnSerial", "_ecgKey"];
    private _patient = _session param [0, objNull];
    if (!isNull _patient) then {[_patient, _ecgKey, false] call ACME_fnc_ecgJostleRequest;};
    // Creation failure can also run this path. Recheck the captured UI before
    // enqueueing a return, rather than adopting a newer display as its baseline.
    if (_allowReturn
        && {(uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", 0]) == _medicalEpoch}
        && {(missionNamespace getVariable ["ace_medical_gui_lastOpenedOn", -1]) == _lastOpened}
        && {(uiNamespace getVariable ["ACME_medicalReturnSerial", 0]) == _returnSerial}
        && {(allDisplays findIf {!(_x in _displays)}) < 0}
        && {!(uiNamespace getVariable ["ACME_minigame_open", false])}) then {
        [_return, _session, _medic] call _restore;
    };
};
private _active = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (!isNull _closing && {_closing isNotEqualTo _active}) exitWith {
    // An obsolete display owns no global controls or provider/menu context,
    // but its captured lease still needs an idempotent release of its own key.
    if (_closing getVariable ["ACME_IV_Closed", false]) exitWith {};
    _closing setVariable ["ACME_IV_Closed", true];
    private _session = _closing getVariable ["ACME_IV_Session", []];
    private _patient = _session param [0, objNull];
    private _key = _closing getVariable ["ACME_IV_ECGKey", ""];
    if (!isNull _patient && {_key != ""}) then {[_patient, _key, false] call ACME_fnc_ecgJostleRequest;};
};
if (isNull _active) exitWith {};
if (_active getVariable ["ACME_IV_Closed", false]) exitWith {};
_active setVariable ["ACME_IV_Closed", true];
private _session = +(_active getVariable ["ACME_IV_Session", []]);
private _return = +(_active getVariable ["ACME_IV_ReturnMenu", []]);
private _medic = _active getVariable ["ACME_IV_Medic", objNull];
private _ecgPat = _session param [0, objNull];
private _ecgKey = _active getVariable ["ACME_IV_ECGKey", "ui:iv:" + str clientOwner];
if (!isNull _ecgPat) then {[_ecgPat, _ecgKey, false] call ACME_fnc_ecgJostleRequest;};
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

// The same return applies after complete placement, partial work, or Escape.
// Flashlight rebuilding preserves the captured page without opening it underneath.
[_return, _session, _medic] call _restore;
