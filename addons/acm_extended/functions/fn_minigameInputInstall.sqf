/* Install on the procedure display, where dialogs receive keyboard focus. */
disableSerialization;
params [["_display", displayNull, [displayNull]]];
if (isNull _display || {!hasInterface} || {_display getVariable ["ACME_InputInstalled", false]}) exitWith {};
_display setVariable ["ACME_InputInstalled", true];
_display setVariable ["ACME_InputHeld", createHashMap];
_display setVariable ["ACME_InputTaps", createHashMap];
_display setVariable ["ACME_InputMods", [false,false,false]];
_display setVariable ["ACME_InputLastAt", diag_tickTime];
_display displayAddEventHandler ["KeyDown", {_this call ACME_fnc_minigameInput;}];
_display displayAddEventHandler ["KeyUp", {(_this + [true]) call ACME_fnc_minigameInput;}];
_display displayAddEventHandler ["MouseButtonDown", {[_this,"down"] call ACME_fnc_minigameInputMouse;}];
_display displayAddEventHandler ["MouseButtonUp", {[_this,"up"] call ACME_fnc_minigameInputMouse;}];
_display displayAddEventHandler ["MouseZChanged", {[_this,"wheel"] call ACME_fnc_minigameInputMouse;}];
_display displayAddEventHandler ["Unload", {
    (_this select 0) setVariable ["ACME_InputHeld", createHashMap];
    (_this select 0) setVariable ["ACME_InputTaps", createHashMap];
}];
