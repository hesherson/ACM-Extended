// send the live presence of this medic in the chest-seal minigame: their actual fingertips, or the tool in
// hand.
// we send the real computed finger points rather than a bare cursor: four points for the four-finger rake, with its
// true spread and the flattening and trailing it does as you drag it down the chest, or one point for the
// one-finger palpate. reconstructing that from a cursor on the far end would only ever approximate it.
// the points are normalized to the body image, 0 to 1 across the body rect, and never screen pixels, because medics
// will be on different resolutions and aspects, 32:9 against 16:9, and the receiver maps them back onto its own
// body rect.
// it is throttled, and a change of tool or side sends immediately, so a seal appearing in someone's hand is never
// held up behind the timer.
// call it as [_patient, _side, _tool, _pts] call ACME_fnc_chestSealPresenceSend.
// _tool is "finger", which draws a dot at each point, or "seal" or "spear", which draw the sprite at the single
// point.
params ["_patient", "_side", "_tool", "_pts"];
if (isNull _patient || {!hasInterface}) exitWith {};

private _now = diag_tickTime;
private _rate = missionNamespace getVariable ["ACME_CS_presenceRate", 0.07];  // about 14 hz.
private _lastT = uiNamespace getVariable ["ACME_CS_presenceLastT", -1];
private _lastState = uiNamespace getVariable ["ACME_CS_presenceLastState", ["", ""]];

private _burp = [];
private _holes = uiNamespace getVariable ["ACME_CS_Holes", []];
private _idx = uiNamespace getVariable ["ACME_CS_BurpIdx", -1];
if (_idx >= 0 && {_idx < count _holes}) then {
    _burp = [[_holes select _idx] call ACME_fnc_chestSealKey,
        uiNamespace getVariable ["ACME_CS_BurpFrame", 0], uiNamespace getVariable ["ACME_CS_BurpSide", "right"]];
};
private _stateNow = [netId _patient, _tool, _side, _burp, count _pts > 0];
private _forced = !(_stateNow isEqualTo _lastState);  // a tool picked up or put down, or flipped front to back.
if (!_forced && {_lastT >= 0} && {(_now - _lastT) < _rate}) exitWith {};

uiNamespace setVariable ["ACME_CS_presenceLastT", _now];
uiNamespace setVariable ["ACME_CS_presenceLastState", _stateNow];


// Roster changes occur on join/leave, not on every cursor sample. No distance cutoff.
private _viewer = uiNamespace getVariable ["ACME_CS_presenceViewer", player];
private _targets = (uiNamespace getVariable ["ACME_CS_presenceTargets", []]) - [_viewer];
private _packet = [netId _patient, netId _viewer, name _viewer, _side, _tool, _pts, _burp];
uiNamespace setVariable ["ACME_CS_presencePacket", _packet];
if !(_targets isEqualTo []) then {
    ["ACME_CS_presence", _packet, _targets] call CBA_fnc_targetEvent;
};
