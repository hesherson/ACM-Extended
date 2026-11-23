#include "\x\acm\addons\main\ui_theme.hpp"
/*
 * Megacode Kelly instructor panel onLoad.
 *
 * The whole visible panel is built here at runtime (the dialog class is empty), in the ACM interface style of the
 * transfusion menu (B363): neutral dark surfaces, off-white ink, RobotoCondensed, muted section labels.
 *   title bar     MEGACODE KELLY, and a live status line (rhythm, scenario) on the right
 *   monitor       four sweep lanes (ECG II, pleth, ABP, CO2) and their numbers beside them
 *   tab bar       the pages on the left, RESET and CLOSE apart on the right
 *   page          the controls of the chosen page (ACME_fnc_megacodeMenu)
 * Sizes: the panel fits inside the aspect-safe canvas (ACME_fnc_uiCanvas) in both width and height; on a narrow
 * screen it gets less wide, not smaller. Every font size is a share of the panel height, so text keeps one size
 * against the controls it sits in at 4:3, 16:10, 16:9 and ultrawide.
 * The monitor draws the ACM LifePak's own 176-sample windows (two consecutive windows, ~10.5 s, 350 segments).
 */
params [["_display", displayNull, [displayNull]]];
if (isNull _display) exitWith {};
uiNamespace setVariable ["ACME_Megacode_DLG", _display];

private _dummy = uiNamespace getVariable ["ACME_MC_target", objNull];
if (isNull _dummy || {!(_dummy getVariable ["ACME_isMegacode", false])}) exitWith {
    diag_log "[ACME][Megacode] Panel load aborted: target is null or not a Megacode manikin";
    [{closeDialog 0;}, []] call CBA_fnc_execNextFrame;
};

// Deterministic defaults for a newly spawned or legacy manikin.
{
    _x params ["_key", "_value"];
    if (isNil {_dummy getVariable _key}) then {_dummy setVariable [_key, _value, true];};
} forEach [
    ["ACME_MC_HR",78], ["ACME_MC_HRTgt",78],
    ["ACME_MC_SpO2",98], ["ACME_MC_SpO2Tgt",98],
    ["ACME_MC_SBP",122], ["ACME_MC_SBPTgt",122],
    ["ACME_MC_DBP",78], ["ACME_MC_DBPTgt",78],
    ["ACME_MC_RR",14], ["ACME_MC_RRTgt",14],
    ["ACME_MC_EtCO2",38], ["ACME_MC_EtCO2Tgt",38],
    ["ACME_MC_Temp",37]
];

// Save whatever AED target this client had before the panel and temporarily make Kelly the monitor target.
// The LifePak generators intentionally read this target when resolving custom rhythms and their exact beat clock.
uiNamespace setVariable ["ACME_MC_previousAEDTarget", missionNamespace getVariable ["ACM_circulation_AED_Monitor_Target", objNull]];
[[["aedMonitorTarget", _dummy]]] call ACM_circulation_fnc_setLocalUiState;

// The shared palette (ui_theme.hpp roles as SQF colours), read by ACME_fnc_megacodeMenu too.
private _theme = createHashMapFromArray [
    ["panel",     [0.067,0.071,0.078,0.985]],
    ["surface",   [0.094,0.098,0.110,1]],
    ["well",      [0.050,0.053,0.059,1]],
    ["rule",      [0.161,0.169,0.188,1]],
    ["hover",     [0.125,0.129,0.145,1]],
    ["active",    [0.188,0.196,0.224,1]],
    ["ink",       [0.953,0.945,0.929,1]],
    ["secondary", [0.796,0.816,0.855,1]],
    ["muted",     [0.659,0.659,0.659,1]],
    ["darkInk",   [0.067,0.071,0.078,1]],
    ["selected",  [0.796,0.816,0.855,1]],
    ["danger",    [0.380,0.125,0.125,1]],
    ["dangerInk", [1,0.78,0.76,1]]
];
uiNamespace setVariable ["ACME_MC_theme", _theme];

