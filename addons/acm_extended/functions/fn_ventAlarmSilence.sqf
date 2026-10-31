// Input cannot outlive its captured patient/device panel.
if !([] call ACME_fnc_ventPanelContext) exitWith {};
// silence, and close the window.
// silencing acknowledges the alarm you have seen. it does not deafen you to the next one: fn_ventalarmtick clears the
// silence the moment a new alarm appears, so nobody can mute the machine and walk away from the problem that kills
// the patient. that behavior already existed, and this simply gives it the own button of the device.
if (!hasInterface) exitWith {};

private _tgt = uiNamespace getVariable ["ACME_vent_target", objNull];
if (!isNull _tgt) then {
    // the silence lasts one minute. after that, if the underlying condition has not been fixed, the alarm re-asserts
    // itself: the _showRed test of the tick is alarms active and missiontime past the silence deadline, so the box goes
    // red again on its own the instant the minute is up.
    // silencing buys you sixty seconds to act rather than a way to make the problem disappear. a new alarm still
    // un-silences immediately, in fn_ventalarmtick.
    private _dur = missionNamespace getVariable ["ACME_vent_alarmSilenceSeconds", 60];
    _tgt setVariable ["ACME_vent_alarmSilencedUntil", serverTime + _dur, true];
};

playSound "ACME_VentClick";

{ if (!isNull _x) then { ctrlDelete _x; }; } forEach (uiNamespace getVariable ["ACME_vent_alarmWin", []]);
uiNamespace setVariable ["ACME_vent_alarmWin", []];
uiNamespace setVariable ["ACME_vent_alarmPage", 0];
uiNamespace setVariable ["ACME_vent_alarmWinOpen", false];  // dial goes back to the live screen behind it
// drop the flash target with the window. the controls above are already deleted, and arma recycles handles, so a
// retained handle is not merely useless, it is a handle to somebody else's control.
uiNamespace setVariable ["ACME_vent_alarmFillCtrl", controlNull];
uiNamespace setVariable ["ACME_vent_alarmFlashHz", 0];
