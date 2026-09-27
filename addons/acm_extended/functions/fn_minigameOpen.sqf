// open a minigame, as either a dialog or a display.
// call it as ["ACME_Thoracostomy_Dialog"] call ACME_fnc_minigameOpen.
// on why there are two paths, and why the new one is off by default.
// the goal is ACE's real interaction menu opening over a minigame, so you can pick a light source without leaving
// the patient. that is impossible today for a reason that is in ACE's source rather than ours, because the
// keydown of ace_interact_menu does this before it opens anything:
// while {dialog} do { closedialog 0; };
// it closes every open dialog, in a loop, by design. our minigames are createdialog dialogs, so pressing ctrl+win
// in one does not open a menu over it. it closes it.
// the fix, in principle, is to stop being a dialog. a display created as a child of display 46 is not a dialog, so
// dialog returns false, ACE's loop never fires, and ACE's genuine menu opens right over the panel. that is
// exactly how the map survives ctrl+win, because the map is display 12 rather than a dialog.
// so why is it not simply on? because a dialog hands you a working mouse for free and a display does not, and that
// cannot be verified without running the game.
// the evidence that worries me is in ACE itself. its cursormenu display keeps its own cursor position:
// _cursorscreenpos = [worldtoscreen _cursorpos2, gvar(cursorpos)] select (cursormenuopened)
// and drives it from MouseMoving handlers. ACE is simulating a cursor, which strongly suggests a child display of
// 46 does not simply behave like a dialog for input. our minigames live or die on getMousePosition and on control
// mouse events, and if those do not survive, three minigames become unusable at once.
// so this is a spike rather than a conversion: one minigame, behind a switch, defaulting to the path that is known
// to work. turn it on, open a thoracostomy, and answer the four questions in the patch notes. if the mouse holds
// up, the other two follow in one build and a great deal of code gets deleted. if it does not, flip the switch
// back and nothing was lost.
params ["_dialogClass"];
if (!hasInterface) exitWith {};

// record how this panel is being opened rather than what the setting says. they are not the same thing, because
// display mode currently converts only the thoracostomy, so with the switch on, the iv and chest seal are still
// dialogs. code that reads the setting to decide how to treat a panel will get the other two wrong, which is
// exactly what happened: fn_installlightkey started forwarding ctrl+win to ACE inside the chest seal, and ACE
// closed it.
if (!(missionNamespace getVariable ["ACME_minigame_displayMode", false])) exitWith {
    uiNamespace setVariable ["ACME_minigame_openedAsDisplay", false];
    createDialog _dialogClass;  // the known-good path.
};

uiNamespace setVariable ["ACME_minigame_openedAsDisplay", true];

// display mode. it is a child of the mission display, so dialog is false and ACE leaves it alone.
private _parent = findDisplay 46;
if (isNull _parent) exitWith {
    // This is a dialog fallback, so do not leave the display-mode flag armed. installLightKey and close/reopen
    // behavior must follow the object that actually exists, not the requested experimental mode.
    uiNamespace setVariable ["ACME_minigame_openedAsDisplay", false];
    createDialog _dialogClass;
};

// close every open dialog first. this is the whole ballgame, and the first spike missed it.
// a createdialog panel replaces whatever dialog was open, because arma allows one dialog at a time. that is how
// the minigame used to make the ACE medical menu go away: not politely, simply by existing.
// a display does not do that. so in display mode the medical menu stayed open underneath us, and everything went
// wrong at once, all from that one fact.
// ACE's keydown runs while {dialog} do {closedialog 0}. dialog was still true, because the medical menu is a
// dialog, so ctrl+win closed the medical menu and never touched our panel, and never opened its own menu over it
// either.
// esc went to the focused dialog, which was the medical menu, so the KeyDown of our display never even fired.
// and the medical menu sat there visible in the background the whole time.
// one cause, three symptoms. close the dialogs, and the display becomes the only thing holding input.
while {dialog} do { closeDialog 0; };

// a frame, so the closing dialog is fully gone before the display takes its place. creating a display in the same
// frame that a dialog is tearing down is asking for the focus to land in the wrong place.
[{
    params ["_cls", "_p"];
    if (isNull _p) exitWith { createDialog _cls; };
    _p createDisplay _cls;
}, [_dialogClass, _parent]] call CBA_fnc_execNextFrame;