// One fit-inside geometry. ACME_fnc_uiCanvas keeps ultrawide authored at 16:9; the aspect gives way between 1.61
// and 1.25 so a 4:3 or 16:10 screen gets a narrower panel at full height instead of a smaller one.
private _canvas = call ACME_fnc_uiCanvas;
_canvas params ["_canvasX", "_canvasY", "_canvasW", "_canvasH"];
private _maxW = _canvasW * 0.96;
private _maxH = _canvasH * 0.90;
private _aspect = ((_maxW / (_maxH max 0.001)) max 1.25) min 1.61;
private _panelW = _maxW min (_maxH * _aspect);
private _panelH = _panelW / _aspect;
private _panelX = _canvasX + ((_canvasW - _panelW) / 2);
private _panelY = _canvasY + ((_canvasH - _panelH) / 2);

private _padX = _panelW * 0.012;
private _padY = _panelH * 0.016;
private _titleH = _panelH * 0.070;
private _monitorTop = _panelY + _titleH + _padY;
private _monitorH = _panelH * 0.440;
private _laneH = _monitorH / 4;
private _fieldX = _panelX + _padX;
private _fieldW = _panelW * 0.630;
private _waveX = _fieldX + (_panelW * 0.050);           // room on the left for the lane names
private _waveW = (_fieldX + _fieldW) - _waveX - (_panelW * 0.008);
private _vitalX = _fieldX + _fieldW + (_panelW * 0.008);
private _vitalW = (_panelX + _panelW - _padX) - _vitalX;
private _navY = _monitorTop + _monitorH + (_panelH * 0.022);
private _navH = _panelH * 0.058;
private _pageX = _panelX + _padX;
private _pageY = _navY + _navH + (_panelH * 0.012);
private _pageW = _panelW - (2 * _padX);
private _pageH = (_panelY + _panelH - _padY) - _pageY;
// the page's working area, inset inside its surface.
private _contentX = _pageX + (_panelW * 0.010);
private _contentY = _pageY + (_panelH * 0.014);
private _contentW = _pageW - (_panelW * 0.020);
private _contentH = _pageH - (_panelH * 0.024);
uiNamespace setVariable ["ACME_MC_geometry", [_panelX,_panelY,_panelW,_panelH,_contentX,_contentY,_contentW,_contentH,_waveX,_waveW,_monitorTop,_laneH,_vitalX,_vitalW,_navY,_navH]];

private _all = [];
private _mkText = {
    params ["_display","_all","_pos","_text",["_fg",[1,1,1,1]],["_bg",[0,0,0,0]],["_size",0.025],["_font",ACM_UI_FONT]];
    private _c = _display ctrlCreate ["RscText", -1];
    _c ctrlSetPosition _pos;
    _c ctrlSetText _text;
    _c ctrlSetTextColor _fg;
    _c ctrlSetBackgroundColor _bg;
    _c ctrlSetFont _font;
    _c ctrlSetFontHeight _size;
    _c ctrlCommit 0;
    _all pushBack _c;
    _c
};
private _mkStructured = {
    params ["_display","_all","_pos",["_size",0.025]];
    private _c = _display ctrlCreate ["RscStructuredText", -1];
    _c ctrlSetPosition _pos;
    _c ctrlSetBackgroundColor [0,0,0,0];
    _c ctrlSetFontHeight _size;
    _c ctrlCommit 0;
    _all pushBack _c;
    _c
};
private _rule = _theme get "rule";
private _muted = _theme get "muted";

// Frame, title bar and its rule.
[_display,_all,[_panelX,_panelY,_panelW,_panelH],"",[1,1,1,1],_theme get "panel"] call _mkText;
[_display,_all,[_panelX,_panelY,_panelW,_titleH],"",[1,1,1,1],_theme get "surface"] call _mkText;
[_display,_all,[_panelX,_panelY+_titleH-(_panelH*0.002),_panelW,_panelH*0.002],"",[1,1,1,1],_rule] call _mkText;
[_display,_all,[_panelX+_padX,_panelY,_panelW*0.20,_titleH],"MEGACODE KELLY",_theme get "ink",[0,0,0,0],_panelH*0.034,"RobotoCondensedBold"] call _mkText;
[_display,_all,[_panelX+_padX+(_panelW*0.155),_panelY,_panelW*0.20,_titleH],"Instructor control panel",_muted,[0,0,0,0],_panelH*0.026] call _mkText;
private _status = [_display,_all,[_panelX+(_panelW*0.40),_panelY+(_titleH*0.24),_panelW*0.60-_padX,_titleH*0.62],_panelH*0.025] call _mkStructured;
uiNamespace setVariable ["ACME_MC_statusCtrl", _status];

