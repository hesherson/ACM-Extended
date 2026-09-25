// Local service access ends with this panel. The patient device continues its normal lifecycle.
disableSerialization;
params [["_closing", displayNull]];
private _serviceParent = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (_this isNotEqualTo [] && {_closing isNotEqualTo _serviceParent}) exitWith {};
uiNamespace setVariable ["ACME_vent_openSerial", 1 + (uiNamespace getVariable ["ACME_vent_openSerial", 0])];
uiNamespace setVariable ["ACME_vent_openPending", false];
// A submitted exchange is settled only by its ACK; an unfinished hatch animation is safe to cancel.
private _batterySupply = uiNamespace getVariable ["ACME_vent_batterySupply", []];
uiNamespace setVariable ["ACME_vent_batterySupply", []];
uiNamespace setVariable ["ACME_vent_swapUntil", -1];
if !(_batterySupply isEqualTo []) then {[_batterySupply] call ACME_fnc_treatmentSupplyRefund;};
if (!isNull _serviceParent) then {
    private _prompt = _serviceParent getVariable ["ACME_vent_techPrompt", displayNull];
    if (!isNull _prompt) then { _prompt closeDisplay 2; };
    _serviceParent setVariable ["ACME_vent_techUnlocked", false];
    _serviceParent setVariable ["ACME_vent_techAuthCode", ""];
    _serviceParent setVariable ["ACME_vent_techAuthTarget", objNull];
    _serviceParent setVariable ["ACME_vent_itemConfirmed", []];
};
// the dialog unload: stop the tick and destroy any dynamic graph bars. the settings persist on the player.
{ ctrlDelete _x } forEach (uiNamespace getVariable ["ACME_vent_graphBars", []]);
uiNamespace setVariable ["ACME_vent_graphBars", []];
private _pfh = uiNamespace getVariable ["ACME_vent_pfh", -1];
if (_pfh >= 0) then { [_pfh] call CBA_fnc_removePerFrameHandler; };
uiNamespace setVariable ["ACME_vent_pfh", -1];

// the value fields are created into the dialog, so they die with it. clear the handles, or the next open would find
// an array of dead controls and skip building fresh ones, and the ALERTS values would simply not appear.
{ if (!isNull _x) then { ctrlDelete _x; }; } forEach (uiNamespace getVariable ["ACME_vent_valFields", []]);
uiNamespace setVariable ["ACME_vent_valFields", []];
uiNamespace setVariable ["ACME_vent_pendingValues", nil];
uiNamespace setVariable ["ACME_vent_graphSweep", controlNull];
uiNamespace setVariable ["ACME_vent_graphVtRow", controlNull];
{ if (!isNull _x) then { ctrlDelete _x; }; } forEach (uiNamespace getVariable ["ACME_vent_alarmWin", []]);
uiNamespace setVariable ["ACME_vent_alarmWin", []];
uiNamespace setVariable ["ACME_vent_alarmWinOpen", false];
uiNamespace setVariable ["ACME_vent_alarmPage", 0];
uiNamespace setVariable ["ACME_vent_battIcoCur", ""];

// a hold cannot survive the panel that created it. without this, an alt-tab mid-hold would leave the stamp in
// uinamespace, and the next time the panel opened the tick would find a four-second-old hold and power the vent off
// instantly, on a patient nobody had touched.
uiNamespace setVariable ["ACME_vent_mmbDown", -1];
uiNamespace setVariable ["ACME_vent_mmbFired", false];
[] call ACME_fnc_ventHoldClear;

// the shutdown sequence must not outlive the panel that ran it, or the next open would find a live shutdown clock,
// replay POWERING OFF, and power down a ventilator nobody had touched.
uiNamespace setVariable ["ACME_vent_shutT0", -1];
private _stC = uiNamespace getVariable ["ACME_vent_shutTitle", controlNull];
if (!isNull _stC) then { ctrlDelete _stC; };
uiNamespace setVariable ["ACME_vent_shutTitle", controlNull];

uiNamespace setVariable ["ACME_vent_dlg", displayNull];
uiNamespace setVariable ["ACME_vent_target", objNull];
