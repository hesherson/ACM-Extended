// this runs each frame while the ACE world interaction menu is open. the pfh is started and stopped by the menu
// hooks in postinit.
// if the currently-selected interaction target is a blood fridge, ping its owner, throttled, so the fridge opens
// and stays open. when the player looks away the selected target changes, the pings stop, and the server tick
// closes it after the timeout.
private _tgt = missionNamespace getVariable ["ace_interact_menu_selectedTarget", objNull];
if (isNull _tgt) exitWith {};
if !(_tgt getVariable ["ACME_bloodFridge", false]) exitWith {};

private _anchor = _tgt getVariable ["ACME_bf_anchor", _tgt];
if (isNull _anchor) exitWith {};

private _last = ACE_player getVariable ["ACME_bf_lastPingT", -1];
if ((diag_tickTime - _last) < 0.4) exitWith {};

ACE_player setVariable ["ACME_bf_lastPingT", diag_tickTime];
ACE_player setVariable ["ACME_bf_lastFridge", _anchor];
["ACME_bfViewPing", [_anchor, ACE_player]] call CBA_fnc_serverEvent;