// Monitor: black wave field and the numbers column.
[_display,_all,[_fieldX,_monitorTop,_fieldW,_monitorH],"",[1,1,1,1],[0,0,0,1]] call _mkText;
[_display,_all,[_vitalX,_monitorTop,_vitalW,_monitorH],"",[1,1,1,1],_theme get "well"] call _mkText;
// Page surface.
[_display,_all,[_pageX,_pageY,_pageW,_pageH],"",[1,1,1,1],_theme get "surface"] call _mkText;

// Tab bar: the seven pages, then RESET and CLOSE apart on the right.
private _nav = [
    ["VITALS","vitals",{[87300,"vitals"] call ACME_fnc_megacodeMenu;},"Heart rate, SpO2, blood pressure, respiration, EtCO2, temperature and a forced shock state"],
    ["RHYTHM","rhythm",{[87300,"rhythm"] call ACME_fnc_megacodeMenu;},"Cardiac rhythm, perfusing or pulseless"],
    ["AIRWAY","airway",{[87300,"airway"] call ACME_fnc_megacodeMenu;},"Airway obstruction, apnea and chest injuries"],
    ["WOUNDS","wounds",{[87300,"wounds"] call ACME_fnc_megacodeMenu;},"Add wounds to a body region, junctional bleeds, clear all"],
    ["NEURO","neuro",{[87300,"neuro"] call ACME_fnc_megacodeMenu;},"ICP, GCS, herniation and consciousness"],
    ["SCENARIO","scenario",{[87300,"scenario"] call ACME_fnc_megacodeMenu;},"Run an evolving scenario that deteriorates toward arrest"],
    ["LOG","log",{[87300,"log"] call ACME_fnc_megacodeMenu;},"Everything applied to the manikin, newest first"],
    ["RESET","reset",{call ACME_fnc_megacodeReset;},"Reset the manikin to a clean, healthy baseline"],
    ["CLOSE","done",{closeDialog 0;},"Close the control panel"]
];
private _gap = _panelW * 0.004;
private _groupGap = _panelW * 0.030;
private _navW = _panelW - (2 * _padX);
private _btnW = (_navW - _groupGap - (_gap * ((count _nav) - 2))) / (count _nav);
private _navCtrls = [];
{
    _x params ["_label","_key","_eh","_tip"];
    private _bx = _pageX + (_forEachIndex * (_btnW + _gap)) + (if (_forEachIndex >= 7) then {_groupGap - _gap} else {0});
    private _b = _display ctrlCreate ["ACME_ThemeButton", -1];
    _b ctrlSetPosition [_bx, _navY, _btnW, _navH];
    _b ctrlSetText _label;
    _b ctrlSetTooltip _tip;
    _b ctrlSetFont "RobotoCondensedBold";
    _b ctrlSetFontHeight (_panelH * 0.027);
    _b setVariable ["ACME_MC_pageKey", _key];
    _b ctrlAddEventHandler ["ButtonClick", _eh];
    _b ctrlCommit 0;
    _all pushBack _b;
    _navCtrls pushBack _b;
} forEach _nav;
uiNamespace setVariable ["ACME_MC_navCtrls", _navCtrls];

