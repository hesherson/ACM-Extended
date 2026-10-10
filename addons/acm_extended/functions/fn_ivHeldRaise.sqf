// keep the instrument in the hand of the medic above everything else on the IV screen.
// call it as [] call ACME_fnc_ivHeldRaise, from the top of fn_ivMinigameTick and before anything reads the held
// control.
//
// WHY THIS EXISTS.
// ctrlCreate appends a new control ABOVE every control that already exists. it cannot insert one underneath.
// the held cursor is created once, in fn_ivMinigameInit, and the antiseptic dabs, the puncture marks, the
// bruises and the catheter hub are all created later, while the screen is open. every one of them therefore
// landed on top of the instrument the medic was holding.
// the alcohol pad showed this worst, because a scrub creates a new dab every few millimetres of travel. the pad
// did not vanish. it went under a growing pile of red dabs, and the red drew over the swab that was supposed to
// be laying it down.
// this is the same problem, and the same cure, as fn_ventVeilRaise on the ventilator panel.
//
// HOW IT WORKS.
// the test is whether the held control is the last control in the display. that is cheap, and it is self
// healing: it does not need to know who created what, or in what order, only whether anything has appeared since.
// when something has, the control is re-created at the top and the old one is deleted.
// the tick writes the texture, the position, the size and the angle on the frame after this runs, so a fresh
// control carries no state that needs copying.

disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _dlg) exitWith {};

private _held = uiNamespace getVariable ["ACME_IV_HeldCursorCtrl", controlNull];
if (isNull _held) exitWith {};

private _all = (allControls _dlg) select {!(_x getVariable ["ACME_NV_OverlayControl", false])};
private _n = count _all;
if (_n == 0) exitWith {};

// The square catheter canvas uses a plain-picture class. Other tools keep their
// established keep-aspect cursor. Styles cannot be changed at runtime in Arma.
private _cathCanvas = (uiNamespace getVariable ["ACME_IV_Held", "none"]) in ["needle", "line", "extension", "flush", "dressing", "lock"];
// Already on top with the right class: this is the normal steady-state path.
if (((_all select (_n - 1)) isEqualTo _held) && {(_held getVariable ["ACME_IV_CathCanvas", false]) isEqualTo _cathCanvas}) exitWith {};

// something was created above it. move it back to the top.
private _shown = ctrlShown _held;
private _new = _dlg ctrlCreate [if (_cathCanvas) then {"ACME_IV_CathCursor"} else {"ACME_IV_HeldCursor"}, -1];
if (isNull _new) exitWith {};
_new setVariable ["ACME_IV_CathCanvas", _cathCanvas];
// carry the visible state across, so a raise on a frame with nothing in the hand does not flash the sprite on.
// the position and the texture are written by the tick immediately after this, so they are not copied.
_new ctrlSetPosition (ctrlPosition _held);
_new ctrlSetText (ctrlText _held);
_new ctrlSetTextColor (ctrlTextColor _held);
// Re-created controls retain the source identity needed for NV off/close restoration.
{private _v = _held getVariable _x; if (!isNil "_v") then {_new setVariable [_x,_v];};} forEach ["ACME_NV_BaseTexture","ACME_NV_Variant","ACME_NV_BaseColor","ACME_NV_LastColor"];
_new ctrlCommit 0;
_new ctrlShow _shown;
ctrlDelete _held;
uiNamespace setVariable ["ACME_IV_HeldCursorCtrl", _new];
// the held control carries the mouse handlers. fn_ivMinigameInit hooks them when it creates the control, so a
// re-created control has to be hooked again or the screen stops taking clicks the moment the first dab lands.
[_new] call ACME_fnc_ivMinigameHookCtrl;
