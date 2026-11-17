/*
 * Megacode Kelly instructor panel onLoad.
 *
 * B117 Megacode audit:
 * - build the complete visible panel at runtime so legacy config geometry cannot clip on 4:3 / 5:4 / 16:10;
 * - fit the authored 1.61:1 panel inside BOTH the aspect-safe canvas width and height;
 * - use the LifePak/AED 176-sample monitor contract for ECG, pleth and capnography;
 * - create AED-style line + dot trace controls instead of the old 400-column independent renderer;
 * - keep one explicit control registry so unload can tear every dynamic control down cleanly.
 * B123: present two consecutive 176-sample LifePak windows (~10.5 s total) across 350 drawable segments.
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

// One fit-inside geometry calculation. ACME_fnc_uiCanvas keeps ultrawide authored at 16:9; this additional
// width clamp is what fixes narrower displays, where the old height-only width calculation ran off-screen.
private _canvas = call ACME_fnc_uiCanvas;
_canvas params ["_canvasX", "_canvasY", "_canvasW", "_canvasH"];
private _aspect = 1.61;
private _maxW = _canvasW * 0.96;
private _maxH = _canvasH * 0.90;
private _panelW = _maxW min (_maxH * _aspect);
private _panelH = _panelW / _aspect;
private _panelX = _canvasX + ((_canvasW - _panelW) / 2);
private _panelY = _canvasY + ((_canvasH - _panelH) / 2);

private _padX = _panelW * 0.012;
private _padY = _panelH * 0.012;
private _titleH = _panelH * 0.052;
private _monitorTop = _panelY + _titleH + _padY;
private _monitorH = _panelH * 0.485;
private _waveX = _panelX + _padX + (_panelW * 0.020);
private _waveW = _panelW * 0.590;
private _vitalX = _panelX + (_panelW * 0.635);
private _vitalW = (_panelX + _panelW - _padX) - _vitalX;
private _laneH = _monitorH / 4;
private _navH = _panelH * 0.052;
private _navY = _panelY + (_panelH * 0.600);
private _contentX = _panelX + _padX;
private _contentY = _navY + _navH + (_panelH * 0.012);
private _contentW = _panelW - (2 * _padX);
private _contentH = (_panelY + _panelH - _padY) - _contentY;
uiNamespace setVariable ["ACME_MC_geometry", [_panelX,_panelY,_panelW,_panelH,_contentX,_contentY,_contentW,_contentH,_waveX,_waveW,_monitorTop,_laneH,_vitalX,_vitalW,_navY,_navH]];

private _all = [];
private _mkText = {
    params ["_display","_all","_pos","_text",["_fg",[1,1,1,1]],["_bg",[0,0,0,0]],["_style",0],["_size",0.025],["_font","RobotoCondensed"]];
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

// Opaque runtime frame deliberately covers the legacy static config panel/buttons. The config remains a safe
// fallback that creates the dialog; all visible/interactive geometry is owned here and therefore scales uniformly.
[_display,_all,[_panelX,_panelY,_panelW,_panelH],"",[1,1,1,1],[0.015,0.022,0.032,0.985],0,_panelH*0.025] call _mkText;
[_display,_all,[_panelX,_panelY,_panelW*0.64,_titleH],"  MEGACODE KELLY   //   INSTRUCTOR CONTROL PANEL",[0.50,0.85,1,1],[0.055,0.085,0.12,1],0,_panelH*0.030,"PuristaBold"] call _mkText;
[_display,_all,[_panelX+_padX,_monitorTop,_waveW+(_panelW*0.025),_monitorH],"",[1,1,1,1],[0,0,0,1],0,_panelH*0.02] call _mkText;
[_display,_all,[_vitalX,_monitorTop,_vitalW,_monitorH],"",[1,1,1,1],[0.012,0.020,0.030,1],0,_panelH*0.02] call _mkText;
[_display,_all,[_contentX,_contentY,_contentW,_contentH],"",[1,1,1,1],[0.035,0.048,0.067,0.98],0,_panelH*0.02] call _mkText;

// Navigation row. Runtime-created buttons supersede the legacy config buttons, which remain covered underneath.
private _nav = [
    ["VITALS","vitals",{[87300,"vitals"] call ACME_fnc_megacodeMenu;}],
    ["RHYTHM","rhythm",{[87300,"rhythm"] call ACME_fnc_megacodeMenu;}],
    ["AIRWAY","airway",{[87300,"airway"] call ACME_fnc_megacodeMenu;}],
    ["WOUNDS","wounds",{[87300,"wounds"] call ACME_fnc_megacodeMenu;}],
    ["NEURO/+","neuro",{[87300,"neuro"] call ACME_fnc_megacodeMenu;}],
    ["SCENARIO","scenario",{[87300,"scenario"] call ACME_fnc_megacodeMenu;}],
    ["LOG","log",{[87300,"log"] call ACME_fnc_megacodeMenu;}],
    ["RESET","reset",{call ACME_fnc_megacodeReset;}],
    ["DONE","done",{closeDialog 0;}]
];
private _gap = _panelW * 0.0035;
private _btnW = (_contentW - (_gap * ((count _nav)-1))) / (count _nav);
private _navCtrls = [];
{
    _x params ["_label","_key","_eh"];
    private _b = _display ctrlCreate ["ACME_ThemeButton", -1];
    _b ctrlSetPosition [_contentX + (_forEachIndex * (_btnW + _gap)), _navY, _btnW, _navH];
    _b ctrlSetText _label;
    _b ctrlSetTextColor [0.92,0.95,1,1];
    _b ctrlSetBackgroundColor (switch (_key) do {case "scenario":{[0.20,0.12,0.28,1]}; case "log":{[0.10,0.20,0.16,1]}; case "reset":{[0.35,0.20,0.10,1]}; case "done":{[0.30,0.10,0.12,1]}; default {[0.10,0.13,0.18,1]};});
    _b ctrlSetFont "PuristaBold";
    _b ctrlSetFontHeight (_navH * 0.45);
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
    [0,1,0,1],
    [0,0.6,1,1],
    [1,0.32,0.32,1],
    [1,0.5,0.2,1]
];
private _labels = ["II","Pleth","ABP","CO2"];
private _sampleCount = 351; // two 176-sample windows share the middle sample -> 350 drawable segments
private _sampleW = _waveW / (_sampleCount - 1);
private _trace = [];
private _laneCenters = [];
for "_lane" from 0 to 3 do {
    private _top = _monitorTop + (_lane * _laneH);
    private _cy = _top + (_laneH * 0.50);
    _laneCenters pushBack _cy;
    [_display,_all,[_panelX+_padX,_top+(_laneH*0.04),_panelW*0.052,_laneH*0.24],_labels select _lane,_colors select _lane,[0,0,0,0],0,_laneH*0.20,"PuristaBold"] call _mkText;
    // faint lane baseline
    [_display,_all,[_waveX,_cy,_waveW,_panelH*0.0012],"",[1,1,1,1],[0.18,0.22,0.26,0.45],0,_laneH*0.1] call _mkText;
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

// Numeric monitor fields aligned to the four lanes.
private _vitalCtrls = createHashMap;
private _vitalDefs = [
    ["HR","HR",[0,1,0,1],"bpm",0],
    ["SpO2","SpO2",[0,0.6,1,1],"%",1],
    ["BP","NIBP",[1,1,1,1],"mmHg",2],
    ["EtCO2","EtCO2",[1,0.5,0.2,1],"mmHg",3]
];
{
    _x params ["_key","_label","_color","_unit","_lane"];
    private _cy = _laneCenters select _lane;
    [_display,_all,[_vitalX,_cy-(_laneH*0.41),_vitalW,_laneH*0.24],format ["%1  %2",_label,_unit],_color,[0,0,0,0],0,_laneH*0.18,"PuristaBold"] call _mkText;
    private _num = _display ctrlCreate ["RscStructuredText", -1];
    _num ctrlSetPosition [_vitalX,_cy-(_laneH*0.15),_vitalW,_laneH*0.54];
    _num ctrlSetFontHeight (_laneH * (if (_key == "BP") then {0.35} else {0.43}));
    _num ctrlCommit 0;
    _all pushBack _num;
    _vitalCtrls set [_key,[_num,_color]];
} forEach _vitalDefs;

private _secondaryY = _panelY + (_titleH*0.06);
{
    _x params ["_key","_label","_color","_unit","_idx"];
    private _x0 = _panelX + (_panelW*0.66) + (_idx * (_panelW*0.165));
    [_display,_all,[_x0,_secondaryY,_panelW*0.16,_titleH*0.34],format ["%1  %2",_label,_unit],_color,[0,0,0,0],0,_titleH*0.26,"PuristaBold"] call _mkText;
    private _num = _display ctrlCreate ["RscStructuredText", -1];
    _num ctrlSetPosition [_x0,_secondaryY+(_titleH*0.30),_panelW*0.16,_titleH*0.62];
    _num ctrlSetFontHeight (_titleH*0.42);
    _num ctrlCommit 0;
    _all pushBack _num;
    _vitalCtrls set [_key,[_num,_color]];
} forEach [
    ["RR","RR",[1,1,1,1],"/min",0],
    ["Temp","Temp",[1,0.70,0.30,1],"C",1]
];
uiNamespace setVariable ["ACME_MC_vitalCtrls", _vitalCtrls];

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
uiNamespace setVariable ["ACME_MC_dynamicCtrls",_all];

private _oldPFH = uiNamespace getVariable ["ACME_MC_tickPFH",-1];
if (_oldPFH >= 0) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};
private _pfh = [{call ACME_fnc_megacodePanelTick},0.03,[]] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_MC_tickPFH",_pfh];
uiNamespace setVariable ["ACME_MC_page","vitals"];
[87300,"vitals"] call ACME_fnc_megacodeMenu;

diag_log format ["[ACME][Megacode] Panel opened: canvas=%1 panel=[%2,%3,%4,%5] aspect=%6 samples=176",_canvas,_panelX,_panelY,_panelW,_panelH,_panelW/(_panelH max 0.001)];