// Four monitor lanes. ECG/pleth/capno use the AED's native 176 samples. ABP is retained as Kelly-only because
// ACM's LifePak has no invasive arterial-pressure waveform generator.
private _colors = [
    [0.30,0.95,0.40,1],
    [0.35,0.78,1,1],
    [1,0.40,0.40,1],
    [1,0.80,0.30,1]
];
private _labels = ["II","PLETH","ABP","CO2"];
private _sampleCount = 351; // two 176-sample windows share the middle sample -> 350 drawable segments
private _sampleW = _waveW / (_sampleCount - 1);
private _trace = [];
private _laneCenters = [];
for "_lane" from 0 to 3 do {
    private _top = _monitorTop + (_lane * _laneH);
    private _cy = _top + (_laneH * 0.50);
    _laneCenters pushBack _cy;
    if (_lane > 0) then {
        // lane divider across the wave field and the numbers column.
        [_display,_all,[_fieldX,_top,_fieldW,_panelH*0.0015],"",[1,1,1,1],[0.16,0.17,0.19,0.85]] call _mkText;
        [_display,_all,[_vitalX,_top,_vitalW,_panelH*0.0015],"",[1,1,1,1],_rule] call _mkText;
    };
    [_display,_all,[_fieldX+(_panelW*0.004),_top+(_laneH*0.06),_panelW*0.046,_laneH*0.26],_labels select _lane,_colors select _lane,[0,0,0,0],_panelH*0.024,"RobotoCondensedBold"] call _mkText;
    // faint lane baseline
    [_display,_all,[_waveX,_cy,_waveW,_panelH*0.0012],"",[1,1,1,1],[0.18,0.22,0.26,0.30]] call _mkText;
    private _segments = [];
    private _dots = [];
    for "_i" from 0 to (_sampleCount - 2) do {
        private _line = _display ctrlCreate ["RscLine", -1];
        _line ctrlSetTextColor (_colors select _lane);
        _line ctrlSetBackgroundColor [0,0,0,0];
        _line ctrlSetPosition [_waveX+(_i*_sampleW),_cy,_sampleW,0];
        _line ctrlShow false;
        _line ctrlCommit 0;
        _all pushBack _line;
        _segments pushBack _line;

        private _dot = _display ctrlCreate ["RscText", -1];
        _dot ctrlSetBackgroundColor (_colors select _lane);
        private _d = (_panelH*0.0024) max 0.0012;
        _dot ctrlSetPosition [_waveX+(_i*_sampleW),_cy,_d,_d];
        _dot ctrlShow false;
        _dot ctrlCommit 0;
        _all pushBack _dot;
        _dots pushBack _dot;
    };
    _trace pushBack [_segments,_dots];
};
uiNamespace setVariable ["ACME_MC_traceCtrls", _trace];
uiNamespace setVariable ["ACME_MC_laneCenters", _laneCenters];
uiNamespace setVariable ["ACME_MC_waveSampleW", _sampleW];
uiNamespace setVariable ["ACME_MC_waveX", _waveX];
uiNamespace setVariable ["ACME_MC_laneH", _laneH];

// Numbers beside the lanes: the main value of each lane on the left of the column; on the ABP and CO2 lanes the
// temperature and the respiratory rate on the right. Entry: [control, colour, hex for the tick, align].
private _vitalCtrls = createHashMap;
private _mainW = _vitalW * 0.58;
private _sideX = _vitalX + _mainW;
private _sideW = _vitalW - _mainW - (_panelW * 0.006);
{
    _x params ["_key","_label","_unit","_lane","_color","_hex","_side"];
    private _top = _monitorTop + (_lane * _laneH);
    private _x0 = if (_side) then {_sideX} else {_vitalX + (_panelW * 0.008)};
    private _w0 = if (_side) then {_sideW} else {_mainW - (_panelW * 0.008)};
    private _align = if (_side) then {"right"} else {"left"};
    private _cap = [_display,_all,[_x0,_top+(_laneH*0.05),_w0,_laneH*0.26],_panelH*0.022] call _mkStructured;
    _cap ctrlSetStructuredText parseText format ["<t align='%1' font='RobotoCondensedBold' color='%2'>%3</t> <t align='%1' color='#a8a8a8'>%4</t>",_align,_hex,_label,_unit];
    private _numSize = if (_side) then {_laneH*0.36} else {_laneH*(if (_key == "BP") then {0.44} else {0.55})};
    private _num = [_display,_all,[_x0,_top+(_laneH*0.30),_w0,_laneH*0.66],_numSize] call _mkStructured;
    _vitalCtrls set [_key,[_num,_color,_hex,_align]];
} forEach [
    ["HR","HR","bpm",0,[0.30,0.95,0.40,1],"#4df266",false],
    ["SpO2","SpO2","%",1,[0.35,0.78,1,1],"#59c7ff",false],
    ["BP","NIBP","mmHg",2,[0.953,0.945,0.929,1],"#f3f1ed",false],
    ["Temp","TEMP","C",2,[0.85,0.85,0.85,1],"#d9d9d9",true],
    ["EtCO2","EtCO2","mmHg",3,[1,0.80,0.30,1],"#ffcc4d",false],
    ["RR","RR","/min",3,[0.953,0.945,0.929,1],"#f3f1ed",true]
];
uiNamespace setVariable ["ACME_MC_vitalCtrls", _vitalCtrls];

