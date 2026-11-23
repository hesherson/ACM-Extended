// push one entry onto the megacode instructor activity log, shown on the LOG tab of the panel. it is newest first
// and capped at 40 lines.
// each entry is stamped with the mission time, in mm:ss, so the order of applied changes reads like a code timeline.
// it is safe to call from anywhere, and no-op text is ignored. if the LOG page is currently open, it refreshes live
// so the instructor sees the entry land.
// _this is _msg, a string, or [_msg, _colorhex].
params [["_arg", "", ["", []]]];

private _msg = ""; private _hex = "#cfe8ff";
if (_arg isEqualType []) then {
    _arg params [["_m", ""], ["_h", "#cfe8ff"]];
    _msg = _m; _hex = _h;
} else {
    _msg = _arg;
};
if (_msg isEqualTo "") exitWith {};

// an mm:ss mission-time stamp.
private _sec = floor CBA_missionTime;  // the synced mission clock, the same on every machine and for late joiners.
private _ss  = _sec % 60;
private _stamp = format ["%1:%2", floor (_sec / 60), (if (_ss < 10) then {format ["0%1", _ss]} else {str _ss})];

private _log = uiNamespace getVariable ["ACME_MC_log", []];
_log insert [0, [[format ["[%1]  %2", _stamp, _msg], _hex]]];
if (count _log > 40) then { _log deleteRange [40, (count _log) - 40]; };
uiNamespace setVariable ["ACME_MC_log", _log];

// a live refresh if the LOG page is the active page.
if ((uiNamespace getVariable ["ACME_MC_page", ""]) isEqualTo "log"
    && {!isNull (uiNamespace getVariable ["ACME_Megacode_DLG", displayNull])}) then {
    [87300, "log"] call ACME_fnc_megacodeMenu;
};