// The state a page was drawn from, per page; the tick redraws an open page when it no longer matches (a remote
// change, e.g. the server starting a scenario or a late unconsciousness, then shows without a click).
uiNamespace setVariable ["ACME_MC_pageSigFn", {
    params ["_d","_page"];
    switch (_page) do {
        case "vitals": {[_d getVariable ["ACME_shock_forced",[]]]};
        case "rhythm": {[_d getVariable ["ACME_MC_rhythmKey",_d getVariable ["ACME_MC_rhythm","sinus"]]]};
        case "airway": {[_d getVariable ["ACME_MC_airway","patent"]]};
        case "neuro": {[_d getVariable ["ACE_isUnconscious",false],_d getVariable ["ACME_MC_herniation",false]]};
        case "scenario": {[_d getVariable ["ACME_MC_scenActive",false],_d getVariable ["ACME_MC_scenName",""]]};
        default {[]};
    }
}];

// AED-compatible clock and buffer state. The generator itself owns morphology; Kelly only owns this consumer's
// sweep position and beat epoch so opening the instructor panel does not require physical LifePak pads.
[_dummy, [["aedUpdateStep", 1]], false] call ACM_circulation_fnc_setRuntimeState;
_dummy setVariable ["ACME_AED_MonitorCursorTime",CBA_missionTime,false];
private _initialRate = [_dummy] call ACM_circulation_fnc_updateEKGHeartRate;
private _rr0 = if (_initialRate > 0) then {60/_initialRate} else {0.75};
[_dummy, [["aedPadsLastBeep", CBA_missionTime]], false] call ACM_circulation_fnc_setRuntimeState;
_dummy setVariable ["ACME_AED_PreviousRR",_rr0,false];
_dummy setVariable ["ACME_AED_NextRR",_rr0,false];
_dummy setVariable ["ACME_AED_BeatSerial",0,false];
_dummy setVariable ["ACME_AED_ClockRhythm",-999,false];
uiNamespace setVariable ["ACME_MC_waveBuffers",[[],[],[],[]]];
uiNamespace setVariable ["ACME_MC_sampleCount",_sampleCount];
uiNamespace setVariable ["ACME_MC_waveSig",""];
uiNamespace setVariable ["ACME_MC_step",1];
uiNamespace setVariable ["ACME_MC_stepAcc",0];
uiNamespace setVariable ["ACME_MC_lastT",diag_tickTime];
uiNamespace setVariable ["ACME_MC_sigCheckT",0];
uiNamespace setVariable ["ACME_MC_dynamicCtrls",_all];

private _oldPFH = uiNamespace getVariable ["ACME_MC_tickPFH",-1];
if (_oldPFH >= 0) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};
private _pfh = [{call ACME_fnc_megacodePanelTick},0.03,[]] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_MC_tickPFH",_pfh];
uiNamespace setVariable ["ACME_MC_page","vitals"];
[87300,"vitals"] call ACME_fnc_megacodeMenu;

if (call ACME_fnc_debugEnabled) then {diag_log format ["[ACME][Megacode] Panel opened: canvas=%1 panel=[%2,%3,%4,%5] aspect=%6 samples=176",_canvas,_panelX,_panelY,_panelW,_panelH,_panelW/(_panelH max 0.001)];};
